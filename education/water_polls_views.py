import datetime
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.forms import extras
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from education.water_polls_view_helper import get_location_for_water_view, get_all_responses
from poll.models import Poll
from education.models import EmisReporter, ScriptScheduleTime
from rapidsms.contrib.locations.models import Location
from script.models import ScriptProgress, Script
from unregister.models import Blacklist


@login_required
def schedule_water_polls(request):
    schedule_form = ScheduleWaterPollForm()
    context_dict = {}
    if request.method == 'POST':
        if request.POST['form_name'] == "water_poll_form":
            schedule_form = ScheduleWaterPollForm(data=request.POST)
            if schedule_form.is_valid():
                schedule_date = schedule_form.cleaned_data['on_date']
                head_teachers_group = Group.objects.get(name='Head Teachers')
                water_script = Script.objects.get(slug='edtrac_script_water_source')
                scheduled_for = schedule_script(schedule_date, get_valid_reporters(head_teachers_group), water_script)
                ScriptScheduleTime.objects.create(script=water_script, scheduled_on=schedule_date)
                context_dict['message'] = "Scheduled %s script for %s reporters" % (water_script.name, scheduled_for)

        elif request.POST['form_name'] == "functional_water_poll_form":
            today = datetime.date.today()
            water_script = Script.objects.get(slug='edtrac_script_water_source')
            functional_water_script = Script.objects.get(slug='edtrac_script_functional_water_source')

            poll = Poll.objects.get(name="edtrac_water_source")
            dt = _get_last_scheduled_date(water_script)
            reporters = EmisReporter.objects.filter(
                contact_ptr__in=poll.responses.filter(categories__category__name='yes', date__gte=dt).values_list(
                    'contact', flat=True).distinct())
            scheduled_for = schedule_script(today, reporters, functional_water_script)
            ScriptScheduleTime.objects.create(script=functional_water_script, scheduled_on=today)
            context_dict['message'] = "Scheduled %s script for %s reporters" % (
            functional_water_script.name, scheduled_for)
    context_dict['form'] = schedule_form
    return render_to_response('education/admin/schedule_water_polls.html', context_dict,
                              RequestContext(request))


def _get_last_scheduled_date(water_script):
    scheduled_dates = ScriptScheduleTime.objects.filter(script=water_script).order_by('-scheduled_on').values_list(
        'scheduled_on', flat=True)
    return scheduled_dates[0] if len(scheduled_dates) > 0 else datetime.date.today()


class ScheduleWaterPollForm(forms.Form):
    on_date = forms.DateField(label="Schedule Date: ", widget=extras.widgets.SelectDateWidget())

    def clean_on_date(self):
        on_date = self.cleaned_data['on_date']
        if on_date < datetime.date.today():
            raise forms.ValidationError('Can not Schedule on this Date')
        return on_date


def schedule_script(date, reporters, script):
    ScriptProgress.objects.filter(script=script).delete()
    count = 0
    for reporter in reporters:
        if reporter.default_connection is not None:
            sp = ScriptProgress.objects.create(connection=reporter.default_connection, script=script)
            sp.set_time(date)
            count += 1
    return count


def get_valid_reporters(group):
    return EmisReporter.objects.filter(groups=group, reporting_location__type__name='district').exclude(
        connection__in=Blacklist.objects.values_list('connection', flat=True), schools=None)


def get_categories_and_data(responses):
    responses.reverse()
    categories = [response[0] for response in responses]
    return categories ,[response[1].get('yes',0) for response in responses]


def get_label_for_poll(poll):
    d = {
        'edtrac_water_source':'water source',
        'edtrac_functional_water_source':'functional water source',
        'water_and_soap': 'water and soap'
    }
    return d.get(poll.name)


def _get_poll_data_dict(location, poll, time_range):
    poll_data_dict = {}
    response, monthly_response, percent = get_all_responses(poll, location, time_range)
    categories, data = get_categories_and_data(monthly_response)
    poll_data_dict['response'] = response
    poll_data_dict['categories'] = categories
    poll_data_dict['data'] = data
    poll_data_dict['label'] = get_label_for_poll(poll)
    poll_data_dict['school_percent'] = percent
    return poll_data_dict

@login_required()
def detail_water_view(request,district=None):
    location,user_location = get_location_for_water_view(district,request)
    water_poll = Poll.objects.get(name='edtrac_water_source')
    functional_water_poll = Poll.objects.get(name='edtrac_functional_water_source')
    water_and_soap_poll = Poll.objects.get(name='water_and_soap')
    polls=[water_poll,functional_water_poll,water_and_soap_poll]
    time_range = [getattr(settings,'SCHOOL_TERM_START'),getattr(settings,'SCHOOL_TERM_END')]
    water_source_form = WaterForm()
    district_water_report_form = DistrictWaterForm()
    if request.method == 'POST':
        water_source_form=WaterForm(data=request.POST)
        if water_source_form.is_valid():
            to_date = water_source_form.cleaned_data['to_date']
            from_date = water_source_form.cleaned_data['from_date']
            time_range = [from_date,to_date]
    data_list = [_get_poll_data_dict(location, poll, time_range) for poll in polls]
    time_period = "Data shown for time: %s to %s" %(time_range[0].strftime("%d %B %Y"),time_range[1].strftime("%d %B %Y"))
    return render_to_response('education/admin/detail_water.html',
                              {'data_list':data_list,'form':water_source_form,
                               'location':user_location,'time_period':time_period, 'district_form':district_water_report_form},
                              RequestContext(request))

@login_required()
def district_water_view(request):
    if request.method == 'POST':
        district_water_report_form = DistrictWaterForm(data=request.POST)
        if district_water_report_form.is_valid():
            district_id = district_water_report_form.cleaned_data['district_choices']
            return HttpResponseRedirect(reverse('detail-water-view', kwargs={'district':district_id}))
        return HttpResponseRedirect(reverse('detail-water-view'))

class WaterForm(forms.Form):
    from_date = forms.DateTimeField()
    to_date = forms.DateTimeField()

    def clean(self):
        data = self.cleaned_data
        if data.get('from_date') > data.get('to_date'):
            raise forms.ValidationError("To date less than from date")
        return data

class DistrictWaterForm(forms.Form):
    district_list = list(Location.objects.filter(type='district'))
    district_choices = forms.ChoiceField(choices=[(district.id, district.name) for district in district_list])