from django.conf.urls.defaults import *
from . import views
from rapidsms_httprouter.models import Message

urlpatterns = patterns('',
   url(r'^generic/index/$', views.generic, {'model':Message, 'filter_forms':[views.SearchForm], 'action_forms':[views.SearchForm],'objects_per_page':25}),
)
