from django.conf.urls.defaults import *
from .views import add_contact, new_contact
from .forms import FreeSearchForm, FilterGroupsForm, MassTextForm
from rapidsms.models import Contact
from generic.views import generic
from .utils import get_messages
from django.contrib.auth.decorators import login_required
from rapidsms_httprouter.models import Message
from generic.sorters import SimpleSorter
from .forms import FreeSearchTextForm, DistictFilterMessageForm, HandledByForm, ReplyTextForm

urlpatterns = patterns('',
   url(r'^contact/index/$', generic, {'model':Contact, 'filter_forms':[FreeSearchForm, FilterGroupsForm], 'action_forms':[MassTextForm],'objects_per_page':25}),
   url(r'^contact/add', add_contact),
   url(r'^contact/new', new_contact),
   url(r'^contact/messagelog/$', login_required(generic), {
      'model':Message,
      'queryset':get_messages,
      'filter_forms':[FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
      'action_forms':[ReplyTextForm],
      'objects_per_page':25,
      'partial_row':'contact/partials/message_row.html',
      'base_template':'contact/messages_base.html',
      'columns':[('Text', True, 'text', SimpleSorter()),
                 ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
                 ('Date', True, 'date', SimpleSorter(),),
                 ('Type', True, 'handled_by', SimpleSorter(),),
                 ('Response', False, 'response', None,),
                 ],
    }, name="contact-messagelog"),
)