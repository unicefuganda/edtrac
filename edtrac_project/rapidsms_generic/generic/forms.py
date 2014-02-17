from django import forms
from django.forms import ValidationError
from generic.models import Module, StaticModuleContent
import datetime

class FilterForm(forms.Form):
    """ abstract filter class for filtering contacts"""
    def __init__(self, data=None, **kwargs):
        self.request = kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)

    def filter(self, request, queryset):
        raise NotImplementedError("Subclasses of FilterForm must implement the filter() method!")


class ActionForm(forms.Form):
    """Action forms consume a list of selected object from the generic list 
    view (generic.views.generic), performing an action on them.  ActionForm
    subclasses are usually tied to a particular view or at least a particular model,
    as the peform() method could in theory be passed any iterable in the 'results'
    parameter.
    """
    def __init__(self, data=None, **kwargs):
        self.request = kwargs.pop('request')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)

    def perform(self, request, results):
        raise NotImplementedError("Subclasses of ActionForm must implement the perform() method!")


class ModuleForm(forms.Form):
    """ abstract class for module creation forms"""

    def createModule(self, dashboard, view_name, title):
        offset = 0
        if dashboard.modules.filter(column=0).count():
            offset = dashboard.modules.filter(column=0).order_by('-offset')[0].offset + 1
        return Module.objects.create(dashboard=dashboard, view_name=view_name, column=0, offset=offset, title=title)

    def setModuleParams(self, dashboard, module=None, title=None):
        raise NotImplementedError("Subclasses of ModuleForm must implement the setModuleParams() method!")


class DateRangeForm(forms.Form):
    start = forms.IntegerField(required=True, widget=forms.HiddenInput())
    end = forms.IntegerField(required=True, widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = self.cleaned_data
        try:
            start = cleaned_data.get('start')
            cleaned_data['start'] = datetime.datetime.fromtimestamp(float(start))

            end = cleaned_data.get('end')
            cleaned_data['end'] = datetime.datetime.fromtimestamp(float(end))
        except TypeError:
            raise ValidationError('Need both start and end values that are strings or numbers')
        return cleaned_data


class TimeRangeForm(forms.Form):
    range = forms.ChoiceField(choices=(('w', 'Previous Calendar Week'), ('m', 'Previous Calendar Month'), ('q', 'Previous calendar quarter'),))


class StaticModuleForm(ModuleForm):
    old_content = forms.ModelChoiceField(queryset=StaticModuleContent.objects.all(), required=False, empty_label='Create New')
    content = forms.CharField(max_length=5000, required=False)
    title = forms.CharField(max_length=30, required=False)
    def setModuleParams(self, dashboard, module=None, title=None):
        if self.cleaned_data['old_content']:
            content = self.cleaned_data['old_content']
        else:
            content = StaticModuleContent.objects.create(content=self.cleaned_data['content'])
        module = module or self.createModule(dashboard, 'generic.views.static_module', title=self.cleaned_data['title'])
        module.params.create(module=module, param_name='content_id', param_value=content.pk, is_url_param=True)
        return module

