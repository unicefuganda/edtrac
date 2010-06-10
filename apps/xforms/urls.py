from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = patterns('',
    url(r"^xforms/$", login_required(views.xforms), name="xforms"),
    url(r"^xforms/new/$", login_required(views.new_xform)),
    url(r"^xforms/(\d+)/edit/$", login_required(views.edit_xform)),
    url(r"^xforms/(\d+)/delete/$", login_required(views.delete_xform)),
    url(r"^xforms/(\d+)/add_field/$", login_required(views.add_field)),
    url(r"^xforms/(\d+)/edit_field/(\d+)/$", login_required(views.edit_field)),
    url(r"^xforms/(\d+)/delete_field/(\d+)/$", login_required(views.delete_field)),
	url(r"^static/xforms/(?P<path>.*)$", 'django.views.static.serve', {'document_root' : 'apps/xforms/static'}),
)
