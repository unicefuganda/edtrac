from django.conf.urls.defaults import *
from contact.views import contacts_management
from contact.views.forms import freeSearchForm,filterGroups,MassTextForm
from contact import settings


urlpatterns = patterns('',
url(r'^contact/index', contacts_management.index,{'form_types':[filterGroups,freeSearchForm],'action_types':[MassTextForm],'template':'contact/index.html'},name='contact',),
url(r'^contact/contact_list', contacts_management.contacts_list,{'template':settings.CONTACTS_TEMPLATE,'form_types':[filterGroups,freeSearchForm]}),
url(r'^contact/add', contacts_management.add_contact),
url(r'^contact/new', contacts_management.new_contact),
url(r'^contact/actions', contacts_management.form_actions),
)