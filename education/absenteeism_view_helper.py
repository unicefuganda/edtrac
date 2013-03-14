# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from django.db.models import Sum
from education.models import EnrolledDeployedQuestionsAnswered
from education.reports import get_week_date
from poll.models import Poll
from rapidsms.contrib.locations.models import Location
from collections import defaultdict

def get_aggregation_by_time(filtered_responses):
    aggregated_list = []
    for responses in filtered_responses:
        sum_value = 0
        for response in responses:
          sum_value += response.values()[0]
        aggregated_list.append(sum_value)
    return aggregated_list

def get_aggregation_by_location(filtered_responses):
    aggregated_dict = defaultdict(lambda: 0)
    for responses in filtered_responses:
        for response in responses:
            for key in response:
                aggregated_dict[key] += response[key]
    return aggregated_dict

def transform(untransformed_data):
    transformed_data = []
    for data in untransformed_data:
        d = []
        for item in data:
            d.append({item['contact__reporting_location__name']: item['eav_values__value_float__sum']})
        transformed_data.append(d)
    return transformed_data


def get_responses_by_location(user_profile, name, depth=4):
    locations = [user_profile.location]

    if user_profile.is_member_of('Ministry Officials') or user_profile.is_member_of(
            'Admins') or user_profile.is_member_of('UNICEF Officials'):
        locations = Location.objects.filter(type='district').filter(pk__in= \
            EnrolledDeployedQuestionsAnswered.objects.values_list('school__location__pk', flat=True))

    filtered_responses = get_responses_over_depth(name, list(locations), depth)
    return get_aggregation_by_location(transform(filtered_responses)), get_aggregation_by_time(
        transform(filtered_responses))


def get_district_responses(locations, poll):
    q = poll.responses.filter(contact__reporting_location__in=locations).values('contact__reporting_location__name')
    return q.annotate(Sum('eav_values__value_float'))


def get_responses_over_depth(name, locations, depth):
    poll = Poll.objects.get(name=name)
    q = get_district_responses(locations, poll)
    date_weeks = get_week_date(depth=depth)
    return [q.filter(date__range=date_range) for date_range in date_weeks]