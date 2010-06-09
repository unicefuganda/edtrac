from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = patterns('',
    url(r"^xforms/$", login_required(views.xforms), name="xforms"),
    url(r"^xforms/new/$", login_required(views.new_xform)),
    url(r"^xforms/(\d+)/add_field/$", login_required(views.add_field)),
    url(r"^xforms/(\d+)/edit/$", login_required(views.edit_xform)),
)
