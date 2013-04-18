import datetime

from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth.models import Group
from django.forms import extras
from django.shortcuts import render_to_response
from django.template import RequestContext
from education.models import EmisReporter
from education.water_polls_view_helper import get_location_for_water_view, get_responses, get_monthly_responses
from poll.models import Poll
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


def get_categories_and_data(responses):
    responses.reverse()
    categories = [response[0] for response in responses]
    return categories ,[response[1].get('yes',0) for response in responses]

def detail_water_view(request,district=None):
    location = get_location_for_water_view(district,request)
    poll = Poll.objects.get(name='edtrac_water_source')
    responses = get_responses(poll,location)
    monthly_responses = get_monthly_responses(poll,location)
    categories, data = get_categories_and_data(monthly_responses)
    return render_to_response('education/admin/detail_water.html',
                              {'resposnes': responses, 'monthly_categories': categories, 'monthly_data': data},
                              RequestContext(request))
