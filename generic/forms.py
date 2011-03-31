from django import forms

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

    def createModule(self, dashboard):
        module = Module.objects.create(dashboard=dashboard)
        module.column = 0
        if dashboard.modules.filter(column=0).count():
            module.offset = dashboard.modules.filter(column=0).order_by('-offset')[0].offset + 1
        else:
            module.offset = 0
        module.save()
        return module

    def setModuleParams(self, dashboard, module=None):
        raise NotImplementedError("Subclasses of ModuleForm must implement the setModuleParams() method!")