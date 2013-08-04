# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from education.models import EmisReporter, School
from education.utils import get_months
from rapidsms.contrib.locations.models import Location
from unregister.models import Blacklist


def get_location_for_water_view(district_pk, request):
    if district_pk is None:
        profile = request.user.get_profile()
        locations,user_location = [profile.location],profile.location.name
        if profile.is_member_of('Ministry Officials') or profile.is_member_of('Admins') or profile.is_member_of(
                'UNICEF Officials'):
            locations = Location.objects.filter(type="district", pk__in=EmisReporter.objects.exclude(
                connection__in=Blacklist.objects.values_list('connection', flat=True), schools=None).values_list(
                'reporting_location__pk', flat=True))
            user_location = 'Uganda'
    else:
        location = Location.objects.get(pk=district_pk)
        locations,user_location = [location],location.name
    return locations,user_location


def _format_to_ret_for_all_responses(month, all_responses):
    return month[0].strftime("%B"),_extract_percentage_for_each_response_category_from(all_responses.filter(response__date__range=month))


def get_reporting_school_percentage(responses, location):
    response_count = responses.values_list('response__contact__emisreporter__schools').distinct().count()
    total_schools = School.objects.exclude(emisreporter=None).filter(location__in=location).count()
    return compute_percent(response_count,total_schools)


def get_all_responses(poll, location, time_range):
    unknown_responses = poll.responses.filter(categories__category__name='unknown')
    all_responses = poll.responses_by_category().filter(response__contact__reporting_location__in=location).exclude(response__in=unknown_responses)
    term_responses = all_responses.filter(response__date__range = time_range)
    percent_of_schools = get_reporting_school_percentage(term_responses,location)
    months= get_months(time_range[0],time_range[1])
    months.reverse()
    monthly_result = [_format_to_ret_for_all_responses(month, all_responses)for month in months]
    #       dictionary of category and percent, tuple of month and dict, percentage for a school
    return _extract_percentage_for_each_response_category_from(term_responses).items(), monthly_result, percent_of_schools



def _extract_percentage_for_each_response_category_from(responses):
    to_ret = [[item.get('category__name'), item.get('value')] for item in responses]
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