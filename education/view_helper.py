from __future__ import division
import datetime
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from .forms import *
from .models import *
from uganda_common.utils import *
from rapidsms.contrib.locations.models import Location
from poll.models import Poll, ResponseCategory
from .reports import *
from education.absenteeism_view_helper import *
from django.utils import simplejson
from dateutil import parser
from education.view_helper_utils import *


# home page dashboard view generator
def view_stats(req,
               enrol_deploy_poll=None,
               attendance_poll=None,
               title=None,
               url_name_district=None,
               url_name_school='school-detail',
               template_name='education/timeslider_base.html'):
    location_data = []
    time_range_form = ResultForm()
    context_vars = {}
    poll_enroll = Poll.objects.get(name=enrol_deploy_poll)
    poll_attendance = Poll.objects.get(name=attendance_poll)
    real_data = []
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials'):
        locations = Location.objects.filter(type__in=['district', 'sub_county'])
    else:
        locations = [profile.location]

    # No post Data
    if req.method != 'POST':
        date_weeks = get_week_date(depth=2)
        location_data = []
        context_vars = {}
        current_week = date_weeks[0]
        previous_week = date_weeks[1]

        for location in locations:
            enrolled = sum(get_numeric_data([poll_enroll], [location], term_range))
            #current week
            attendance_current_week = sum(get_numeric_data([poll_attendance], [location], current_week))
            percent_current_week = round(compute_absent_values(attendance_current_week, enrolled), 2)
            #previous week
            attendance_previous_week = sum(get_numeric_data([poll_attendance], [location], previous_week))
            percent_previous_week = round(compute_absent_values(attendance_previous_week, enrolled), 2)

            try:
                diff = (percent_current_week - percent_previous_week)
            except (TypeError, IndexError):
                diff = '--'

            if enrolled > 0:
                real_data.append([location, percent_current_week, percent_previous_week, diff, enrolled])

            if location.type_id == 'sub_county' and enrolled > 0:
                location_data.append(
                    [location, percent_current_week, percent_previous_week, diff, enrolled, attendance_current_week,
                     attendance_previous_week])
            elif location.type_id == 'district':
                location_data.append(
                    [location, percent_current_week, percent_previous_week, diff, enrolled, attendance_current_week,
                     attendance_previous_week])
    else:
        time_range_form = ResultForm(data=req.POST)
        to_ret = []
        if time_range_form.is_valid():
            from_date = time_range_form.cleaned_data['from_date']
            to_date = time_range_form.cleaned_data['to_date']
            month_delta = abs(from_date.month - to_date.month)
            date_weeks = []
            month_flag = None
            if month_delta <= 2: # same month get days in between
                month_flag = False # don't split data in months
                while from_date <= to_date:
                    if from_date.weekday() == 3: #is to_day a Thursday?
                        date_weeks.append(previous_calendar_week(t=from_date)) # get range from Wed to Thur.
                    from_date += datetime.timedelta(days=1)
            else:
                month_flag = True # split data in months
                while from_date <= to_date:
                    date_weeks.append([dateutils.month_start(from_date),
                                       dateutils.month_end(dateutils.increment(from_date, months=1))])
                    next_date = dateutils.increment(from_date, months=1)
                    delta = next_date - from_date
                    from_date += datetime.timedelta(days=abs(delta.days))

                schools_temp = School.objects.filter(
                    pk__in=EnrolledDeployedQuestionsAnswered.objects.select_related().values_list('school__pk',
                                                                                                  flat=True))
                for location in locations:
                    temp = []
                    location_schools = schools_temp.select_related().filter(location=location) # store in memory
                    for d in date_weeks:
                        total_attendance = 0 # per school
                        total_enrollment = 0 # per school
                        for school in location_schools:
                            enrolled = sum(get_numeric_data_by_school([poll_enroll], [school], term_range))
                            attendance = 0
                            if enrolled > 0:
                                if month_flag:
                                    attendance = sum(get_numeric_data_by_school([poll_attendance], [school], d))
                                else:
                                    attendance = sum(get_numeric_data_by_school([poll_attendance], [school], d))
                            total_attendance += attendance
                            total_enrollment += enrolled

                        percent = compute_absent_values(total_attendance, total_enrollment)
                        temp.append(percent)
                    to_ret.append([location, temp])

                return render_to_response(template_name, {'form': time_range_form, 'dataset': to_ret,
                                                          'title': title, 'month_flag': month_flag,
                                                          'url_name': url_name_district,
                                                          'date_batch': date_weeks}, RequestContext(req))

    context_vars.update({'location_data': location_data})
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials'):
        x = {'url_name': url_name_district,
             'headings': ['District', 'Data', 'Current week', 'Previous week', 'Percentage difference']}
    else:
        x = {'url_name': url_name_school,
             'headings': ['School', 'Current week', 'Previous week', 'Percentage difference']}
    if context_vars.has_key('form') == False and context_vars.has_key('title') == False:
        context_vars.update({'form': time_range_form, 'title': title}) # add the keys to context_vars dict

    context_vars.update(x)

    return render_to_response(template_name, context_vars, RequestContext(req))


def view_stats_by_school(location_id, enrollment_poll_name, attendance_poll_name):
    #locale = Location.objects.exclude(type="country").filter(type__in=['district','sub_county'])
    locale = Location.objects.get(id=location_id)
    _schools = School.objects.filter(location=locale)
    poll_enroll = Poll.objects.get(name=enrollment_poll_name)
    poll_attendance = Poll.objects.get(name=attendance_poll_name)
    date_weeks = get_week_date(depth=2)
    school_data = []
    existing_data = []
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    current_week = date_weeks[0]
    previous_week = date_weeks[1]

    for school in _schools:
        enrollment = sum(get_numeric_data_by_school([poll_enroll], [school], term_range))
        attendance_current_week = sum(get_numeric_data_by_school([poll_attendance], [school], current_week))
        attendance_previous_week = sum(get_numeric_data_by_school([poll_attendance], [school], previous_week))
        # percent computation
        percent_current_week = round(compute_absent_values(attendance_current_week, enrollment), 2)
        percent_previous_week = round(compute_absent_values(attendance_previous_week, enrollment), 2)

        try:
            diff = percent_current_week - percent_previous_week
        except (TypeError, IndexError):
            diff = '--'

        if enrollment > 0:
            existing_data.append(
                [school, percent_current_week, percent_previous_week, diff, enrollment, attendance_current_week,
                 attendance_previous_week])
        school_data.append(
            [school, percent_current_week, percent_previous_week, diff, enrollment, attendance_current_week,
             attendance_previous_week])

    return school_data, existing_data


@login_required
def report_dashboard(request, district=None):
    return render_to_response('education/admin/detail_report.html', RequestContext(request))


@login_required
def term_dashboard(request):
    return render_to_response('education/admin/detail_term_report.html', RequestContext(request))


@login_required
def time_range_dashboard(request):
    context = {}
    context['start_date'] = request.GET['start_date']
    context['end_date'] = request.GET['end_date']
    context['indicator'] = request.GET['indicator']
    return render_to_response('education/admin/detail_timefilter_report.html', context, RequestContext(request))


#   Reporting API
@login_required
def dash_report_api(request):
    jsonDataSource = []
    config_list = get_polls_for_keyword('all')
    time_range = get_week_date(depth=4)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in time_range]
    time_range.reverse()
    profile = request.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials'):
        locations = Location.objects.filter(type__in=['district', 'sub_county'])
    else:
        locations = [profile.location]

    collective_result, chart_data, school_percent, tooltips = get_aggregated_report_data(locations, time_range,
                                                                                         config_list)
    jsonDataSource.append(
        {'results': collective_result, 'chartData': chart_data, 'school_percent': school_percent, 'weeks': weeks,
         'toolTips': tooltips})
    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')


@login_required
def dash_report_term(request):
    jsonDataSource = []
    config_list = get_polls_for_keyword('all')
    time_depth = 4
    current_term_range = []
    current_term_range.append(getattr(settings, 'SCHOOL_TERM_START'))
    if getattr(settings, 'SCHOOL_TERM_END') > datetime.datetime.today():
        current_term_range.append(datetime.datetime.today())

    time_range = get_date_range(current_term_range[0], current_term_range[1], time_depth)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in time_range]
    time_range.reverse()

    profile = request.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials'):
        locations = Location.objects.filter(type__in=['district', 'sub_county'])
    else:
        locations = [profile.location]

    collective_result, chart_data, school_percent, tooltips = get_aggregated_report_data(locations, time_range,
                                                                                         config_list)
    jsonDataSource.append(
        {'results': collective_result, 'chartData': chart_data, 'school_percent': school_percent, 'weeks': weeks,
         'toolTips': tooltips})

    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')


@login_required
def dash_report_params(request):
    jsonDataSource = []
    time_depth = 4
    start_date = parser.parse(request.GET['start_date'])
    end_date = parser.parse(request.GET['end_date'])
    indicator = request.GET['indicator']
    time_range = get_date_range(start_date, end_date, time_depth)
    config_list = get_polls_for_keyword(indicator)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in time_range]
    time_range.reverse()
    profile = request.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials'):
        locations = Location.objects.filter(type__in=['district', 'sub_county'])
    else:
        locations = [profile.location]
    collective_result, chart_data, school_percent, tooltips = get_aggregated_report_data(locations, time_range,
                                                                                         config_list)
    jsonDataSource.append(
        {'results': collective_result, 'chartData': chart_data, 'school_percent': school_percent, 'weeks': weeks,
         'toolTips': tooltips})
    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')





