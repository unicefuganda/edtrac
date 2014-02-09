from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from . import views


urlpatterns = patterns('',

    url(r'^$',
        login_required(views.registration),
        name="registration"),

    url(r'^(?P<pk>\d+)/edit/$',
        login_required(views.registration),
        name="registration_edit")
)