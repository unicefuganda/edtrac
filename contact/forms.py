from django import forms
from rapidsms.models import Contact,Connection
from django.forms.widgets import Widget
from django.template.loader import get_template
from django.template.context import Context
from django.core.paginator import Paginator, Page
from status160.models import  Team
from django.db.models import Q
from django.forms.widgets import HiddenInput
from rapidsms_httprouter.router import get_router, start_sending_mass_messages, stop_sending_mass_messages
from rapidsms.messages.outgoing import OutgoingMessage
from generic.forms import ActionForm, FilterForm
from ureport.models import MassText
from django.contrib.sites.models import Site

class FilterGroupsForm(FilterForm):
    """ concrete implementation of filter form """
    group=forms.ModelMultipleChoiceField(queryset=Team.objects.all().order_by('name'), required=True)

    def filter(self,request, queryset):
        return queryset.filter(groups__in=self.cleaned_data['group'])

class NewContactForm(forms.ModelForm):

    class Meta:
        model = Contact

class FreeSearchForm(FilterForm):
    """ concrete implementation of filter form """

    term = forms.CharField(max_length=100, required=True)

    def filter(self, request, queryset):
        term=self.cleaned_data['term']
        return queryset.filter(Q(name__icontains=term)
            | Q(reporting_location__name__icontains=term))

class MassTextForm(ActionForm):

    text = forms.CharField(max_length=160, required=True)
    action_label = 'Send Message'

    def perform(self, request, results):
        connections = Connection.objects.filter(contact__in=results).distinct()
        router = get_router()
        text = self.cleaned_data['text']
        mass_text = MassText.objects.create(user=request.user, text=text)
        mass_text.sites.add(Site.objects.get_current())
        start_sending_mass_messages()
        for conn in connections:
            mass_text.contacts.add(conn.contact)
            outgoing = OutgoingMessage(conn, text)
            router.handle_outgoing(outgoing)
        stop_sending_mass_messages()
        return "Message successfully sent to %d numbers" % connections.count()
