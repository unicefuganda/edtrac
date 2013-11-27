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
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials'):
        locations = Location.objects.filter(type__in=['district', 'sub_county'])
    else:
        locations = [profile.location]

    # No post Data
    if req.method != 'POST':
        periods = get_week_date(depth=2)
        location_data = []
        context_vars = {}
        current_week = periods[0]
        previous_week = periods[1]

        enrolled = get_numeric_data_all_locations(poll_enroll, term_range)
        #current week
        attendance_current_week = get_numeric_data_all_locations(poll_attendance, current_week)
        #previous week
        attendance_previous_week = get_numeric_data_all_locations(poll_attendance, previous_week)

        for location in locations:
            location_enrolled = 0
            location_attendance_current_week = 0
            location_attendance_previous_week = 0
            if location.id in enrolled:
                location_enrolled = enrolled[location.id]
            if location.id in attendance_current_week:
                location_attendance_current_week = attendance_current_week[location.id]
            if location.id in attendance_previous_week:
                location_attendance_previous_week = attendance_previous_week[location.id]

            percent_current_week = round(compute_absent_values(location_attendance_current_week, location_enrolled), 2)
            percent_previous_week = round(compute_absent_values(location_attendance_previous_week, location_enrolled), 2)

            if location.type_id == 'sub_county' and location_enrolled > 0:
                location_data.append(
                    [location, percent_current_week, percent_previous_week, location_enrolled, location_attendance_current_week,
                     location_attendance_previous_week])
            elif location.type_id == 'district':
                location_data.append(
                    [location, percent_current_week, percent_previous_week, location_enrolled, location_attendance_current_week,
                     location_attendance_previous_week])
    else:
        time_range_form = ResultForm(data=req.POST)
        to_ret = []
        if time_range_form.is_valid():
            from_date = time_range_form.cleaned_data['from_date']
            to_date = time_range_form.cleaned_data['to_date']
            month_delta = abs(from_date.month - to_date.month)
            periods = []

            if month_delta <= 2: # same month get days in between
                month_flag = False # don't split data in months
                while from_date <= to_date:
                    if from_date.weekday() == 3: #is to_day a Thursday?
                        periods.append(previous_calendar_week(t=from_date)) # get range from Wed to Thur.
                    from_date += datetime.timedelta(days=1)
            else:
                month_flag = True # split data in months
                while from_date <= to_date:
                    periods.append([dateutils.month_start(from_date),
                                       dateutils.month_end(dateutils.increment(from_date, months=1))])
                    next_date = dateutils.increment(from_date, months=1)
                    delta = next_date - from_date
                    from_date += datetime.timedelta(days=abs(delta.days))

            all_locations_periodic_absenteeism = {}
            for period in periods:
                enrolled = get_numeric_data_all_locations(poll_enroll, term_range)
                attendance = get_numeric_data_all_locations(poll_attendance, period)

                for location in locations:
                    location_enrolled = 0
                    location_attendance = 0
                    if location.id in enrolled:
                        location_enrolled = enrolled[location.id]
                    if location.id in attendance:
                        location_attendance = attendance[location.id]

                    location_periodic_absenteeism_value = round(compute_absent_values(location_attendance, location_enrolled), 2)
                    if location.id not in all_locations_periodic_absenteeism:
                        all_locations_periodic_absenteeism[location.id] = {'location': location, 'periodic_absenteeism':[]}
                    all_locations_periodic_absenteeism[location.id]['periodic_absenteeism'].append(location_periodic_absenteeism_value)

            for location_id, location_periodic_absenteeism in all_locations_periodic_absenteeism.iteritems():
                to_ret.append([location_periodic_absenteeism['location'], location_periodic_absenteeism['periodic_absenteeism']])

            return render_to_response(template_name, {'form': time_range_form, 'dataset': to_ret,
                                                          'title': title, 'month_flag': month_flag,
                                                          'url_name': url_name_district,
                                                          'date_batch': periods}, RequestContext(req))

    context_vars.update({'location_data': location_data})
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials'):
        x = {'url_name': url_name_district,
             'headings': ['District', 'Data', 'Current week', 'Previous week']}
    else:
        x = {'url_name': url_name_school,
             'headings': ['School', 'Current week', 'Previous week']}
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
        enrollment = sum(get_numeric_data_by_school(poll_enroll, [school], term_range))
        attendance_current_week = sum(get_numeric_data_by_school(poll_attendance, [school], current_week))
        attendance_previous_week = sum(get_numeric_data_by_school(poll_attendance, [school], previous_week))
        # percent computation
        percent_current_week = round(compute_absent_values(attendance_current_week, enrollment), 2)
        percent_previous_week = round(compute_absent_values(attendance_previous_week, enrollment), 2)

        if enrollment > 0:
            existing_data.append(
                [school, percent_current_week, percent_previous_week, enrollment, attendance_current_week,
                 attendance_previous_week])
        school_data.append(
            [school, percent_current_week, percent_previous_week, enrollment, attendance_current_week,
             attendance_previous_week])

    return school_data, existing_data


@login_required
def report_dashboard(request):
    try:
        report_mode = request.GET['report_mode']
    except:
        report_mode = 'average'
    context = {}
    context['report_mode'] = report_mode

    profile = request.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        return render_to_response('education/admin/detail_report.html',context, RequestContext(request))
    else:
        location = [profile.location]
        context['report_mode'] = report_mode
        context['district'] = location[0].name
        return render_to_response('education/admin/detail_report_district.html',context, RequestContext(request))



@login_required
def report_district_dashboard(request):
    try:
        report_mode = request.GET['report_mode']
        district = request.GET['district']
    except:
        report_mode = 'average'

    context = {}
    context['report_mode'] = report_mode
    context['district'] = district
    return render_to_response('education/admin/detail_report_district.html',context, RequestContext(request))



@login_required
def term_dashboard(request):
    try:
        report_mode = request.GET['report_mode']
    except:
        report_mode = 'average'
    context = {}
    context['report_mode'] = report_mode
    return render_to_response('education/admin/detail_term_report.html',context, RequestContext(request))


@login_required
def time_range_dashboard(request):
    context = {}
    context['start_date'] = request.GET['start_date']
    context['end_date'] = request.GET['end_date']
    context['indicator'] = request.GET['indicator']
    context['report_mode'] = request.GET['report_mode']
    return render_to_response('education/admin/detail_timefilter_report.html', context, RequestContext(request))


#   Reporting API
@login_required
def dash_report_api(request):
    try:
        report_mode = request.GET['report_mode']
    except :
        report_mode = 'average'

    report_mode_log = report_mode

    jsonDataSource = []
    config_list = get_polls_for_keyword('all')
    time_range = get_week_date(depth=4)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in time_range]
    time_range.reverse()
    profile = request.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        locations = Location.objects.filter(type__in=['district'])
    else:
        locations = [profile.location]

    collective_result, chart_data, school_percent, tooltips, report_mode = get_aggregated_report_data(locations, time_range,
                                                                                         config_list,report_mode)
    jsonDataSource.append(
        {'results': collective_result, 'chartData': chart_data, 'school_percent': school_percent, 'weeks': weeks,
         'toolTips': tooltips,'report_mode' : report_mode, 'logger' :report_mode_log})
    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')

@login_required
def dash_report_district(request):
    try:
        report_mode = request.GET['report_mode']
        district = request.GET['district']
    except :
        report_mode = 'average'

    jsonDataSource = []
    config_list = get_polls_for_keyword('all')
    time_range = get_week_date(depth=4)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in time_range]
    time_range.reverse()
    location = Location.objects.filter(type__in=['district'],name__in=[district])

    collective_result, chart_data, school_percent, tooltips, report_mode = get_aggregated_report_for_district(location, time_range,config_list,report_mode)
    jsonDataSource.append(
        {'results': collective_result, 'chartData': chart_data, 'school_percent': school_percent, 'weeks': weeks,
         'toolTips': tooltips,'report_mode' : report_mode})
    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')


@login_required
def dash_report_term(request):

    try:
        report_mode = request.GET['report_mode']
    except:
        report_mode = 'average'

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
        locations = Location.objects.filter(type__in=['district'])
    else:
        locations = [profile.location]

    collective_result, chart_data, school_percent, tooltips,report_mode = get_aggregated_report_data(locations, time_range,
                                                                                         config_list,report_mode)
    jsonDataSource.append(
        {'results': collective_result, 'chartData': chart_data, 'school_percent': school_percent, 'weeks': weeks,
         'toolTips': tooltips, 'report_mode' : report_mode})

    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')


@login_required
def dash_report_params(request):
    jsonDataSource = []
    time_depth = 4
    start_date = parser.parse(request.GET['start_date'])
    end_date = parser.parse(request.GET['end_date'])
    indicator = request.GET['indicator']
    report_mode = request.GET['report_mode']
    time_range = get_date_range(start_date, end_date, time_depth)
    config_list = get_polls_for_keyword(indicator)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in time_range]
    time_range.reverse()
    profile = request.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials'):
        locations = Location.objects.filter(type__in=['district'])
    else:
        locations = [profile.location]

    if indicator =='all':
        collective_result, chart_data, school_percent, tooltips, report_mode = get_aggregated_report_data(locations, time_range,config_list,report_mode)
        jsonDataSource.append(
        {'results': collective_result, 'chartData': chart_data, 'school_percent': school_percent, 'weeks': weeks,
         'toolTips': tooltips, 'report_mode':report_mode})
    else:
        collective_result, chart_data, school_percent, tooltips,report_mode = get_aggregated_report_data_single_indicator(locations, time_range,config_list,report_mode)
        jsonDataSource.append(
        {'results': collective_result, 'chartData': chart_data, 'school_percent': school_percent, 'weeks': weeks,
         'toolTips': tooltips})

    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')





