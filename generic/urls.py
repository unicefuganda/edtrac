from django.conf.urls.defaults import *
from generic.views import *

urlpatterns = patterns('',
   url(r'^generic/dummy/$', dummy,name='dummy'),
   url(r'^generic/dummy2/$', dummy2,name='dummy2'),
   url(r'^generic/dummy3/$', dummy3,name='dummy3'),
)