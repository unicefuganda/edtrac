from django import forms

class FilterForm(forms.Form):
    """ abstract filter class for filtering contacts"""

    def filter(self, request, queryset):
        raise NotImplementedError("Subclasses of FilterForm must implement the filter() method!")

class ActionForm(forms.Form):
    """ abstract class for all the filter forms"""
    
    def perform(self, request, results):
        raise NotImplementedError("Subclasses of ActionForm must implement the perform() method!")