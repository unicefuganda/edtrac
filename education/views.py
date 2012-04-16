from __future__ import division
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
import django.contrib
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, TemplateView, ListView, CreateView, FormView
from .forms import *
from .models import *
from uganda_common.utils import *
from rapidsms.contrib.locations.models import Location
from generic.views import generic
from generic.sorters import SimpleSorter
from poll.models import Poll
from .reports import *
from .utils import *
from .utils import _schedule_monthly_script, _schedule_termly_script, _schedule_weekly_scripts
from urllib2 import urlopen
from rapidsms.views import login, logout
import  re, datetime, operator, xlwt, exceptions
from datetime import date
#from decimal import getcontext, Decimal
from .utils import themes


Num_REG = re.compile('\d+')

super_user_required=user_passes_test(lambda u: u.groups.filter(name__in=['Admins','DFO']).exists() or u.is_superuser)

def login(req):
    return login(req, template_name="education/admin/admin_dashboard.html")

def logout(req):
    return logout(req, tempalte_name="educatoin/admin/admin_dashboard.html")


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
        if kwargs.has_key('context_vars'):
            context_vars = kwargs['context_vars']
        else:
            context_vars = None
        template_name = kwargs['template_name']
        if not template_name:
            #if no template name is given
            t = "education/index.html"
        else:
            t = "education/%s"%template_name
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

    head_teachers_attendance = get_responses_to_polls(poll_name="edtrac_head_teachers_attendance")

    return render_to_response('education/dashboard/attdance.html', {
        'girlsp3_present' : girlsp3_attendance, 'girlsp3_absent' : girlsp3_absent,
        'boysp3_present' : boysp3_attendance, 'boysp3_absent' : boysp3_absent,
        'girlsp6_present' : girlsp6_attendance, 'girlsp6_absent' : girlsp6_absent,
        'boysp6_present' : boysp6_attendance, 'boysp6_absent' : boysp6_absent,
        'female_teachers_present' : female_teachers_present, 'female_teachers_absent' : female_teachers_absent,
        'male_teachers_present' : male_teachers_present, 'male_teachers_absent' : male_teachers_absent
    } , RequestContext(request))

#TODO provide an attendance view for ministry officials


#VIOLENCE
"""
functions to generate violence specific data to different roles (deo, admin, ministry and others)
"""

def dash_violence(request):
    violence_to_ret = list_poll_responses(Poll.objects.get(name="emis_headteachers_abuse"))
    # this should be equal
    districts = violence_to_ret.keys()
    district_violence_cases = [23, 56, 23, 66]

    return render_to_response('education/dashboard/violence.html',{\
        'x_vals':districts,\
        'y_vals':district_violence_cases
    }, RequestContext(request))

def dash_ministry_violence(request):
    #NOTE: violence and abuse almost similar
    violence = list_poll_responses(Poll.objects.get(name="emis_headteachers_abuse"))
    districts = violence.keys()
    #assumption is still 4 districts
    #dummy data
    district_violence_cases = [23,56, 23, 66]
    dicty = dict(zip(districts, district_violence_cases))
    return render_to_response('education/dashboard/violence.html',
            {'x_vals':districts, 'y_vals' : district_violence_cases, 'dicty' : dicty, 'chart_title':'Violence Cases Recorded'},
        RequestContext(request)
    )


def dash_deo_violence(request):
    #TODO: use months for the x-values
    #filter only values in the district
    location = request.user.get_profile().location
    violence = get_sum_of_poll_response(Poll.objects.get(name="emis_headteachers_abuse"),
        location=location)

    months = ["Jan", "Feb", "March"]
    district_violence = [343,234,64]
    return render_to_response('education/dashboard/violence.html',
            {'x_vals' : months, 'y_vals' : district_violence, 'chart_title':'Violence Cases Recorded'},
        RequestContext(request)
    )

#MEALS
"""
We want to easily populate graphs for deo, admin and ministry roles
"""

def dash_meals(request):
    meal_poll_to_ret = list_poll_responses(Poll.objects.get(name="emis_headteachers_meals"))
    # this should be equal
    districts = meal_poll_to_ret.keys()
    lunches_to_ret = zip(districts, [20, 30, 40, 10])
    return render_to_response('education/dashboard/meals.html', {\
        'lunches':lunches_to_ret,\
        }, RequestContext(request))

def dash_ministry_meals(req):
    meal_poll_responses = list_poll_responses(Poll.objects.get(name="emis_headteachers_meals"))
    districts = meal_poll_responses.keys()
    lunches_to_ret = zip(districts, [10, 20, 30, 40])
    return render_to_response('education/dashboard/meals.html', {
        'lunches':lunches_to_ret}, RequestContext(req))

def dash_deo_meals(req):
    return render_to_response('education/dashboard/meals.html', {}, RequestContext(req))

# Progress code

def dash_progress(request):
    #curriculum progress for p6 and p3
    p3_response = 34
    return render_to_response('education/dashboard/progress.html', {'p3':p3_response}, RequestContext(request))


def dash_admin_progress(req):
    # correspond with group names
    authorized_users = ['Admins', 'Ministry Officials', 'UNICEF Officials']

    authorized_user = False

    profile = req.user.get_profile()

    for auth_user in authorized_users:
        if profile.is_member_of(auth_user):
            authorized_user = True
            break
    on_schedule = 'green'
    behind_schedule = 'orange'
    way_behind_schedule = 'red'

    if authorized_user:
        locations = Location.objects.filter(
            type = "district",
            pk__in = EmisReporter.objects.exclude(
                reporting_location = None,
                schools = None,\
                connection__in = Blacklist.objects.values_list('connection', flat=True)).\
                values_list('reporting_location__pk', flat=True))
        loc_data = []
        for location in locations:
            try:
                c_list = list(
                    curriculum_progress_list("edtrac_p3curriculum_progress", location=location)
                )
                loc_data.append([location, curriculum_progress_mode(c_list)])
            except TypeError:
                loc_data.append([location, 0])

        return render_to_response('education/progress/admin_progress_details.html',
                {'location_data': loc_data}, RequestContext(req))
    else:
        schools = School.objects.filter(pk__in = EmisReporter.objects.filter(reporting_location=profile.location).values_list('schools__pk', flat=True))
        loc_data = []
        p = Poll.objects.get(name='edtrac_p3curriculum_progress')
        for school in schools:
            response_dates = p.responses.filter(contact__connection__in = school.emisreporter_set.\
                values_list('connection',flat=True)).values_list('date', flat=True)
            response = [r.eav.poll_number_value for r in p.responses.\
                filter(contact__connection__in = school.emisreporter_set.values_list('connection',flat=True))]
            response_sieve = zip(response_dates, response)
            response_sieve = sorted(response_sieve, reverse=True)
            try:
                if response_sieve[0][1] is None:
                    loc_data.append([school, 'incorrect response'])
                else:
                    loc_data.append([school, response_sieve[0][1]])
            except IndexError:
                # no or missing data
                loc_data.append([school, 'missing'])
                # clean up
        loc_data = sorted(loc_data, key=operator.itemgetter(1))

        temp = [item for item in loc_data if item[1] == 'missing' or item[1] == 'incorrect response']
        temp_2 = [item for item in loc_data if item not in temp]
        temp_2 = sorted(temp_2, key=operator.itemgetter(1), reverse=True)
        loc_data = temp_2 + temp
        return render_to_response('education/progress/district_progress_details.html',
            {'location_data':loc_data, 'location':profile.location}, RequestContext(req))

def dash_admin_progress_district(req, district_pk):
    location = Location.objects.filter(type="district").get(pk=district_pk)

    schools = School.objects.filter(pk__in = EmisReporter.objects.filter(reporting_location=location).\
        values_list('schools__pk', flat=True)).order_by('name')
    loc_data = []

    p = Poll.objects.get(name='edtrac_p3curriculum_progress')
    for school in schools:
        response_dates = p.responses.filter(contact__connection__in = school.emisreporter_set.\
            values_list('connection',flat=True)).values_list('date', flat=True)

        response = [r.eav.poll_number_value for r in p.responses.\
            filter(contact__connection__in = school.emisreporter_set.values_list('connection',flat=True))]
        response_sieve = zip(response_dates, response)
        response_sieve = sorted(response_sieve, reverse=True)
        try:
            if response_sieve[0][1] is None:
                loc_data.append([school, 'incorrect response'])
            else:
                loc_data.append([school, response_sieve[0][1]])
        except IndexError:
            # no or missing data
            loc_data.append([school, 'missing'])
        # clean up
        loc_data = sorted(loc_data, key=operator.itemgetter(1))
        temp = [item for item in loc_data if item[1] == 'missing' or item[1] == 'incorrect response']
        temp_2 = [item for item in loc_data if item not in temp]
        temp_2 = sorted(temp_2, key=operator.itemgetter(1), reverse=True)
        loc_data = temp_2 + temp

    return render_to_response('education/progress/district_progress_admin_details.html',
            {'location_data':loc_data, 'location':location}, RequestContext(req))


def dash_ministry_progress(request):
    pass


# Meetings
"""
code to implement meetings
"""
def dash_meetings(request):
    message_ids = [poll_response['message_id'] for poll_response in Poll.objects.get(name="emis_meetings").responses.values()]
    all_messages =[msg.text for msg in Message.objects.filter(id__in=message_ids)]
    try:
        to_ret = {}
        set_messages = set(all_messages)
        for msg in set_messages:
            to_ret[int(msg)] = all_messages.count(int(msg))
    except ValueError:
        print "some non numeric values were provided"
    return render_to_response('education/dashboard/meetings.html', {}, RequestContext(request))

def dash_admin_meetings(req):
    return render_to_response("education/admin/admin_meetings.html",{}, RequestContext(req))


def dash_ministry_meetings(req):
    #this is what gets rendered to viewers on the ministry level
    #TODO: use utility functions and compute this figure from other total EMIS reporters
    message_ids = [poll_response['message_id'] for poll_response in Poll.objects.get(name="emis_meetings").responses.values()]
    all_messages =[msg.text for msg in Message.objects.filter(id__in=message_ids)]
    try:
        to_ret = {}
        set_messages = set(all_messages)
        for msg in set_messages:
            to_ret[int(msg)] = all_messages.count(int(msg))
    except ValueError:
        print "some non numeric values were provided"
    return render_to_response('education/dashboard/meetings.html', {}, RequestContext(req))

def dash_deo_meetings(req):
    return render_to_response('education/deo/meetings.html', {}, RequestContext(req))

# Dashboard specific view functions

@login_required
def dashboard(request):
    profile = request.user.get_profile()
    if profile.is_member_of('DEO') or profile.is_member_of('DFO'):
        return deo_dashboard(request)
    elif profile.is_member_of('Admins') or profile.is_member_of('Ministry Officials') or profile.is_member_of('UNICEF Officials'):
        return admin_dashboard(request)
    else:
        return HttpResponseRedirect('/')

# generate context vars
def generate_dashboard_vars(location=None):
    """
    An overly ambitious function that generates context variables for a location if provided
    This gets populated in the dashboard.
    """
    locations = []
    if location.name == "Uganda":
        # get locations from active districts only
        locations = Location.objects.filter(pk__in=EmisReporter.objects.values_list('reporting_location__pk', flat=True)).distinct()
    else:
        locations.append(location)

    responses_to_violence = poll_response_sum("edtrac_headteachers_abuse", month_filter = 'monthly', locations = locations, month_20to19=True)
    # percentage change in violence from previous month
    violence_change = cleanup_sums(responses_to_violence)
    if violence_change > 0:
        violence_change_class = "decrease"
        violence_change_data = "data-green"
    elif violence_change < 0:
        violence_change_class = "increase"
        violence_change_data = "data-red"
    else:
        violence_change_class = "zero"
        violence_change_data = "data-white"


    # CSS class (dynamic icon)
    x, y = poll_responses_past_week_sum("edtrac_boysp3_attendance", locations=locations, weeks=2)
    enrol = poll_responses_term("edtrac_boysp3_enrollment", belongs_to="location", locations=locations)
    try:
        boysp3 = 100*(enrol - x ) / enrol
    except ZeroDivisionError:
        boysp3 = 0

    try:
        # boys in the past week
        boysp3_past = 100*(enrol - y ) / enrol
    except ZeroDivisionError:
        boysp3_past = 0

    boysp3_diff = boysp3 - boysp3_past

    if boysp3_diff > 0:
        boysp3_class = 'increase'
        boysp3_data = 'data-red'
    elif boysp3_diff < 0:
        boysp3_class = 'decrease'
        boysp3_data = 'data-green'
    else:
        boysp3_class = 'zero'
        boysp3_data = 'data-white'

    x, y  = poll_responses_past_week_sum("edtrac_boysp6_attendance", locations=locations, weeks=2)
    enrol = poll_responses_term("edtrac_boysp6_enrollment", belongs_to="location", locations=locations)
    try:
        boysp6 = 100*(enrol - x ) / enrol
    except ZeroDivisionError:
        boysp6 = 0

    try:
        boysp6_past = 100*(enrol - y ) / enrol
    except ZeroDivisionError:
        boysp6_past = 0

    boysp6_diff = boysp6 - boysp6_past

    if boysp6_diff > 0:
        boysp6_class = 'increase'
        boysp6_data = 'data-red'
    elif boysp6_diff < 0:
        boysp6_class = 'decrease'
        boysp6_data = 'data-green'
    else:
        boysp6_class = 'zero'
        boysp6_data = 'data-white'

    x, y = poll_responses_past_week_sum("edtrac_girlsp3_attendance",locations=locations, weeks=2)
    enrol = poll_responses_term("edtrac_girlsp3_enrollment", belongs_to="location", locations=locations)
    try:
        girlsp3 = 100*(enrol - x ) / enrol
    except ZeroDivisionError:
        girlsp3 = 0

    try:
        girlsp3_past = 100*(enrol - y ) / enrol
    except ZeroDivisionError:
        girlsp3_past = 0

    girlsp3_diff = girlsp3 - girlsp3_past

    if girlsp3_diff > 0:
        girlsp3_class = "increase"
        girlsp3_data = 'data-red'
    elif girlsp3_diff < 0:
        girlsp3_class = "decrease"
        girlsp3_data = 'data-green'
    else:
        girlsp3_class = "zero"
        girlsp3_data = 'data-white'

    x, y = poll_responses_past_week_sum("edtrac_girlsp6_attendance", locations=locations, weeks=2)
    enrol = poll_responses_term("edtrac_girlsp6_enrollment", belongs_to="location", locations=locations)

    try:
        girlsp6 = 100*(enrol - x ) / enrol
    except ZeroDivisionError:
        girlsp6 = 0

    try:
        girlsp6_past = 100*(enrol - y ) / enrol
    except ZeroDivisionError:
        girlsp6_past = 0

    girlsp6_diff = girlsp6 - girlsp6_past

    if girlsp6_diff > 0:
        girlsp6_class = "increase"
        girlsp6_data = 'data-red'

    elif girlsp6_diff < 0:
        girlsp6_class = 'decrease'
        girlsp6_data = 'data-green'
    else:
        girlsp6_data = 'data-white'
        girlsp6_class = "zero"

    x, y = poll_responses_past_week_sum("edtrac_f_teachers_attendance",locations=locations, weeks=2)
    deploy = poll_responses_term("edtrac_f_teachers_deployment", belongs_to="location", locations=locations)
    try:
        female_teachers = 100*(deploy - x ) / deploy
    except ZeroDivisionError:
        female_teachers = 0

    try:
        female_teachers_past = 100*(deploy - y ) / deploy
    except ZeroDivisionError:
        female_teachers_past = 0

    female_teachers_diff = female_teachers - female_teachers_past

    if female_teachers_diff > 0:
        female_teachers_class = "increase"
        female_teachers_data = 'data-red'
    elif female_teachers_diff < 0:
        female_teachers_class = "decrease"
        female_teachers_data = 'data-green'
    else:
        female_teachers_data = "data-white"
        female_teachers_class = "zero"

    x, y = poll_responses_past_week_sum("edtrac_m_teachers_attendance", weeks = 2, locations=locations)
    deploy = poll_responses_term("edtrac_m_teachers_deployment", belongs_to="location", locations=locations)
    try:
        male_teachers = 100*(deploy - x ) / deploy
    except ZeroDivisionError:
        male_teachers = 0

    try:
        male_teachers_past = 100*(deploy - y ) / deploy
    except ZeroDivisionError:
        male_teachers_past = 0

    male_teachers_diff = male_teachers - male_teachers_past

    if male_teachers_diff < 0:
        male_teachers_class = "decrease"
        male_teachers_data = 'data-green'
    elif male_teachers_diff > 0:
        male_teachers_class = "increase"
        male_teachers_data = 'data-red'
    else:
        male_teachers_class = "zero"
        male_teachers_data = 'data-white'


    try:
        if len(locations) == 1:
            progress_list =curriculum_progress_list("edtrac_p3curriculum_progress", time_range = True, location=locations[0])
            if progress_list == 0:
                c_list = 0
            else:
                c_list = list(progress_list)
        else:
            c_list = list(curriculum_progress_list("edtrac_p3curriculum_progress", time_range = True))

        if c_list == 0:
            mode = 0
        else:
            mode = curriculum_progress_mode(c_list)

    except exceptions.TypeError:
        # shouldn't really reach this state (unless data isn't there)
        mode = 0

    try:
        mode_progress = (100 * sorted(themes.keys()).index(mode)+1) / float(len(themes.keys())) # offset zero-based index by 1
    except ValueError:
        mode_progress = 0 # when no values are recorded

    if len(locations) == 1:
        response_to_meals = get_count_response_to_polls(Poll.objects.get(name = "edtrac_headteachers_meals"),
            time_range = get_week_date()[0], choices = [0], location_name = locations[0].name)
    else:
        response_to_meals = get_count_response_to_polls(Poll.objects.get(name = "edtrac_headteachers_meals"),
            time_range = get_week_date()[0], choices = [0])

    p = sorted(response_to_meals.items(), key=lambda(k,v):(v[0][1], k))

    worst_meal = p[len(p)-1]

    # ideally head teachers match the number of SMCs in eductrac

    female_head_teachers = EmisReporter.objects.filter(reporting_location__in =\
        locations, groups__name="Head Teachers", gender='F').exclude(schools = None)
    female_head_t_deploy = EmisReporter.objects.filter(reporting_location__in = locations, schools__in=\
        female_head_teachers.values_list('schools', flat=True),
        groups__name = 'SMC').distinct().count()

    male_head_teachers = EmisReporter.objects.filter(reporting_location__in =\
        locations, groups__name="Head Teachers", gender='M').exclude(schools = None)

    male_head_t_deploy = EmisReporter.objects.filter(reporting_location__in = locations, schools__in=\
        male_head_teachers.values_list('schools', flat=True),
            groups__name = 'SMC').distinct().count()




    d1, d2 = get_week_date(depth = 2)
    resp_d1_female = Poll.objects.get(name="edtrac_head_teachers_attendance").responses_by_category().filter(
        response__contact__in = EmisReporter.objects.filter(reporting_location__in = locations, schools__pk__in=\
        female_head_teachers.values_list('schools__pk', flat=True)),
        response__date__range = d1
    )

    resp_d2_female = Poll.objects.get(name="edtrac_head_teachers_attendance").responses_by_category().filter(
        response__contact__in = EmisReporter.objects.filter(reporting_location__in = locations, schools__pk__in=\
            female_head_teachers.values_list('schools__pk', flat=True)),
            response__date__range = d2
        )

    # get the count for female head teachers present in the last 3 days

    female_d1 = extract_key_count(resp_d1_female, 'yes')
    if female_d1 is not None:
        try:
            female_d1 = 100 * (female_d1 / female_head_t_deploy)
        except ZeroDivisionError, TypeError:
            female_d1 = 0
    else:
        female_d1 = '--'

    female_d2 = extract_key_count(resp_d2_female, 'yes')
    if female_d2 is not None:
        try:
            female_d2 = 100 * (female_d2 / female_head_t_deploy)
        except ZeroDivisionError, TypeError:
            female_d2 = 0
    else:
        female_d2 = '--'

    if not female_d2 and not female_d1:

        f_head_diff = female_d2 - female_d1

        if f_head_diff > 0:
            f_head_t_class = "increase"
            f_head_t_data = 'data-red'
        elif f_head_diff < 0:
            f_head_t_class = "decrease"
            f_head_t_data = 'data-green'
        else:
            f_head_t_class = "zero"
            f_head_t_data = 'data-white'
    else:
        f_head_diff = '--'
        f_head_t_class = 'zeror'
        f_head_t_data = 'data-white'

    #TODO -> extract data on head teachers.
    resp_d1_male = Poll.objects.get(name="edtrac_head_teachers_attendance").responses_by_category().filter(
        response__contact__in = EmisReporter.objects.filter(reporting_location__in = locations, schools__in=\
            male_head_teachers.values_list('schools', flat=True)),
        response__date__range = d1
    )

    resp_d2_male = Poll.objects.get(name="edtrac_head_teachers_attendance").responses_by_category().filter(
        response__contact__in = EmisReporter.objects.filter(reporting_location__in = locations, schools__in=\
            male_head_teachers.values_list('schools', flat=True)),
        response__date__range = d2
    )
    # get the count for female head teachers present in the last 3 days

    male_d1 = extract_key_count(resp_d1_male, 'yes')
    if male_d1 is not None:
        try:
            male_d1 = 100 * (male_d1 / male_head_t_deploy)
        except ZeroDivisionError, TypeError:
            male_d1 = 0
    else:
        male_d1 = '--'


    male_d2 = extract_key_count(resp_d2_male, 'yes')
    if male_d2 is not None:
        try:
            male_d2 = 100 * (male_d2 / male_head_t_deploy)
        except ZeroDivisionError, TypeError:
            male_d2 = 0
    else:
        male_d2 = '--'

    if not male_d2 and not male_d1:

        m_head_diff = male_d2 - male_d1

        if m_head_diff > 0:
            m_head_t_class = "increase"
            m_head_t_data = 'data-red'
        elif m_head_diff < 0:
            m_head_t_class = "decrease"
            m_head_t_data = 'data-green'
        else:
            m_head_t_class = "zero"
            m_head_t_data = 'data-white'
    else:
        m_head_diff = '--'
        m_head_t_class = 'zero'
        m_head_t_data = 'data-white'

    school_to_date = School.objects.filter(pk__in=EmisReporter.objects.filter(reporting_location__in = locations).values_list('schools__pk', flat=True)).count()

    try:
        school_reporters = EmisReporter.objects.filter(
            reporting_location__in = locations,
            groups__name__in=["Head Teachers", "Teachers"], connection__in=Message.objects.\
            filter(date__range = get_week_date(depth = 2)[1]).values_list('connection', flat = True)).\
            exclude(schools = None).exclude(connection__in = Blacklist.objects.values_list('connection', flat=True))
        school_active = (100 * School.objects.filter(pk__in = school_reporters.values_list('schools__pk', flat=True)).\
            count()) / school_to_date
    except ZeroDivisionError:
        school_active = 0


    # capitation grants
    cg = Poll.objects.get(name="edtrac_upe_grant")
    yeses_cg = cg.responses_by_category().get(category__name = "yes").get('value')
    nos_cg = cg.responses_by_category().get(category__name = 'no').get('value')
    # percent of those that received grants
    try:
        grant_percent = 100 * yeses_cg / (yeses_cg + nos_cg)
    except ZeroDivisionError:
        grant_percent = 0

    return {
        'worst_meal' : worst_meal,
        'c_mode' : mode,
        'mode_progress' : mode_progress,
        'violence_change' : violence_change,
        'violence_change_class' : violence_change_class,
        'violence_change_data' : violence_change_data,
        'male_teachers' : male_teachers,
        'male_teachers_past' : male_teachers_past,
        'male_teachers_diff' : male_teachers_diff,
        'male_teachers_class' : male_teachers_class,
        'male_teachers_data' : male_teachers_data,
        'female_teachers_class' : female_teachers_class,
        'female_teachers' :female_teachers,
        'female_teachers_past' : female_teachers_past,
        'female_teachers_diff' : female_teachers_diff,
        'female_teachers_data' : female_teachers_data,
        'girlsp3' : girlsp3,
        'girlsp3_past' : girlsp3_past,
        'girlsp3_class': girlsp3_class,
        'girlsp3_diff' : girlsp3_diff,
        'girlsp3_data' : girlsp3_data,
        'girlsp6' : girlsp6,
        'girlsp6_past' : girlsp6_past,
        'girlsp6_diff' : girlsp6_diff,
        'girlsp6_class' : girlsp6_class,
        'girlsp6_data' : girlsp6_data,
        'boysp3' : boysp3,
        'boysp3_past': boysp3_past,
        'boysp3_class' : boysp3_class,
        'boysp3_diff' : boysp3_diff,
        'boysp3_data' : boysp3_data,
        'boysp6' : boysp6,
        'boysp6_past' : boysp6_past,
        'boysp6_class' : boysp6_class,
        'boysp6_diff' : boysp6_diff,
        'boysp6_data' : boysp6_data,
        'f_head_t_week' : female_d2,
        'f_head_t_week_before' : female_d1,
        'f_head_diff' : f_head_diff,
        'm_head_t_week' : male_d2,
        'm_head_t_week_before' : male_d1,
        'm_head_diff' : m_head_diff,
        'f_head_t_class' : f_head_t_class,
        'm_head_t_class' : m_head_t_class,
        'month':datetime.datetime.now(),
        'schools_to_date': school_to_date,
        'school_active' : school_active,
        'grant_percent' : grant_percent
    }

##########################################################################################################
##########################################################################################################
############################ Ministry Dashboard #############################################################
##########################################################################################################
##########################################################################################################
@login_required
def ministry_dashboard(request):
    location = request.user.get_profile().location
    return render_to_response("education/ministry/ministry_dashboard.html", generate_dashboard_vars(location=location),
        RequestContext(request))


class ProgressMinistryDetails(TemplateView):
    template_name = "education/ministry/ministry_progress_details.html"
    @method_decorator(login_required)
    def get_context_data(self, **kwargs):
        context = super(ProgressMinistryDetails, self).get_context_data(**kwargs)
        return context

class MealsMinistryDetails(TemplateView):
    template_name = "education/ministry/ministry_meals_details.html"
    #TODO open this up with more data variables
    def get_context_data(self, **kwargs):
        context = super(MealsMinistryDetails, self).get_context_data(**kwargs)
        ##context['some_key'] = <some_list_of_response>
        return context


##########################################################################################################
##########################################################################################################
############################ Admin Dashboard #############################################################
##########################################################################################################
##########################################################################################################
@login_required
def admin_dashboard(request):
    if request.user.get_profile().is_member_of('Ministry Officials') or request.user.get_profile().is_member_of('Admins')\
        or request.user.get_profile().is_member_of('UNICEF Officials'):
        location = Location.objects.get(name="Uganda")
    else:
        location = request.user.get_profile().location
    return render_to_response("education/admin/admin_dashboard.html", generate_dashboard_vars(location=location),
        RequestContext(request))

class NationalStatistics(TemplateView):
    template_name = "education/admin/national_statistics.html"


    #simple helper function
    def compute_percent(self, reps, groups = []):
        if groups:
            all_reporters = EmisReporter.objects.filter(groups__name__in=groups).exclude(connection__in=\
                Blacklist.objects.values_list('connection',flat=True))
        else:
            all_reporters = EmisReporter.objects.exclude(connection__in=\
                Blacklist.objects.values_list('connection',flat=True))

        try:
            return 100 * reps.count() / all_reporters.count()
        except ZeroDivisionError:
            return 0


    def get_context_data(self, **kwargs):
        context = super(NationalStatistics, self).get_context_data(**kwargs)

        profile = self.request.user.get_profile()
        if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
            districts = Location.objects.filter(type="district").\
                filter(name__in=EmisReporter.objects.exclude(connection__in=Blacklist.objects.values_list('connection',flat=True))\
                    .values_list('reporting_location__name', flat=True))
            district_schools = [
                (district,
                School.objects.filter(pk__in=EmisReporter.objects.exclude(schools=None).exclude(connection__in = Blacklist.objects.values_list('connection',flat=True)).\
                    filter(reporting_location__name = district.name).distinct().values_list('schools__pk',flat=True)).count())
                for district in districts
            ]
            #School.objects.filter(pk__in=\
            #    EmisReporter.objects.filter(reporting_location=district).exclude(schools = None).values_list('schools__pk',flat=True)).count())            
            context['total_districts'] = districts.count()
            context['district_schools'] = district_schools
            context['school_count'] = School.objects.filter(pk__in=EmisReporter.objects.exclude(schools=None).\
                exclude(connection__in = Blacklist.objects.values_list('connection',flat=True)).distinct().values_list('schools__pk',flat=True)).count()
            # getting weekly system usage
            # reporters that sent messages in the past week.
            reps = EmisReporter.objects.filter(groups__name="Head Teachers", connection__in=Message.objects.\
                filter(date__range = get_week_date(depth = 2)[1]).values_list('connection', flat = True)).\
                exclude(schools = None).exclude(connection__in = Blacklist.objects.values_list('connection', flat=True))

            district_active = [
                    (
                    district, self.compute_percent(reps.filter(reporting_location__pk=district.pk), groups=['Head Teachers'])
                    )
                for district in districts
            ]
            district_active.sort(key=operator.itemgetter(1), reverse=True)
            context['district_active'] = district_active[:3]
            context['district_less_active'] = district_active[-3:]

            context['head_teacher_count'] = reps.count()
            context['smc_count'] = EmisReporter.objects.exclude(schools=None).exclude(connection__in = Blacklist.objects.\
                values_list('connection', flat = True)).filter(groups__name = "SMC").count()

            context['p6_teacher_count'] = EmisReporter.objects.exclude(schools=None, connection__in = Blacklist.objects.\
                values_list('connection', flat = True)).filter(groups__name = "Teachers", grade = "P6").count()

            context['p3_teacher_count'] = EmisReporter.objects.exclude(schools=None, connection__in = Blacklist.objects.\
                values_list('connection', flat = True)).filter(groups__name = "Teachers", grade = "P3").count()
            context['total_teacher_count'] = EmisReporter.objects.exclude(schools=None, connection__in = Blacklist.objects.\
                values_list('connection', flat = True)).filter(groups__name="Teachers").count()

            context['deo_count'] = EmisReporter.objects.exclude(schools=None, connection__in = Blacklist.objects.\
            values_list('connection', flat = True)).filter(groups__name="DEO").count()

            context['gem_count'] = EmisReporter.objects.exclude(schools=None, connection__in = Blacklist.objects.\
            values_list('connection', flat = True)).filter(groups__name="GEM").count()

            context['all_reporters'] = EmisReporter.objects.exclude(schools=None, connection__in = Blacklist.objects.\
            values_list('connection', flat = True)).count()



            schools = School.objects.filter(pk__in = EmisReporter.objects.exclude(schools=None, connection__in=\
                Blacklist.objects.values_list('connection',flat=True)).values_list('schools__pk', flat=True))
            context['expected_reporters'] = len(schools) * 4
            # reporters that used EduTrac the past week
            school_reporters = EmisReporter.objects.filter(groups__name__in=["Head Teachers", "Teachers"], connection__in=Message.objects.\
                filter(date__range = get_week_date(depth = 2)[1]).values_list('connection', flat = True)).\
                exclude(schools = None).exclude(connection__in = Blacklist.objects.values_list('connection', flat=True))

            school_active = [
                (school, self.compute_percent(school_reporters.filter(schools__pk=school.pk), groups=['Head Teachers', 'Teachers']))
                for school in schools
                ]

            school_active.sort(key=operator.itemgetter(1), reverse=True)
            context['school_active_count'] = School.objects.filter(pk__in = school_reporters.values_list('schools__pk', flat=True)).count()
            context['school_active'] = school_active[:3]
            context['school_less_active'] = school_active[-3:]


            return context

        else:

            return self.render_to_response(dashboard(self.request))


class CapitationGrants(TemplateView):
    template_name = 'education/admin/capitation_grants.html'
    #TODO include SMC replies to question on whether grant chat is displayed publicly in schools visited


    # handy function for % computation
    def compute_percent(self, x, y):
        try:
            return (100 * x) / y
        except ZeroDivisionError:
            return 0

    def extract_info(self, list):
        to_ret = []
        for item in list:
            to_ret.append(
                [item.get('category__name'), item.get('value')]
            )
        final_ret = {}
        for li in to_ret:
            final_ret[li[0]] = li[1]

        total = sum(filter(None, final_ret.values()))
        # recompute and return as percentages

        for key in final_ret.keys():
            final_ret[key] = self.compute_percent(final_ret.get(key), total)

        return final_ret

    def get_context_data(self, **kwargs):
        context = super(CapitationGrants, self).get_context_data(**kwargs)
        cg = Poll.objects.get(name="edtrac_upe_grant")

        # correspond with group names
        authorized_users = ['Admins', 'Ministry Officials', 'UNICEF Officials']

        authorized_user = False

        for auth_user in authorized_users:
            if self.request.user.get_profile().is_member_of(auth_user):
                authorized_user = True
                break

        context['authorized_user'] = authorized_user

        if authorized_user:

            head_teacher_count = EmisReporter.objects.filter(groups__name = "Head Teachers").exclude(schools=None).count()
            responses = cg.responses_by_category(location=Location.tree.root_nodes()[0])
            all_responses = cg.responses_by_category()
            location_ids = Location.objects.filter(
                type="district", pk__in = \
                    EmisReporter.objects.exclude(connection__in=Blacklist.objects.\
                        values_list('connection', flat=True), schools=None).filter(groups__name="Head Teachers").\
                        values_list('reporting_location__pk',flat=True)).values_list('id',flat=True)

            locs = Location.objects.filter(id__in = location_ids)

            districts_to_ret = []
            for location in locs:
                head_teacher_count = EmisReporter.objects.exclude(schools = None, connection__in =\
                    Blacklist.objects.values_list('connection', flat = True)).filter(reporting_location=location,
                        groups__name = 'Head Teachers').count()
                other_responses = list(cg.responses_by_category(location = location, for_map=False))

                info = self.extract_info(other_responses)

                districts_to_ret.append(( location, info.items()))


            context['capitation_location_data'] = responses

            try:
                ht_no = (100 * all_responses.get(category__name = 'no').get('value')) / head_teacher_count
            except ZeroDivisionError:
                ht_no = 0

            try:
                ht_unknown = (100 * all_responses.get(category__name = 'unknown').get('value')) / head_teacher_count
            except ZeroDivisionError:
                ht_unknown = 0

            try:
                ht_yes = (100 * all_responses.get(category__name = 'yes').get('value')) / head_teacher_count
            except ZeroDivisionError:
                ht_yes = 0

            context['national_responses'] = [('Yes', ht_yes), ('No', ht_no), ('unknown',ht_unknown)]
            context['head_teacher_count'] = 100 * (head_teacher_count / EmisReporter.objects.exclude(schools=None,\
                connection__in = Blacklist.objects.values_list('connection', flat=True)).count())

            context['districts'] = districts_to_ret

            return context

        else:

            location = self.request.user.get_profile().location
            responses = cg.responses_by_category(
                location = location,
                for_map = False
            )
            htc = EmisReporter.objects.exclude(schools = None, connection__in =\
                    Blacklist.objects.values_list('connection', flat = True)).filter(groups__name = 'Head Teachers',\
                    reporting_location = location).count()
            try:

                htc_p = (100 *  cg.responses.filter(contact__reporting_location = location, contact__connection__in =\
                            EmisReporter.objects.exclude(schools = None, connection__id__in =\
                                Blacklist.objects.values_list('connection', flat = True)).filter(groups__name = 'Head Teachers',\
                                reporting_location = location).values_list('connection__id', flat=True)).count()) / htc

            except ZeroDivisionError:
                htc_p = 0

            context['head_teacher_count'] = htc_p


            info = self.extract_info(list(responses))
            context['district'] = location
            context['district_info'] = info.items()
            return context


# Details views... specified by ROLES
class ViolenceAdminDetails(TemplateView):
    template_name = "education/admin/admin_violence_details.html"
    #TODO open this up with more data variables
    def get_context_data(self, **kwargs):
        context = super(ViolenceAdminDetails, self).get_context_data(**kwargs)
        #TODO: filtering by ajax and time

        if self.request.user.get_profile().is_member_of('Ministry Officials') or self.request.user.get_profile().is_member_of('UNICEF Officials'):
            location = Location.objects.get(name="Uganda")
        else:
            location = self.request.user.get_profile().location

        violence_cases_schools = poll_response_sum("edtrac_headteachers_abuse",
            location=location, month_filter=True, months=2, ret_type=list)

        violence_cases_gem = poll_response_sum('edtrac_gem_abuse', location=location, month_filter=True, months=2, ret_type=list)

        general_violence = []
        general_violence = get_numeric_report_data('edtrac_headteachers_abuse', location=location)

        school_total = [] # total violence cases reported by school
        for name, list_val in violence_cases_schools:
            try:
                diff = (list_val[0] - list_val[1]) / list_val[0]
            except ZeroDivisionError:
                diff = '--'
            school_total.append((list_val[0], list_val[1], diff))
            list_val.append(diff)

        context['violence_cases_reported_by_schools'] = violence_cases_schools

        first_col, second_col, third_col = [],[],[]
        for first, second, third in school_total:
            first_col.append(first), second_col.append(second), third_col.append(third)
        first_col = [i for i in first_col if i != '--']
        second_col = [i for i in second_col if i != '--']
        third_col = [i for i in third_col if i != '--']

        context['school_totals'] = [sum(first_col), sum(second_col), sum(third_col)]

        gem_total = [] # total violence cases reported by school
        for name, list_val in violence_cases_gem:
            try:
                diff = (list_val[0] - list_val[1]) / list_val[0]
            except ZeroDivisionError:
                diff = '--'
            gem_total.append((list_val[0], list_val[1], diff))
            list_val.append(diff)

        context['violence_cases_reported_by_gem'] = violence_cases_gem

        first_col, second_col, third_col = [],[],[]
        for first, second, third in gem_total:
            first_col.append(first), second_col.append(second), third_col.append(third)
        first_col = [i for i in first_col if i != '--']
        second_col = [i for i in second_col if i != '--']
        third_col = [i for i in third_col if i != '--']
        context['gem_totals'] = [sum(first_col), sum(second_col), sum(third_col)]


        # depth of 2 months
        context['report_dates'] = [start for start, end in get_month_day_range(datetime.datetime.now(), depth=2)]
        school_report_count = 0
        gem_report_count = 0
        #TODO
        # -> 100 * (reports-that-are-sent-to-edtrac / reports-that-should-have-come-edtrac a.k.a. all schools)
        #
        # Assumes every administrator's location is the root location Uganda
        for dr in get_month_day_range(datetime.datetime.now(), depth=2):

            if self.request.user.get_profile().location.type.name == 'country':
                contacts = Contact.objects.filter(reporting_location__in=self.request.user.get_profile().\
                    location.get_descendants().filter(type="district"))
            else:
                contacts = Contact.objects.filter(reporting_location=self.request.user.get_profile().location)

            school_resp_count = Poll.objects.get(name="edtrac_headteachers_abuse").responses.filter(
                contact__in = contacts,
                date__range = dr).count()

            gem_resp_count = Poll.objects.get(name="edtrac_gem_abuse").responses.filter(
                contact__in = contacts,
                date__range = dr).count()

            school_report_count += school_resp_count
            gem_report_count += gem_resp_count

        try:
            context['sch_reporting_percentage'] = 100 * ( school_report_count / (float(len(get_month_day_range(datetime.datetime.now(),
                depth=2))) * school_report_count))
        except ZeroDivisionError:
            context['sch_reporting_percentage'] = 0

        try:
            context['gem_reporting_percentage'] = 100 * ( gem_report_count / (float(len(get_month_day_range(datetime.datetime.now(),
                depth=2))) * gem_report_count))
        except ZeroDivisionError:
            context['gem_reporting_percentage'] = 0

        return context

#District violence details (TODO: permission/rolebased viewing)
class DistrictViolenceDetails(TemplateView):
    template_name = "education/dashboard/district_violence_detail.html"

    def get_context_data(self, **kwargs):
        context = super(DistrictViolenceDetails, self).get_context_data(**kwargs)

        location = Location.objects.filter(type="district").get(pk=int(self.kwargs.get('pk'))) or self.request.user.get_profile().location

        schools = School.objects.filter(
            pk__in = EmisReporter.objects.filter(reporting_location=location).values_list('schools__pk', flat=True))

        school_case = []
        month_now, month_before = get_month_day_range(datetime.datetime.now(), depth=2)
        for school in schools:
            # optimize with value queries
            now_data = get_numeric_report_data( 'edtrac_headteachers_abuse', time_range = month_now, school = school,
                to_ret = 'sum', belongs_to = 'schools')

            before_data = get_numeric_report_data('edtrac_headteachers_abuse', time_range = month_before, school = school,\
                to_ret = 'sum', belongs_to = 'schools')
            # sieve out only schools with either value of violence cases being shown
            if now_data > 0 or before_data > 0:
                school_case.append((school, now_data, before_data))

        #reports = poll_response_sum("edtrac_headteachers_abuse", month_filter=True, months=1)
        emis_reporters = EmisReporter.objects.exclude(connection__in=\
            Blacklist.objects.values_list('connection')).filter(schools__in=schools)

        context['location'] = location
        context['school_vals'] = school_case
        #        context['school_count'] = School.objects.filter(location__in=EmisReporter.objects.exclude(connection__in=Blacklist.objects.values_list('connection').\
        #            values_list('reporting_location'))).count()
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
            #locations = Location.objects.get(name="Uganda").get_descendants().filter(type="district").order_by("name")
            #context['total_districts'] = Location.objects.get(name="Uganda").get_descendants().filter(type="district").count()
            context['total_disticts'] = locations.count()
        else:
            locations = [profile.location]

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
#    query = req.POST[u'query']
#    split_query = re.split(ur'(?u)\W', query)
#    while u'' in split_query:
#        split_query.remove(u'')
#    results = []
#    for word in split_query:
#        for district in Location.objects.filter(type="district", name__icontains=word):
#            if re.match(ur'(?ui)\b' + word + ur'\b'):
#                entry = {
#                    u'id':district.id,
#                    u'name':district.name
#                }
#            if not entry in results:
#                results.append(entry)

class ProgressAdminDetails(TemplateView):
    template_name = "education/progress/admin_progress_details.html"

    def get_context_data(self, **kwargs):
        context = super(ProgressAdminDetails, self).get_context_data(**kwargs)
        ##context['some_key'] = <some_list_of_response>
        # we get all violence cases ever reported
        #TODO: filtering by ajax and time
        context['progress'] = list_poll_responses(Poll.objects.get(name="edtrac_p3ccurriculum_progress"))
        # decimal module used to work with really floats with more than 2 decimal places
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




##########################################################################################################
##########################################################################################################
############################ DEO Dashboard #############################################################
##########################################################################################################
##########################################################################################################
@login_required
def deo_dashboard(req):
    location = req.user.get_profile().location
    return render_to_response("education/deo/deo_dashboard.html", generate_dashboard_vars(location=location), RequestContext(req))


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

def control_panel(req):
    profile = req.user.get_profile()
    if profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials') or profile.is_member_of('Ministry Officials'):
        return render_to_response('education/partials/control_panel.html', {}, RequestContext(req))
    else:
        return render_to_response('education/partials/control_panel_dist.html',{}, RequestContext(req))

class AuditTrail(TemplateView):
    template_name = "education/admin/audit_trail.html"


class DistrictViolenceCommunityDetails(DetailView):
    context_object_name = "district_violence"
    model = Location

    def get_context_data(self, **kwargs):
        context = super(DistrictViolenceCommunityDetails, self).get_context_data(**kwargs)
        location = Location.objects.filter(type="district").get(pk=int(self.kwargs.get('pk'))) or self.request.user.get_profile().location
        #schools and reports from a district

        #reports = poll_response_sum("edtrac_headteachers_abuse", month_filter=True, months=1)
        emis_reporters = EmisReporter.objects.filter(groups__name="GEM", connection__in =\
            Poll.objects.get(name="edtrac_gem_abuse").responses.values_list('contact__connection',flat=True))
#
#        Blacklist.objects.\
#                values_list('connection', flat=True)).filter(reporting_location=location, groups__name="GEM")
        context['location'] = location
        context['reporters'] = emis_reporters
        #        context['school_count'] = School.objects.filter(location__in=EmisReporter.objects.exclude(connection__in=Blacklist.objects.values_list('connection').\
        #            values_list('reporting_location'))).count()
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

HEADINGS = ['District', 'Absent (%) This week', 'Absent (%) Last week', 'Change (%) for absenteeism from last week']

@login_required
def boysp3_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").filter(type="district").get(id=location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        temp = [school]
        temp.extend(
            return_absent(
                'edtrac_boysp3_attendance','edtrac_boysp3_enrollment', school=school
            )
        )

        to_ret.append(temp)
    to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

    return render_to_response("education/boysp3_district_attd_detail.html", { 'location':location,\
        'location_data':to_ret,
        'week':datetime.datetime.now(),
        'headings' : ['School', 'Current Week (%)', 'Week before (%)', 'Percentage change']}, RequestContext(req))

@login_required
def boysp6_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").filter(type="district").get(id=location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        temp = [school]
        temp.extend(return_absent('edtrac_boysp6_attendance', 'edtrac_boysp6_enrollment', school = school))
        to_ret.append(temp)

    to_ret.sort(key = operator.itemgetter(1)) # sort by current month data


    return render_to_response("education/boysp6_district_attd_detail.html", { 'week':datetime.datetime.now(),\
        'location':location,\
        'headings' : ['School', 'Current Week (%)', 'Week before (%)', 'Percentage change'],
        'location_data':to_ret },\
        RequestContext(req))


@login_required
def girlsp3_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").filter(type='district').get(id = location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        temp = [school]
        temp.extend(return_absent('edtrac_girlsp3_attendance', 'edtrac_girlsp3_enrollment', school = school))
        to_ret.append(temp)

    to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

    return render_to_response("education/girlsp3_district_attd_detail.html", { 'week':datetime.datetime.now(),\
        'location_data':to_ret,
        'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
        'location':location}, RequestContext(req))

@login_required
def girlsp6_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").filter(type='district').get(id = location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        temp = [school]
        temp.extend(return_absent('edtrac_girlsp3_attendance', 'edtrac_girlsp3_enrollment', school = school))
        to_ret.append(temp)

    to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

    return render_to_response("education/girlsp6_district_attd_detail.html",
            { 'week':datetime.datetime.now(),\
               'location_data':to_ret,
               'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
               'location':location}, RequestContext(req))


@login_required
def female_t_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").filter(type='district').get(id = location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        temp = [school]
        temp.extend(return_absent('edtrac_f_teachers_attendance', 'edtrac_f_teachers_deployment', school = school))
        to_ret.append(temp)

    to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

    return render_to_response("education/female_t_district_attd_detail.html",
            { 'week':datetime.datetime.now(),\
              'location_data':to_ret,
              'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
              'location':location}, RequestContext(req))

@login_required
def male_t_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").filter(type='district').get(id = location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        temp = [school]
        temp.extend(return_absent('edtrac_m_teachers_attendance', 'edtrac_m_teachers_deployment', school = school))
        to_ret.append(temp)

    to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

    return render_to_response("education/male_t_district_attd_detail.html",
            { 'week':datetime.datetime.now(),\
              'location_data':to_ret,
              'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
              'location':location}, RequestContext(req))

def boys_p3_attendance(req):
    profile = req.user.get_profile()
    location = profile.location
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of('UNICEF Officials'):
        """
        This view shows data by district
        """
        locations = Location.objects.exclude(type="country").filter(type="district", name__in=\
            EmisReporter.objects.distinct().values_list('reporting_location__name', flat=True)).order_by("name")
        # return view that will give shool-based views
        # --> ref function just below this <---
        return boys_p3_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)

        to_ret = []
        for school in schools:
            temp = [school]
            temp.extend(return_absent('edtrac_boysp3_attendance', 'edtrac_boysp3_enrollment', school = school))
            to_ret.append(temp)

        to_ret.sort(key = operator.itemgetter(1)) # sort by current month data

        return  render_to_response(
            'education/partials/boys_p3_attendance.html',
            {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location':location
            },
            RequestContext(req))

def boys_p3_attd_admin(req, **kwargs):
    """
    Helper function to get differences in absenteeism across districts.
    """
    # P3 attendance /// what to show an admin or Ministry official
    locations = kwargs.get('locations')

    to_ret = return_absent('edtrac_boysp3_attendance', 'edtrac_boysp3_enrollment', locations)
    return render_to_response(
        'education/partials/boys_p3_attd_admin.html',
        {'location_data':to_ret,
         'headings': HEADINGS,
         'week':datetime.datetime.now()}, RequestContext(req)
    )


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

        return  render_to_response(
            'education/partials/boys_p6_attendance.html',
                {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            },
            RequestContext(req)
        )

def boys_p6_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for P6 boys.
    """
    # P6 attendance /// what to show an admin or Ministry official
    to_ret = return_absent('edtrac_boysp6_attendance', 'edtrac_boysp6_enrollment', locations=locations)

    return render_to_response('education/partials/boys_p6_attd_admin.html',
            {'location_data':to_ret,'headings':HEADINGS,'week':datetime.datetime.now()}, RequestContext(req))

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

        return  render_to_response(
            'education/partials/girls_p3_attendance.html',
                {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            },
            RequestContext(req))

def girls_p3_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for P3 girls
    """
    to_ret = return_absent('edtrac_girlsp3_attendance', 'edtrac_girlsp3_enrollment', locations=locations)
    return render_to_response('education/partials/girls_p3_attd_admin.html', 
        {'location_data':to_ret,'headings':HEADINGS,'week':datetime.datetime.now()}, RequestContext(req))


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

        return  render_to_response(
            'education/partials/girls_p6_attendance.html',
                {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            },
            RequestContext(req))

def girls_p6_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for P6 girls
    """
    to_ret = return_absent('edtrac_girlsp6_attendance', 'edtrac_girlsp6_enrollment', locations=locations)
    return render_to_response('education/partials/girls_p6_attd_admin.html',
        {'location_data':to_ret, 'headings':HEADINGS, 'week':datetime.datetime.now()}, RequestContext(req))

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

        return  render_to_response(
            'education/partials/female_teachers_attendance.html',
                {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            },
            RequestContext(req))

def female_teacher_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for all female teachers
    """
    to_ret = return_absent('edtrac_f_teachers_attendance', 'edtrac_f_teachers_deployment', locations=locations)
    return render_to_response('education/partials/female_teachers_attd_admin.html',
            {'location_data':to_ret,
             'headings':HEADINGS,
             'week':datetime.datetime.now()}, RequestContext(req))

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

        return  render_to_response(
            'education/partials/male_teachers_attendance.html',
                {
                'week':datetime.datetime.now(),
                'headings':['School', "Current Week (%)", "Week before (%)", "Percentage change"],
                'location_data': to_ret,
                'location' : location
            },
            RequestContext(req))

def male_teacher_attd_admin(req, locations=None):
    """
    Helper function to get differences in absenteeism across districts for all female teachers
    """
    to_ret = return_absent('edtrac_m_teachers_attendance', 'edtrac_m_teachers_deployment', locations=locations)
    return render_to_response('education/partials/male_teachers_attd_admin.html',
            {'location_data':to_ret,
             'headings':HEADINGS,
             'week':datetime.datetime.now()}, RequestContext(req))

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
            filter(reporting_location__type = 'district').values_list('reporting_location__name', flat=True))

    else:
        #DEO
        schools = School.objects.filter(location=location).order_by("name", "location__name")
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
def delete_reporter(request, reporter_pk):
    reporter = get_object_or_404(EmisReporter, pk=reporter_pk)
    if request.method == 'POST':
        reporter.delete()
    return HttpResponse(status=200)

@login_required
def edit_reporter(request, reporter_pk):
    reporter = get_object_or_404(EmisReporter, pk=reporter_pk)
    reporter_group_name = reporter.groups.all()[0].name
    reporter_form = EditReporterForm(instance=reporter)
    if request.method == 'POST':
        reporter_form = EditReporterForm(instance=reporter,
            data=request.POST)
        if reporter_form.is_valid():
            reporter_form.save()
            saved_reporter_grp = EmisReporter.objects.get(pk=reporter_pk).groups.all()[0].name
            if reporter.default_connection and reporter.groups.count() > 0:
                # remove from other scripts
                # if reporter's groups remain the same.
                if reporter_group_name == saved_reporter_grp:
                    pass
                else:
                    ScriptProgress.objects.exclude(script__slug="edtrac_autoreg").filter(connection=reporter.default_connection).delete()
                    _schedule_weekly_scripts(reporter.groups.all()[0], reporter.default_connection, ['Teachers', 'Head Teachers', 'SMC'])


                    _schedule_monthly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_head_teachers_monthly', 'last', ['Head Teachers'])
                    _schedule_monthly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_gem_monthly', 20, ['GEM'])
                    _schedule_monthly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_smc_monthly', 5, ['SMC'])


                    _schedule_termly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_smc_termly', ['SMC'])
                    _schedule_termly_script(reporter.groups.all()[0], reporter.default_connection, 'edtrac_head_teachers_termly', ['Head Teachers'])

        else:
            return render_to_response('education/partials/reporters/edit_reporter.html',
                    {'reporter_form': reporter_form,
                     'reporter': reporter},
                context_instance=RequestContext(request))
        return render_to_response('/education/partials/reporters/reporter_row.html',
                {'object':EmisReporter.objects.get(pk=reporter_pk),
                 'selectable':True},
            context_instance=RequestContext(request))
    else:
        return render_to_response('education/partials/reporters/edit_reporter.html',
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
            emis_ids = request.POST.getlist('emis_id')
            if len(names) > 0:
                for i, name in enumerate(names):
                    location = Location.objects.get(pk=int(locations[i]))
                    emis_id = emis_ids[i]
                    name, created = School.objects.get_or_create(name=name, location=location, emis_id=emis_id)
                    schools.append(name)

                return render_to_response('education/partials/addschools_row.html', {'object':schools, 'selectable':False}, RequestContext(request))
    else:
        form = SchoolForm()
    return render_to_response('education/deo/add_schools.html',
            {'form': form,
             }, context_instance=RequestContext(request))

@login_required
def delete_school(request, school_pk):
    school = get_object_or_404(School, pk=school_pk)
    if request.method == 'POST':
        school.delete()
    return HttpResponse(status=200)

@login_required
def edit_school(request, school_pk):
    school = get_object_or_404(School, pk=school_pk)
    school_form = SchoolForm(instance=school)
    if request.method == 'POST':
        school_form = SchoolForm(instance=school,
            data=request.POST)
        if school_form.is_valid():
            school_form.save()
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

    reporters = school.emisreporter_set.all()

    #monthly_violence =
    return render_to_response("education/school_detail.html", {\
        'school_name': school.name,
        'months' : [d_start for d_start, d_end in month_ranges],
        'monthly_data' : monthly_data,
        'monthly_data_teachers' : monthly_data_teachers,
        'reporters' : reporters
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
def excel_reports(req):
    return render_to_response('education/excelreports/excel_dashboard.html',{},RequestContext(req))

#visualization
#TODO add to dashboards or stats views {work on generic views}
#class ChartView(TemplateView):
#    # boys and girls attendance
#    context_object_name = "girl_boy_list"
#    from .utils import produce_curated_data
#    queryset = produce_curated_data()
#    template_name = "education/emis_chart.html"

@login_required
def attendance_chart(req): #consider passing date function nicely and use of slugs to pick specific data
    categories = "P1 P2 P3 P4 P5 P6 P7".split()
    boyslugs = ["boys_%s"%g for g in "p1 p2 p3 p4 p5 p6 p7".split()]
    girlslugs = ["girls_%s"%g for g in "p1 p2 p3 p4 p5 p6 p7".split()]
    from .reports import get_location, previous_calendar_week
    #user_location = get_location(request, district_id)
    user_location = Location.objects.get(pk=1)

    ## Limited number of schools by 25
    schools = School.objects.filter(location__in=user_location.get_descendants(include_self=True).all())[:25]
    #    date_tup = previous_calendar_week()
    #    kw = ('start','end')
    #    dates = dict(zip(kw,date_tup))

    #monthly diagram

    #TODO include date filtering for more than 1week {need a use-case}

    def value_gen(slug, dates, schools):
        toret = XFormSubmissionValue.objects.exclude(submission__has_errors=True)\
        .filter(attribute__slug__in=slug)\
        .filter(created__range=(dates.get('start'),dates.get('end')))\
        .filter(submission__connection__contact__emisreporter__schools__in=schools)\
        .values('submission__connection__contact__emisreporter__schools__name')\
        .values_list('submission__connection__contact__emisreporter__schools__name','value_int')
        return toret

    boy_values = value_gen(boyslugs,dates,schools)
    girl_values = value_gen(girlslugs,dates,schools)

    def cleanup(values):
        index = 0
        clean_val = []
        while index < len(values):
            school_values = []
            #school_values.append(values[index][0])
            school_values.append(values[index][1])
            for i in range(index,(index+6)):
                try:
                    school_values.append(values[i][1])
                except IndexError:
                    school_values.append(0)
                    # cleanup
                school_values.reverse()
            index += 6
            clean_val.append(school_values)
        return clean_val

    schools = [school_name.name for school_name in schools]
    boy_attendance = {}
    girl_attendance = {}

    clean_boy_values = cleanup(boy_values)
    clean_girl_values = cleanup(girl_values)

    for school_name, school_boy_value_list, school_girl_value_list in zip(schools, clean_boy_values, clean_girl_values):
        boy_attendance[school_name]  = school_boy_value_list
        girl_attendance[school_name] = school_girl_value_list

    """
    #uncomment; WIP for chunked
    new_date = previous_calendar_month_week_chunks() #iterate for these 4 weeks
    new_date_named = zip(['wk1', 'wk2', 'wk3', 'wk4'],new_date)
    data_by_week = []
    for week in new_date:
        dates = dict(zip(['start', 'end'],[week[0],week[1]]))
        #boys + girls
        all_data = value_gen(slugs,dates,schools)
        data_by_week.append(compute_total(all_data))

    """

    # use attendance dicts to populate attendance of folks in school
    return render_to_response('education/emis_chart.html',{
        'boy_attendance':boy_attendance.items(),
        'girl_attendance':girl_attendance.items(),
        'categories':categories,
        },RequestContext(req))


@super_user_required
def edit_user(request, user_pk=None):
    title=""
    user=User()
    if request.method == 'POST':
        if user_pk:
            user = get_object_or_404(User, pk=user_pk)
        user_form = UserForm(request.POST,instance=user,edit=True)
        if user_form.is_valid():
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

            return HttpResponseRedirect(reverse("emis-users"))

    elif user_pk:
        user = get_object_or_404(User, pk=user_pk)
        user_form = UserForm(instance=user,edit=True)
        title="Editing "+user.username
    else:
        user_form = UserForm(instance=user)

    return render_to_response('education/partials/edit_user.html', {'user_form': user_form,'title':title},
        context_instance=RequestContext(request))

@login_required
def alerts_detail(request, alert, district_id=None):
    user_location = get_location(request, district_id)
    schools_queryset = School.objects.filter(location__in=user_location.get_descendants(include_self=True).all())
    start_date = datetime.datetime(datetime.datetime.now().year, 1, 1)
    end_date = datetime.datetime.now()
    if int(alert) == 1:
        results_title = "Schools which didn't send in Pupil Attendance Data this Week"
        start_date, end_date = previous_calendar_week()
        responsive_schools = XFormSubmissionValue.objects.all()\
        .filter(Q(submission__xform__keyword__icontains='boys')|Q(submission__xform__keyword__icontains='girls'))\
        .filter(created__range=(start_date, end_date))\
        .filter(submission__connection__contact__emisreporter__schools__location__in=user_location.get_descendants(include_self=True).all())\
        .values_list('submission__connection__contact__emisreporter__schools__name', flat=True)
        schools_queryset = schools_queryset.exclude(name__in=responsive_schools)

    if int(alert) == 2:
        print 2
        results_title = "Schools which have not sent in Pupil Enrollment Data this Year"
        responsive_schools = XFormSubmissionValue.objects.all()\
        .filter(Q(submission__xform__keyword__icontains='enrolledb')|Q(submission__xform__keyword__icontains='enrolledg'))\
        .filter(created__range=(start_date, end_date))\
        .filter(submission__connection__contact__emisreporter__schools__location__in=user_location.get_descendants(include_self=True).all())\
        .values_list('submission__connection__contact__emisreporter__schools__name', flat=True)
        schools_queryset = schools_queryset.exclude(name__in=responsive_schools)

    if int(alert) == 3:
        results_title = "Schools which have not sent in Teacher Deployment Data this Year"
        responsive_schools = XFormSubmissionValue.objects.all()\
        .filter(submission__xform__keyword__icontains='deploy')\
        .filter(created__range=(start_date, end_date))\
        .filter(submission__connection__contact__emisreporter__schools__location__in=user_location.get_descendants(include_self=True).all())\
        .values_list('submission__connection__contact__emisreporter__schools__name', flat=True)
        schools_queryset = schools_queryset.exclude(name__in=responsive_schools)

    return generic(request,
        model = School,
        queryset = schools_queryset,
        filter_forms = [FreeSearchSchoolsForm, SchoolDistictFilterForm],
        action_forms = [SchoolMassTextForm],
        objects_per_page = 25,
        results_title = results_title,
        partial_row = 'education/partials/alerts_row.html',
        partial_header = 'education/partials/partial_header.html',
        base_template = 'education/schools_base.html',
        columns = [('Name', True, 'name', SimpleSorter()),
            ('District', True, 'location__name', None,),
            ('Head Teacher', False, 'emisreporter', None,),
            ('Reporters', False, 'emisreporter', None,),
            ('Last Report Date ', True, 'report_date', None,)
        ],
        sort_column = 'date',
        sort_ascending = False,
        alert = alert,
    )

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
        #      top_columns = [
        #            ('', 1, None),
        #            ('head teacher attendance (reported by SMCs)', 2, None),
        #            ('head teacher attendance (reported by GEM)', 2, None),
        #        ],
        columns = [
            ('school', False, 'school', None),
            ('present', False, 'present', None),
            ('reporting date', False, 'date', None),
            #            ('present', False, 'present', None),
            #            ('reporting date', False, 'date', None),
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
    for script in Script.objects.all().order_by('slug'):
        forms.append((script, ScriptsForm(instance=script)))

    if request.method == 'POST':
        script_form = ScriptsForm(request.POST,instance=Script.objects.get(slug=request.POST.get('slug')))
        if script_form.is_valid():
            script_form.save()

    return render_to_response('education/partials/edit_script.html', {'forms': forms},
        context_instance=RequestContext(request))

#TODO work on forms
def choose_level(request):
    forms = []
    pass


def reschedule_scripts(request, script_slug):
#    import subprocess
#    from django.core.management import call_command
    grp = get_script_grp(script_slug)
    if script_slug.endswith('_weekly'):
#        call_command('reschedule_weekly_polls', grp)
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

# Reporters view

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
        context_instance = RequestContext(req)
    )