from django import forms
from rapidsms.models import Contact
from django.forms.widgets import Widget
from django.template.loader import get_template
from django.template.context import Context
from django.core.paginator import Paginator,Page

class contactsWidget(Widget):
    def __init__(self,language=None,attrs=None,**kwargs):
        super(contactsWidget,self).__init__(attrs)
    def id_for_label(self,id):
        return id
    def render(self,name,value,attrs=None):
        if value is None:
            value = []
        contacts=Contact.objects.all()
        data = {}
        template = get_template('contact/users.html')
        return template.render(Context(data))





class contactsForm(forms.Form):
    users=forms.ModelMultipleChoiceField(queryset=Contact._default_manager.all(),widget=contactsWidget)

class NewContactForm(forms.ModelForm):
    class Meta:
        model=Contact
class filterForm(forms.Form):
    pass