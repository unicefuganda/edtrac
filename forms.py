from django import forms
from rapidsms.models import Contact,Connection
from django.forms.widgets import Widget
from django.template.loader import get_template
from django.template.context import Context
from django.core.paginator import Paginator, Page
from status160.models import  Team
from django.db.models import Q
from django.forms.widgets import HiddenInput
from rapidsms_httprouter.router import get_router
from rapidsms.messages.outgoing import OutgoingMessage
from contact import settings

class ContactsWidget(Widget):
    def __init__(self, contacts_template,language=None, attrs=None, **kwargs):
        self.contacts_template=contacts_template
        super(ContactsWidget, self).__init__(attrs)

    def id_for_label(self, id):
        return id

    def render(self, name, value, attrs=None):
        if value is None:
            value = []
        contacts_list = Contact.objects.all()
        data = {}
        paginator = Paginator(contacts_list, 20, allow_empty_first_page=True)
        contacts = paginator.page(1)
        data.update(contacts=contacts)
        template = get_template(self.contacts_template)
        return template.render(Context(data))

    def value_from_datadict(self,data,files,name):
        try:
            d=[int(val) for val in dict(data)[name]]
        except KeyError:
            d=[]
        return d

class ContactsForm(forms.Form):

    def __init__(self,template, *args, **kwargs):
        self.template=template
        super(ContactsForm, self).__init__(*args, **kwargs)
    contacts=forms.CharField(required=False,widget=ContactsWidget(settings.CONTACTS_TEMPLATE))

class ContactsFilterForm(forms.Form):
    """ abstract filter class for filtering contacts"""
    @property
    def filter(self):
        raise NotImplementedError("Subclasses of ContactsFilterForm must implement the filter() method!")

class ContactsActionForm(forms.Form):
    """ abstract class for all the filter forms"""
    @property    
    def perform(self,queryset):
        raise NotImplementedError("Subclasses of ContactsActionForm must implement the perform() method!")

class FilterGroupsForm(ContactsFilterForm):
    """ concrete implementation of filter form """
    group=forms.ModelMultipleChoiceField(queryset=Team.objects.all().order_by('name'), required=False)
    def filter(self):
        queryset=Contact.objects.all()
        return queryset.filter(groups__in=self.cleaned_data['group'])

class NewContactForm(forms.ModelForm):

    class Meta:
        model = Contact

class FreeSearchForm(ContactsFilterForm):
    """ concrete implementation of filter form """

    term = forms.CharField(max_length=100)

    def filter(self):
        queryset=Contact.objects.all()
        term=self.cleaned_data['term']
        qs=queryset.filter(Q(name__icontains=term)
            | Q(reporting_location__name__icontains=term))
        return qs

class MassTextForm(ContactsActionForm):

    text = forms.CharField(max_length=160, required=True)
    form_type=forms.CharField(widget=HiddenInput(attrs ={'value':'MassTextForm'}))

    def perform(self,queryset):
        connections = Connection.objects.filter(contact__in=queryset).distinct()
        router = get_router()
        text=self.cleaned_data['text']
        for conn in connections:
            outgoing = OutgoingMessage(conn, text)
            router.handle_outgoing(outgoing)

class CreateGroup(ContactsActionForm):

    name = forms.CharField(max_length=160, required=True)

    def perform(self):
        group_name=self.cleaned_data['text']
        for conn in connections:
            outgoing = OutgoingMessage(conn, text)
            router.handle_outgoing(outgoing)
