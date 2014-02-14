import datetime
from django import forms

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
            raise forms.ValidationError('Need both start and end values that are strings or numbers')
        return cleaned_data
