# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

#targets
from django.conf import settings
from education.models import EmisReporter, School
from education.utils import get_week_count, themes, Statistics
from poll.models import Poll
from rapidsms.contrib.locations.models import Location
from unregister.models import Blacklist

target = {
    1:1.1,
    2:1.2,
    3:1.3,
    4:2.1,
    5:2.2,
    6:2.3,
    7:3.1,
    8:3.2,
    9:3.3,
    10:4.1,
    11:4.2,
    12:4.3
}


def add_offset_according_to_term_number(target_value):
    term_start= getattr(settings,'SCHOOL_TERM_START')
    first_term_start= getattr(settings,'FIRST_TERM_BEGINS')
    second_term_start= getattr(settings,'SECOND_TERM_BEGINS')
    third_term_start= getattr(settings,'THIRD_TERM_BEGINS')

    if term_start == first_term_start:
        return target_value , 'first'
    if term_start == second_term_start:
        return target_value+4 , 'second'
    if term_start ==third_term_start:
        return target_value+8 , 'third'

def get_target_value(given_date):
    term_start = getattr(settings,'SCHOOL_TERM_START')
    week_count = get_week_count(term_start,given_date)
    target_value = target[week_count]
    target_value ,term = add_offset_according_to_term_number(target_value)
    return target_value ,term

def get_location_for_curriculum_view(district_pk, request):
    sub_location_type = 'School'
    if district_pk is None:
        profile = request.user.get_profile()
        locations,user_location = [profile.location], profile.location.name
        if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
                'UNICEF Officials'):
            locations = Location.objects.filter(type="district", pk__in=EmisReporter.objects.exclude(
                connection__in=Blacklist.objects.values_list('connection', flat=True), schools=None).values_list(
                'reporting_location__pk', flat=True))
            user_location = 'Uganda'
            sub_location_type = 'District'
    else:
        location = Location.objects.get(pk=district_pk)
        locations, user_location = [location], location.name
    return locations, user_location, sub_location_type


def get_curriculum_data_by_location(location, date_range, filter_on):
    poll = Poll.objects.get(name='edtrac_p3curriculum_progress')
    kwargs = {filter_on: location}
    responses = poll.responses.filter(date__range=date_range,**kwargs).values_list('eav_values__value_float', flat=True)
    if responses.count() == 0:
        return "No Reports made this week", []
    valid_responses = responses.filter(eav_values__value_float__in = themes.keys())
    if valid_responses.count() == 0:
        return "Progress undetermined this week", []
    if valid_responses.count() == 1:
        return valid_responses[0], valid_responses
    mode = Statistics(list(valid_responses)).mode
    if len(mode) == 0:
        return "Progress undetermined this week", valid_responses
    return mode, valid_responses

def get_curriculum_data(locations, time_range):
    valid_responses = []
    curriculum_data_by_location = {}
    if len(locations) == 1:
        sub_locations = School.objects.filter(pk__in = EmisReporter.objects.filter(reporting_location=locations[0]).values_list('schools__pk', flat=True))
        filter_on = 'contact__emisreporter__schools'
    else:
        sub_locations = locations
        filter_on = 'contact__reporting_location'

    for sub_location in sub_locations:
        mode,responses = get_curriculum_data_by_location(sub_location, time_range, filter_on)
        curriculum_data_by_location[sub_location] = mode
        valid_responses.extend(responses)

    return curriculum_data_by_location, valid_responses