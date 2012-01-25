from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, TemplateView
from .forms import *
from .models import *
from uganda_common.utils import *
from rapidsms.contrib.locations.models import Location
from generic.views import generic
from generic.sorters import SimpleSorter
from poll.models import Poll
from .reports import *
from .utils import *
from urllib2 import urlopen
import  re, datetime, operator


Num_REG = re.compile('\d+')

super_user_required=user_passes_test(lambda u: u.groups.filter(name__in=['Admins','DFO']).exists() or u.is_superuser)

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

@login_required
def deo_dashboard(request):
    location = request.user.get_profile().location
    violence = get_sum_of_poll_response(Poll.objects.get(name="emis_headteachers_abuse"),
        location=location)
    months = ["Jan", "Feb", "March"]
    district_violence = [343,234,64]
    dicty = dict(zip(months, district_violence))

    return index(request, template_name="deo/deo_dashboard.html",
        context_vars={'dicty':dicty,
                      'x_vals':months,
                      'y_vals':district_violence})

@login_required
def ministry_dashboard(request):
    violence = list_poll_responses(Poll.objects.get(name="emis_headteachers_abuse"))
    districts = violence.keys()
    #assumption is still 4 districts
    district_violence = [23,56, 23, 66]
    dicty = dict(zip(districts, district_violence))

    meal_poll_responses = list_poll_responses(Poll.objects.get(name="emis_headteachers_meals"))
    districts = meal_poll_responses.keys()
    lunches_to_ret = dict(zip(districts, [10, 20, 30, 40]))

    return index(request, template_name="ministry/ministry_dashboard.html",
        context_vars={'dicty':dicty,
                      'x_vals':districts,
                      'y_vals':district_violence,
                      'lunches':lunches_to_ret})

@login_required
def admin_dashboard(request):
    location = request.user.get_profile().location
    responses_to_violence = get_sum_of_poll_response(Poll.objects.get(name = "edtrac_headteachers_abuse"),
        month_filter = True,
        location = location,
        ret_type = list, months=2)

    responses_to_meals = get_sum_of_poll_response(Poll.objects.get(name = "edtrac_headteachers_meals"),
                       month_filter=True,
                       location=location, ret_type = list, action='avg', months=2)

    responses_to_smc_meetings_poll = get_sum_of_poll_response(Poll.objects.get(name="edtrac_smc_meetings"),
        month_filter = True, location=location, ret_type=list
    )
    responses_to_grants_received = get_sum_of_poll_response(Poll.objects.get(name="edtrac_upe_grant"),
        month_filter=True, location=location, ret_type=list
    )

    sorted_violence_list = responses_to_violence
    sorted_hungry_list = responses_to_meals
    #sorted list...

    top_three_violent_districts = sorted_violence_list[:3]
    #can make a dictionary
    top_three_hungry_districts = sorted_hungry_list[:3]

    return index(request, template_name="admin/admin_dashboard.html",
        context_vars={
            'top_three_violent_districts':top_three_violent_districts,
            'top_three_hungry_districts':top_three_hungry_districts
            })

# Details views... specified by ROLES
class ViolenceAdminDetails(TemplateView):
    template_name = "education/admin/admin_violence_details.html"
    #TODO open this up with more data variables
    def get_context_data(self, **kwargs):
        context = super(ViolenceAdminDetails, self).get_context_data(**kwargs)
        #TODO: filtering by ajax and time
        #For demo purpooses
#        districts = ['kyegegwa', 'kotido', 'kaboong']
#        context['violence_cases_reported_by_schools'] = [(loc.__unicode__(), [23,34, loc]) for loc in Location.objects.filter(type="district", name__in=[d.title() for d in districts])]
#        context['violence_cases_reported_by_community'] = [(loc.__unicode__(), [23,18, loc]) for loc in Location.objects.filter(type="district", name__in=[d.title() for d in districts])]
        context['violence_cases_reported_by_schools'] = get_sum_of_poll_response(Poll.objects.get(name="edtrac_headteachers_abuse"),
            location=self.request.user.get_profile().location, month_filter=True, months=2, ret_type=list)
        return context

class ViolenceDeoDetails(TemplateView):
    template_name = "education/deo/deo_violence_details.html"

    def get_context_data(self, **kwargs):
        context = super(ViolenceDeoDetails, self).get_context_data(**kwargs)
        #context['violence_cases'] = list_poll_responses(Poll.objects.get(name="emis_headteachers_abuse"))
        context['violence_cases'] = get_sum_of_poll_response(Poll.objects.get(name="edtrac_headteachers_abuse"),
            location=self.request.user.get_profile().location, month_filter=True)
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ViolenceDeoDetails, self).dispatch(*args, **kwargs)

#District violence details (TODO: permission/rolebased viewing)
class DistrictViolenceDetails(DetailView):
    context_object_name = "district_violence"
    model = Location

    def get_context_data(self, **kwargs):
        context = super(DistrictViolenceDetails, self).get_context_data(**kwargs)
        location = Location.objects.filter(type="district").get(pk=int(self.kwargs.get('pk')))
        context['location'] = location

        #schools and reports from a district
        schools = School.objects.filter(location=location)
        reports = get_sum_of_poll_response(Poll.objects.get(name="edtrac_headteachers_abuse"), month_filter=True, months=1)
        context['schools'] = School.objects.filter(location=location)

        context['school_vals'] = [('kaio', 23), ('ksdf',34)]
        return context

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

class ProgressMinistryDetails(TemplateView):
    template_name = "education/ministry/ministry_progress_details.html"
    @method_decorator(login_required)
    def get_context_data(self, **kwargs):
        context = super(ProgressMinistryDetails, self).get_context_data(**kwargs)
        return context

class ProgressDeoDetails(TemplateView):
    template_name = "education/deo/deo_progress_details.html"

    def get_context_data(self, **kwargs):
        context = super(ProgressDeoDetails, self).get_context_data(**kwargs)
        #TODO mixins and filters
        context['progress'] = list_poll_responses(Poll.objects.get(name="edtrac_p3curriculum_progress"))

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

class MealsMinistryDetails(TemplateView):
    template_name = "education/ministry/ministry_meals_details.html"
    #TODO open this up with more data variables
    def get_context_data(self, **kwargs):
        context = super(MealsMinistryDetails, self).get_context_data(**kwargs)
        ##context['some_key'] = <some_list_of_response>
        return context

class MealsAdminDetails(TemplateView):
    template_name = "education/admin/admin_meals_details.html"
    def get_context_data(self, **kwargs):
        context = super(MealsAdminDetails, self).get_context_data(**kwargs)

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
        if not connection.contact and \
            not ScriptProgress.objects.filter(script__slug='emis_autoreg', connection=connection).count():
                        ScriptProgress.objects.create(script=Script.objects.get(slug="emis_autoreg"), \
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
            connection, created = Connection.objects.get_or_create(identity=identity, backend=backend)
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
    reporter_form = EditReporterForm(instance=reporter)
    if request.method == 'POST':
        reporter_form = EditReporterForm(instance=reporter,
                data=request.POST)
        if reporter_form.is_valid():
            reporter_form.save()
        else:
            return render_to_response('education/partials/edit_reporter.html',
                    {'reporter_form': reporter_form,
                     'reporter': reporter},
                    context_instance=RequestContext(request))
        return render_to_response('/education/partials/reporter_row.html',
                                  {'object':EmisReporter.objects.get(pk=reporter_pk),
                                   'selectable':True},
                                  context_instance=RequestContext(request))
    else:
        return render_to_response('education/partials/edit_reporter.html',
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
    base_template = 'education/timeslider_base.html',
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
    grp = get_script_grp(script_slug)
    if script_slug.endswith('_weekly'):
        reschedule_weekly_polls(grp)
    elif script_slug.endswith('_monthly'):
        reschedule_monthly_polls(grp)
    else:
        reschedule_termly_polls(grp)
    new_script_date = ScriptProgress.objects.filter(script__slug=script_slug)[0].time
    response = HttpResponse("This Script has been rescheduled to: %s " % new_script_date.strftime("%d-%m-%Y %H:%M"))
    return response     

