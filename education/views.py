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
import  re, datetime, operator, xlwt


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

def dash_ministry_progress(request):
    pass

def dash_admin_progress(req):
    p3_response = 34
    return render_to_response('education/admin/progress.html', {'p3':p3_response}, RequestContext(req))

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

#BEGIN Capitation

def dash_capitation(request):
    #to_ret = YES, NO, I don't know
    to_ret = zip(['Yes','No', "Unknown"],[30, 30, 40])
    return render_to_response('education/dashboard/capitation.html', {'responses':to_ret}, RequestContext(request))

def dash_ministry_capitation(req):
    to_ret = zip(['Yes','No', "Unknown"],[30, 30, 40])
    return render_to_response('education/dashboard/capitation.html', {'responses':to_ret}, RequestContext(req))

def dash_deo_capitation(req):
    to_ret = zip(['Yes','No', "Unknown"],[30, 30, 40])
    return render_to_response('education/dashboard/capitation.html', {'responses':to_ret}, RequestContext(req))




# Dashboard specific view functions

@login_required
def dashboard(request):
    profile = request.user.get_profile()
    if profile.is_member_of('DEO'):
        return deo_dashboard(request)
    elif profile.is_member_of('Ministry Officials'):
        return ministry_dashboard(request)
    elif profile.is_member_of('Admins'):
        return admin_dashboard(request)
    else:
        return testindex(request)

# generate context vars
def generate_dashboard_vars(location=None):
    locations = []
    if location.name == "Uganda":
        # get locations from active districts only
        locations = Location.objects.filter(pk__in=EmisReporter.objects.values_list('reporting_location__pk', flat=True)).distinct()
    else:
        locations.append(location)
    responses_to_violence = poll_response_sum("edtrac_headteachers_abuse",month_filter = 'monthly', locations = locations)
    # percentage change in violence from previous month
    violence_change = cleanup_sums(responses_to_violence)
    if violence_change > 0:
        violence_change_class = "increase"
        violence_change_data = "data-green"
    elif violence_change < 0:
        violence_change_class = "decrease"
        violence_change_data = "data-red"
    else:
        violence_change_class = "zero"
        violence_change_data = "data-white"

    # CSS class (dynamic icon)
    x, y = poll_responses_past_week_sum("edtrac_boysp3_attendance", locations=locations, weeks=1)
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

    try:
        boysp3_diff = 100 * (x - y) / x
    except ZeroDivisionError:
        boysp3_diff = 0 # just return zero (till more data is populated in the system)

    if x > y:
        boysp3_class = 'negative'
    elif x < y:
        boysp3_class = 'positive'
    else:
        boysp3_class = 'zero'

    x, y  = poll_responses_past_week_sum("edtrac_boysp6_attendance", locations=locations, weeks=1)
    enrol = poll_responses_term("edtrac_boysp6_enrollment", belongs_to="location", locations=locations)
    try:
        boysp6 = 100*(enrol - x ) / enrol
    except ZeroDivisionError:
        boysp6 = 0

    try:
        boysp6_past = 100*(enrol - y ) / enrol
    except ZeroDivisionError:
        boysp6_past = 0

    try:
        boysp6_diff = 100 * ( x - y ) / x
    except ZeroDivisionError:
        boysp6_diff = 0

    if x > y:
        boysp6_class = 'negative'
    elif x < y:
        boysp6_class = 'positive'
    else:
        boysp6_class = 'zero'

    x, y = poll_responses_past_week_sum("edtrac_girlsp3_attendance",locations=locations, weeks=1)
    enrol = poll_responses_term("edtrac_girlsp3_enrollment", belongs_to="location", locations=locations)
    try:
        girlsp3 = 100*(enrol - x ) / enrol
    except ZeroDivisionError:
        girlsp3 = 0

    try:
        girlsp3_past = 100*(enrol - y ) / enrol
    except ZeroDivisionError:
        girlsp3_past = 0

    try:
        girlsp3_diff = 100 * ( x - y ) / x
    except ZeroDivisionError:
        girlsp3_diff = 0

    if x > y:
        girlsp3_class = "negative"
    elif x < y:
        girlsp3_class = "positive"
    else:
        girlsp3_class = "zero"

    x, y = poll_responses_past_week_sum("edtrac_girlsp6_attendance", locations=locations, weeks=1)
    enrol = poll_responses_term("edtrac_girlsp6_enrollment", belongs_to="location", locations=locations)

    try:
        girlsp6 = 100*(enrol - x ) / enrol
    except ZeroDivisionError:
        girlsp6 = 0

    try:
        girlsp6_past = 100*(enrol - y ) / enrol
    except ZeroDivisionError:
        girlsp6_past = 0

    try:
        girlsp6_diff = 100 * ( x - y ) / x
    except ZeroDivisionError:
        girlsp6_diff = 0

    if x > y:
        girlsp6_class = "negative"
    elif x < y:
        girlsp6_class = "positive"
    else:
        girlsp6_class = "zero"

    x, y = poll_responses_past_week_sum("edtrac_f_teachers_attendance",locations=locations, weeks=1)
    deploy = poll_responses_term("edtrac_f_teachers_deployment", belongs_to="location", locations=locations)
    try:
        female_teachers = 100*(deploy - x ) / deploy
    except ZeroDivisionError:
        female_teachers = 0

    try:
        female_teachers_past = 100*(deploy - y ) / deploy
    except ZeroDivisionError:
        female_teachers_past = 0

    try:
        female_teachers_diff = 100 * ( x - y ) / x
    except ZeroDivisionError:
        female_teachers_diff = 0

    if x > y:
        female_teachers_class = "negative"
    elif x < y:
        female_teachers_class = "positive"
    else:
        female_teachers_class = "zero"

    x, y = poll_responses_past_week_sum("edtrac_m_teachers_attendance", weeks=1, locations=locations)
    deploy = poll_responses_term("edtrac_m_teachers_deployment", belongs_to="location", locations=locations)
    try:
        male_teachers = 100*(deploy - x ) / deploy
    except ZeroDivsionError:
        male_teachers = 0

    try:
        male_teachers_past = 100*(deploy - y ) / deploy
    except ZeroDivisionError:
        male_teachers_past = 0

    try:
        male_teachers_diff = 100 * ( x - y ) / x
    except ZeroDivisionError:
        male_teachers_diff = 0

    if x > y:
        male_teachers_class = "negative"
    elif x < y:
        male_teachers_class = "positive"
    else:
        male_teachers_class = "zero"

    responses_to_meals = poll_response_sum("edtrac_headteachers_meals",
        month_filter='biweekly', locations=locations)
    # percentage change in meals missed
    meal_change = cleanup_sums(responses_to_meals)
    if meal_change > 0:
        meal_change_class = "increase"
        meal_change_data = "data-green"
    elif meal_change < 0:
        meal_change_class = "decrease"
        meal_change_data = "data-red"
    else:
        meal_change_class = "zero"
        meal_change_data = "data-white"


#    responses_to_smc_meetings_poll = poll_response_sum("edtrac_smc_meetings",
#        month_filter = True, location=locations, ret_type=list)
#
#    responses_to_grants_received = poll_response_sum("edtrac_smc_upe_grant",
#        month_filter=True, location=locations, ret_type=list)
#
#    sorted_violence_list = responses_to_violence
#    sorted_hungry_list = responses_to_meals
#    #sorted list...
#
#    top_three_violent_districts = sorted_violence_list[:3]
#    #can make a dictionary
#    top_three_hungry_districts = sorted_hungry_list[:3]

    return {
#        'top_three_violent_districts':top_three_violent_districts,
#        'top_three_hungry_districts':top_three_hungry_districts,
        'violence_change' : violence_change,
        'violence_change_class' : violence_change_class,
        'violence_change_data' : violence_change_data,
        'meal_change' : meal_change,
        'meal_change_class': meal_change_class,
        'meal_change_data' : meal_change_data,
        'male_teachers' : male_teachers,
        'male_teachers_past' : male_teachers_past,
        'male_teachers_diff' : male_teachers_diff,
        'male_teachers_class' : male_teachers_class,
        'female_teachers_class' : female_teachers_class,
        'female_teachers' :female_teachers,
        'female_teachers_past' : female_teachers_past,
        'female_teachers_diff' : female_teachers_diff,
        'girlsp3' : girlsp3,
        'girlsp3_past' : girlsp3_past,
        'girlsp3_class': girlsp3_class,
        'girlsp3_diff' : girlsp3_diff,
        'girlsp6' : girlsp6,
        'girlsp6_past' : girlsp6_past,
        'girlsp6_diff' : girlsp6_diff,
        'girlsp6_class' : girlsp6_class,
        'boysp3' : boysp3,
        'boysp3_past': boysp3_past,
        'boysp3_class' : boysp3_class,
        'boysp3_diff' : boysp3_diff,
        'boysp6' : boysp6,
        'boysp6_past' : boysp6_past,
        'boysp6_class' : boysp6_class,
        'boysp6_diff' : boysp6_diff,
        'month':datetime.datetime.now(),
        'schools_to_date':School.objects.filter(pk__in=EmisReporter.objects.exclude(schools=None).\
                    values_list('schools__pk')).count()
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
    location = request.user.get_profile().location
    return render_to_response("education/admin/admin_dashboard.html", generate_dashboard_vars(location=location),
        RequestContext(request))

# Details views... specified by ROLES
class ViolenceAdminDetails(TemplateView):
    template_name = "education/admin/admin_violence_details.html"
    #TODO open this up with more data variables
    def get_context_data(self, **kwargs):
        context = super(ViolenceAdminDetails, self).get_context_data(**kwargs)
        #TODO: filtering by ajax and time
        violence_cases_schools = poll_response_sum("edtrac_headteachers_abuse",
            location=self.request.user.get_profile().location, month_filter=True, months=2, ret_type=list)

        total = []

        for name, list_val in violence_cases_schools:
            try:
                diff = (list_val[0] - list_val[1]) / list_val[0]
                total.append((list_val[0], list_val[1], diff))
            except ZeroDivisionError:
                diff = '--'

            list_val.append(diff)

        context['violence_cases_reported_by_schools'] = violence_cases_schools

        first_col, second_col, third_col = [],[],[]
        for first, second, third in total:
            first_col.append(first), second_col.append(second), third_col.append(third)
        context['totals'] = [sum(first_col), sum(second_col), sum(third_col)]

        # depth of 2 months
        context['report_dates'] = [start for start, end in get_month_day_range(datetime.datetime.now(), depth=2)]
        report_count = 0
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

            resp_count = Poll.objects.get(name="edtrac_headteachers_abuse").responses.filter(
                contact__in = contacts,
                date__range = dr).count()

            report_count += resp_count
        try:
            context['reporting_percentage'] = 100 * ( report_count / (float(len(get_month_day_range(datetime.datetime.now(),
                depth=2))) * report_count))
        except ZeroDivisionError:
            context['reporting_percentage'] = 0
        return context

class AttendanceAdminDetails(TemplateView):
    template_name = "education/admin/attendance_details.html"

    def get_context_data(self, **kwargs):

        context = super(AttendanceAdminDetails, self).get_context_data(**kwargs)
        #TODO: proper drilldown of attendance by school
        # National level ideally "admin" and can be superclassed to suit other roles
        profile = self.request.user.get_profile()
        if profile.is_member_of("Admins") or profile.is_member_of("Ministry Officials"):
            names = list(set(EmisReporter.objects.exclude(reporting_location=None).filter(reporting_location__type="district").\
                        values_list('reporting_location__name',flat=True).distinct()))
            locations = Location.objects.filter(name__in=names).order_by("name")
            #locations = Location.objects.get(name="Uganda").get_descendants().filter(type="district").order_by("name")
            #context['total_districts'] = Location.objects.get(name="Uganda").get_descendants().filter(type="district").count()
            context['total_disticts'] = locations.count()
        else:
            locations = [profile.location]

        headings = [
            'Location', 'Boys P3', 'Boys P6', 'Girls P3', 'Girls P6', 'Female Teachers', "Male Teachers",
            "Male Head Teachers", "Female Head Teachers"
                    ]
        context['headings'] = headings
        context['week'] = datetime.datetime.now()
        context['location'] = profile.location
        location_data_container = []
        for loc in locations:
            location_data_container.append(
                [loc,
                 poll_response_sum("edtrac_boysp3_attendance", month_filter='weekly', location=loc),
                 poll_response_sum("edtrac_boysp6_attendance", month_filter='weekly', location=loc),
                 poll_response_sum("edtrac_girlsp3_attendance", month_filter='weekly', location=loc),
                 poll_response_sum("edtrac_girlsp3_attendance", month_filter='weekly', location=loc),
                 poll_response_sum("edtrac_f_teachers_attendance", month_filter='weekly', location=loc),
                 poll_response_sum("edtrac_m_teachers_attendance", month_filter='weekly', location=loc),
                 poll_response_sum("edtrac_head_teachers_attendance", month_filter="weekly", location=loc),
                 poll_response_sum("edtrac_head_teachers_attendance", month_filter="weekly", location=loc)
                ]
            )
        context['location_data'] = location_data_container

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
    template_name = "education/admin/admin_progress_details.html"

    def get_context_data(self, **kwargs):
        from .utils import themes
        context = super(ProgressAdminDetails, self).get_context_data(**kwargs)
        ##context['some_key'] = <some_list_of_response>
        # we get all violence cases ever reported
        #TODO: filtering by ajax and time
        context['progress'] = list_poll_responses(Poll.objects.get(name="edtrac_p3curriculum_progress"))
        # decimal module used to work with really floats with more than 2 decimal places
        from decimal import getcontext, Decimal
        getcontext().prec = 1
        context['progress_figures'] = get_count_response_to_polls(Poll.objects.get(name="edtrac_p3curriculum_progress"),\
            location=self.request.user.get_profile().location,
            choices = [Decimal(str(key)) for key in themes.keys()],
            poll_type="numeric"
        )
        return context


class MealsAdminDetails(TemplateView):
    template_name = "education/admin/admin_meals_details.html"
    def get_context_data(self, **kwargs):
        choices=[0, 25, 50, 75, 100]
        context = super(MealsAdminDetails, self).get_context_data(**kwargs)
        context['school_meals_reports'] = get_count_response_to_polls(Poll.objects.get(name="edtrac_headteachers_meals"),\
            month_filter=True, choices=choices)

        context['community_meals_reports'] = get_count_response_to_polls(Poll.objects.get(name="edtrac_smc_meals"),
            month_filter=True, choices=choices)
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

## management controll panel

def control_panel(req):
    return render_to_response('education/partials/control_panel.html', {}, RequestContext(req))



#District violence details (TODO: permission/rolebased viewing)
class DistrictViolenceDetails(DetailView):
    context_object_name = "district_violence"
    model = Location

    def get_context_data(self, **kwargs):
        context = super(DistrictViolenceDetails, self).get_context_data(**kwargs)
        location = Location.objects.filter(type="district").get(pk=int(self.kwargs.get('pk'))) or self.request.user.get_profile().location
        schools = School.objects.filter(location=location)
        school_case = []
        for school in schools:
            # optimize with value queries
            school_case.append((school,
                            poll_response_sum('edtrac_headteachers_abuse', school=school, time_range=get_month_day_range(datetime.datetime.now()))))

        #schools and reports from a district

        #reports = poll_response_sum("edtrac_headteachers_abuse", month_filter=True, months=1)
        emis_reporters = EmisReporter.objects.exclude(connection__in=\
            Blacklist.objects.values_list('connection')).filter(schools__in=schools)

        context['location'] = location
        context['school_vals'] = school_case
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

# Meals being had at a district
class DistrictMealsDetails(DetailView):
    context_object_name = "district_meals"
    model = Location

    def get_context_data(self, **kwargs):
        context = super(DistrictMealsDetails, self).get_context_data(**kwargs)
        location = Location.objects.filter(type="district").get(pk=int(self.kwargs.get('pk')))
        context['location'] = location
        return context


##########################################################################################################
##########################################################################################################
################################ Other handy views for EduTrac ############################################
##########################################################################################################
##########################################################################################################

HEADINGS = ['Location', 'Absent (%) This week', 'Absent (%) Last week', 'Change (%) for absenteeism from last week']

@login_required
def boysp3_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").get(id=location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        to_ret.append((
            school, poll_response_sum("edtrac_boysp3_attendance", month_filter='weekly',school=school)
        ))
    return render_to_response("education/boysp3_district_attd_detail.html", { 'location':location,\
                                        'location_data':to_ret,\
                                        'week':datetime.datetime.now(),\
                                        'headings' : ['School', 'Number']
                                        }, RequestContext(req))

@login_required
def boysp6_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").get(id=location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        to_ret.append((
            school, poll_response_sum("edtrac_boysp6_attendance", month_filter='weekly',school=school)
            ))
    return render_to_response("education/boysp6_district_attd_detail.html", { 'week':datetime.datetime.now(),\
        'location':location,\
        'headings':['School','Number'],\
        'location_data':to_ret },\
        RequestContext(req))


@login_required
def girlsp3_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").get(id=location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        to_ret.append((
            school, poll_response_sum("edtrac_girlsp3_attendance", month_filter='weekly', school=school)
            ))
    return render_to_response("education/girlsp3_district_attd_detail.html", { 'location_data':to_ret,\
                                                                               'headings':['School', "Number"],\
                                                                               'location':location}, RequestContext(req))

@login_required
def girlsp6_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").get(id=location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        to_ret.append((
            school, poll_response_sum("edtrac_girlsp6_attendance", month_filter='weekly',school=school)
            ))
    return render_to_response("education/girlsp6_district_attd_detail.html", { 'location_data':to_ret }, RequestContext(req))


@login_required
def female_t_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").get(id=location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        to_ret.append((
            school, poll_response_sum('edtrac_boysp3_attendance', month_filter='weekly',school=school)
            ))
    return render_to_response("education/female_t_district_attd_detail.html", { 'location_data':to_ret }, RequestContext(req))

@login_required
def male_t_district_attd_detail(req, location_id):
    """
    This gets the details about schools in a district, the people in attedance, etc.
    """
    location = Location.objects.exclude(type="country").get(id=location_id)
    schools = School.objects.filter(location=location)
    to_ret = []
    for school in schools:
        to_ret.append((
            school, poll_response_sum("edtrac_boysp3_attendance", month_filter='weekly',school=school)
            ))
    return render_to_response("education/male_t_district_attd_detail.html", { 'location_data':to_ret }, RequestContext(req))

def boys_p3_attendance(req):
    location = req.user.get_profile().location
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins'):
        """
        This view shows data by district
        """
        locations = Location.objects.exclude(type="country").filter(type="district", name__in=EmisReporter.objects.distinct().values_list('reporting_location__name', flat=True)).order_by("name")
        # return view that will give shool-based views
        # --> ref function just below this <---
        return boys_p3_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)
        data_to_render = []
        for school in schools:
            data = poll_response_sum("edtrac_boysp3_attendance", month_filter='weekly', school=school)
            data_to_render.append(
                [
                    school,
                    school.location,
                    data
                ]
            )

        return  render_to_response(
            'education/partials/boys_p3_attendance.html',
            {
                'week':datetime.datetime.now(),
                'headings':['School', 'District', 'Number'],
                'location_data': data_to_render
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
    location = req.user.get_profile().location
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins'):
        locations = Location.objects.exclude(type="country").filter(name__in=\
            EmisReporter.objects.values_list('reporting_location__name', flat=True)).distinct().order_by("name")
        return boys_p6_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)
        data_to_render = []
        for school in schools:
            data = poll_response_sum("edtrac_boysp6_attendance", month_filter='weekly', school=school)
            data_to_render.append(
                [
                    school,
                    school.location,
                    data
                ]
            )

        return  render_to_response(
            'education/partials/boys_p6_attendance.html',
                {
                'week':datetime.datetime.now(),
                'headings':['School', 'District', 'Number'],
                'location_data': data_to_render
            },
            RequestContext(req)
        )

def boys_p6_attd_admin(req, **kwargs):
    """
    Helper function to get differences in absenteeism across districts for P6 boys.
    """
    # P6 attendance /// what to show an admin or Ministry official
    locations = kwargs.get('locations')
    to_ret = return_absent('edtrac_boysp6_attendance', 'edtrac_boysp6_enrollment', locations)
    
    return render_to_response(
        'education/partials/boys_p6_attd_admin.html',
        {'location_data':to_ret,
            'headings': HEADINGS,
            'week':datetime.datetime.now()}, RequestContext(req))            


def girls_p3_attendance(req):
    location = req.user.get_profile().location
    profile = req.user.get_profile()
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins'):
        locations = Location.objects.exclude(type="country").filter(name__in=\
            EmisReporter.objects.values_list('reporting_location__name', flat=True)).distinct().order_by("name")
        return girls_p3_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)
        data_to_render = []

        for school in schools:
            data = poll_response_sum("edtrac_girlsp3_attendance", month_filter='weekly', school=school)
            data_to_render.append([school, school.location, data])

            return render_to_response('education/partials/girls_p3_attendance.html',{
                                        'week':datetime.datetime.now(),
                                        'headings':['School', 'District', 'Number'],
                                        'location_data': data_to_render}, RequestContext(req))

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
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins'):
        locations = Location.objects.exclude(type="country").filter(name__in=\
            EmisReporter.objects.values_list('reporting_location__name', flat=True)).distinct().order_by("name")
        return girls_p6_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)
        data_to_render = []
        for school in schools:
            data = poll_response_sum("edtrac_girlsp6_attendance", month_filter='weekly', school=school)
            data_to_render.append([school, school.location, data])
        return render_to_response(
            'education/partials/girls_p6_attendance.html',
                {'week':datetime.datetime.now(),
                'headings':['School', 'District', 'Number'],
                'location_data': data_to_render}, RequestContext(req))

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
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins'):
        locations = Location.objects.exclude(type="country").filter(name__in=\
            EmisReporter.objects.distinct().values_list('reporting_location__name',flat=True)).order_by("name")
        return female_teacher_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)

        data_to_render = []
        for school in schools:
            data = poll_response_sum(
                Poll.objects.get(name="edtrac_f_teachers_attendance"),month_filter='weekly',location=school.location)
            data_to_render.append([school, school.location, data])
        return render_to_response(
            'education/partials/female_teachers_attendance.html',
                {
                'week':datetime.datetime.now(),
                'headings':['School', 'District', 'Number'],
                'location_data': data_to_render
            },
            RequestContext(req)
        )

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
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins'):
        locations = Location.objects.exclude(type="country").filter(name__in=\
            EmisReporter.objects.distinct().values_list('reporting_location__name',flat=True)).order_by("name")
        return male_teacher_attd_admin(req, locations=locations)
    else:
        #DEO
        schools = School.objects.filter(location=location)

        data_to_render = []
        for school in schools:
            data = poll_response_sum(
                Poll.objects.get(name="edtrac_m_teachers_attendance"),month_filter='weekly',location=school.location)
            data_to_render.append([school, school.location, data])
        return render_to_response(
            'education/partials/male_teachers_attendance.html',
                {
                'week':datetime.datetime.now(),
                'headings':['School', 'Location', 'Number'],
                'location_data': data_to_render
            },
            RequestContext(req)
        )

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
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins'):
        schools = School.objects.filter(location__name__in=EmisReporter.objects.distinct().values_list('reporting_location__name', flat=True))
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
    if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins'):
        schools = School.objects.filter(location__name__in=list(set(EmisReporter.objects.distinct().\
            values_list('reporting_location__name', flat=True)))).order_by('name','location__name')
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
    last_submissions = school_last_xformsubmission(request, school_id)
    return render_to_response("education/school_detail.html", {\
        'school': school,
        'last_submissions': last_submissions,
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
                profile.role=Role.objects.get(pk=user.groups.all()[0].pk)
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