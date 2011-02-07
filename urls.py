from django.conf.urls.defaults import *
from contact.views import contacts_management

urlpatterns = patterns('',

url(r'^contact/index', contacts_management.index,name='contact'),
url(r'^contact/contact_list', contacts_management.contacts_list),
url(r'^contact/add', contacts_management.add_contact),
url(r'^contact/new', contacts_management.new_contact),
)