from django.conf.urls.defaults import *
from contact.views import contacts_management
from contact.views.forms import freeSearchForm,filterGroups,MassTextForm

urlpatterns = patterns('',

url(r'^contact/index', contacts_management.index,{'form_types':[filterGroups],'action_types':[MassTextForm],'template':'contact/index.html', 'partial':'contact_list'},name='contact',),
url(r'^contact/contact_list', contacts_management.contacts_list,{'form_types':[filterGroups]}),
url(r'^contact/add', contacts_management.add_contact),
url(r'^contact/new', contacts_management.new_contact),
url(r'^contact/actions', contacts_management.form_actions),
)