from django import forms
from generic.models import Module

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

    def createModule(self, dashboard, view_name):
        offset = 0
        if dashboard.modules.filter(column=0).count():
            offset = dashboard.modules.filter(column=0).order_by('-offset')[0].offset + 1
        return Module.objects.create(dashboard=dashboard, view_name=view_name, column=0, offset=offset)

    def setModuleParams(self, dashboard, module=None):
        raise NotImplementedError("Subclasses of ModuleForm must implement the setModuleParams() method!")