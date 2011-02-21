from django.conf.urls.defaults import *
from . import views
from contact.forms import FreeSearchForm, FilterGroupsForm, MassTextForm
from contact import settings

urlpatterns = patterns('',
   url(r'^contact/index', views.contacts,{'form_types':[FilterGroupsForm,FreeSearchForm],'action_types':[MassTextForm],'template':'contact/index.html'},name='contact',),
   url(r'^contact/contact_list', views.contacts_list,{'template':settings.CONTACTS_TEMPLATE,'form_types':[FilterGroupsForm,FreeSearchForm]}),
   url(r'^contact/add', views.add_contact),
   url(r'^contact/new', views.new_contact),
   url(r'^contact/actions', views.form_actions),
)