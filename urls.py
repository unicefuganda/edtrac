from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = patterns('',
    url(r"^polls/$", login_required(views.polls), name="polls"),
    url(r"^polls/(\d+)/submissions.csv$", views.responses_as_csv),    
    url(r"^polls/new/$", login_required(views.new_poll)),
    url(r"^polls/(\d+)/responses/$", login_required(views.view_responses)),
    url(r"^polls/responses/(\d+)/view/$", login_required(views.view_response)),
    url(r"^polls/(\d+)/report/$", login_required(views.view_report)),
    url(r"^polls/responses/(\d+)/edit/$", login_required(views.edit_response)),
    url(r"^polls/responses/(\d+)/delete/$", login_required(views.delete_response)),    
    url(r"^polls/(\d+)/view/$", login_required(views.view_poll)),
    url(r"^polls/(\d+)/details/$", login_required(views.view_poll_details)),
    url(r"^polls/(\d+)/edit/$", login_required(views.edit_poll)),
    url(r"^polls/(\d+)/delete/$", login_required(views.delete_poll)),
    url(r"^polls/(\d+)/start/$", login_required(views.start_poll)),
    url(r"^polls/(\d+)/end/$", login_required(views.end_poll)),
    url(r"^polls/(\d+)/add_category/$", login_required(views.add_category)),
    url(r"^polls/(\d+)/edit_category/(\d+)/$", login_required(views.edit_category)),
    url(r"^polls/(\d+)/category/(\d+)/$", login_required(views.view_category)),
    url(r"^polls/(\d+)/delete_category/(\d+)/$", login_required(views.delete_category)),
    url(r"^polls/(\d+)/category/(\d+)/rule/(\d+)/$", login_required(views.view_rule)),    
    url(r"^polls/(\d+)/category/(\d+)/rule/(\d+)/edit/$", login_required(views.edit_rule)),
    url(r"^polls/(\d+)/category/(\d+)/rules/add/$", login_required(views.add_rule)),    
    url(r"^polls/(\d+)/category/(\d+)/rule/(\d+)/delete/$", login_required(views.delete_rule)),
    url(r"^polls/(\d+)/category/(\d+)/rules/$", login_required(views.view_rules)),
    url(r"^polls/(\d+)/categories/add/$", login_required(views.add_category)),

    # CSV Export
#    url(r"^polls/(\d+)/submissions.csv$", views.submissions_as_csv)
)
