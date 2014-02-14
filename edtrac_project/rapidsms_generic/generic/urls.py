from django.conf.urls.defaults import *
from generic.views import *

urlpatterns = patterns('',
    url(r'^generic/(?P<content_id>\d+)/module/$', static_module),
)