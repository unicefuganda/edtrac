# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from django.db.models import Sum
from education.models import EnrolledDeployedQuestionsAnswered
from education.reports import get_week_date
from poll.models import Poll
from rapidsms.contrib.locations.models import Location


def get_responses_by_location(user_profile, name, depth=4):
    locations = [user_profile.location]

    if user_profile.is_member_of('Ministry Officials') or user_profile.is_member_of(
            'Admins') or user_profile.is_member_of('UNICEF Officials'):
        locations = Location.objects.filter(type='district').filter(pk__in= \
            EnrolledDeployedQuestionsAnswered.objects.values_list('school__location__pk', flat=True))

    return get_responses_over_month(name, list(locations), depth)


def get_district_responses(locations, poll):
    q = poll.responses.filter(contact__reporting_location__in=locations).values('contact__reporting_location__name')
    return q.annotate(Sum('eav_values__value_float'))


def get_responses_over_month(name, locations, depth):
    poll = Poll.objects.get(name=name)
    q = get_district_responses(locations, poll)
    date_weeks = get_week_date(depth=depth)
    return [q.filter(date__range=date_range) for date_range in date_weeks]