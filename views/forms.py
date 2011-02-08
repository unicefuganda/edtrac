from django import forms
from rapidsms.models import Contact
from django.forms.widgets import Widget
from django.template.loader import get_template
from django.template.context import Context
from django.core.paginator import Paginator, Page
import abc

class contactsWidget(Widget):
    def __init__(self, language=None, attrs=None, **kwargs):
        super(contactsWidget, self).__init__(attrs)

    def id_for_label(self, id):
        return id

    def render(self, name, value, attrs=None):
        if value is None:
            value = []
        contacts = Contact.objects.all()
        data = {}
        template = get_template('contact/contacts.html')
        return template.render(Context(data))


class contactsFilterForm(forms.Form):
    """ abstract filter class for filtering contacts"""
     __metaclass__ = abc.ABCMeta
    def perform(self,queryset):
        pass



class contactsActionForm(forms.Form):
    """ abstract class for all the filter forms"""
     __metaclass__ = abc.ABCMeta
    @abc.abstractmethod
    def filter(queryset):
        pass

class filterGroups(contactsFilterForm):
    """ concrete implementation of filter form """
    group=forms.ModelMultipleChoiceField(queryset=Team.objects.all().order_by('name'), required=False)
    def filter(self):
        queryset=Contact.objects.all()
        return queryset.filter(group__in=self.cleaned_data['group'])

class NewContactForm(forms.ModelForm):
    class Meta:
        model = Contact

class freeSearchForm(contactsFilterForm):
    """ concrete implementation of class """
    term = forms.CharField(max_length=100)
    def filter(self,queryset):
        term=self.cleaned_data['term']
        qs=queryset.filter(Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(reporting_location__icontains=term))
