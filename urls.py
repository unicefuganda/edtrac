from django.conf.urls.defaults import *
from contact.views import contacts_management
from contact.views.forms import freeSearchForm,filterGroups

urlpatterns = patterns('',

url(r'^contact/index', contacts_management.index,{'form_types':[filterGroups],'template':'contact/index.html'},name='contact',),
url(r'^contact/contact_list', contacts_management.contacts_list,{'form_types':[filterGroups]}),
url(r'^contact/add', contacts_management.add_contact),
url(r'^contact/new', contacts_management.new_contact),
)