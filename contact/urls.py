from django.conf.urls.defaults import *
from .views import add_contact, new_contact
from .forms import FreeSearchForm, FilterGroupsForm, MassTextForm
from contact import settings
from rapidsms.models import Contact
from generic.views import generic

urlpatterns = patterns('',
   url(r'^contact/index/$', generic, {'model':Contact, 'filter_forms':[FreeSearchForm, FilterGroupsForm], 'action_forms':[MassTextForm],'objects_per_page':25}),
   url(r'^contact/add', add_contact),
   url(r'^contact/new', new_contact),
)