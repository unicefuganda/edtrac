from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = patterns('',
    url(r"^xforms/$", login_required(views.xforms), name="xforms"),
    url(r"^xforms/new/$", login_required(views.new_xform)),
    url(r"^xforms/(\d+)/submissions/$", login_required(views.view_submissions)),
    url(r"^xforms/submissions/(\d+)/edit/$", login_required(views.edit_submission)),
    url(r"^xforms/(\d+)/view/$", login_required(views.view_form)),
    url(r"^xforms/(\d+)/details/$", login_required(views.view_form_details)),
    url(r"^xforms/(\d+)/edit/$", login_required(views.edit_form)),
    url(r"^xforms/(\d+)/order/$", login_required(views.order_xform)),
    url(r"^xforms/(\d+)/delete/$", login_required(views.delete_xform)),
    url(r"^xforms/(\d+)/add_field/$", login_required(views.add_field)),
    url(r"^xforms/(\d+)/edit_field/(\d+)/$", login_required(views.edit_field)),
    url(r"^xforms/(\d+)/field/(\d+)/$", login_required(views.view_field)),
    url(r"^xforms/(\d+)/field/(\d+)/constraint/(\d+)/$", login_required(views.view_constraint)),
    url(r"^xforms/(\d+)/field/(\d+)/constraint/(\d+)/edit/$", login_required(views.edit_constraint)),
    url(r"^xforms/(\d+)/field/(\d+)/constraint/(\d+)/delete/$", login_required(views.delete_constraint)),
    url(r"^xforms/(\d+)/field/(\d+)/constraint/$", login_required(views.add_constraint)),
    url(r"^xforms/(\d+)/field/(\d+)/constraints/$", login_required(views.view_constraints)),
    url(r"^xforms/(\d+)/field/(\d+)/constraints/order/$", login_required(views.order_constraints)),
    url(r"^xforms/(\d+)/field/(\d+)/constraints/add/$", login_required(views.add_constraint)),
    url(r"^xforms/(\d+)/delete_field/(\d+)/$", login_required(views.delete_field)),
     
    # these are ODK URLs to be used by ODK Collect
    url(r"^formList$", views.odk_list_forms),
    url(r"^xforms/odk/get/(\d+)/$", views.odk_get_form),
    url(r"^submission", views.odk_submission),

    # CSV Export
    url(r"^xforms/(\d+)/submissions.csv$", views.submissions_as_csv)
)
