from django.conf.urls.defaults import *
from contact.views import contacts_management

urlpatterns = patterns('',

url(r'^contact/index', contacts_management.index,name='contact'),
)