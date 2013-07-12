from __future__ import division
from urllib2 import urlopen
import re
import datetime
import operator
import copy
from datetime import date
import json

from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, TemplateView, ListView
from django.db.models import Q
import xlwt
from django.utils.safestring import mark_safe
from education.curriculum_progress_helper import get_target_value, get_location_for_curriculum_view, get_curriculum_data, target
from rapidsms_httprouter.models import Message
from .forms import *
from .models import *
from uganda_common.utils import *
from rapidsms.contrib.locations.models import Location
from generic.views import generic
from generic.sorters import SimpleSorter
from poll.models import Poll, ResponseCategory
from script.models import ScriptStep, Script
from .reports import *
from .utils import *
from .utils import _schedule_monthly_script, _schedule_termly_script, _schedule_weekly_scripts, _schedule_teacher_weekly_scripts
from unregister.models import Blacklist
from .utils import themes
from education.absenteeism_view_helper import *
from django.utils import simplejson


# home page dashboard view generator
def view_stats(req,
                   enrol_deploy_poll=None,
                   attendance_poll=None,
                   title=None,
                   url_name_district=None,
                   url_name_school = 'school-detail',
                   template_name='education/timeslider_base.html'):
    location_data = []
    time_range_form = ResultForm()
    context_vars = {}
    poll_enroll = Poll.objects.get(name=enrol_deploy_poll)
    poll_attendance = Poll.objects.get(name=attendance_poll)
    real_data = []
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        #locations = Location.objects.filter(type='district').filter(pk__in = EnrolledDeployedQuestionsAnswered.objects.values_list('school__location__pk',flat=True))
        locations = Location.objects.filter(type='district')
    else:
        locations = [profile.location]

    # No post Data
    if req.method != 'POST':
        date_weeks = get_week_date(depth=2)
        location_data = []
        context_vars = {}
        current_week = date_weeks[0]
        previous_week = date_weeks[1]
        diff = '--'
        term_range=[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]


        for location in locations:
            diff = '--'
            enrolled = sum(get_numeric_data_from_source_by_location(poll_enroll,location,term_range))
            #current week
            attendance_current_week = sum(get_numeric_data_from_source_by_location(poll_attendance,location,current_week))
            percent_current_week = round(compute_absent_values(attendance_current_week,enrolled),2)
            #previous week
            attendance_previous_week = sum(get_numeric_data_from_source_by_location(poll_attendance,location,previous_week))
            percent_previous_week = round(compute_absent_values(attendance_previous_week,enrolled),2)

            try:
                diff = (percent_current_week - percent_previous_week)
            except (TypeError,IndexError):
                diff = '--'

            if enrolled > 0:
                real_data.append({'Location' : location, 'Enrollment' : enrolled, 'current_week' :attendance_current_week,'prev_week' : attendance_previous_week,'diff' : diff })

            location_data.append([location,percent_current_week,percent_previous_week,diff])

    context_vars.update({'location_data':location_data})
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        x = {'url_name':url_name_district, 'headings':['District', 'Current week', 'Previous week', 'Percentage difference']}
    else:
        x = {'url_name':url_name_school, 'headings':['School', 'Current week', 'Previous week', 'Percentage difference']}
    if context_vars.has_key('form') ==False and context_vars.has_key('title') == False:
        context_vars.update({'form':time_range_form,'title':title}) # add the keys to context_vars dict

    context_vars.update(x)

    return render_to_response(template_name, context_vars, RequestContext(req))


def get_aggregated_report_data(locations,time_range,config_list):
    collective_result = {}
    chart_data = []
    head_teacher_set = []
    tmp_data = []
    school_report = []
    schools_by_location = []
    high_chart_tooltip = []

    # Get term range from settings file (config file)
    term_range=[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]

    # get data into memory to be used in this request
    dataSource = get_record_collection(locations,term_range)
    headteachersSource = EmisReporter.objects.filter(reporting_location__in=locations, groups__name="Head Teachers").exclude(schools=None).select_related()
    schoolSource = School.objects.filter(location__in=locations).select_related()
    indicator_list = ['P3 Pupils','P6 Pupils','Teachers']
    schools_total = len(schoolSource)
     # Initialize chart data and school percent List / dict holder
    for indicator in indicator_list:
        chart_data.append({ indicator : [0]*len(time_range)})
        school_report.append({ indicator : [0]*len(time_range)})
        high_chart_tooltip.append({indicator : {'present': 0, 'enrollment' : 0, 'percent' : 0}})

    chart_data.append({'Head Teachers' :[0]*len(time_range)})
    school_report.append({'Head Teachers' :[0]*len(time_range)})
    high_chart_tooltip.append({'Head Teachers' : {'present': 0, 'enrollment' : 0, 'percent' : 0}})

    for location in locations:
        absenteeism_percent = 0
        week_context = []
        config_set_result = {}
        # get school in current location
        schools_in_location = schoolSource.filter(location__in=[location])

        schools_by_location.append({'location' : location,'school_count':len(schools_in_location)})
        for config in config_list:
            if config.get('collective_dict_key') in indicator_list:
                enrollment_polls = Poll.objects.filter(name__in=[config.get('enrollment_poll')[0]])
                attendance_polls = Poll.objects.filter(name__in=[config.get('attendance_poll')[0]])
                enroll_indicator_total = sum(get_numeric_data(enrollment_polls,dataSource,[location],term_range))
                week_count = 0
                weekly_results = []
                weekly_school_count = []

                for week in time_range:
                    week_count +=1
                    # get attendance total for week by indicator from config file
                    attend_week_total = sum(get_numeric_data(attendance_polls,dataSource,[location],week))
                    # get schools that Responded
                    schools_that_responded = len(get_numeric_data_by_school(attendance_polls,dataSource,schools_in_location,week))
                    week_percent = compute_absent_values(attend_week_total,enroll_indicator_total)
                    absenteeism_percent +=week_percent
                    week_context.append({'Week '+str(week_count) : week_percent, 'Week Range' : week})
                    weekly_school_count.append(schools_that_responded)
                    weekly_results.append(absenteeism_percent)

                for item in chart_data:
                    for k,v in item.items():
                        if k == config.get('collective_dict_key'):
                            item[k] = [sum(a) for a in zip(*[v,weekly_results])]

                for item in school_report:
                    for k,v in item.items():
                        if k == config.get('collective_dict_key'):
                            item[k] = [sum(a) for a in zip(*[v,weekly_school_count])]

                for item in high_chart_tooltip:
                    for k,v in item.items():
                        if k == config.get('collective_dict_key'):
                            enroll = v.get('enrollment') + enroll_indicator_total
                            attendance = v.get('present') + (sum(weekly_school_count))/len(time_range)
                            v['enrollment'] = enroll
                            v['present'] = attendance


                config_set_result[config.get('collective_dict_key')] = round(absenteeism_percent/len(time_range),2) # adds average percentage to dict_key
                tmp_data.append({location.name :{'Indicator' :config.get('collective_dict_key'),'Schools' :weekly_school_count }})

            else: # used to compute head teachers absenteeism
                deployedHeadTeachers = get_deployed_head_Teachers(headteachersSource,[location])
                attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])
                weekly_present = []
                weekly_percent = []
                weekly_school_count = []
                for week in time_range:
                    present,absent = get_count_for_yes_no_response(attendance_polls,dataSource,[location],week)
                    schools_that_responded = len(get_numeric_data_by_school(attendance_polls,dataSource,schools_in_location,week))
                    weekly_present.append(present)
                    weekly_percent.append(compute_absent_values(present,deployedHeadTeachers))
                    weekly_school_count.append(schools_that_responded)

                percent_absent = compute_absent_values(sum(weekly_present)/len(time_range),deployedHeadTeachers)
                head_teacher_set.append({'Location':location,'present':weekly_present,'deployed' :deployedHeadTeachers,'percent':percent_absent })
                config_set_result[config.get('collective_dict_key')] = round(percent_absent,2)
                for item in chart_data:
                    for k,v in item.items():
                        if k == 'Head Teachers':
                            item[k] = [sum(a) for a in zip(*[v,weekly_percent])]
                for item in school_report:
                    for k,v in item.items():
                        if k == config.get('collective_dict_key'):
                            item[k] = [sum(a) for a in zip(*[v,weekly_school_count])]


        collective_result[location.name] = config_set_result
    time_data = []
    school_data = {}

    # get averages to display on chart (formula : divide the aggregated value along each each week for each indicator and divide by week range count )
    for item in chart_data:
        for k,v in item.items():
            output = []
            for val in v:
                output.append(round(val/len(time_range),2))
            time_data.append({'name' : k, 'data' : output})
    # get school response average
    for item in school_report:
        for k,v in item.items():
            output = []
            for val in v:
                output.append(val)
                school_data[k] = round(((sum(output)/len(time_range))/schools_total)*100,2)


    return collective_result, time_data, school_data


def view_stats_by_school(location_id,enrollment_poll_name,attendance_poll_name):
    locale = Location.objects.exclude(type="country").filter(type="district")
    _schools = School.objects.filter(location=locale.get(id=location_id))
    poll_enroll = Poll.objects.get(name=enrollment_poll_name)
    poll_attendance = Poll.objects.get(name=attendance_poll_name)
    date_weeks = get_week_date(depth=2)
    school_data = []
    existing_data = []
    term_range=[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    current_week = date_weeks[0]
    previous_week = date_weeks[1]

    for school in _schools:
        enrollment = sum(get_numeric_data_from_source_by_school(poll_enroll,school,term_range))
        attendance_current_week = sum(get_numeric_data_from_source_by_school(poll_attendance,school,current_week))
        attendance_previous_week = sum(get_numeric_data_from_source_by_school(poll_attendance,school,previous_week))
        # percent computation
        percent_current_week = round(compute_absent_values(attendance_current_week,enrollment),2)
        percent_previous_week = round(compute_absent_values(attendance_previous_week,enrollment),2)

        try:
            diff = percent_current_week - percent_previous_week
        except (TypeError,IndexError):
            diff = '--'

        if enrollment > 0:
            existing_data.append([school,percent_current_week,percent_previous_week,diff])
        school_data.append([school,percent_current_week,percent_previous_week,diff])

    return school_data, existing_data

################################## (Report Numeric Data Computation from source objects) Begin Block #################


def compute_absenteeism_summary(indicator,locations):
    date_weeks = get_week_date(depth=2)
    term_range=[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    current_week_date_range = date_weeks[0]
    previous_week_date_range = date_weeks[1]
    enrollment_total = 0
    current_week_present_total = 0
    previous_week_present_total = 0
    present_by_time = []

    config_list = get_polls_for_keyword(indicator)
    poll_enrollment = Poll.objects.get(name=config_list[0].get('enrollment_poll')[0])
    poll_attendance = Poll.objects.get(name=config_list[0].get('attendance_poll')[0])

    results = get_numeric_data_by_locations(poll_enrollment,locations,term_range)
    if not is_empty(results):
        enrollment_total = sum(results)

    results =  get_numeric_data_by_locations(poll_attendance,locations,current_week_date_range)
    if not is_empty(results):
        current_week_present_total = sum(results)

    results = get_numeric_data_by_locations(poll_attendance,locations,previous_week_date_range)
    if not is_empty(results):
        previous_week_present_total = sum(results)

    absent_current_week = round(compute_absent_values(current_week_present_total, enrollment_total),2)
    absent_previous_week = round(compute_absent_values(previous_week_present_total, enrollment_total),2)
    present_by_time.append(absent_current_week)
    present_by_time.append(absent_previous_week)

    return present_by_time


def get_digit_value_from_message_text(messge):
    digit_value = 0
    regex = re.compile(r"(-?\d+(\.\d+)?)")
     #split the text on number regex. if the msg is of form
     #'19'or '19 years' or '19years' or 'age19'or 'ugx34.56shs' it returns a list of length 4
    msg_parts = regex.split(messge)
    if len(msg_parts) == 4:
        digit_value = round(float(msg_parts[1]),3)
    return digit_value

def get_count_for_yes_no_response(polls,dataSource, locations=None, time_range=None):
    yes = 0
    no = 0
    if time_range:
        if locations:
                responses =  dataSource.filter(date__range=time_range,poll__in=polls,has_errors=False,contact__reporting_location__in=locations,message__direction='I')
                for response in responses:
                    if 'yes' in response.message.text.lower():
                        yes += 1
                    if 'no' in response.message.text.lower():
                        no +=1
    return yes, no



#  Function called to populate in-memory Data, reduces on number of db queries per request.
def get_record_collection(locations,time_range):
    results = []
    try:
        if time_range:
            if locations:
                results = Response.objects.filter(date__range=time_range,has_errors=False,contact__reporting_location__in=locations,message__direction='I').select_related()
    except:
        pass # Log database errors (or lookup db error exceptions and be specific on exception)
    return results

def get_deployed_head_Teachers(dataSource, locations=None):
    result = 0
    if locations:
        deployedHeadTeachers = EmisReporter.objects.filter(reporting_location__in=locations,
                                                           schools__in=dataSource.values_list('schools', flat=True),
                                                           groups__name='SMC').distinct()
        result = len(deployedHeadTeachers)
    return result


def get_numeric_data(polls,dataSource, locations=None, time_range=None):
    results = []
    if time_range:
        if locations:
                responses =  dataSource.filter(date__range=time_range,poll__in=polls,has_errors=False,contact__reporting_location__in=locations,message__direction='I')
                for response in responses:
                    results.append(get_digit_value_from_message_text(response.message.text))
    return results

def get_numeric_data_by_school(polls,dataSource, schools=None, time_range=None):
    results = []
    if time_range:
        if schools:
                responses = dataSource.filter(date__range=time_range,poll__in=polls,has_errors=False,contact__emisreporter__schools__in= schools,message__direction='I')
                for response in responses:
                    results.append(get_digit_value_from_message_text(response.message.text))

    return results

def get_numeric_data_on_polls_by_locations(polls, locations=None, time_range=None):
    results = []
    if time_range:
        if locations:
                responses = Response.objects.filter(date__range=time_range,poll__in=polls,has_errors=False,contact__reporting_location__in=locations,message__direction='I')
                for response in responses:
                    results.append(get_digit_value_from_message_text(response.message.text))

    return results

def get_numeric_data_by_locations(poll, locations=None, time_range=None):
    results = []
    if time_range:
        if locations:
                responses = Response.objects.filter(date__range=time_range,poll=poll,has_errors=False,contact__reporting_location__in=locations,message__direction='I')
                for response in responses:
                    results.append(get_digit_value_from_message_text(response.message.text))

    return results



def get_numeric_data_from_source_by_location(poll, locations=None, time_range=None):
    results = []
    if time_range:
        if locations:
                responses = Response.objects.filter(date__range=time_range,poll=poll,has_errors=False,contact__reporting_location=locations,message__direction='I')
                for response in responses:
                    results.append(get_digit_value_from_message_text(response.message.text))
    return results


def get_numeric_data_from_source_by_school(poll, school=None, time_range=None):
    results = []
    if time_range:
        if school:
                responses = Response.objects.filter(date__range=time_range,poll=poll,has_errors=False,contact__emisreporter__schools=school,message__direction='I')
                for response in responses:
                    results.append(get_digit_value_from_message_text(response.message.text))

    return results



def get_numeric_values_from_list(responses):
    result = []
    if not is_empty(responses):
        for response in responses:
            if response.values()[0] != None:
                result.append(response.values()[0])

    return result

def compute_absent_values(present,enrollment):
    try:
        if present != 0:
            return  round(((enrollment - present)*100 / enrollment),2)
        else:
            return 0
    except ZeroDivisionError:
        return 0



################################## (Report Numeric Data Computation from source objects) End Block #################


# Reporting Views
# note : duplicate code made to reduce over dependency.


@login_required
def report_dashboard(request, district=None):

    return render_to_response('education/admin/detail_report.html', RequestContext(request))


#   Reporting API

def dash_report_api(request):
    jsonDataSource = []
    config_list = get_polls_for_keyword('all')
    time_range = get_week_date(depth=4)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in time_range]
    time_range.reverse()
    #locations = Location.objects.filter(type='district').exclude(name='Moroto')
    locations = Location.objects.filter(name__in=['Buliisa','Kasese','Amuru','Pader','Agago','Bundibugyo','Arua',
                                                  'Kaabong','Kabarole','Kyegegwa','Nebbi','Oyam','Ntoroko','Nwoya','Zombo',
                                                  'Lamwo','Lyantonde','Nakapiripirit'],type='district')

    collective_result, chart_data, school_percent = get_aggregated_report_data(locations,time_range,config_list)
    jsonDataSource.append({'results': collective_result, 'chartData':chart_data, 'school_percent' : school_percent,'weeks' : weeks })

    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')

def dash_report_term(request):
    jsonDataSource = []
    config_list = get_polls_for_keyword('all')
    time_depth = 4

    current_term_range = []
    current_term_range.append(getattr(settings, 'SCHOOL_TERM_START'))
    if getattr(settings, 'SCHOOL_TERM_END') > datetime.datetime.today():
        current_term_range.append(datetime.datetime.today())

    time_range = get_date_range(current_term_range[0], current_term_range[1],time_depth)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in time_range]
    time_range.reverse()
    #locations = Location.objects.filter(type='district').exclude(name='Moroto')
    locations = Location.objects.filter(name__in=['Buliisa','Kasese','Amuru','Pader','Agago','Bundibugyo','Arua',
                                                  'Kaabong','Kabarole','Kyegegwa','Nebbi','Oyam','Ntoroko','Nwoya','Zombo',
                                                  'Lamwo','Lyantonde','Nakapiripirit'],type='district')
    collective_result, chart_data, school_percent = get_aggregated_report_data(locations,time_range,config_list)
    jsonDataSource.append({'results': collective_result, 'chartData':chart_data, 'school_percent' : school_percent,'weeks' : weeks })

    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')


def dash_report_params(request,start_date=None, end_date=None, indicator=None):
    jsonDataSource = []
    config_list = get_polls_for_keyword(indicator)
    time_range = get_week_date(depth=4)
    params = [{'start_date' : start_date,'end_date' : end_date,'indicator' : indicator}]
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in time_range]
    time_range.reverse()

    jsonDataSource.append({'results': params, 'chartData':config_list, 'school_percent' : time_range,'weeks' : weeks })

    return HttpResponse(simplejson.dumps(jsonDataSource), mimetype='application/json')











