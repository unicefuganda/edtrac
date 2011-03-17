from django.conf.urls.defaults import *
from .views import add_contact, new_contact
from .forms import FreeSearchForm, FilterGroupsForm, MassTextForm
from rapidsms.models import Contact
from generic.views import generic
from .utils import get_messages, get_mass_messages
from django.contrib.auth.decorators import login_required
from rapidsms_httprouter.models import Message
from generic.sorters import SimpleSorter, TupleSorter
from .forms import FreeSearchTextForm, DistictFilterMessageForm, HandledByForm, ReplyTextForm
from ureport.models import MassText

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
                 ('Type', True, 'application', SimpleSorter(),),
                 ('Response', False, 'response', None,),
                 ],
      'sort_column':'date',
      'sort_ascending':False,
    }, name="contact-messagelog"),
   url(r'^contact/massmessages/$', login_required(generic), {
      'model':MassText,
      'queryset':get_mass_messages,
      'objects_per_page':10,
      'partial_row':'contact/partials/mass_message_row.html',
      'base_template':'contact/mass_messages_base.html',
      'columns':[('Message', True, 'text', TupleSorter(0)),
                 ('Time', True, 'date', TupleSorter(1),),
                 ('User', True, 'user', TupleSorter(2),),
                 ('Recipients', True, 'response', TupleSorter(3),),
                 ('Type', True, 'type', TupleSorter(4),),
                 ],
      'sort_column':'date',
      'sort_ascending':False,
      'selectable':False,
    }),
)