from django import forms
from generic.models import Module, StaticModuleContent

class FilterForm(forms.Form):
    """ abstract filter class for filtering contacts"""

    def filter(self, request, queryset):
        raise NotImplementedError("Subclasses of FilterForm must implement the filter() method!")

class ActionForm(forms.Form):
    """ abstract class for all the filter forms"""
    
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
class TimeRangeForm(forms.Form):
    range=forms.ChoiceField(choices= (('w','Previous Calendar Week'),('m','Previous Calendar Month'),('q','Previous calendar quarter'),))

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