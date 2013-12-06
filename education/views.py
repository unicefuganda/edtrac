from __future__ import division
from urllib2 import urlopen
import re
import operator
import copy
import json

from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, TemplateView, ListView
from django.views.decorators.vary import vary_on_cookie
from django.db.models import Q
from django.core.cache import cache
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
import reversion
from reversion.models import Revision
from unregister.models import Blacklist
from .utils import themes
from education.absenteeism_view_helper import *
import datetime
from datetime import date
from education.view_helper import *
from education.view_helper_utils import *

Num_REG = re.compile('\d+')

super_user_required = \
    user_passes_test(lambda u: u.groups.filter(
        name__in=['Admins', 'DFO', 'UNICEF Officials']).exists() or u.is_superuser)


@login_required
def index(request, **kwargs):
    """
    kwargs is where we list the variables that can be passed as our context
    use as follows: index(request, context_vars={'some_model_queryset'=Model.objects.all})
    """
    if not kwargs:
        return render_to_response("education/index.html", {}, RequestContext(request))
    else:
        #When choosing to use kwargs, don't forget to include template and context_var variables
        # if you don't need a template or just need the original template, use template_name=None
        context_vars = kwargs.get('context_vars')
        template_name = kwargs['template_name']
        if not template_name:
            #if no template name is given
            t = "education/index.html"
        else:
            t = "education/%s" % template_name
        return render_to_response(t, context_vars, RequestContext(request))


#MAPS
@login_required
def dash_map(request):
    return render_to_response('education/dashboard/map.html', {}, RequestContext(request))


def dash_ministry_map(request):
    return render_to_response('education/dashboard/map.html', {}, RequestContext(request))


def dash_attdance(request):
    boysp3_attendance = get_responses_to_polls(poll_name='edtrac_boysp3_attendance')
    boysp3_enrolled = get_responses_to_polls(poll_name="edtrac_boysp3_enrollment")
    boysp3_absent = boysp3_enrolled - boysp3_attendance

    girlsp3_attendance = get_responses_to_polls(poll_name="edtrac_girlsp3_attendance")
    girlsp3_enrolled = get_responses_to_polls(poll_name="edtrac_girlsp3_enrollment")
    girlsp3_absent = girlsp3_enrolled - girlsp3_attendance

    boysp6_attendance = get_responses_to_polls(poll_name="edtrac_boysp6_attendance")
    boysp6_enrolled = get_responses_to_polls(poll_name="edtrac_boysp6_enrollment")
    boysp6_absent = boysp6_enrolled - boysp6_attendance

    girlsp6_attendance = get_responses_to_polls(poll_name="edtrac_girlsp6_attendance")
    girlsp6_enrolled = get_responses_to_polls(poll_name="edtrac_girlsp6_enrollment")
    girlsp6_absent = girlsp6_enrolled - girlsp6_attendance

    total_male_teachers = get_responses_to_polls(poll_name="edtrac_m_teachers_deployment")
    total_female_teachers = get_responses_to_polls(poll_name="edtrac_f_teachers_deployment")

    male_teachers_present = get_responses_to_polls(poll_name="edtrac_m_teachers_attendance")
    male_teachers_absent = total_male_teachers - male_teachers_present

    female_teachers_present = get_responses_to_polls(poll_name="edtrac_f_teachers_attendance")
    female_teachers_absent = total_female_teachers - female_teachers_present

    return render_to_response('education/dashboard/attdance.html', {
        'girlsp3_present' : girlsp3_attendance, 'girlsp3_absent' : girlsp3_absent,
        'boysp3_present' : boysp3_attendance, 'boysp3_absent' : boysp3_absent,
        'girlsp6_present' : girlsp6_attendance, 'girlsp6_absent' : girlsp6_absent,
        'boysp6_present' : boysp6_attendance, 'boysp6_absent' : boysp6_absent,
        'female_teachers_present' : female_teachers_present, 'female_teachers_absent' : female_teachers_absent,
        'male_teachers_present' : male_teachers_present, 'male_teachers_absent' : male_teachers_absent
    } , RequestContext(request))


def get_mode_progress(mode):
    try:
        mode_progress = (100 * sorted(target.values()).index(mode) + 1) / float(len(target.keys())) # offset zero-based index by 1
    except ValueError:
        mode_progress = 0 # when no values are recorded
    return mode_progress


def get_progress_color(current_mode, target_value):
    on_schedule = 'green'
    behind_schedule = 'red'
    if current_mode < target_value:
        return behind_schedule
    return on_schedule


def get_weeks_in_term():
    term_start= getattr(settings,'SCHOOL_TERM_START')
    first_term_start= getattr(settings,'FIRST_TERM_BEGINS')
    second_term_start= getattr(settings,'SECOND_TERM_BEGINS')
    third_term_start= getattr(settings,'THIRD_TERM_BEGINS')
    weeks = []
    for term_starts in [first_term_start, second_term_start, third_term_start]:
        if term_start == term_starts:
            weeks.extend(get_weeks(get_week_date()[1],depth=get_week_count(get_week_date()[0],term_starts)))
            break
        weeks.extend(get_weeks(dateutils.increment(term_starts, weeks=12),depth=12))
    return weeks


def format_week(week,sep):
    day1 = week[0].strftime("%d"+sep+"%b"+sep+"%Y")
    day2 = week[1].strftime("%d"+sep+"%b"+sep+"%Y")
    formated_week = "%s to %s" % (day1 , day2)
    return formated_week

def _get_formated_date_choice(week):
    if week[0] < datetime.datetime.today() < week[1]:
        return format_week(week, ","), "current week( %s )" % format_week(week, "-")
    return format_week(week, ","), format_week(week, "-")

class CurriculumForm(forms.Form):
    error_css_class = 'error'
    SELECT_CHOICES = [_get_formated_date_choice(week) for week in get_weeks_in_term()]
    choose_week_to_view = forms.ChoiceField(choices=SELECT_CHOICES, required=False)


class ReporterDetailView(DetailView):
    model = EmisReporter


def format_to_datetime_object(week_as_string):
    day1 = week_as_string.split()[0]
    day2 = week_as_string.split()[2]
    day_one = datetime.datetime.strptime(day1,"%d,%b,%Y")
    day_two = datetime.datetime.strptime(day2,"%d,%b,%Y")
    return [day_one,day_two]


def get_modes_and_target(current_mode, target_value):
    target_progress = get_mode_progress(target_value)
    if len(current_mode) > 0 and isinstance(current_mode,list):
        max_mode = max([i[0] for i in current_mode])
        mode_progress = get_mode_progress(max_mode)
        color = get_progress_color(max_mode, target_value)
        return color, mode_progress, target_progress
    mode_progress = 0
    color = 'red'
    return color, mode_progress, target_progress


def get_mode_if_exception_thrown(loc_data):
    if "Progress undetermined this week" in loc_data.values():
        return "Progress undetermined this week"
    return "No Reports made this week"

@login_required
def curriculum_progress(request,district_pk=None):
    locations, user_location, sub_location_type,template_name = get_location_for_curriculum_view(district_pk, request)
    if request.method == 'POST':
        curriculum_form = CurriculumForm(data=request.POST)
        if curriculum_form.is_valid():
            target_week = format_to_datetime_object(curriculum_form.cleaned_data['choose_week_to_view'])
            target_date = target_week[0]
        else:
            return render_to_response('education/progress/admin_progress_details.html',
                                      {'form': curriculum_form}, RequestContext(request))
    else:
        target_week = get_week_date()
        curriculum_form = CurriculumForm(initial={'choose_week_to_view': format_week(target_week, ",")})
        target_date = target_week[0]

    loc_data , valid_responses = get_curriculum_data(locations,target_week)
    try:
        current_mode = Statistics(valid_responses).mode
    except StatisticsException:
        current_mode = get_mode_if_exception_thrown(loc_data)

    target_value , term = get_target_value(target_date)
    if isinstance(current_mode,list) and len(current_mode) == 0:
        current_mode = "Progress undetermined this week"

    color, mode_progress, target_progress = get_modes_and_target(current_mode, target_value)
    return render_to_response(template_name,
                              {'form': curriculum_form, 'location_data': loc_data,
                               'target': target_value,
                               'current_mode': current_mode, 'mode_progress': mode_progress,
                               'target_progress': target_progress,
                               'class_sent_from_behind': color, 'sub_location_type': sub_location_type, 'term': term},
                              RequestContext(request))

def dash_admin_meetings(req):
    profile = req.user.get_profile()
    location = profile.location

    p = Poll.objects.get(name = 'edtrac_smc_meetings')

    if profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials') or profile.is_member_of('Ministry Officials'):
        meeting_stats = get_count_response_to_polls(p,
            #404 is shortcode for unknown
            choices = [0, 1, 2, 3, 404], # number of meetings
            with_percent = True, #percentage counted based on number of schools
            termly = True, admin=True)

        return render_to_response("education/admin/admin_meetings.html",{
            'meeting_basis': meeting_stats.get('correctly_answered'),
            'titles':",".join(str(k) for k in meeting_stats.get('to_ret').keys()),
            'meetings':",".join(str(v) for v in meeting_stats.get('to_ret').values())
        }, RequestContext(req))
    else:
        meeting_stats = get_count_response_to_polls(p,
            location_name = location.name,
            #404 is shortcode for unknown
            choices = [0, 1, 2, 3, 404], # number of meetings
            with_percent = True, #percentage counted based on number of schools
            termly = True,
            admin = False
        )
        return render_to_response('education/admin/other_meetings.html',
                {'location_name':location.name,
                 'meeting_basis': meeting_stats.get('correctly_answered'),
                 'meetings':",".join(str(v) for v in meeting_stats.get('to_ret').values()),
                 'titles':",".join(str(k) for k in meeting_stats.get('to_ret').keys()),
                 'meeting_basis':meeting_stats.get('correctly_answered')}, RequestContext(req))


def preprocess_response(resp):
    """
    reprocess the response values and return just one value
    """
    if not resp:
        return '--'
    elif None in resp:
        return 'wrong response'
    else:
        return resp[0] # assumption only one SMC is attached to that school

def dash_district_meetings(req, district_name):
    district = Location.objects.filter(type="district").get(name = district_name)

    p = Poll.objects.get(name = 'edtrac_smc_meetings')

    schools_data = EmisReporter.objects.exclude(connection__in = Blacklist.objects.values_list('connection')).\
    filter(groups__name = 'SMC', reporting_location = district).exclude(schools = None).order_by('schools__name').\
    values_list('schools__name','schools__id','connection__pk')

    school_container = {}
    for school_name, school_id, smc_connection in schools_data:
        school_container[(school_name, school_id)] = preprocess_response([r.eav.poll_number_value for r in p.responses.filter(contact__connection__pk = smc_connection,
            date__range =[getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
        )])

    #TODO -> sort the school container items

    return render_to_response(
        'education/admin/district_meetings.html',
            {'location_name':district_name, 'meeting_count':school_container.items()}, RequestContext(req))

# Dashboard specific view functions

@login_required
@vary_on_cookie
def dashboard(request):
    return admin_dashboard(request)

def capitation_grants(locations):
    # capitation grants
    cg = Poll.objects.get(name="edtrac_upe_grant")

    yes_category = cg.categories.get(name='yes')
    yeses_cg = cg.responses.filter(contact__reporting_location__in=locations,
                                   categories__category=yes_category).values_list('contact').distinct().count()

    # percent of those that received grants
    head_teacher_count = EmisReporter.objects.exclude(schools=None, connection__in= \
        Blacklist.objects.values_list('connection', flat=True)).filter(groups__name='Head Teachers', \
                                                                       reporting_location__in=locations).count()
    try:
        grant_percent = (100 * yeses_cg) / head_teacher_count
    except ZeroDivisionError:
        grant_percent = 0

    return {'grant_percent': grant_percent}


def month_total(poll_name, locations):
    poll = Poll.objects.get(name=poll_name)
    return NumericResponsesFor(poll) \
               .forLocations(locations) \
               .forDateRange(get_month_day_range(datetime.datetime.now(), depth=1)[0]) \
               .total()


def violence_numbers_girls(locations):
    return {'violence_numbers_girls' : month_total('edtrac_violence_girls', locations)}


def violence_numbers_boys(locations):
    return {'violence_numbers_boys' : month_total('edtrac_violence_boys', locations)}


def violence_numbers_reported(locations):
    return {'violence_numbers_reported' : month_total('edtrac_violence_reported', locations)}


def compute_percent(x,y):
    if y != 0:
        return (100 * x) / y
    else:
        return 0

def get_two_weeks_absenteeism(gender, locations, get_time):
    date_weeks = get_week_date(depth=2, get_time=get_time)

    if is_holiday(date_weeks[0][0], getattr(settings, 'SCHOOL_HOLIDAYS')) \
       or is_holiday(date_weeks[1][0], getattr(settings, 'SCHOOL_HOLIDAYS')):
        return '--','--'
    else:
        poll = Poll.objects.get(name='edtrac_head_teachers_attendance')
        yesses_this_week = gendered_text_responses(date_weeks[0], locations, ['Yes', 'YES', 'yes'], gender)
        yesses_last_week = gendered_text_responses(date_weeks[1], locations, ['Yes', 'YES', 'yes'], gender)
        noes_this_week = gendered_text_responses(date_weeks[0], locations, ['No', 'NO', 'no'], gender)
        noes_last_week = gendered_text_responses(date_weeks[1], locations, ['No', 'NO', 'no'], gender)

        this_week_absent = compute_percent(noes_this_week, yesses_this_week + noes_this_week)
        past_week_absent = compute_percent(noes_last_week, yesses_last_week + noes_last_week)

        return this_week_absent, past_week_absent


def p3_absent_boys(locations, get_time=datetime.datetime.now):
    """
    Attendance of P3 Pupils; this gets the absenteeism
    """
    boysp3, boysp3_past = compute_absenteeism_summary('P3Boys',locations,get_time=get_time)
    return {'boysp3' : boysp3, 'boysp3_past' : boysp3_past,}


def p6_boys_absent(locations, get_time=datetime.datetime.now):
    boysp6, boysp6_past =  compute_absenteeism_summary('P6Boys',locations,get_time=get_time)
    return {'boysp6' : boysp6, 'boysp6_past' : boysp6_past}


def p3_absent_girls(locations, get_time=datetime.datetime.now):
    girlsp3 ,girlsp3_past =  compute_absenteeism_summary('P3Girls',locations,get_time=get_time)
    return {'girlsp3' : girlsp3, 'girlsp3_past' : girlsp3_past}


def p6_girls_absent(locations,get_time=datetime.datetime.now):
    girlsp6,girlsp6_past =  compute_absenteeism_summary('P6Girls',locations,get_time=get_time)
    return {'girlsp6' : girlsp6, 'girlsp6_past' : girlsp6_past}


def f_teachers_absent(locations, get_time=datetime.datetime.now):
    female_teachers ,female_teachers_past =  compute_absenteeism_summary('FemaleTeachers',locations,get_time=get_time)
    return {'female_teachers' :female_teachers,'female_teachers_past' : female_teachers_past,}


def m_teachers_absent(locations, get_time=datetime.datetime.now):
    male_teachers,male_teachers_past =  compute_absenteeism_summary('MaleTeachers',locations, get_time=get_time)
    return {'male_teachers' : male_teachers, 'male_teachers_past' : male_teachers_past}


def get_target_week():
    for week in get_weeks_in_term():
        if week[0] < datetime.datetime.today() < week[1]:
            return week


def progress(stages, stage):
    numerator = stages.index(stage) + 1
    denominator = len(stages)
    return 100 * numerator / denominator

def p3_curriculum(locations):
    target_week = get_week_date()
    poll = Poll.objects.get(name='edtrac_p3curriculum_progress')

    mode = NumericResponsesFor(poll) \
                .forDateRange(target_week) \
                .forLocations(locations) \
                .forValues(themes.keys()) \
                .mode()

    if mode:
        return {'mode_progress' : progress(sorted(themes.keys()), mode), 'c_mode' : [[mode]]}
    else:
        return {'mode_progress' : 0, 'c_mode' : "Progress undetermined this week"}

def meals_missed(locations, get_time):
    poll = Poll.objects.get(name = "edtrac_headteachers_meals")
    this_month = get_month_day_range(get_time())
    schools_without_meals = NumericResponsesFor(poll) \
                                .forLocations(locations) \
                                .forDateRange(this_month) \
                                .excludeGreaterThan(0) \
                                .groupBySchools()

    return {'meals_missed' : len(schools_without_meals)}


def head_teachers_female(locations, get_time=datetime.datetime.now):
    female_d1,female_d2 = get_two_weeks_absenteeism('F', locations, get_time)
    try:
        f_head_diff = female_d2 - female_d1

        if f_head_diff < 0:
            f_head_t_class = "decrease"
            f_head_t_data = 'data-red'
        elif f_head_diff > 0:
            f_head_t_class = "increase"
            f_head_t_data = 'data-green'
        else:
            f_head_t_class = "zero"
            f_head_t_data = 'data-white'
    except:
        f_head_diff = '--'
        f_head_t_class = "zero"
        f_head_t_data = 'data-white'


    return {'f_head_t_week' : female_d1, 'f_head_t_week_before' : female_d2, 'f_head_diff' : f_head_diff,
            'f_head_t_class' : f_head_t_class, 'f_head_t_data':f_head_t_data}

def head_teachers_male(locations, get_time=datetime.datetime.now):
    male_d1, male_d2 = get_two_weeks_absenteeism('M', locations, get_time=get_time)
    try:
        m_head_diff = male_d2 - male_d1

        if m_head_diff < 0:
            m_head_t_class = "decrease"
            m_head_t_data = 'data-red'
        elif m_head_diff > 0:
            m_head_t_class = "increase"
            m_head_t_data = 'data-green'
        else:
            m_head_t_class = "zero"
            m_head_t_data = 'data-white'
    except:
        m_head_diff = '--'
        m_head_t_class = "zero"
        m_head_t_data = 'data-white'


    return {'m_head_t_week' : male_d1, 'm_head_t_data':m_head_t_data, 'm_head_t_week_before' : male_d2, 'm_head_diff' : m_head_diff,
            'm_head_t_class' : m_head_t_class}


def schools_valid(locations, group_names, blacklisted):
    school_valid = EmisReporter.objects.filter(
        groups__name__in=group_names,
        reporting_location__in=locations
    ).exclude(connection__in=blacklisted).exclude(schools=None) \
     .values('schools__id').distinct().count()

    return {'total_schools_valid': school_valid}

def schools_active(locations):
    try:
        count_reps = EmisReporter.objects.filter(groups__name__in=['Teachers', 'Head Teachers', 'SMC', 'GEM', 'Other Reporters', 'DEO', 'MEO'],
                                reporting_location__in = locations).exclude(connection__in=Blacklist.objects.all()).exclude(schools=None).count()

        count = 0
        for p in Poll.objects.filter(name__icontains = 'attendance').select_related():
            if len(locations) == 1:
                count += p.responses.filter(
                    contact__reporting_location__in = locations, date__range = get_week_date(depth = 2)[0]
                ).distinct().select_related().count()
            else:
                count += p.responses.filter(date__range = get_week_date(depth=2)[0]).distinct().select_related().count()

        school_active = (100 * count) / count_reps

    except ZeroDivisionError:
        school_active = 0

    return {'school_active': school_active}


def smc_meetings(locations):
    # SMC meetings are count based
    school_to_date = School.objects.filter(pk__in=EmisReporter.objects.\
        filter(reporting_location__name__in = [loc.name for loc in locations]).select_related().\
        values_list('schools__pk', flat=True)).count()

    smc_meeting_poll = Poll.objects.get(name = 'edtrac_smc_meetings')
    meetings = NumericResponsesFor(smc_meeting_poll) \
                    .excludeZeros() \
                    .forDateRange([getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]) \
                    .forLocations(locations) \
                    .total()

    try:
        total_meetings = 100 * meetings / school_to_date
    except ZeroDivisionError:
        total_meetings = 0

    return {'smc_meetings': total_meetings, 'schools_to_date': school_to_date}


def total_reporters(locations, group_names, blacklisted):
    total_reporters = EmisReporter.objects.filter(
        groups__name__in=group_names,
        reporting_location__in=locations
    ).exclude(
        connection__in=blacklisted
    ).exclude(
        schools=None
    ).count()

    return {'total_reporters': total_reporters}

# generate context vars
def generate_dashboard_vars(location):
    """
    An overly ambitious function that generates context variables for a location if provided
    This gets populated in the dashboard.
    """

    context_vars = {}
    if location.name == "Uganda":
        # get locations from active districts only
        locations = Location.objects.filter(pk__in=EmisReporter.objects.\
            values_list('reporting_location__pk', flat=True)).distinct()
    else:
        locations = [location]

    group_names = ['Teachers', 'Head Teachers', 'SMC', 'GEM',
                   'Other Reporters', 'DEO', 'MEO']
    blacklisted = Blacklist.objects.all().values_list('connection', flat=True)

    # violence girls
    context_vars.update(violence_numbers_girls(locations))

    #violence boys
    context_vars.update(violence_numbers_boys(locations))

    #violence_reported
    context_vars.update(violence_numbers_reported(locations))

    # capitations grants
    context_vars.update(capitation_grants(locations))

    #active schools
    context_vars.update(schools_active(locations))

    #valid schools
    context_vars.update(schools_valid(locations, group_names, blacklisted))

    #SMC meetings
    context_vars.update(smc_meetings(locations))

    #female head teachers that missed school
    context_vars.update(head_teachers_female(locations))

    #male head teachers that missed school
    context_vars.update(head_teachers_male(locations))

    # time stamps
    context_vars.update({'month':datetime.datetime.now()})

    # progress
    context_vars.update(p3_curriculum(locations))

    # Female teachers
    context_vars.update(f_teachers_absent(locations))

    # P3 teachers male
    context_vars.update(m_teachers_absent(locations))

    # P3 boys
    context_vars.update(p3_absent_boys(locations))

    # P3 Girls
    context_vars.update(p3_absent_girls(locations))

    # P6 Girls
    context_vars.update(p6_girls_absent(locations))

    # P6 Boys
    context_vars.update(p6_boys_absent(locations))

    #Meals
    context_vars.update(meals_missed(locations, get_time = datetime.datetime.now))

    #Total Reporters
    context_vars.update(total_reporters(locations, group_names, blacklisted))

    return context_vars

# view generator
def view_generator(req,
                   enrol_deploy_poll=None,
                   attendance_poll=None,
                   title=None,
                   url_name_district=None,
                   url_name_school = 'school-detail',
                   template_name='education/timeslider_base.html'):
    """
    A generic function to create views based on time ranges.
    """
    time_range_form = ResultForm()
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins')\
        or profile.is_member_of('UNICEF Officials'):
        # high level officials will access all districts
        locations = Location.objects.filter(type='district').filter(pk__in =\
            EnrolledDeployedQuestionsAnswered.objects.values_list('school__location__pk',flat=True))
    else:
        # other officials will access individual districts
        locations = [profile.location]

    if req.method == 'POST':
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
                        date_weeks.append(previous_calendar_week(t = from_date)) # get range from Wed to Thur.
                    from_date += datetime.timedelta(days = 1)
            else:
                month_flag = True # split data in months
                while from_date <= to_date:
                    date_weeks.append([dateutils.month_start(from_date),dateutils.month_end(dateutils.increment(from_date, months=1))])
                    next_date = dateutils.increment(from_date, months = 1)
                    delta = next_date - from_date
                    from_date += datetime.timedelta(days = abs(delta.days))

            if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins')\
                or profile.is_member_of('UNICEF Officials'):

                schools_temp = School.objects.filter(pk__in = \
                    EnrolledDeployedQuestionsAnswered.objects.select_related().values_list('school__pk', flat=True))
                for location in locations:
                    temp = []
                    # get schools in this location
                    location_schools = schools_temp.select_related().filter(location = location) # store in memory
                    for d in date_weeks:
                        total_attendance = 0 # per school
                        total_enrollment = 0 # per school
                        for school in location_schools:
                            enrolled = poll_responses_term(enrol_deploy_poll, belongs_to='schools', school = school )
                            if enrolled > 0:
                                if month_flag:
                                    attendance = get_numeric_report_data(attendance_poll, school = school,
                                        time_range=list(d), to_ret = 'avg') # use averages
                                else:
                                    attendance = get_numeric_report_data(attendance_poll, school = school,
                                        time_range=list(d), to_ret = 'sum')

                                total_attendance += attendance
                                total_enrollment += enrolled

                        try:
                            percentage = (total_enrollment - total_attendance) * 100 / total_enrollment
                        except ZeroDivisionError:
                            percentage = '--'
                        temp.append(percentage)
                    to_ret.append([location, temp])

                return render_to_response(template_name, {'form':time_range_form, 'dataset':to_ret,
                                                          'title': title,'month_flag': month_flag,
                                                          'url_name':url_name_district,
                                                          'date_batch':date_weeks}, RequestContext(req))

            else:
                location_schools = School.objects.filter(pk__in = EnrolledDeployedQuestionsAnswered.objects.select_related().\
                    filter(school__location=locations[0]).values_list('school__pk', flat=True)).select_related()
                #Non admin types#
                for school in location_schools:
                    for d in date_weeks:
                        temp = []
                        enrollment = poll_responses_term(enrol_deploy_poll, belongs_to='schools', school = school )
                        if month_flag:
                            attendance = get_numeric_report_data(attendance_poll, school = school,
                                time_range=list(d), to_ret = 'avg')
                        else:
                            attendance = get_numeric_report_data(attendance_poll, school = school,
                                time_range=list(d), to_ret = 'sum')
                        try:
                            percentage = (enrollment - attendance) * 100 / enrollment
                        except ZeroDivisionError:
                            percentage = '--'
                        temp.append(percentage)

                    to_ret.append([school, temp])
                return render_to_response(template_name, {'form':time_range_form, 'dataset_school':to_ret,
                                                                             'title': title,'month_flag':month_flag,
                                                                             'url_name': url_name_school,
                                                                             'date_batch':date_weeks}, RequestContext(req))
        else:
            return render_to_response(template_name, {'form':time_range_form,
                                                                         'url_name':url_name_district,
                                                                         'title':title}, RequestContext(req))

    # NO POST data sent!
    else:
        date_weeks = []
        date_weeks.append(previous_calendar_week(t = datetime.datetime.now()))
        sw = date_weeks[0][0]
        date_weeks.append(previous_calendar_week(t = dateutils.increment(datetime.datetime(sw.year, sw.month, sw.day, 10), weeks = -1)))

        location_data = []
        schools_temp = School.objects.select_related().\
            filter(pk__in =\
                EnrolledDeployedQuestionsAnswered.objects.select_related().filter(school__location__in=locations).values_list('school__pk',flat=True))

        context_vars = {}
        if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins')\
            or profile.is_member_of('UNICEF Officials'):
            for location in locations:
                temp = []
                # get schools in this location
                location_schools = schools_temp.select_related().filter(location = location)
                for d in date_weeks:
                    total_attendance = 0 # per school
                    total_enrollment = 0 # per school
                    for school in location_schools:
                        enrolled = poll_responses_term(enrol_deploy_poll, belongs_to='schools', school = school )
                        attendance = get_numeric_report_data(attendance_poll, school = school,
                            time_range=list(d), to_ret = 'sum')
                        total_attendance += attendance
                        total_enrollment += enrolled
                    try:
                        percentage = (total_enrollment - total_attendance) * 100 / total_enrollment
                    except ZeroDivisionError:
                        percentage = '--'
                    temp.append(percentage)
                try:
                    diff = temp[0] - temp[1]
                except TypeError:
                    diff = '--'

                location_data.append([location, temp[0], temp[1], diff])
            context_vars.update({'location_data':location_data})
        else:
            location_schools = School.objects.select_related().filter(pk__in = EnrolledDeployedQuestionsAnswered.objects.select_related().\
                filter(school__location=locations[0]).values_list('school__pk', flat=True))
            #Non admin types
            to_ret = []

            for school in location_schools:
                enrollment = poll_responses_term(enrol_deploy_poll, belongs_to='schools', school = school )
                temp = []
                for d in date_weeks:
                    attendance = get_numeric_report_data(attendance_poll, school = school,
                        time_range=list(d), to_ret = 'sum')
                    try:
                        percentage = (enrollment - attendance) * 100 / enrollment
                    except ZeroDivisionError:
                        percentage = '--'
                    temp.append(percentage)

                to_ret.append([school, temp])

            context_vars = {'form':time_range_form, 'dataset_school':to_ret,
                                                      'title': title,
                                                      'url_name': url_name_school,
                                                      'date_batch':date_weeks}



        if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
            x = {'url_name':url_name_district, 'headings':['District', 'Current week', 'Previous week', 'Percentage difference']}
        else:
            x = {'url_name':url_name_school, 'headings':['School', 'Current week', 'Previous week', 'Percentage difference']}

        if context_vars.has_key('form') ==False and context_vars.has_key('title') == False:
            context_vars.update({'form':time_range_form,'title':title}) # add the keys to context_vars dict
        context_vars.update(x)
        return render_to_response(template_name, context_vars, RequestContext(req))

@login_required
def admin_dashboard(request):
    if request.user.get_profile().is_member_of('Ministry Officials') or request.user.get_profile().is_member_of('Admins')\
    or request.user.get_profile().is_member_of('UNICEF Officials'):
        location = Location.objects.get(name="Uganda")
    else:
        location = request.user.get_profile().location

    key = "context-vars-for-location-" + str(location.id)
    context_vars = cache.get(key)

    if not context_vars:
        context_vars = generate_dashboard_vars(location=location)
        cache.set(key, context_vars)

    return render_to_response("education/admin/admin_dashboard.html", context_vars, RequestContext(request))


class NationalStatistics(TemplateView):
    template_name = "education/admin/national_statistics.html"
    groups = ['Teachers', 'Head Teachers', 'SMC', 'GEM', 'Other Reporters', 'DEO', 'MEO']

    def compute_percent(self, reps, groups = groups):
        all_reporters = EmisReporter.objects.filter(groups__name__in=groups).exclude(connection__in=Blacklist.objects.all()).exclude(schools=None)
        try:
            reps.count() / all_reporters.count()
        except ZeroDivisionError:
            return 0

    def get_context_data(self, **kwargs):
            context = super(NationalStatistics, self).get_context_data(**kwargs)
            groups = ['Teachers', 'Head Teachers', 'SMC', 'GEM', 'Other Reporters', 'DEO', 'MEO']
            all_reporters = EmisReporter.objects.filter(groups__name__in=groups).exclude(connection__in=Blacklist.objects.all()).exclude(schools=None)


            profile = self.request.user.get_profile()
            if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
                districts = Location.objects.filter(type="district").\
                filter(name__in=EmisReporter.objects.exclude(schools=None).exclude(connection__in=Blacklist.objects.values_list('connection',flat=True)).values_list('reporting_location__name', flat=True))
                reps = EmisReporter.objects.select_related().filter(groups__name__in=['Teachers', 'Head Teachers', 'SMC', 'GEM', 'Other Reporters'], connection__in=Message.objects.\
                   filter(date__range = get_week_date(depth = 2)[1]).values_list('connection', flat = True)).exclude(schools = None).exclude(connection__in = Blacklist.objects.values_list('connection', flat=True))

                district_schools = [
                (district,
                 School.objects.filter(pk__in=EmisReporter.objects.exclude(schools=None).exclude(connection__in = Blacklist.objects.values_list('connection',flat=True)).\
                 filter(reporting_location__name = district.name).distinct().values_list('schools__pk',flat=True)).count())
                for district in districts
                ]

                context['total_districts'] = districts.count()
                context['district_schools'] = district_schools
                schools= School.objects.filter(pk__in=EmisReporter.objects.exclude(schools=None).\
                exclude(connection__in = Blacklist.objects.values_list('connection',flat=True)).distinct().values_list('schools__pk',flat=True))
                context['school_count'] = schools.count()
                total_schools = 0
                for district in districts:
                    s_count = School.objects.filter(pk__in=EmisReporter.objects.exclude(schools=None).exclude(connection__in = Blacklist.objects.values_list('connection',flat=True)).\
                                                    filter(reporting_location__name = district.name).distinct().values_list('schools__pk',flat=True)).count()
                    total_schools += s_count

                context['total_schools'] = total_schools


                district_active = [
                (
                    district, self.compute_percent(reps.filter(reporting_location__pk=district.pk), groups=['Head Teachers'])
                    )
                for district in districts
                ]
                district_active.sort(key=operator.itemgetter(1), reverse=True)
                context['district_active'] = district_active[:3]
                context['district_less_active'] = district_active[-3:]
                head_teacher_count = all_reporters.filter(groups__name='Head Teachers').count()
                smc_count = all_reporters.filter(groups__name = "SMC").count()
                p6_teacher_count = all_reporters.filter(groups__name = "Teachers", grade = "P6").count()
                p3_teacher_count = all_reporters.filter(groups__name = "Teachers", grade = "P3").count()
                total_teacher_count = all_reporters.filter(groups__name="Teachers").count()
                deo_count = all_reporters.filter(groups__name="DEO").count()
                gem_count = all_reporters.filter(groups__name="GEM").count()
                teacher_data_unclean = total_teacher_count - p3_teacher_count - p6_teacher_count

                context['head_teacher_count'] = head_teacher_count
                context['smc_count'] = smc_count
                context['p6_teacher_count'] = p6_teacher_count
                context['p3_teacher_count'] = p3_teacher_count
                context['total_teacher_count'] = total_teacher_count
                context['teacher_data_unclean'] = teacher_data_unclean
                context['deo_count'] = deo_count
                context['gem_count'] = gem_count
                context['all_reporters'] = all_reporters.count()

                context['expected_reporters'] = schools.count() * 4
                # reporters that used EduTrac the past week
                active_school_reporters = all_reporters.filter(connection__in=Message.objects.exclude(application='script').\
                    filter(date__range = get_week_date(depth = 2)[1]).values_list('connection', flat = True))

                school_active = [
                (school, self.compute_percent(active_school_reporters.filter(schools__pk=school.pk), groups=['Head Teachers', 'Teachers', 'GEM', 'SMC','Other Reporters']))
                for school in schools
                ]

                school_active.sort(key=operator.itemgetter(1), reverse=True)
                context['school_active_count'] = School.objects.filter(pk__in = active_school_reporters.values_list('schools__pk', flat=True)).count()
                context['school_active'] = school_active[:3]
                context['school_less_active'] = school_active[-3:]
                return context
            else:
                return self.render_to_response(dashboard(self.request))


def get_term_range(term):
    if term == 'first':
        return [getattr(settings,'FIRST_TERM_BEGINS'),dateutils.increment(getattr(settings,'FIRST_TERM_BEGINS'),weeks=12)]
    if term == 'second':
        return [getattr(settings,'SECOND_TERM_BEGINS'),dateutils.increment(getattr(settings,'SECOND_TERM_BEGINS'),weeks=12)]
    if term == 'third':
        return [getattr(settings,'THIRD_TERM_BEGINS'),dateutils.increment(getattr(settings,'THIRD_TERM_BEGINS'),weeks=12)]
    if term == '' or term =='current' or term is None:
        return [getattr(settings,'SCHOOL_TERM_START'),getattr(settings,'SCHOOL_TERM_END')]

class CapitationGrants(TemplateView):
    poll_name =''
    restrict_group=''

    def compute_percent(self, x, y):
        try:
            return (100 * x) / y
        except ZeroDivisionError:
            return 0

    def _extract_info(self, list):
        to_ret = []
        for item in list:
            to_ret.append(
                [item.get('category__name'), item.get('value')]
            )
        final_ret = {}
        for li in to_ret:
            final_ret[li[0]] = li[1]

        total = sum(filter(None, final_ret.values()))

        for key in final_ret.keys():
            final_ret[key] = self.compute_percent(final_ret.get(key), total)

        return final_ret

    def _get_per_category_responses_for_school(self, responses_by_category, school):
        info = [stat for stat in responses_by_category if
                stat['response__contact__emisreporter__schools__name'] == school.name]
        return school, self._extract_info(info).items()

    def _get_schools_info(self, responses_at_location,location):
        responses_by_category = responses_at_location.values(
            'response__contact__emisreporter__schools__name',
            'category__name').annotate(value=Count('pk'))
        schools = location.schools.all()

        return [self._get_per_category_responses_for_school(responses_by_category, school) for school in schools]

    def get_context_data(self, **kwargs):
        term = self.kwargs.get('term')
        term_range = get_term_range(term)
        context = super(CapitationGrants, self).get_context_data(**kwargs)
        cg = Poll.objects.select_related().get(name=self.poll_name)
        authorized_users = ['Admins', 'Ministry Officials', 'UNICEF Officials']
        authorized_user = False
        for auth_user in authorized_users:
            if self.request.user.get_profile().is_member_of(auth_user):
                authorized_user = True
                break
        context['authorized_user'] = authorized_user
        er = EmisReporter.objects.select_related()
        unknown_unknowns = cg.responses.filter(~Q(message__text__iregex="i don('?)t know"),
                                               categories__category__name="unknown")
        if authorized_user:

            reporter_count = er.filter(groups__name=self.restrict_group).exclude(schools=None).count()

            all_responses = cg.responses_by_category().exclude(response__in=unknown_unknowns).filter(response__date__range=term_range)

            locs = Location.objects.filter(
                type="district", pk__in= \
                    er.exclude(connection__in=Blacklist.objects. \
                        values_list('connection', flat=True), schools=None).filter(groups__name=self.restrict_group). \
                        values_list('reporting_location__pk', flat=True))

            districts_to_ret = []
            for location in locs:
                info = self._extract_info(all_responses.filter(response__contact__reporting_location=location))

                districts_to_ret.append((location, info.items()))

            total_responses = all_responses.values_list('response__contact').distinct().count()
            context['responses'] = self._extract_info(all_responses).items()
            context['location'] = Location.tree.root_nodes()[0]
            context['sub_locations'] = districts_to_ret
            context['sub_location_type'] = "district"
        else:

            location = self.request.user.get_profile().location
            all_responses = cg.responses_by_category().exclude(response__in=unknown_unknowns).filter(response__date__range=term_range)
            responses_at_location = all_responses.filter(response__contact__reporting_location=location)
            total_responses = responses_at_location.values_list('response__contact').distinct().count()

            reporter_count = er.exclude(schools=None, connection__in= \
                Blacklist.objects.values_list('connection', flat=True)).filter(groups__name=self.restrict_group, \
                                                                               reporting_location=location).count()

            context['responses'] = self._extract_info(responses_at_location).items()
            context['location'] = location
            context['sub_locations'] = self._get_schools_info(responses_at_location, location)
            context['sub_location_type'] = "school"

        context['reporter_count'] = self.compute_percent(total_responses, reporter_count)
        context['group'] = self.restrict_group
        return context


# Details views... specified by ROLES
def set_logged_in_users_location(profile):
    if profile.is_member_of('Minstry Officials') or profile.is_member_of('UNICEF Officials') or profile.is_member_of(
            'Admins'):
        location = Location.objects.get(name='Uganda')
    else:
        location = profile.location
    return location


def violence_details_dash(req):
    profile = req.user.get_profile()
    context_vars = {}
    location = set_logged_in_users_location(profile)

    if isinstance(location, list) and len(location) > 1:
        #for the curious case that location actually returns a list of locations
        locations = location
    if isinstance(location, Location):
        if location.type.name == 'country':
            locations = Location.objects.select_related().get(name=location).get_descendants().filter(type="district")
            locations = list(locations)
        else:
            locations = [locations]

    month_day_range = get_month_day_range(datetime.datetime.now(), depth=2)
    current_month = month_day_range[0]
    previous_month  = month_day_range[1]

    edtrac_violence_girls_poll = Poll.objects.get(name="edtrac_violence_girls")
    edtrac_violence_boys_poll  = Poll.objects.get(name="edtrac_violence_boys")
    edtrac_violence_reported_poll = Poll.objects.get(name="edtrac_violence_reported")
    edtrac_gem_abuse_poll = Poll.objects.get(name="edtrac_gem_abuse")

    violence_cases_girls_current_month = get_numeric_data_for_location(edtrac_violence_girls_poll, locations, current_month)
    violence_cases_girls_previous_month = get_numeric_data_for_location(edtrac_violence_girls_poll, locations, previous_month)
    violence_cases_boys_current_month = get_numeric_data_for_location(edtrac_violence_boys_poll, locations, current_month)
    violence_cases_boys_previous_month = get_numeric_data_for_location(edtrac_violence_boys_poll, locations, previous_month)
    violence_cases_reported_current_month = get_numeric_data_for_location(edtrac_violence_reported_poll, locations, current_month)
    violence_cases_reported_previous_month = get_numeric_data_for_location(edtrac_violence_reported_poll, locations, previous_month)
    violence_cases_gem_current_month = get_numeric_data_for_location(edtrac_gem_abuse_poll, locations, current_month)
    violence_cases_gem_previous_month = get_numeric_data_for_location(edtrac_gem_abuse_poll, locations, previous_month)

    violence_cases_girls = []
    girls_current_month_total, girls_previous_month_total = 0, 0
    for location in locations:
        violence_current_month_value, violence_previous_month_value = 0, 0
        if location.id in violence_cases_girls_current_month:
            girls_current_month_total += violence_cases_girls_current_month[location.id]
            violence_current_month_value = violence_cases_girls_current_month[location.id]
        if location.id in violence_cases_girls_previous_month:
            girls_previous_month_total += violence_cases_girls_previous_month[location.id]
            violence_previous_month_value = violence_cases_girls_previous_month[location.id]
        violence_cases_girls.append((location.name, (violence_current_month_value, violence_previous_month_value, location)))
    context_vars['violence_cases_girls'] = violence_cases_girls
    context_vars['girls_totals'] = [girls_current_month_total, girls_previous_month_total]

    violence_cases_boys = []
    boys_current_month_total, boys_previous_month_total = 0, 0
    for location in locations:
        violence_current_month_value, violence_previous_month_value = 0, 0
        if location.id in violence_cases_boys_current_month:
            boys_current_month_total += violence_cases_boys_current_month[location.id]
            violence_current_month_value = violence_cases_boys_current_month[location.id]
        if location.id in violence_cases_boys_previous_month:
            boys_previous_month_total += violence_cases_boys_previous_month[location.id]
            violence_previous_month_value = violence_cases_boys_previous_month[location.id]
        violence_cases_boys.append((location.name, (violence_current_month_value, violence_previous_month_value, location)))
    context_vars['violence_cases_boys'] = violence_cases_boys
    context_vars['boys_totals'] = [boys_current_month_total, boys_previous_month_total]

    violence_cases_reported = []
    reported_current_month_total, reported_previous_month_total = 0, 0
    for location in locations:
        violence_current_month_value, violence_previous_month_value = 0, 0
        if location.id in violence_cases_reported_current_month:
            reported_current_month_total += violence_cases_reported_current_month[location.id]
            violence_current_month_value = violence_cases_reported_current_month[location.id]
        if location.id in violence_cases_reported_previous_month:
            reported_previous_month_total += violence_cases_reported_previous_month[location.id]
            violence_previous_month_value = violence_cases_reported_previous_month[location.id]
        violence_cases_reported.append((location.name, (violence_current_month_value, violence_previous_month_value, location)))
    context_vars['violence_cases_reported'] = violence_cases_reported
    context_vars['reported_totals'] = [reported_current_month_total, reported_previous_month_total]

    violence_cases_gem = []
    gem_current_month_total, gem_previous_month_total = 0, 0
    for location in locations:
        violence_current_month_value, violence_previous_month_value = 0, 0
        if location.id in violence_cases_gem_current_month:
            gem_current_month_total += violence_cases_gem_current_month[location.id]
            violence_current_month_value = violence_cases_gem_current_month[location.id]
        if location.id in violence_cases_gem_previous_month:
            gem_previous_month_total += violence_cases_gem_previous_month[location.id]
            violence_previous_month_value = violence_cases_gem_previous_month[location.id]
        violence_cases_gem.append((location.name, (violence_current_month_value, violence_previous_month_value, location)))
    context_vars['violence_cases_reported_by_gem'] = violence_cases_gem
    context_vars['gem_totals'] = [gem_current_month_total, gem_previous_month_total]

    context_vars['report_dates'] = [start for start, end in get_month_day_range(datetime.datetime.now(), depth=2)]
    school_report_count = 0
    gem_report_count = 0
    for dr in get_month_day_range(datetime.datetime.now(), depth=2):

        if profile.location.type.name == 'country':
            contacts = Contact.objects.select_related().filter(reporting_location__in=profile.\
                location.get_descendants().filter(type="district"))
        else:
            contacts = Contact.objects.select_related().filter(reporting_location=profile.location)

        school_resp_count = Poll.objects.select_related().get(name="edtrac_violence_girls").responses.filter(
            contact__in = contacts,
            date__range = dr).count()

        gem_resp_count = Poll.objects.select_related().get(name="edtrac_gem_abuse").responses.filter(
            contact__in = contacts,
            date__range = dr).count()

        school_report_count += school_resp_count
        gem_report_count += gem_resp_count

    try:
        context_vars['sch_reporting_percentage'] = 100 * ( school_report_count / (float(len(get_month_day_range(datetime.datetime.now(),
            depth=2))) * school_report_count))
    except ZeroDivisionError:
        context_vars['sch_reporting_percentage'] = 0

    try:
        context_vars['gem_reporting_percentage'] = 100 * ( gem_report_count / (float(len(get_month_day_range(datetime.datetime.now(),
            depth=2))) * gem_report_count))
    except ZeroDivisionError:
        context_vars['gem_reporting_percentage'] = 0

    now = datetime.datetime.now()
    month_ranges = get_month_day_range(now, depth=now.month)
    month_ranges.sort()

    h_teach_month = []
    girls_violence_month = []
    boys_violence_month =[]
    reported_violence_month = []
    gem_month = []

    h_teach_data = []
    gem_data = []
    girls_violence_data = []
    boys_violence_data = []
    reported_violence_data = []

    if profile.is_member_of('Minstry Officials') or profile.is_member_of('UNICEF Officials') or profile.is_member_of('Admins'):
        for month_range in month_ranges:
            gem_month.append(month_range[0].strftime('%B'))
            gem_data.append(get_numeric_data(edtrac_gem_abuse_poll, locations, month_range))

            girls_violence_month.append(month_range[0].strftime('%B'))
            girls_violence_data.append(get_numeric_data(edtrac_violence_girls_poll, locations, month_range))

            boys_violence_month.append(month_range[0].strftime('%B'))
            boys_violence_data.append(get_numeric_data(edtrac_violence_boys_poll, locations, month_range))

            reported_violence_month.append(month_range[0].strftime('%B'))
            reported_violence_data.append(get_numeric_data(edtrac_violence_reported_poll, locations, month_range))
    else:
        for month_range in month_ranges:
            h_teach_month.append(month_range[0].strftime('%B'))
            h_teach_data.append(get_numeric_data(edtrac_violence_girls_poll, locations, month_range))

            gem_month.append(month_range[0].strftime('%B'))
            gem_data.append(get_numeric_data(edtrac_gem_abuse_poll, locations, month_range))

            girls_violence_month.append(month_range[0].strftime('%B'))
            girls_violence_data.append(get_numeric_data(edtrac_violence_girls_poll, locations, month_range))

            boys_violence_month.append(month_range[0].strftime('%B'))
            boys_violence_data.append(get_numeric_data(edtrac_violence_boys_poll, locations, month_range))

            reported_violence_month.append(month_range[0].strftime('%B'))
            reported_violence_data.append(get_numeric_data(edtrac_violence_reported_poll, locations, month_range))

    monthly_data_h_teachers = ';'.join([str(item[0])+'-'+str(item[1]) for item in zip(h_teach_month, h_teach_data)])
    monthly_violence_data_girls = ';'.join([str(item[0])+'-'+str(item[1]) for item in zip(girls_violence_month, girls_violence_data)])
    monthly_violence_data_boys = ';'.join([str(item[0])+'-'+str(item[1]) for item in zip(boys_violence_month, boys_violence_data)])
    monthly_violence_data_reported = ';'.join([str(item[0])+'-'+str(item[1]) for item in zip(reported_violence_month, reported_violence_data)])
    monthly_data_gem = ';'.join([str(item[0])+'-'+str(item[1]) for item in zip(gem_month, gem_data)])

    context_vars['monthly_data_gem'] = monthly_data_gem
    context_vars['monthly_violence_data_girls'] = monthly_violence_data_girls
    context_vars['monthly_violence_data_boys'] = monthly_violence_data_boys
    context_vars['monthly_violence_data_reported'] = monthly_violence_data_reported
    context_vars['monthly_data_h_teach'] = monthly_data_h_teachers
    context_vars['schools_responding_to_all_questions'] = total_number_of_schools_that_responded_to_all_violence_questions(locations, current_month)

    if profile.is_member_of('Minstry Officials') or profile.is_member_of('UNICEF Officials') or profile.is_member_of('Admins'):
        return render_to_response('education/admin/admin_violence_details.html', context_vars, RequestContext(req))
    elif profile.is_member_of('DEO'):
        context_vars['location_name'] = profile.location
        return render_to_response('education/deo/deo2_violence_details.html', context_vars, RequestContext(req))

def __schools_reporting(poll_name, time_range, locations):
    poll = Poll.objects.get(name=poll_name)
    schools = NumericResponsesFor(poll).forDateRange(time_range).forLocations(locations).groupBySchools().keys()
    return set(schools)

def total_number_of_schools_that_responded_to_all_violence_questions(locations, month_range):
    schools_responding_re_boys = __schools_reporting("edtrac_violence_boys", month_range, locations)
    schools_responding_re_girls = __schools_reporting("edtrac_violence_girls", month_range, locations)
    schools_responding_re_reporting = __schools_reporting("edtrac_violence_reported", month_range, locations)
    return len(schools_responding_re_boys & schools_responding_re_girls & schools_responding_re_reporting)

def __get_school_name_from(response):
    try:
        school_name = response.contact.emisreporter.schools.all()[0].name
    except IndexError:
        school_name = None
    return school_name

def __get_responses_for(poll_name):
    responses_for_all_questions = Response.objects.filter(poll__name__in =["edtrac_violence_girls","edtrac_violence_boys","edtrac_violence_reported"])
    return responses_for_all_questions.filter(poll__name = poll_name)

class DistrictViolenceDetails(TemplateView):
    template_name = "education/dashboard/district_violence_detail.html"

    def get_context_data(self, **kwargs):
        context = super(DistrictViolenceDetails, self).get_context_data(**kwargs)

        location = Location.objects.filter(type="district").get(pk=int(self.kwargs.get('pk'))) or self.request.user.get_profile().location

        schools = School.objects.filter(
            pk__in = EmisReporter.objects.filter(reporting_location=location).values_list('schools__pk', flat=True))

        school_case = []
        month_now, month_before = get_month_day_range(datetime.datetime.now(), depth=2)
        totalViolence = 0
        nowViolence = 0
        beforeViolence = 0
        for school in schools:
            # optimize with value queries
            now_data = get_numeric_report_data( 'edtrac_headteachers_abuse', time_range = month_now, school = school,
                to_ret = 'sum', belongs_to = 'schools')

            before_data = get_numeric_report_data('edtrac_headteachers_abuse', time_range = month_before, school = school,\
                to_ret = 'sum', belongs_to = 'schools')

            data = int(now_data + before_data)
            totalViolence += data
            nowViolence += now_data
            beforeViolence += before_data

            if now_data > 0 or before_data > 0:
                school_case.append((school, now_data, before_data, data))

        context['totalViolence'] = totalViolence
        context['nowViolence'] = nowViolence
        context['beforeViolence'] = beforeViolence

        context['location'] = location
        context['school_vals'] = school_case

        context['month_now'] = month_now[0]
        context['month_before'] = month_before[0]

        return context


class AttendanceAdminDetails(TemplateView):
    template_name = "education/admin/attendance_details.html"

    def get_context_data(self, **kwargs):

        context = super(AttendanceAdminDetails, self).get_context_data(**kwargs)
        #TODO: proper drilldown of attendance by school
        # National level ideally "admin" and can be superclassed to suit other roles

        profile = self.request.user.get_profile()
        context['role_name'] = profile.role.name
        if profile.is_member_of("Admins") or profile.is_member_of("Ministry Officials") or profile.is_member_of('UNICEF Officials'):
            names = list(set(EmisReporter.objects.exclude(reporting_location=None).filter(reporting_location__type="district").\
            values_list('reporting_location__name',flat=True)))
            locations = Location.objects.filter(name__in=names).order_by("name")
            context['total_disticts'] = locations.count()

        headings = [ 'Location', 'Boys P3', 'Boys P6', 'Girls P3', 'Girls P6', 'Female Teachers', "Male Teachers"]
        context['headings'] = headings
        context['week'] = datetime.datetime.now()
        context['location'] = profile.location
        return context


# search functionality
def search_form(req):

    searchform = SearchForm()
    if req.method == 'POST':
        searchform = SearchForm(req.POST)
        if searchform.is_valid():
            searchform.save()
    return render_to_response(
        'education/partials/search-form.html',
            {'form': searchform},
        RequestContext(req)
    )

class ProgressAdminDetails(TemplateView):
    template_name = "education/progress/admin_progress_details.html"

    def get_context_data(self, **kwargs):
        context = super(ProgressAdminDetails, self).get_context_data(**kwargs)
        context['progress'] = list_poll_responses(Poll.objects.get(name="edtrac_p3curriculum_progress"))
        getcontext().prec = 1
        context['progress_figures'] = get_count_response_to_polls(Poll.objects.get(name="edtrac_p3curriculum_progress"),\
            location=self.request.user.get_profile().location,
            choices = [Decimal(str(key)) for key in themes.keys()])
        return context

CHOICES = [0, 25, 50, 75, 100]
class MealsAdminDetails(TemplateView):
    template_name = "education/admin/admin_meals_details.html"

    def get_context_data(self, **kwargs):
        choices = CHOICES
        context = super(MealsAdminDetails, self).get_context_data(**kwargs)
        context['school_meals_reports'] = get_count_response_to_polls(Poll.objects.get(name="edtrac_headteachers_meals"),\
            month_filter=True, choices=choices)

        context['community_meals_reports'] = get_count_response_to_polls(Poll.objects.get(name="edtrac_smc_meals"),
            month_filter=True, choices=choices, with_percent=True)
        districts = Location.objects.filter(type="district", id__in =\
            EmisReporter.objects.exclude(reporting_location = None).\
                values_list('reporting_location__id', flat=True)).order_by('name').\
                    values_list('name', flat=True)
        # basic filtering for CSS
        districts = [[d, False] for d in districts]
        districts[0][1] = True

        context['districts'] = districts

        return context

# Meals being had at a district
class DistrictMealsDetails(DetailView):
    template_name = "education/admin/district_meal.html"
    context_object_name = "district_meals"
    model = Location

    def get_object(self):
        return self.model.objects.filter(type="district").get(name = self.kwargs.get('name'))

    def get_context_data(self, **kwargs):
        context = super(DistrictMealsDetails, self).get_context_data(**kwargs)
        location = self.get_object()
        choices = CHOICES

        school_meal_reports = get_count_response_to_polls(
            Poll.objects.get(name="edtrac_headteachers_meals"),
            location_name = location.name,
            month_filter=True,
            choices=choices,
            with_range = True,
            with_percent = True
        )
        context['school_meals_reports'] = school_meal_reports

        context['location'] = location
        now = datetime.datetime.now()
        ranges = get_month_day_range(now, depth = now.month)
        ranges.reverse()

        context['date_ranges'] = ranges

        return context

@login_required
def deo_dashboard(req):
    location = req.user.get_profile().location
    return render_to_response("education/deo/deo_dashboard.html", generate_dashboard_vars(location=location), RequestContext(req))

@login_required
def quitters(req):
    quitters = EmisReporter.objects.filter(connection__identity__in=Blacklist.objects.values_list('connection__identity',flat=True))
    return render_to_response('education/partials/reporters/quitters.html',{'quitters':quitters}, RequestContext(req))

class ViolenceDeoDetails(TemplateView):
    template_name = "education/deo/deo_violence_details.html"

    def get_context_data(self, **kwargs):
        context = super(ViolenceDeoDetails, self).get_context_data(**kwargs)
        #context['violence_cases'] = list_poll_responses(Poll.objects.get(name="emis_headteachers_abuse"))
        context['violence_cases'] = poll_response_sum(Poll.objects.get(name="edtrac_headteachers_abuse"),
            location=self.request.user.get_profile().location, month_filter=True)
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ViolenceDeoDetails, self).dispatch(*args, **kwargs)


class ProgressDeoDetails(TemplateView):
    template_name = "education/deo/deo_progress_details.html"

    def get_context_data(self, **kwargs):
        context = super(ProgressDeoDetails, self).get_context_data(**kwargs)
        #TODO mixins and filters
        context['progress'] = list_poll_responses(Poll.objects.get(name="edtrac_p3curriculum_progress"))

        return context

##########################################################################################################
##########################################################################################################
############################ More Generic Views ##########################################################
##########################################################################################################
##########################################################################################################

## management control panel

@login_required
def control_panel(req):
    profile = req.user.get_profile()
    if profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials') or profile.is_member_of('Ministry Officials'):
        return render_to_response('education/partials/control_panel.html', {}, RequestContext(req))
    else:
        return render_to_response('education/partials/control_panel_dist.html',{}, RequestContext(req))

@login_required
def audit_trail(req):
    profile = req.user.get_profile()
    if profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        # aparently the only places where comments are made is functions that involve editing users, reporters, etc.
        revisions = Revision.objects.exclude(comment='').order_by('-date_created').values_list('user__username','comment','date_created')
    else:
        revisions = Revision.objects.exclude(user__username = 'admin', comment='').\
        order_by('-date_created').values_list('user__username','comment','date_created')
    return render_to_response('education/admin/audit_trail.html',{'revisions':revisions}, RequestContext(req))

class DistrictViolenceCommunityDetails(DetailView):
    context_object_name = "district_violence"
    model = Location

    def get_context_data(self, **kwargs):
        context = super(DistrictViolenceCommunityDetails, self).get_context_data(**kwargs)
        location = Location.objects.filter(type="district").get(pk=int(self.kwargs.get('pk'))) or self.request.user.get_profile().location
        emis_reporters = EmisReporter.objects.filter(groups__name="GEM", connection__in =\
            Poll.objects.get(name="edtrac_gem_abuse").responses.values_list('contact__connection',flat=True))
        context['location'] = location
        context['reporters'] = emis_reporters
        context['month'] = datetime.datetime.now()
        return context


# Progress happening in a district
class DistrictProgressDetails(DetailView):
    context_object_name = "district_progress"
    model = Location
    #TODO provide filters
    def get_context_data(self, **kwargs):
        context = super(DistrictProgressDetails, self).get_context_data(**kwargs)
        location = Location.objects.filter(type="district").get(pk=int(self.kwargs.get('pk')))
        context['location'] = location
        return context



##########################################################################################################
##########################################################################################################
################################ Other handy views for EduTrac ############################################
##########################################################################################################
##########################################################################################################

HEADINGS = ['District', 'Absent (%) This week', 'Absent (%) Last week']
#define location and school for p3 and p6 students
locale = Location.objects.exclude(type="country").filter(type="district")


@login_required
def boysp3_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    select_location = Location.objects.get(id=location_id)

    school_data, existing_data = view_stats_by_school(location_id,'edtrac_boysp3_enrollment','edtrac_boysp3_attendance')

    return render_to_response("education/boysp3_district_attd_detail.html", { 'location':select_location,\
                                                                              'location_data':school_data,
                                                                              'week':datetime.datetime.now(),
                                                                              'headings' : ['School','Data', 'Current Week (%)', 'Week before (%)']}, RequestContext(req))

@login_required
def boysp6_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    select_location = Location.objects.get(id=location_id)

    school_data, existing_data = view_stats_by_school(location_id,'edtrac_boysp6_enrollment','edtrac_boysp6_attendance')

    return render_to_response("education/boysp6_district_attd_detail.html", { 'location':select_location,\
                                                                              'location_data':school_data,
                                                                              'week':datetime.datetime.now(),
                                                                              'headings' : ['School','Data','Current Week (%)', 'Week before (%)']}, RequestContext(req))

@login_required
def girlsp3_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    select_location = Location.objects.get(id=location_id)

    school_data, existing_data = view_stats_by_school(location_id,'edtrac_girlsp3_enrollment','edtrac_girlsp3_attendance')

    return render_to_response("education/girlsp3_district_attd_detail.html", { 'location':select_location,\
                                                                              'location_data':school_data,
                                                                              'week':datetime.datetime.now(),
                                                                              'headings' : ['School','Data','Current Week (%)', 'Week before (%)']}, RequestContext(req))

@login_required
def girlsp6_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    select_location = Location.objects.get(id=location_id)

    school_data, existing_data = view_stats_by_school(location_id,'edtrac_girlsp6_enrollment','edtrac_girlsp6_attendance')

    return render_to_response("education/girlsp6_district_attd_detail.html", { 'location':select_location,\
                                                                              'location_data':school_data,
                                                                              'week':datetime.datetime.now(),
                                                                              'headings' : ['School','Data','Current Week (%)', 'Week before (%)']}, RequestContext(req))

@login_required
def female_t_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    select_location = Location.objects.get(id=location_id)

    school_data, existing_data = view_stats_by_school(location_id,'edtrac_f_teachers_deployment','edtrac_f_teachers_attendance')

    return render_to_response("education/female_t_district_attd_detail.html", { 'location':select_location,\
                                                                              'location_data':school_data,
                                                                              'week':datetime.datetime.now(),
                                                                              'headings' : ['School','Data','Current Week (%)', 'Week before (%)']}, RequestContext(req))

@login_required
def male_t_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    select_location = Location.objects.get(id=location_id)

    school_data, existing_data = view_stats_by_school(location_id,'edtrac_m_teachers_deployment','edtrac_m_teachers_attendance')

    return render_to_response("education/male_t_district_attd_detail.html", { 'location':select_location,\
                                                                              'location_data':school_data,
                                                                              'week':datetime.datetime.now(),
                                                                              'headings' : ['School','Data','Current Week (%)', 'Week before (%)']}, RequestContext(req))

def boys_p3_attendance(req, **kwargs):
    profile = req.user.get_profile()
    location = profile.location
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        """
        This view shows data by district
        """
        locations = Location.objects.exclude(type="country").filter(type="district", name__in=\
            EmisReporter.objects.select_related().distinct().values_list('reporting_location__name', flat=True)).order_by("name")
        # return view that will give school-based views
        # --> ref function just below this <---
        return boys_p3_attd_admin(req, locations=locations)
    else:
        #DEO
        dates = kwargs.get('dates')
        schools = School.objects.filter(location=location)

        to_ret = []
        for school in schools:
            temp = [school]
            for d in dates:
                temp.extend(return_absent('edtrac_boysp3_attendance', 'edtrac_boysp3_enrollment', school = school, date_week=d))
            to_ret.append(temp)
        to_ret.sort(key = operator.itemgetter(1)) # sort by current month data
        return {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location':location
            }

def boys_p3_attd_admin(req, **kwargs):
    """
    Helper function to get differences in absenteeism across districts.
    """
    # P3 attendance /// what to show an admin or Ministry official
    locations = kwargs.get('locations')

    to_ret = return_absent('edtrac_boysp3_attendance', 'edtrac_boysp3_enrollment', locations)

    return {'location_data':to_ret, 'headings': HEADINGS, 'week':datetime.datetime.now()}


def boys_p6_attendance(req):
    profile = req.user.get_profile()
    location = profile.location
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        locations = Location.objects.exclude(type="country").filter(type="district", name__in=\
        EmisReporter.objects.values_list('reporting_location__name', flat=True)).distinct().order_by("name")
        return boys_p6_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)
        to_ret = []
        for school in schools:
            temp = [school]
            temp.extend(return_absent('edtrac_boysp6_attendance', 'edtrac_boysp6_enrollment', school = school))
            to_ret.append(temp)

        to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

        return  {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            }

def boys_p6_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for P6 boys.
    """
    # P6 attendance /// what to show an admin or Ministry official
    to_ret = return_absent('edtrac_boysp6_attendance', 'edtrac_boysp6_enrollment', locations=locations)

    return {'location_data':to_ret,'headings':HEADINGS,'week':datetime.datetime.now()}

def girls_p3_attendance(req):
    location = req.user.get_profile().location
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        locations = Location.objects.exclude(type="country").filter(type="district", name__in=\
            EmisReporter.objects.values_list('reporting_location__name', flat=True)).distinct().order_by("name")
        return girls_p3_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)
        to_ret = []
        for school in schools:
            temp = [school]
            temp.extend(return_absent('edtrac_girlsp3_attendance', 'edtrac_girlsp3_enrollment', school = school))
            to_ret.append(temp)

        to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

        return  {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            }
def girls_p3_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for P3 girls
    """
    to_ret = return_absent('edtrac_girlsp3_attendance', 'edtrac_girlsp3_enrollment', locations=locations)
    return {'location_data':to_ret,'headings':HEADINGS,'week':datetime.datetime.now()}


def girls_p6_attendance(req):
    location = req.user.get_profile().location
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        locations = Location.objects.exclude(type="country").filter(type="district", name__in=\
            EmisReporter.objects.values_list('reporting_location__name', flat=True)).distinct().order_by("name")
        return girls_p6_attd_admin(req, locations=locations)
    else:

        #DEO
        schools = School.objects.filter(location=location)
        to_ret = []
        for school in schools:
            temp = [school]
            temp.extend(return_absent('edtrac_girlsp6_attendance', 'edtrac_girlsp6_enrollment', school = school))
            to_ret.append(temp)

        to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

        return {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            }
def girls_p6_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for P6 girls
    """
    to_ret = return_absent('edtrac_girlsp6_attendance', 'edtrac_girlsp6_enrollment', locations=locations)
    return {'location_data':to_ret, 'headings':HEADINGS, 'week':datetime.datetime.now()}

def female_teacher_attendance(req):
    location = req.user.get_profile().location
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        locations = Location.objects.exclude(type="country").filter(type="district", name__in=\
            EmisReporter.objects.distinct().values_list('reporting_location__name',flat=True)).order_by("name")
        return female_teacher_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)
        to_ret = []
        for school in schools:
            temp = [school]
            temp.extend(return_absent('edtrac_f_teachers_attendance', 'edtrac_f_teachers_deployment', school = school))
            to_ret.append(temp)

        to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

        return  {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            }
def female_teacher_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for all female teachers
    """
    to_ret = return_absent('edtrac_f_teachers_attendance', 'edtrac_f_teachers_deployment', locations=locations)
    return {'location_data':to_ret,
             'headings':HEADINGS,
             'week':datetime.datetime.now()}

def male_teacher_attendance(req):
    location = req.user.get_profile().location
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        locations = Location.objects.exclude(type="country").filter(type="district", name__in=\
            EmisReporter.objects.distinct().values_list('reporting_location__name',flat=True)).order_by("name")
        return male_teacher_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)
        to_ret = []
        for school in schools:
            temp = [school]
            temp.extend(return_absent('edtrac_m_teachers_attendance', 'edtrac_m_teachers_deployment', school = school))
            to_ret.append(temp)

        to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

        return {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            }

def male_teacher_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for all female teachers
    """
    to_ret = return_absent('edtrac_m_teachers_attendance', 'edtrac_m_teachers_deployment', locations=locations)
    return {'location_data':to_ret, 'headings':HEADINGS, 'week':datetime.datetime.now()}

def male_head_teacher_attendance(req):
    location = req.user.get_profile().location
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        schools = School.objects.filter(location__name__in=EmisReporter.objects.distinct().\
        filter(reporting_location__type = 'district').values_list('reporting_location__name', flat=True))
    else:
        #DEO
        schools = School.objects.filter(location=location)
    data_to_render = []
    for school in schools:
        #TODO separate male and female head teachers
        data = poll_response_sum(Poll.objects.get(name="edtrac_head_teachers_attendance"),month_filter='weekly',location=school.location)
        data_to_render.append(
            [
                school,
                school.location,
                data
            ]
        )
    return render_to_response(
        'education/partials/male_head_teacher_attendance.html',
            {
            'week':datetime.datetime.now(),
            'headings':['School', 'District', 'Number'],
            'location_data': data_to_render
        },
        RequestContext(req)
    )

def female_head_teacher_attendance(req):
    location = req.user.get_profile().location
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        schools = School.objects.filter(location__name__in= EmisReporter.objects.distinct().\
            select_related().filter(reporting_location__type = 'district').values_list('reporting_location__name', flat=True))

    else:
        #DEO
        schools = School.objects.select_related().filter(location=location).order_by("name", "location__name")
    data_to_render = []
    for school in schools:
        #TODO separate male and female head teachers
        data = poll_response_sum(Poll.objects.get(name="edtrac_head_teachers_attendance"),month_filter='weekly',location=school.location)
        data_to_render.append(
            [
                school,
                school.location,
                data
            ]
        )
    return render_to_response(
        'education/partials/female_head_teacher_attendance.html',
            {
            'week':datetime.datetime.now(),
            'headings':['School', 'District', 'Number'],
            'location_data': data_to_render
        },

        RequestContext(req)
    )

@login_required
def time_range_boysp3(req):
    return view_stats(req,
        enrol_deploy_poll='edtrac_boysp3_enrollment',
        attendance_poll='edtrac_boysp3_attendance',
        title='P3 Boys Absenteeism',
        url_name_district = "boysp3-district-attd-detail"
    )

@login_required
def time_range_boysp6(req):
    return view_stats(req,
        enrol_deploy_poll='edtrac_boysp6_enrollment',
        attendance_poll='edtrac_boysp6_attendance',
        title='P6 Boys Absenteeism',
        url_name_district = "boysp6-district-attd-detail"
    )

@login_required
def time_range_girlsp3(req):
    return view_stats(req,
        enrol_deploy_poll='edtrac_girlsp3_enrollment',
        attendance_poll='edtrac_girlsp3_attendance',
        title='P3 Girls Absenteeism',
        url_name_district = "girlsp3-district-attd-detail"
    )

@login_required
def time_range_girlsp6(req):
    return view_stats(req,
        enrol_deploy_poll='edtrac_girlsp6_enrollment',
        attendance_poll='edtrac_girlsp6_attendance',
        title='P6 Girls Absenteeism',
        url_name_district = "girlsp6-district-attd-detail"
    )

@login_required
def time_range_teachers_m(req):
    return view_stats(req,
        enrol_deploy_poll='edtrac_m_teachers_deployment',
        attendance_poll='edtrac_m_teachers_attendance',
        title='Male teachers absenteeism',
        url_name_district = "male-teacher-district-attd-detail"
    )

@login_required
def time_range_teachers_f(req):
    return view_stats(req,
        enrol_deploy_poll='edtrac_f_teachers_deployment',
        attendance_poll='edtrac_f_teachers_attendance',
        title='Female teachers absenteeism',
        url_name_district = "female-teacher-district-attd-detail"
    )

@login_required
def time_range_head_teachers(req):
    """
    Get a date-ranged page for Head teachers
    """

    """
    A function that compute time-ranged data for female teachers. This function is split in two: handling of POST data and
    GET data. It also makes a difference between User groups so you different role players like DEO, Admins, UNICEF
    Officials
    """

    time_range_form = ResultForm()
    locations = Location.objects.filter(type='district').filter(pk__in = EmisReporter.objects.values_list('reporting_location__pk',flat=True))

    if req.method == 'POST':
        # handling of POST data
        time_range_form = ResultForm(data=req.POST)
        to_ret = []
        if time_range_form.is_valid():
            from_date = time_range_form.cleaned_data['from_date']
            to_date = time_range_form.cleaned_data['to_date']
            month_delta = abs(from_date.month - to_date.month)

            date_weeks = []

            if month_delta <= 2: # same month get days in between
                while from_date <= to_date:
                    if from_date.weekday() == 3: #is to_day a Thursday?
                        date_weeks.append(previous_calendar_week(t = from_date)) # get range from Wed to Thur.
                    from_date += datetime.timedelta(days = 1)
            else:
                # case for when more than 2 months is selected
                while from_date <= to_date:
                    #TODO refine data points
                    date_weeks.append([dateutils.month_start(from_date),dateutils.month_end(from_date)])
                    from_date = dateutils.increment(from_date, months = 1)

            # splitting the results by analysing membership of Officials accessing EduTrac
            if req.user.get_profile().is_member_of('Ministry Officials') or\
               req.user.get_profile().is_member_of('Admins') or req.user.get_profile().is_member_of('UNICEF Officials'):
                schools_temp = School.objects.select_related().\
                    filter(pk__in = EmisReporter.objects.select_related().\
                        filter(groups__name = "Head Teachers").values_list('schools__pk',flat=True))

                for location in locations:
                    temp = []
                    # get schools in this location
                    schools = schools_temp.filter(contact__reporting_location__name = location.name).\
                        values_list('contact__emisreporter__schools__pk', flat=True).select_related()
                    location_schools = School.objects.filter(pk__in = schools).select_related()
                    for d in date_weeks:
                        total_attendance = 0 # per school
                        total_deployment = 0 # per school
                        for school in location_schools:
                            deployed = poll_responses_term('edtrac_f_teachers_deployment', belongs_to='schools', school = school )
                            attendance = get_numeric_report_data('edtrac_f_teachers_attendance', school = school,
                                time_range=list(d), to_ret = 'sum')
                            total_attendance += attendance
                            total_deployment += deployed
                        try:
                            percentage = (total_deployment - total_attendance) * 100 / total_deployment
                        except ZeroDivisionError:
                            percentage = '--'
                        temp.append(percentage)

                    to_ret.append([location, temp])
            else:
                #Non admin types
                date_weeks, to_ret = [], []
                date_weeks.append(previous_calendar_week(t = datetime.datetime.now()))
                for location in locations:
                    temp = []
                    # get schools in this location
                    schools = schools_temp.filter(contact__reporting_location__name = location.name).\
                    values_list('contact__emisreporter__schools__pk', flat=True)
                    location_schools = School.objects.filter(pk__in=schools).select_related()
                    for d in date_weeks:
                        total_attendance = 0 # per school
                        total_deployment = 0 # per school
                        for school in location_schools:
                            deployed = poll_responses_term('edtrac_f_teachers_deployment', belongs_to='schools', school = school )
                            attendance = get_numeric_report_data('edtrac_f_teachers_attendance', school = school,
                                time_range=list(d), to_ret = 'sum')
                            total_attendance += attendance
                            total_deployment += deployed
                        try:
                            percentage = (total_deployment - total_attendance) * 100 / total_deployment
                        except ZeroDivisionError:
                            percentage = '--'
                        temp.append(percentage)

                    to_ret.append([location, temp])


            return render_to_response('education/timeslider_base.html', {'form':time_range_form, 'dataset':to_ret,
                                                                         'title':'Female Teacher Absenteeism',
                                                                         'url_name':"female-teacher-district-attd-detail",
                                                                         'date_batch':date_weeks}, RequestContext(req))
        else:
            return render_to_response('education/timeslider_base.html', {'form':time_range_form,
                                                                         'url_name':"female-teacher-district-attd-detail",
                                                                         'title':'Male Teacher Absenteeism'}, RequestContext(req))
    else:
        # initial GET view is displays difference between 2 weeks of the attendance of female teachers as reported by the Head Teacher
        date_weeks = []
        location_data = []
        # get current week
        date_weeks.append(previous_calendar_week())
        temp_date = datetime.datetime(date_weeks[0][0].year, date_weeks[0][0].month, date_weeks[0][0].day) - datetime.timedelta(days = 1)
        # add previous week to date_weeks list
        date_weeks.append(previous_calendar_week(t = temp_date))
        # cache schools query in memory (these are Schools that have enrollment data)
        schools_temp = Poll.objects.select_related().get(name = 'edtrac_f_teachers_deployment').responses.\
            exclude(contact__emisreporter__schools__name = None).select_related()
        context_vars = {}
        for location in locations:
            temp = []
            # get schools in this location
            schools = schools_temp.filter(contact__reporting_location__name = location.name).\
                values_list('contact__emisreporter__schools__pk', flat=True)
            location_schools = School.objects.filter(pk__in = schools).select_related()
            for d in date_weeks:
                total_attendance = 0 # per school
                total_deployment = 0 # per school
                for school in location_schools:
                    deployed = poll_responses_term('edtrac_f_teachers_deployment', belongs_to='schools', school = school )
                    attendance = get_numeric_report_data('edtrac_f_teachers_attendance', school = school,
                        time_range=list(d), to_ret = 'sum')
                    total_attendance += attendance
                    total_deployment += deployed
                try:
                    percentage = (total_deployment - total_attendance) * 100 / total_deployment
                except ZeroDivisionError:
                    percentage = '--'
                temp.append(percentage)
            try:
                diff = temp[0] - temp[1]
            except TypeError:
                diff = '--'

            location_data.append([location, temp[0], temp[1], diff])
        context_vars.update({'location_data':location_data})
        profile = req.user.get_profile()
        if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
            x = {'url_name':"female-teacher-district-attd-detail", "headings":["District", "Current Week", "Previous Week", "Percentage Change"]}
        else:
            x = {'url_name':"school-detail", "headings":["School", "Current Week", "Previous Week", "Percentage Change"]}
        context_vars.update({'form':time_range_form,'title':'Female Teachers Absenteeism'})
        context_vars.update(x)
        return render_to_response('education/timeslider_base.html', context_vars, RequestContext(req))


def whitelist(request):
    numbers = []
    for c in Connection.objects.exclude(backend__name='yo6200'):
        if not c.identity.strip() in numbers:
            numbers.append(c.identity.strip())
    return render_to_response(
        "education/whitelist.txt",
            {'connections': Connection.objects.exclude(backend__name='yo6200').filter(identity__in=numbers)},
        mimetype="text/plain",
        context_instance=RequestContext(request))

def _reload_whitelists():
    refresh_urls = getattr(settings, 'REFRESH_WHITELIST_URL', None)
    if refresh_urls is not None:
        if not type(refresh_urls) == list:
            refresh_urls = [refresh_urls, ]
        for refresh_url in refresh_urls:
            try:
                status_code = urlopen(refresh_url).getcode()
                if int(status_code / 100) == 2:
                    continue
                else:
                    return False
            except Exception as e:
                return False
        return True
    return False

def _addto_autoreg(connections):
    for connection in connections:
        if not connection.contact and\
           not ScriptProgress.objects.filter(script__slug='emis_autoreg', connection=connection).count():
            ScriptProgress.objects.create(script=Script.objects.get(slug="edtrac_autoreg"),\
                connection=connection)

@login_required
def add_connection(request):
    form = NewConnectionForm()
    if request.method == 'POST':
        form = NewConnectionForm(request.POST)
        connections = []
        if form.is_valid():
            identity = form.cleaned_data['identity']
            identity, backend = assign_backend(str(identity.strip()))
            # create
            connection, created = Connection.objects.get_or_create(identity=identity, backend=backend)
            # in case a duplicate process does exist, delete it
            ScriptProgress.objects.filter(connection=connection).delete()
            connections.append(connection)
            other_numbers = request.POST.getlist('other_nums')
            if len(other_numbers) > 0:
                for number in other_numbers:
                    identity, backend = assign_backend(str(number.strip()))
                    connection, created = Connection.objects.get_or_create(identity=identity, backend=backend)
                    connections.append(connection)
            _addto_autoreg(connections)
            _reload_whitelists()
            #            time.sleep(2)
            return render_to_response('education/partials/addnumbers_row.html', {'object':connections, 'selectable':False}, RequestContext(request))

    return render_to_response("education/partials/new_connection.html", {'form':form}, RequestContext(request))

@login_required
def delete_connection(request, connection_id):
    connection = get_object_or_404(Connection, pk=connection_id)
    connection.delete()
    _reload_whitelists()
    return render_to_response("education/partials/connection_view.html", {'object':connection.contact }, context_instance=RequestContext(request))


@login_required
def comments(req):
    profile = req.user.get_profile()
    if profile.is_member_of('Admins') or profile.is_member_of('Ministry Officials') or profile.is_member_of('UNICEF Officials'):
        comments = [(r.get_commentable_display(), r.comment, r.user, r.get_reporting_period_display(),
                     get_range_on_date(r.reporting_period, r) )
        for r in ReportComment.objects.order_by('-report_date')]
    else:
        # DFO/DEO should get only information on their districts
        comments = [(r.get_commentable_display(), r.comment, r.user, r.get_reporting_period_display(),
                     get_range_on_date(r.reporting_period, r))
        for r in ReportComment.objects.filter(user__profile__location=profile.location).order_by('-report_date')]

    return render_to_response('education/partials/comments.html', {'data_set':comments}, RequestContext(req))

@login_required
def new_comment(req):
    report_comment_form = ReportCommentForm(initial = {'user':req.user.pk})
    if req.method == 'POST':
        report_comment_form = ReportCommentForm(req.POST)
        if report_comment_form.is_valid():
            with reversion.create_revision():
                report_comment_form.save()
                reversion.set_comment('wrote a comment')
                return HttpResponseRedirect(reverse('comments'))
        else:
            return render_to_response('education/partials/new_comment.html',
                    {'form':report_comment_form}, RequestContext(req))
    else:
        return render_to_response('education/partials/new_comment.html',{'form':report_comment_form}, RequestContext(req))

@login_required
def edit_comment(req, report_comment_pk):
    report_comment = get_object_or_404(ReportComment, pk=report_comment_pk)
    report_comment_form = ReportCommentForm(instance=report_comment)
    if req.method == 'POST':
        report_comment_form = ReportCommentForm(instance=report_comment, data=req.POST)
        if report_comment_form.is_valid():
            with reversion.create_revision():
                report_comment_form.save()
                reversion.set_comment('edited comment')
            return HttpResponseRedirect(reverse('comments'))
        else:
            return render_to_response('education/partials/edit_comment.html', {'form':report_comment_form},
                RequestContext(req))
    else:
        return render_to_response('education/partials/edit_comment.html', {'form':report_comment_form},
            RequestContext(req))

@login_required
def delete_comment(req, report_comment_pk):
    report_comment = get_object_or_404(ReportComment, pk=report_comment_pk)
    if req.method == 'POST':
        with reversion.create_revision():
            report_comment.delete()
            reversion.set_comment('deleted comment')
        return HttpResponse(status=200)

@login_required
def delete_reporter(request, reporter_pk):
    reporter = get_object_or_404(EmisReporter, pk=reporter_pk)
    reporter_name = reporter.name
    if request.method == 'POST':
        with reversion.create_revision():
            reversion.set_comment('deleted %s'%reporter_name)
            reporter.delete()
    return HttpResponse(status=200)

@login_required
def edit_reporter(request, reporter_pk):
    reporter = get_object_or_404(EmisReporter, pk=reporter_pk)
    reporter_group_name = reporter.groups.all()[0].name

    if request.method == 'POST':
        reporter_form = EditReporterForm(instance=reporter,data=request.POST)
        if reporter_form.is_valid():
            with reversion.create_revision():
                reporter_form.save()
                reversion.set_comment('edited %s details' % reporter.name)

            saved_reporter_grp = EmisReporter.objects.get(pk=reporter_pk).groups.all()[0].name
            if reporter.default_connection and reporter.groups.count() > 0:
                # remove from other scripts
                # if reporter's groups remain the same.
                if reporter_group_name == saved_reporter_grp:
                    pass
                else:
                    ScriptProgress.objects.exclude(script__slug="edtrac_autoreg").filter(connection=reporter.default_connection).delete()
                    _schedule_teacher_weekly_scripts(reporter.groups.all()[0], reporter.default_connection, ['Teachers'])
                    _schedule_weekly_scripts(reporter.groups.all()[0], reporter.default_connection, ['Head Teachers', 'SMC'])


                    _schedule_monthly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_head_teachers_monthly', 'last', ['Head Teachers'])
                    _schedule_monthly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_gem_monthly', 20, ['GEM'])
                    _schedule_monthly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_smc_monthly', 5, ['SMC'])


                    _schedule_termly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_smc_termly', ['SMC'])
                    _schedule_termly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_p3_enrollment_headteacher_termly', ['Head Teachers'])
                    _schedule_termly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_p6_enrollment_headteacher_termly', ['Head Teachers'])
                    _schedule_termly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_teacher_deployment_headteacher_termly', ['Head Teachers'])

            return redirect("reporter-detail", pk=reporter.pk)
    else:
        if reporter.schools.exists():
            reporter_form = EditReporterForm(instance=reporter, initial={'schools':reporter.schools.all()[0]})
        else:
            reporter_form = EditReporterForm(instance=reporter)
    return render_to_response('education/edit_reporter.html',
            {'reporter_form': reporter_form,
             'reporter': reporter},
        context_instance=RequestContext(request))

@login_required
def add_schools(request):
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        schools = []
        if form.is_valid():
            names = filter(None, request.POST.getlist('name'))
            locations = request.POST.getlist('location')
            if len(names) > 0:
                for i, name in enumerate(names):
                    location = Location.objects.get(pk=int(locations[i]))
                    name, created = School.objects.get_or_create(name=name, location=location)
                    schools.append(name)
                return render_to_response('education/partials/addschools_row.html',
                        {'object':schools, 'selectable':False}, RequestContext(request))
    else:
        form = SchoolForm()
    return render_to_response('education/deo/add_schools.html',
            {'form': form,
             }, context_instance=RequestContext(request))

@login_required
def delete_school(request, school_pk):
    school = get_object_or_404(School, pk=school_pk)
    school_name = school.name

    if request.method == 'POST':
        with reversion.create_revision():
            school.delete()
            reversion.set_comment("%s deleted %s"%(request.user.username, school_name))

    return HttpResponse(status=200)

@login_required
def edit_school(request, school_pk):
    school = get_object_or_404(School, pk=school_pk)
    school_form = SchoolForm(instance=school)
    school_name = school.name
    if request.method == 'POST':
        school_form = SchoolForm(instance=school,
            data=request.POST)
        if school_form.is_valid():
            with reversion.create_revision():
                school_form.save()
                reversion.set_comment('edited %s' %  school_name)
        else:
            return render_to_response('education/partials/edit_school.html'
                , {'school_form': school_form, 'school'
                : school},
                context_instance=RequestContext(request))
        return render_to_response('/education/partials/school_row.html',
                {'object':School.objects.get(pk=school_pk),
                 'selectable':True},
            context_instance=RequestContext(request))
    else:
        return render_to_response('education/partials/edit_school.html',
                {'school_form': school_form,
                 'school': school},
            context_instance=RequestContext(request))


@login_required
def school_detail(request, school_id):
    school = School.objects.get(id=school_id)
    today = date.today()
    month_ranges = get_month_day_range(today, depth=today.month)
    month_ranges.reverse()

    slug_list = ['girlsp3', 'boysp3', 'girlsp6', 'boysp6']
    slug_list_tr = ['f_teachers', 'm_teachers']

    monthly_data = []
    monthly_data_teachers = []
    monthly_data_head_teachers = []
    monthly_data_violence = []
    monthly_data_meals = []

    for month_range in month_ranges:
        monthly_data.append(
            [return_absent_month(
                'edtrac_'+ '%s'%slug + '_attendance',
                'edtrac_'+ '%s'%slug + '_enrollment',
                month_range = month_range,
                school = school)
             for slug in slug_list])
        monthly_data_teachers.append(
            [return_absent_month(
                'edtrac_'+'%s'%slug + '_attendance',
                'edtrac_'+'%s'%slug + '_deployment', month_range = month_range, school=school) for slug in slug_list_tr])

    reporters = []
    reps = school.emisreporter_set.values()
    for rep in reps:
        r = EmisReporter.objects.get(id=rep['id'])
        reporters.append(r)


    boys_p3_enrolled = poll_responses_term('edtrac_boysp3_enrollment', belongs_to='schools', school = school)
    boys_p6_enrolled = poll_responses_term('edtrac_boysp6_enrollment', belongs_to='schools', school = school)
    girls_p3_enrolled = poll_responses_term('edtrac_girlsp3_enrollment', belongs_to='schools', school = school)
    girls_p6_enrolled = poll_responses_term('edtrac_girlsp6_enrollment', belongs_to='schools', school = school)
    m_teachers_deployed = poll_responses_term('edtrac_m_teachers_deployment', belongs_to = 'schools', school = school)
    f_teachers_deployed = poll_responses_term('edtrac_f_teachers_deployment', belongs_to = 'schools', school = school)
    return render_to_response("education/school_detail.html", {\
        'school_name': school.name,
        'months' : [d_start for d_start, d_end in month_ranges],
        'monthly_data' : monthly_data,
        'monthly_data_teachers' : monthly_data_teachers,
        'monthly_data_head_teachers': monthly_data_head_teachers,
        'monthly_data_violence' : monthly_data_violence,
        'monthly_data_meals' : monthly_data_meals,
        'reporters' : reporters,
        'boys_p3_enrolled': boys_p3_enrolled,
        'boys_p6_enrolled': boys_p6_enrolled,
        'girls_p3_enrolled' : girls_p3_enrolled,
        'girls_p6_enrolled' : girls_p6_enrolled,
        'm_teachers_deployed': m_teachers_deployed,
        'f_teachers_deployed': f_teachers_deployed
    }, RequestContext(request))

# analytics specific for emis {copy, but adjust to suit your needs}
@login_required
def to_excel(request, start_date=None, end_date=None, district_id=None):
    return create_excel_dataset(request, start_date, end_date, district_id)

@login_required
def school_reporters_to_excel(req):
    book = xlwt.Workbook()
    all_schools = School.objects.all()
    sheet = book.add_sheet('School Reporters')
    headings = ['School', 'Reporters']
    rowx = 0
    for colx, value in enumerate(headings):
        sheet.write(rowx, colx, value)
    sheet.set_panes_frozen(True)
    sheet.set_horz_split_pos(rowx+1)
    sheet.set_remove_splits(True)
    for row in all_schools:
        rowx += 1
        for colx, value in enumerate([row.name, ', '.join([reporter.name for reporter in row.emisreporter_set.all()])]):
            sheet.write(rowx, colx, value)

    response = HttpResponse(mimetype="application/vnd.ms-excel")
    response['Content-Disposition'] = 'attachment; filename=school_reporters_data.xls'
    book.save(response)
    return response


@login_required
def system_report(req=None):
    book = xlwt.Workbook()
    school_dates = [
        getattr(settings, 'SCHOOL_TERM_START'),
        getattr(settings, 'SCHOOL_TERM_END'),
    ]
    first_date = school_dates[0]
    last_date = school_dates[1]
    date_bunches = []
    while first_date <= last_date:
        tmp = get_day_range(first_date)
        first_date = tmp[0]
        date_bunches.append(get_day_range(first_date))
        first_date = dateutils.increment(first_date, weeks=1)

    profile = req.user.get_profile()

    enrolled_answered = \
        EnrolledDeployedQuestionsAnswered.objects.select_related()

    headings = ['School'] + [d.strftime("%d/%m/%Y") for d, _ in date_bunches]

    if profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        district_names = enrolled_answered.values_list(
            'school__location__name', flat=True
        ).distinct()
    else:
        location = profile.location
        district_names = [location.name]

    district_schools = {}
    for dn in district_names:
        district_schools[dn] = School.objects.select_related().filter(
            pk__in=enrolled_answered.filter(
                school__location__name=dn
            ).values_list('school__pk', flat=True)).order_by('name')

    polls = Poll.objects.select_related().filter(
        Q(name__icontains="boys")
        | Q(name__icontains="girls")
        | Q(name='edtrac_f_teachers_attendance')
        | Q(name='edtrac_m_teachers_attendance')
    )

    for district_name in district_schools.keys():
        container = []

        sheet = book.add_sheet(district_name, cell_overwrite_ok=True)
        rowx = 0
        for colx, val_headings in enumerate(headings):
            sheet.write(rowx, colx, val_headings)
            sheet.set_panes_frozen(True)

            # in general, freeze after last heading row
            sheet.set_horz_split_pos(rowx + 1)

            # if user does unfreeze, don't leave a split there
            sheet.set_remove_splits(True)

        for school in district_schools[district_name]:
            school_vals = [school.name]
            for d_bunch in date_bunches:
                submission_count = 0
                for poll in polls:
                    submission_count += poll.responses.filter(
                            contact__in=school.emisreporter_set.values_list(
                                'connection__contact'),
                        date__range = d_bunch
                        ).count()
                school_vals.extend([submission_count])
            container.append(school_vals)

        for row in container:
            rowx += 1
            for colx, value in enumerate(row):
                sheet.write(rowx, colx, value)

    response = HttpResponse(mimetype="application/vnd.ms-excel")
    response['Content-Disposition'] = 'attachment; filename=SystemReport.xls'
    book.save(response)
    return response


@login_required
def excel_reports(req):
    return render_to_response('education/excelreports/excel_dashboard.html',{},RequestContext(req))

@login_required
def edit_user(request, user_pk=None):
    title=""
    user=User()
    if request.method == 'POST' and request.user.get_profile().role_id == Role.objects.get(name = 'Admins').id:
        if user_pk:
            user = get_object_or_404(User, pk=user_pk)
        user_form = UserForm(request.POST,instance=user,edit=True)

        if user_form.is_valid():
            with reversion.create_revision():
                user = user_form.save()
                if user.groups.count() == 0:
                    group = Group.objects.get(pk=user_form.cleaned_data['groups'][0].pk)
                    user.groups.add(group)
                try:
                    profile=UserProfile.objects.get(user=user)
                    profile.location=user_form.cleaned_data['location']
                    profile.role=Role.objects.get(name=user_form.cleaned_data['groups'][0].name)
                    profile.save()
                except UserProfile.DoesNotExist:
                    UserProfile.objects.create(name=user.first_name,user=user,role=Role.objects.get(pk=user_form.cleaned_data['groups'][0].pk),location=user_form.cleaned_data['location'])

                reversion.set_comment("edited %s's profile" % user.username)

            return HttpResponseRedirect(reverse("emis-users"))

    elif user_pk:
        user = get_object_or_404(User, pk=user_pk)
        user_form = UserForm(instance=user,edit=True)
        title="Editing "+user.username
    else:
        user_form = UserForm(instance=user)

    return render_to_response('education/partials/edit_user.html', {'user_form': user_form,'title':title},
        context_instance=RequestContext(request))

def htattendance(request, start_date=None, end_date=None, district_id=None):
    user_location = get_location(request, district_id)
    dates = get_xform_dates(request)

    smc_htpresent = Poll.objects.get(name='emis_absence').responses.exclude(has_errors=True)\
    .filter(date__range=(dates.get('start'), dates.get('end')))\
    .filter(message__connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all())\
    .order_by('message__date')

    return generic(request,
        model = Poll,
        queryset = smc_htpresent,
        objects_per_page = 50,
        results_title = 'Head Teacher Presence as Reported by SMCs',
        columns = [
            ('school', False, 'school', None),
            ('present', False, 'present', None),
            ('reporting date', False, 'date', None),
        ],
        partial_row = 'education/partials/ht_attendance_row.html',
        partial_header = 'education/partials/partial_header.html',
        base_template = 'education/timeslider_base.html',
        needs_date = True,
        selectable = False,
        dates = get_xform_dates,
    )

def gem_htattendance(request, start_date=None, end_date=None, district_id=None):
    user_location = get_location(request, district_id)
    dates = get_xform_dates(request)

    gem_htpresent = XFormSubmission.objects.filter(xform__keyword='gemteachers').exclude(has_errors=True)\
    .filter(created__range=(dates.get('start'), dates.get('end')))\
    .filter(connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all())\
    .order_by('created')

    return generic(request,
        model = XFormSubmission,
        queryset = gem_htpresent,
        objects_per_page = 50,
        results_title = 'Head Teacher Presence as Reported by GEM',
        columns = [
            ('school', False, 'school', None),
            ('present', False, 'present', None),
            ('reporting date', False, 'date', None),
        ],
        partial_row = 'education/partials/gemht_attendance_row.html',
        partial_header = 'education/partials/partial_header.html',
        base_template = 'education/timesli`der_base.html',
        needs_date = True,
        selectable = False,
        dates = get_xform_dates,
    )

def meals(request, district_id=None):

    user_location = get_location(request, district_id)
    dates = get_xform_dates(request)

    meals = Poll.objects.get(name='emis_meals').responses.exclude(has_errors=True)\
    .filter(date__range=(dates.get('start'), dates.get('end')))\
    .filter(message__connection__contact__emisreporter__reporting_location__in=user_location.get_descendants(include_self=True).all())

    return generic(request,
        model = Poll,
        queryset = meals,
        objects_per_page = 50,
        results_title = 'Pupils who had Meals at School',
        columns = [
            ('school', False, 'school', None),
            ('estimated number', False, 'number', None),
            ('reporting date', False, 'date', None),
        ],
        partial_row = 'education/partials/meals_row.html',
        partial_header = 'education/partials/partial_header.html',
        base_template = 'education/timeslider_base.html',
        needs_date = True,
        selectable = False,
        dates = get_xform_dates,
    )


@super_user_required
def edit_scripts(request):

    forms = []
    for script in Script.objects.exclude(name='Special Script').order_by('slug'):
        forms.append((script, ScriptsForm(instance=script)))

    if request.method == 'POST':
        script_form = ScriptsForm(request.POST,instance=Script.objects.get(slug=request.POST.get('slug')))
        if script_form.is_valid():
            script_form.save()

    return render_to_response('education/partials/edit_script.html', {'forms': forms, 'management_for': 'scripts'},
        context_instance=RequestContext(request))

def emis_scripts_special(req):
    scripts = Script.objects.exclude(slug__icontains='weekly').exclude(name='Special Script').exclude(slug='edtrac_autoreg').order_by('slug')

    if req.method == 'POST':
        checked_numbers = req.POST.getlist('checked_numbers')
        checked_numbers = [n for n in checked_numbers if re.match(r'\d+', n)]
        poll_questions = req.POST.getlist('poll_questions')
        poll_scripts = [pq.split('-') for pq in poll_questions] #(poll_id, script_slug)
        d = datetime.datetime.now()
        _script = Script.objects.create(slug=\
        "edtrac_%s %s %s %s:%s:%s"%(d.year,d.month,d.day,d.hour, d.minute, d.second), name="Special Script")

        _poll_scripts = []
        # make sure that the poll/script to sent to just one group not a mixture of groups.
        reporter_group_name = EmisReporter.objects.get(id=checked_numbers[0]).groups.all()[0].name.lower().replace(' ', '_')
        for id, script_slug in poll_scripts:
            if re.search(reporter_group_name, script_slug):
                _poll_scripts.append((id, script_slug))

        for i, li in enumerate(_poll_scripts):
            poll_id, script_slug = li
            _script.steps.add(ScriptStep.objects.create(
                script = _script,
                poll = Poll.objects.get(id = poll_id),
                order = i, # using index for different order???
                rule = ScriptStep.RESEND_MOVEON,
                num_tries = 1,
                start_offset = 60,
                retry_offset = 86400,
                giveup_offset = 86400,
            ))
            _script.save()

        if len(checked_numbers) < 25 and len(checked_numbers) > 0:
            # assuming that "all" is not checked
            for reporter in EmisReporter.objects.filter(id__in=checked_numbers).exclude(connection=None):
                sp = ScriptProgress.objects.create(connection=reporter.default_connection, script=_script)
                sp.set_time(datetime.datetime.now()+datetime.timedelta(seconds=90)) # 30s after default cron wait time
                sp.save()
        else:
            # what if the reporting location is different? Would you instead want to poll the different districts?
            single_reporter_location = True # flag
            reporter_location = EmisReporter.objects.filter(id__in=checked_numbers).\
            exclude(reporting_location=None).values_list('reporting_location__name', flat=True)
            if reporter_location.count() > 0 and len(set(reporter_location)) > 1:
                single_reporter_location = False
                reporter_location = EmisReporter.objects.filter(reporting_location__type = 'district').\
                values_list('reporting_location__name',flat=True)
            else:
                reporter_location = EmisReporter.objects.filter(reporting_location__type='district').\
                filter(reporting_location__name = reporter_location[0]).values_list('reporting_location__name',flat=True)

            single_school = True
            reporter_schools = EmisReporter.objects.filter(id__in=checked_numbers).\
            exclude(schools=None).values_list('schools__name', flat=True)
            if reporter_schools.count() > 0 and len(set(reporter_schools)) > 1:
                single_school = False
                reporter_schools = EmisReporter.objects.values_list('schools__name',flat=True)
            else:
                reporter_schools = EmisReporter.objects.filter(schools__name=reporter_schools[0]).values_list(
                    'schools__name', flat=True
                )

            if single_reporter_location or single_school:
                for reporter in EmisReporter.objects.filter(schools__name__in=reporter_schools,
                    reporting_location__name__in = reporter_location, groups__name =\
                    ' '.join([i.capitalize() for i in reporter_group_name.replace('_',' ').split()])).\
                exclude(connection=None):
                    sp = ScriptProgress.objects.create(connection=reporter.default_connection, script=_script)
                    sp.set_time(datetime.datetime.now()+datetime.timedelta(seconds=90)) # 30s after default cron wait time
                    sp.save()
            else:
                for reporter in EmisReporter.objects.filter(groups__name =\
                ' '.join([i.capitalize() for i in reporter_group_name.replace('_',' ').split()])).exclude(connection=None):
                    sp = ScriptProgress.objects.create(connection=reporter.default_connection, script=_script)
                    sp.set_time(datetime.datetime.now()+datetime.timedelta(seconds=90)) # 30s after default cron wait time
                    sp.save()

        return HttpResponseRedirect(reverse('emis-contact'))
    else:
        return render_to_response('education/partials/reporters/special_scripts.html',{'scripts':scripts}, RequestContext(req))


def reschedule_scripts(request, script_slug):
    grp = get_script_grp(script_slug)
    if script_slug.endswith('_weekly'):
        reschedule_weekly_polls(grp)
    elif script_slug.endswith('_monthly'):
        reschedule_monthly_polls(grp)
    else:
        if request.POST.has_key('date'):
            date = request.POST.get('date')
        else:
            date = None
        reschedule_termly_polls(grp, date)

    new_scripts = ScriptProgress.objects.filter(script__slug=script_slug)
    if new_scripts:
        new_script_date = new_scripts[0].time
        response = HttpResponse("This Script has been rescheduled to: %s " % new_script_date.strftime("%d-%m-%Y %H:%M"))
        return response
    else:
        return HttpResponse("This script can't be rescheduled. Try again")

class EdtracReporter(ListView):
    model = EmisReporter
    template_name = "education/emisreporter_list.html"
    context_object_name = "reporter_list"

########## Maps #################
def attendance_visualization(req):
    return render_to_response(
        'education/partials/map_attendance.html',
            {
            'geoserver_url':getattr(settings, 'GEOSERVER_URL', 'http://localhost/geoserver')
        },
        context_instance = RequestContext(req))


class AbsenteeismForm(forms.Form):
    error_css_class = 'error'
    select_choices = [('all', '--'),
                      ('P3Boys', 'P3 Boys'), ('P3Girls', 'P3 Girls'), ('P3Pupils', 'P3 Pupils'),
                      ('P6Boys', 'P6 Boys'), ('P6Girls', 'P6 Girls'), ('P6Pupils', 'P6 Pupils'),
                      ('MaleTeachers', 'Male Teachers'), ('FemaleTeachers', 'Female Teachers'),
                      ('Teachers', 'Teachers'),
                      ('MaleHeadTeachers', 'Male Head Teachers'), ('FemaleHeadTeachers', 'Female Head Teachers'),
                      ('HeadTeachers', 'Head Teachers'),
    ]
    from_date = forms.DateTimeField(required=False)
    to_date = forms.DateTimeField(required=False)
    indicator = forms.ChoiceField(choices=select_choices, required=False)

    def clean(self):
        data = self.cleaned_data
        if data.get('from_date') is None or data.get('to_date') is None:
            if is_empty(data.get('indicator')):
                raise forms.ValidationError("Fields blank")
        if data.get('from_date') > data.get('to_date'):
            raise forms.ValidationError("To date less than from date")
        return data

@login_required
def detail_attd(request, district=None):
    locations = get_location_for_absenteeism_view(district, request)
    time_range_depth = 4
    if request.method == 'POST':
        absenteeism_form = AbsenteeismForm(data=request.POST)
        if absenteeism_form.is_valid():
            indicator = absenteeism_form.cleaned_data['indicator']
            week_range = get_date_range(absenteeism_form.cleaned_data['from_date'],
                                        absenteeism_form.cleaned_data['to_date'], time_range_depth)
        else:
            return render_to_response('education/admin/detail_attd.html',
                                      {'form': absenteeism_form}, RequestContext(request))

    else:
        absenteeism_form = AbsenteeismForm(initial={'indicator': 'all'})
        week_range = get_week_date(time_range_depth)
        indicator = "all"

    week_range.reverse()
    config_list = get_polls_for_keyword(indicator)
    collective_result, time_data, reporting_school_percent = get_aggregated_report(locations, config_list, week_range)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in week_range]
    return render_to_response('education/admin/detail_attd.html',
                              {'form': absenteeism_form,
                               'collective_result_keys': [config['collective_dict_key'] for config in config_list],
                               'collective_result': collective_result,
                               'time_data': mark_safe(json.dumps(time_data)),
                               'school_percent' : reporting_school_percent,
                               'weeks': mark_safe(json.dumps(weeks)),
                               "locations": locations},
                              RequestContext(request))


@login_required
def detail_dashboard(request, district=None):
    locations = get_location_for_absenteeism_view(district, request)
    time_range_depth = 4
    if request.method == 'POST':
        absenteeism_form = AbsenteeismForm(data=request.POST)
        if absenteeism_form.is_valid():
            indicator = absenteeism_form.cleaned_data['indicator']
            week_range = get_date_range(absenteeism_form.cleaned_data['from_date'], absenteeism_form.cleaned_data['to_date'], time_range_depth)
        else:
            return render_to_response('education/admin/detail_attd.html',
                                      {'form': absenteeism_form}, RequestContext(request))

    else:
        absenteeism_form = AbsenteeismForm(initial={'indicator': 'all'})
        week_range = get_week_date(time_range_depth)
        indicator = "all"

    week_range.reverse()
    config_list = get_polls_for_keyword(indicator)
    collective_result, time_data, reporting_school_percent = get_aggregated_report(locations, config_list, week_range)
    weeks = ["%s - %s" % (i[0].strftime("%m/%d/%Y"), i[1].strftime("%m/%d/%Y")) for i in week_range]
    return render_to_response('education/admin/detail_attd.html',
                              {'form': absenteeism_form,
                               'collective_result_keys': [config['collective_dict_key'] for config in config_list],
                               'collective_result': collective_result,
                               'time_data': mark_safe(json.dumps(time_data)),
                               'school_percent' : reporting_school_percent,
                               'weeks': mark_safe(json.dumps(weeks)),
                               "locations": locations},
                              RequestContext(request))

@login_required
def detail_attd_school(request, location):
    name = request.GET['school']
    school_id = School.objects.get(name=name, location__name=location).id
    return redirect(reverse('school-detail',args=(school_id,)))


class ExportPollForm(forms.Form):
    error_css_class = 'error'
    select_choices = list(Poll.objects.values_list(*['pk','name']))
    from_date = forms.DateTimeField(required=False)
    to_date = forms.DateTimeField(required=False)
    poll_name = forms.ChoiceField(choices=select_choices, required=False)

    def clean(self):
        data = self.cleaned_data
        if data.get('from_date') is None or data.get('to_date') is None:
            if is_empty(data.get('poll_name')):
                raise forms.ValidationError("Fields blank")
        if data.get('from_date') > data.get('to_date'):
            raise forms.ValidationError("To date less than from date")
        return data


def get_district_parent(reporting_location):
    parent_locations = reporting_location.get_ancestors()
    district_parent = [parent for parent in parent_locations if parent.type.name == 'district']
    return district_parent[0].name


def _format_responses(responses):
    a = []
    for response in responses:
        if response.contact:
            contact = response.contact
            sender = contact
            location_type = contact.reporting_location.type
            reporting_location = contact.reporting_location.name
            if not location_type.name == 'district' and not location_type.name == 'country':
                reporting_location = get_district_parent(contact.reporting_location)
                location_type = 'district'
            school = ", ".join(contact.emisreporter.schools.values_list('name', flat=True))
        else:
            sender = response.message.connection.identity
            location_type = "--"
            reporting_location = "--"
            school = "--"
        date = response.message.date
        if response.poll.type == "t":
            value = response.eav.poll_text_value
        elif response.poll.type == "n":
            if hasattr(response.eav, 'poll_number_value'):
                value = response.eav.poll_number_value
            else:
                value = 0
        elif response.poll.type == 'l':
            value = response.eav.poll_location_value.name
        category = response.categories.values_list('category__name',flat=True)
        if len(category) == 0:
            category = "--"
        else:
            category = ", ".join(category)
        a.append((sender,location_type,reporting_location,school,date,value,category))
    return a


def _get_identity(r):
    return r.default_connection.identity if r.default_connection else "--"


def _format_reporters(reporters):
    return [[r.id,r.name, _get_identity(r),r.reporting_location.type.name, r.reporting_location.name, ", ".join(r.schools.values_list('name', flat=True))] for r in reporters]


@login_required
def edtrac_export_poll_responses(request):
    profile = request.user.get_profile()
    if not (profile.is_member_of('Ministry Officials')
            or profile.is_member_of('Admins')
            or profile.is_member_of(
            'UNICEF Officials')):
        return redirect('/')

    if request.method == 'GET':
        form = ExportPollForm()
    else:
        form = ExportPollForm(data=request.POST)
        if form.is_valid():
            poll = get_object_or_404(Poll, pk=form.cleaned_data['poll_name'])

            responses = poll.responses.all().order_by('-pk')
            to_date = form.cleaned_data['to_date']
            from_date = form.cleaned_data['from_date']
            if from_date and to_date:
                to_date = to_date + timedelta(days=1)
                responses = responses.filter(date__range=[from_date, to_date])

            resp = render_to_response(
                'education/admin/export_poll_responses.csv', {
                    'responses': _format_responses(responses)
                },
                mimetype='text/csv',
                context_instance=RequestContext(request)
            )
            resp['Content-Disposition'] = 'attachment;filename="%s.csv"' \
                                          % poll.name
            return resp

    return render_to_response('education/admin/export_poll_responses.html',
                              {'form': form},
                              RequestContext(request),
                              )

@login_required
def edit_sub_county_reporters(request):
    profile = request.user.get_profile()
    if not (profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials')):
        return redirect('/')

    if request.method == 'GET':
        sub_county_reporters = EmisReporter.objects.filter(reporting_location__type = 'sub_county')
        return render_to_response('education/admin/edit_sub_county_reporters.html', {'reporters':sub_county_reporters},RequestContext(request))


@login_required
def export_sub_county_reporters(request):
    profile = request.user.get_profile()
    if not (profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
            'UNICEF Officials')):
        return redirect('/')

    if request.method == 'GET':
        sub_county_reporters = EmisReporter.objects.filter(reporting_location__type='sub_county')
        resp = render_to_response('education/admin/export_sub_county_reporters.csv',
                                  {'responses': _format_reporters(sub_county_reporters)}, mimetype='text/csv',
                                  context_instance=RequestContext(request))
        resp['Content-Disposition'] = 'attachment;filename="sub_county_reporters.csv"'
        return resp

class ExportMessageForm(forms.Form):
    error_css_class = 'error'
    from_date = forms.DateTimeField(required=False)
    to_date = forms.DateTimeField(required=False)

    def clean(self):
        data = self.cleaned_data
        if data.get('from_date') is None or data.get('to_date') is None:
            raise forms.ValidationError("Fields blank")
        if data.get('from_date') > data.get('to_date'):
            raise forms.ValidationError("To date less than from date")
        return data


def _get_school(m):
    if m.connection.contact.emisreporter.schools.all().exists():
        return m.connection.contact.emisreporter.schools.all()[0]
    return None


def _format_messages(messages):
    return[ [m ,m.connection.contact.reporting_location,_get_school(m),m.connection.contact,m.connection,m.date ] for m in messages]


@login_required
def edtrac_export_error_messages(request):
    profile = request.user.get_profile()
    if not (profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
        'UNICEF Officials')):
        return redirect('/')

    if request.method == 'GET':
        form = ExportMessageForm()
    else:
        form = ExportMessageForm(data=request.POST)
        if form.is_valid():
            messages = Message.objects.exclude(
                connection__identity__in = getattr(settings, 'MODEM_NUMBERS')
            ).filter(direction='I',
                connection__contact__emisreporter__reporting_location__in =\
                locations.get(name__iexact="Uganda").get_descendants(include_self=True).all()
            )
            messages= messages.filter(poll_responses=None) | messages.filter(poll_responses__has_errors=True)
            to_date = form.cleaned_data['to_date']
            from_date = form.cleaned_data['from_date']
            if from_date and to_date:
                messages = messages.filter(date__range=[from_date, to_date])

            resp = render_to_response('education/admin/export_error_messages.csv', {'messages'
                                                                                    : _format_messages(messages)}, mimetype='text/csv',
                context_instance=RequestContext(request))
            resp['Content-Disposition'] = 'attachment;filename="error_messages.csv"'\

            return resp

    return render_to_response('education/admin/export_error_messages.html', {'form':form},RequestContext(request))

def get_schools(request):
    location = request.GET['location']
    list_of_schools = [{'text':'--------------','value':''}]
    if not is_empty(location):
        filtered_schools = School.objects.filter(location=Location.objects.get(pk=location,type__slug='district'))
        location_schools = [{'text':school.name,'value':school.pk} for school in filtered_schools]
        list_of_schools.extend(location_schools)
    return HttpResponse(json.dumps(list_of_schools))
