from django import forms
from rapidsms.models import Contact
from django.forms.widgets import Widget
from django.template.loader import get_template
from django.template.context import Context
from django.core.paginator import Paginator, Page
from status160.models import  Team
from django.db.models import Q

class contactsWidget(Widget):
    def __init__(self, language=None, attrs=None, **kwargs):
        super(contactsWidget, self).__init__(attrs)

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
        template = get_template('contact/partials/contacts_list.html')
        return template.render(Context(data))
    def value_from_datadict(self,data,files,name):
        try:
            d=[int(val) for val in dict(data)[name]]
        except KeyError:
            d=[]
        return Contact.objects.filter(pk__in=d)

class contactsForm(forms.Form):
    contacts=forms.CharField(required=False,widget=contactsWidget)
class contactsFilterForm(forms.Form):
    """ abstract filter class for filtering contacts"""
    @property
    def filter(self):
        raise NotImplementedError("subclasses pleaseimplent this")

class contactsActionForm(forms.Form):
    """ abstract class for all the filter forms"""
    def __init__(self,queryset=None,*args,**kwargs):
        self.queryset=queryset
        super(contactsActionForm,self).__init__(*args,**kwargs)
    @property    
    def perform(self):
        raise NotImplementedError("subclasses pleaseimplent this")


class filterGroups(contactsFilterForm):
    """ concrete implementation of filter form """
    group=forms.ModelMultipleChoiceField(queryset=Team.objects.all().order_by('name'), required=False)
    def filter(self):
        queryset=Contact.objects.all()
        return queryset.filter(groups__in=self.cleaned_data['group'])

class NewContactForm(forms.ModelForm):
    class Meta:
        model = Contact

class freeSearchForm(contactsFilterForm):
    """ concrete implementation of filter form """
    term = forms.CharField(max_length=100)
    def filter(self):
        queryset=Contact.objects.all()
        term=self.cleaned_data['term']
        qs=queryset.filter(Q(name__icontains=term)
            | Q(charges__icontains=term)
            | Q(reporting_location__icontains=term))
        return qs
class MassTextForm(contactsActionForm):
    text = forms.CharField(max_length=160, required=True)
    def parform(self):
        connections = Connection.objects.filter(contact__in=queryset).distinct()
        router = get_router()
        text=self.cleaned_data['text']
        for conn in connections:
            outgoing = OutgoingMessage(conn, text)
            router.handle_outgoing(outgoing)
