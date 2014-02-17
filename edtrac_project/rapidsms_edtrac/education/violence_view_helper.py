'''
Created on Apr 08, 2013

@author: raybesiga
'''

# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
from django.conf import settings
from collections import defaultdict
from datetime import timedelta
from django.db.models import Sum, Count

from education.models import EmisReporter, Poll
from education.reports import get_month_day_range
from education.utils import is_empty
from rapidsms.contrib.locations.models import Location
from unregister.models import Blacklist

def get_location_for_violence_view(district, request):
    if district is None:
        profile = request.user.get_profile()
        locations = [profile.location]
        if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
                'UNICEF Officials'):
            locations = Location.objects.filter(type="district", pk__in=EmisReporter.objects.exclude(
                connection__in=Blacklist.objects.values_list('connection',flat=True), schools=None).values_list(
                'reporting_location__pk', flat=True))
    else:
        locations = [Location.objects.get(name__iexact=district, type__name='district')]
    return locations

def get_district_responses(locations, poll):
    q = poll.responses.filter(contact__reporting_location__in=locations).exclude(contact__emisreporter__schools=None)
    if len(locations) == 1:
        q = q.values('contact__emisreporter__schools__name')
    else:
        q = q.values('contact__reporting_location__name')
    return q.annotate(Sum('eav_values__value_float'))

def filter_over_time_range(time_range, responses):
    return responses.filter(date__range=time_range)

def get_responses_over_depth(violence_poll, locations, date_months):
#    violence_poll = Poll.objects.get(name=violence_poll_name)
    district_responses = get_district_responses(locations, violence_poll)

    return [filter_over_time_range(date_range, district_responses) for date_range in
            date_months]

def get_all_responses(poll,location):
    term_range = [getattr(settings,'SCHOOL_TERM_START'),getattr(settings,'SCHOOL_TERM_END')]
    district_responses = get_district_responses(location, poll)
#    all_responses = poll.responses_by_category().filter(response__contact__reporting_location__in=location)
    term_responses = district_responses.filter(response__date__range = term_range)
    months= get_month_day_range(datetime.now(),depth=datetime.today().month)
    to_ret=[]
    for month in months:
        monthly_responses =district_responses.filter(response__date__range=month)
        to_ret.append((month[0].strftime("%B"),_extract_info(monthly_responses)))
    return _extract_info(term_responses).items(),to_ret

def _extract_info(l):
    to_ret = [[item.get('category__name'), item.get('value')] for item in l]
    final_ret = {}
    for li in to_ret:
        final_ret[li[0]] = li[1]

    total = sum(filter(None, final_ret.values()))

    for key in final_ret.keys():
        final_ret[key] = compute_percent(final_ret.get(key), total)

    return final_ret









def compute_percent(x, y):
    try:
        return (100 * x) / y
    except ZeroDivisionError:
        return 0


def get_date_range(from_date, to_date, depth=2):
    if from_date is None and to_date is None:
        return get_month_day_range(depth)

