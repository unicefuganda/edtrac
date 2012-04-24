from .forms import SchoolFilterForm, LimitedDistictFilterForm,\
    RolesFilterForm, ReporterFreeSearchForm, SchoolDistictFilterForm, FreeSearchSchoolsForm, MassTextForm

from .models import EmisReporter, School
from .reports import messages, othermessages, reporters, schools
#from .reports import AttendanceReport, messages, othermessages, reporters, schools
from .sorters import LatestSubmissionSorter
from .views import *
#from education.views import ChartView
from contact.forms import\
    FreeSearchTextForm, DistictFilterMessageForm, HandledByForm, ReplyTextForm
from django.conf.urls.defaults import *
from generic.sorters import SimpleSorter
from generic.views import generic, generic_row
from rapidsms_httprouter.models import Message
from rapidsms_xforms.models import XFormSubmission
from uganda_common.utils import get_xform_dates, get_messages
from django.contrib.auth.views import login_required
from django.contrib.auth.models import User
from django.views.generic import ListView
from .reports import othermessages

urlpatterns = patterns('',
    url(r'^edtrac/messages/$', login_required(generic), {
        'model':Message,
        'queryset':messages,
        'filter_forms':[FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
        'action_forms':[ReplyTextForm],
        'objects_per_page':25,
        'partial_row' : 'education/partials/messages/message_row.html',
        'base_template':'education/partials/contact_message_base.html',
        'paginator_template' : 'education/partials/pagination.html',
        'title' : 'Messages',
        'columns':[('Text', True, 'text', SimpleSorter()),
            ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
            ('Date', True, 'date', SimpleSorter(),),
            ('Type', True, 'application', SimpleSorter(),),
            ('Response', False, 'response', None,),
        ],
        'sort_column':'date',
        'sort_ascending':False,
        }, name="emis-messagelog"),


    url(r'^edtrac/other-messages/$', login_required(generic), {
        'model':Message,
        'queryset':othermessages,
        'filter_forms':[FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
        'action_forms':[ReplyTextForm],
        'objects_per_page':25,
        'partial_row' : 'education/partials/messages/message_row.html',
        'base_template':'education/partials/contact_message_base.html',
        'paginator_template' : 'education/partials/pagination.html',
        'title' : 'Messages',
        'columns':[('Text', True, 'text', SimpleSorter()),
            ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
            ('Date', True, 'date', SimpleSorter(),),
            ('Type', True, 'application', SimpleSorter(),),
            ('Response', False, 'response', None,),
        ],
        'sort_column':'date',
        'sort_ascending':False,
        }, name="emis-other-messages"),



    url(r'^edtrac/messagelog/(?P<error_msgs>\d+)/', login_required(generic), {
        'model':Message,
        'queryset':messages,
        'filter_forms':[FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
        'action_forms':[ReplyTextForm],
        'objects_per_page':25,
        'partial_row':'education/partials/message_row.html',
        'base_template':'education/messages_base.html',
        'columns':[('Text', True, 'text', SimpleSorter()),
            ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
            ('Date', True, 'date', SimpleSorter(),),
            ('Type', True, 'application', SimpleSorter(),),
            ('Response', False, 'response', None,),
        ],
        'sort_column':'date',
        'sort_ascending':False,
        }, name="emis-messagelog"),
    url(r'^edtrac/control-panel/$',control_panel, name="control-panel"),
    url(r'^edtrac/audit-trail/$', audit_trail, name="emis-audittrail"), #AuditTrail.as_view(), name="emis-audittrail"),
    #reporters
    url(r'^edtrac/reporter/$', login_required(generic), {
        'model':EmisReporter,
        'queryset':reporters,
        'filter_forms':[ReporterFreeSearchForm, RolesFilterForm, LimitedDistictFilterForm, SchoolFilterForm],
        'action_forms':[MassTextForm],
        'objects_per_page':25,
        'title' : 'Reporters',
        'partial_row':'education/partials/reporters/reporter_row.html',
        'partial_header':'education/partials/reporters/reporter_partial_header.html',
        'base_template':'education/partials/contact_message_base.html',
        'results_title':'Reporters',
        'columns':[('Name', True, 'name', SimpleSorter()),
            ('Number', True, 'connection__identity', SimpleSorter()),
            ('Grade', True, 'grade', SimpleSorter()),
            ('Gender', True, 'gender', SimpleSorter()),
            ('Role(s)', True, 'groups__name', SimpleSorter(),),
            ('District', False, 'district', None,),
            ('Last Reporting Date', True, 'latest_submission_date', LatestSubmissionSorter(),),
            ('Total Reports', True, 'connection__submissions__count', SimpleSorter(),),
            ('School(s)', True, 'schools__name', SimpleSorter(),),
            #                 ('Location', True, 'reporting_location__name', SimpleSorter(),),
            ('', False, '', None,)],
        }, name="emis-contact"),

    url(r'^edtrac/new-comment/$', new_comment, name='new-comment'),
    url(r'^edtrac/comments/$', comments, name='comments'),
    url(r'^edtrac/reporter/(\d+)/edit/', edit_reporter, name='edit-reporter'),
    url(r'^edtrac/reporter/(\d+)/delete/', delete_reporter, name='delete-reporter'),
    url(r'^edtrac/reporter/(?P<pk>\d+)/show', generic_row, {'model':EmisReporter, 'partial_row':'education/partials/reporters/reporter_row.html'}),
    url(r'^edtrac/ht_attendance/$', htattendance, {}, name='ht-attendance-stats'),
    url(r'^edtrac/ht_attendance/(?P<start_date>[0-9\-]+)/(?P<end_date>[0-9\-]+)$', htattendance, {}, name='ht-attendance-stats'),
    url(r'^edtrac/gemht_attendance/$', gem_htattendance, {}, name='gemht-attendance-stats'),
    url(r'^edtrac/gemht_attendance/(?P<start_date>[0-9\-]+)/(?P<end_date>[0-9\-]+)$', gem_htattendance, {}, name='gemht-attendance-stats'),
    url(r'^edtrac/meals/$', meals, {}, name='meals-stats'),

    url(r'^$', dashboard, name='rapidsms-dashboard'),
    url(r'^emis/whitelist/', whitelist),
    url(r'^connections/add/', add_connection),
    url(r'^connections/(\d+)/delete/', delete_connection),

    url(r'^edtrac/deo_dashboard/', login_required(deo_dashboard), {}, name='deo-dashboard'),
    url(r'^edtrac/school/$', login_required(generic), {
        'model':School,
        'queryset':schools,
        'filter_forms':[FreeSearchSchoolsForm, SchoolDistictFilterForm],
        'objects_per_page':25,
        'partial_row':'education/partials/school_row.html',
        'partial_header':'education/partials/school_partial_header.html',
        'base_template':'education/schools_base.html',
        'columns':[('Name', True, 'name', SimpleSorter()),
            ('District', True, 'location__name', None,),
            ('School ID', False, 'emis_id', None,),
            ('Head Teacher', False, 'emisreporter', None,),
            ('Reporters', False, 'emisreporter', None,),
            ('', False, '', None,)
        ],
        'sort_column':'date',
        'sort_ascending':False,
        }, name="emis-schools"),
    url(r'^edtrac/(\d+)/district-detail-boysp3/', boysp3_district_attd_detail, {}, name="boysp3-district-attd-detail"),
    url(r'^edtrac/(\d+)/district-detail-boysp6/', boysp6_district_attd_detail, {}, name="boysp6-district-attd-detail"),
    url(r'^edtrac/(\d+)/district-detail-girlsp3/', girlsp3_district_attd_detail, {}, name="girlsp3-district-attd-detail"),
    url(r'^edtrac/(\d+)/district-detail-girlsp6/', girlsp6_district_attd_detail, {}, name="girlsp6-district-attd-detail"),
    url(r'^edtrac/(\d+)/district-detail-female-teachers/', female_t_district_attd_detail, {}, name="female-teacher-district-attd-detail"),
    url(r'^edtrac/(\d+)/district-detail-male-teachers/', male_t_district_attd_detail, {}, name="male-teacher-district-attd-detail"),
    url(r'^edtrac/(\d+)/school_detail/', school_detail, {}, name='school-detail'),
    url(r'^edtrac/add_schools/', login_required(add_schools), {}, name='add-schools'),
    url(r'^edtrac/school/(\d+)/edit/', edit_school, name='edit-school'),
    url(r'^edtrac/school/(?P<pk>\d+)/delete/', delete_school, name='delete-school'),
    url(r'^edtrac/school/(?P<pk>\d+)/show', generic_row, {'model':School, 'partial_row':'education/partials/school_row.html'}, name='show-school'),

    url(r'^edtrac/othermessages/$', login_required(generic), {
        'model':Message,
        'queryset':othermessages,
        'filter_forms':[FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
        'action_forms':[ReplyTextForm],
        'objects_per_page':25,
        'partial_row':'education/partials/other_message_row.html',
        'base_template':'education/messages_base.html',
        'columns':[('Text', True, 'text', SimpleSorter()),
            ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
            ('Date', True, 'date', SimpleSorter(),),
        ],
        'sort_column':'date',
        'sort_ascending':False,
        }, name="emis-othermessages"),

    # Excel Reports
    url(r'^edtrac/excelreports/$',excel_reports),
    #users and permissions
    url(r'^edtrac/toexcel/$',to_excel, name="to-excel"),
    url(r'^edtrac/schoolexcel/$', school_reporters_to_excel, name="school_report_excel"),
    url(r'^edtrac/toexcel/(?P<start_date>[0-9\-]+)/(?P<end_date>[0-9\-]+)$',to_excel, name="to-excel"),
    url(r'^edtrac/users/(\d+)/edit/', edit_user, name='edit_user'),
    url(r'^edtac/users/add/', edit_user, name='add_user'),

    url(r'^edtrac/user/$', super_user_required(generic), {
        'model':User,
        'objects_per_page':25,
        'partial_row':'education/partials/user_row.html',
        'partial_header':'education/partials/user_partial_header.html',
        'base_template':'education/users_base.html',
        'results_title':'Managed Users',
        'user_form':UserForm(),
        'columns':[('Username', True, 'username', SimpleSorter()),
            ('Email', True, 'email', None,),
            ('Name', False, 'first_name', None,),
            ('Role', False, 'profile__role', None,),
            ('Location', False, 'profile__location', None,),
            ('Action', False, '', None,),
        ],
        'sort_column':'date',
        'sort_ascending':False,
        }, name="emis-users"),

    url(r'^edtrac/alerts_detail/(?P<alert>\d+)/$', login_required(alerts_detail), {}, name="emis-alerts"),

    #Admin Dashboard
    #TODO protect views here...

    url(r'^edtrac/dash_map/$', dash_map, {}, name="emis-dash-map"),
    url(r'^edtrac/dash_attdance/$', dash_attdance, {}, name="emis-dash-attdance"),

    # attendance views for all roles ---> data prepopulated by location
    url(r'^edtrac/dash/boys-p3/attendance/$', boys_p3_attendance, {}, name="boys-p3"),
    url(r'^edtrac/dash/boys-p6/attendance/$', boys_p6_attendance, {}, name="boys-p6"),
    url(r'^edtrac/dash/girls-p3/attendance/$', girls_p3_attendance, {}, name="girls-p3"),
    url(r'^edtrac/dash/girls-p6/attendance/$', girls_p6_attendance, {}, name="girls-p6"),
    url(r'^edtrac/dash/teacher-female/attendance/$', female_teacher_attendance, {}, name="f-teachers"),
    url(r'^edtrac/dash/teacher-male/attendance/$', male_teacher_attendance, {}, name="m-teachers"),
    url(r'^edtrac/dash/head-teacher-male/attendance/$', male_head_teacher_attendance, {}, name="m-h-teachers"),
    url(r'^edtrac/dash/head-teacher-female/attendance/$', female_head_teacher_attendance, {}, name="f-h-teachers"),
    # end attendance views

    url(r'^edtrac/dash-admin-meetings/$', dash_admin_meetings, {}, name="emis-dash-admin-meetings"),
    url(r'^edtrac/dash-district-meetings/(?P<district_name>\w+)/$', dash_district_meetings, {}, name="emis-district-meetings"),
    url(r'^edtrac/dash_ministry_map/$', dash_ministry_map, {}, name="emis-ministry-dash-map"),
    url(r'^edtrac/dash-admin-progress/$', dash_admin_progress, {}, name="emis-admin-curriculum-progress"),
    url(r'^edtrac/dash-admin-progress/district/(?P<district_pk>\d+)/$', dash_admin_progress_district, {},
        name="emis-admin-curriculum-progress-district"),

    url(r'^edtrac/violence-admin-details/$', ViolenceAdminDetails.as_view(), name="violence-admin-details"),
    url(r'^edtrac/attendance-admin-details/$', AttendanceAdminDetails.as_view(), name="attendance-admin-details"),
    url(r'^edtrac/attd_admin_details/search$', search_form, name="attendance-search"),
    # to find out about violence in a district
    url(r'^edtrac/violence/district/(?P<pk>\d+)/$', DistrictViolenceDetails.as_view(), name="district-violence"),
    url(r'^edtrac/violence-community/district/(?P<pk>\d+)/$', DistrictViolenceCommunityDetails.as_view(template_name =\
    "education/dashboard/district_violence_community_detail.html"), name="district-violence-community"),
    url(r'^edtrac/violence_deo_details/$', ViolenceDeoDetails.as_view(), name="violence-deo-details"),
    url(r'^edtrac/dash_ministry_attdance/$', dash_attdance, {}, name="emis-ministry-dash-attdance"),

    #DEO dashboard
    url(r'^edtrac/dash_deo_map/$', dash_ministry_map, {}, name="emis-deo-dash-map"),
    url(r'^edtrac/dash_deo_attdance/$', dash_attdance, {}, name="emis-deo-dash-attdance"),

    #National statistics
    url(r'^edtrac/national-stats/$', NationalStatistics.as_view(), name="emis-national-stats"),
    url(r'^edtrac/capitation-grants/$', CapitationGrants.as_view(), name = "emis-grants"),
    #PROGRESS views
    url('^edtrac/progress/district/(?P<pk>\d+)/$', DistrictProgressDetails.as_view(template_name=\
    "education/dashboard/district_progress_detail.html"), name="district-progress"),
    url(r'^edtrac/dash-admin-progress-details/$', ProgressAdminDetails.as_view(), name="admin-progress-details"),
    url(r'^edtrac/dash-admin-meals-details/$', MealsAdminDetails.as_view(), name="admin-meals-details"),
    # to find out about the meals in a district
    url(r'^edtrac/meals/district/(?P<name>\w+)/$', DistrictMealsDetails.as_view(), name="district-meal"),
    url(r'^edtrac/reporters/$', EdtracReporter.as_view()), #/page(?P<page>[0-9]+)/$', ListView.as_view(
#    url(r'^edtrac/reporters/create/$', EdtracReporterCreateView.as_view()),
#    url(r'^edtrac/reporters/connection/create/$', EdtracReporterCreateConnection.as_view(), name="new-connection"),

    #    url(r'^emis/attendance/$', include(AttendanceReport().as_urlpatterns(name='emis-attendance'))),
    url(r'^edtrac/scripts/', edit_scripts, name='emis-scripts'),
    url(r'^edtrac/reshedule_scripts/(?P<script_slug>[a-z_]+)/$', reschedule_scripts, name='emis-reschedule-scripts'),
    url(r'^edtrac/attdmap/$', attendance_visualization, name="attendance-visualization"),
)

