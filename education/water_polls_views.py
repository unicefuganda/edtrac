import datetime

from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth.models import Group
from django.forms import extras
from django.shortcuts import render_to_response
from education.models import EmisReporter

from script.models import ScriptProgress, Script
from unregister.models import Blacklist


@login_required
def schedule_water_polls(request):
    if request.method == 'POST':
        schedule_form = ScheduleWaterPollForm(data = request.POST)
        if schedule_form.is_valid():
            schedule_date = schedule_form.cleaned_data['on_date']
            head_teachers_group = Group.objects.get(name='Head Teachers')
            water_script = Script.objects.get(slug='edtrac_script_water_source')
            schedule_script(schedule_date,get_valid_reporters(head_teachers_group),water_script)
    return render_to_response('education/admin/schedule_water_polls.html', {'form':ScheduleWaterPollForm()})

class ScheduleWaterPollForm(forms.Form):
    on_date = forms.DateField(label="Schedule Date: ", widget=extras.widgets.SelectDateWidget())

    def clean_on_date(self):
        on_date = self.cleaned_data['on_date']
        if on_date < datetime.date.today():
            raise forms.ValidationError('Can not Schedule on this Date')
        return on_date


def schedule_script(date,reporters,script):
    for reporter in reporters:
        sp = ScriptProgress.objects.create(connection=reporter.default_connection,script=script)
        sp.set_time(date)


def get_valid_reporters(group):
    return EmisReporter.objects.filter(groups=group, reporting_location__type__name='district').exclude(
        connection__in=Blacklist.objects.values_list('connection', flat=True), schools=None)