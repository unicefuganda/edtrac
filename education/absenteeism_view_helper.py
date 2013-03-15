# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from collections import defaultdict
from django.conf import settings

from django.db.models import Sum, Count

from education.models import EnrolledDeployedQuestionsAnswered, EmisReporter
from education.reports import get_week_date
from poll.models import Poll, ResponseCategory
from rapidsms.contrib.locations.models import Location


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


def get_responses_by_location(user_profile, attendance_poll_name, enrollment_poll_name, depth=4):
    locations = [user_profile.location]

    if user_profile.is_member_of('Ministry Officials') or user_profile.is_member_of(
            'Admins') or user_profile.is_member_of('UNICEF Officials'):
        locations = Location.objects.filter(type='district').filter(pk__in= \
            EnrolledDeployedQuestionsAnswered.objects.values_list('school__location__pk', flat=True))

    filtered_responses, filtered_enrollment = get_responses_over_depth(attendance_poll_name, enrollment_poll_name,
                                                                       list(locations), depth)

    transformed_enrollment = transform([filtered_enrollment])
    enrollment_by_location = get_aggregation_by_location(transformed_enrollment)
    total_enrollment = sum(enrollment_by_location.values())

    transformed_responses = transform(filtered_responses)
    present_by_location = get_aggregation_by_location(transformed_responses)
    present_by_time = get_aggregation_by_time(transformed_responses)

    absent_by_time = [round(compute_percent(i,total_enrollment),2) for i in present_by_time]

    absent_by_location = {}
    for key in present_by_location:
        absent_by_location[key] = round(compute_percent(present_by_location[key],enrollment_by_location[key]*depth),2)

    return absent_by_location, absent_by_time


def get_district_responses(locations, poll):
    q = poll.responses.filter(contact__reporting_location__in=locations).values('contact__reporting_location__name')
    return q.annotate(Sum('eav_values__value_float'))


def filter_over_time_range(time_range, responses):
    return responses.filter(date__range=time_range)


def get_responses_over_depth(attendance_poll_name, enrollment_poll_name, locations, depth):
    attedance_poll = Poll.objects.get(name=attendance_poll_name)
    district_responses = get_district_responses(locations, attedance_poll)

    enrollment_poll = Poll.objects.get(name=enrollment_poll_name)
    district_enrollment = get_district_responses(locations, enrollment_poll)

    date_weeks = get_week_date(depth=depth)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    [filter_over_time_range(date_range, district_responses) for date_range in date_weeks]
    return [filter_over_time_range(date_range, district_responses) for date_range in
            date_weeks], filter_over_time_range(term_range, district_enrollment)


def calculate_yes_and_no_for_time(yes, no, resp_by_time):
    yes_count,no_count = 0,0
    for values in resp_by_time:
        if values[0] == 'yes':
            yes_count += values[2]
        elif values[0] == 'no':
            no_count += values[2]
    yes.append(yes_count)
    no.append(no_count)


def calculate_yes_and_no_for_location(yes, no, resp_by_time_by_location):
    for values in resp_by_time_by_location:
        if values[0] == 'yes':
            yes[values[1]] += values[2]
        elif values[0] == 'no':
            no[values[1]] += values[2]


def get_head_teachers_absent_over_time(locations, gender, depth):
    date_weeks = get_week_date(depth)
    fields = ['category__name', 'response__contact__reporting_location__name']
    head_teachers = EmisReporter.objects.filter(reporting_location__in=locations, groups__name="Head Teachers",
                                                gender=gender).exclude(schools=None)
    head_t_deploy = EmisReporter.objects.filter(reporting_location__in=locations,
                                                schools__in=head_teachers.values_list('schools', flat=True),
                                                groups__name='SMC').distinct()
    head_teacher_poll = Poll.objects.get(name='edtrac_head_teachers_attendance')
    yes_by_time = []
    no_by_time = []

    yes_by_location = defaultdict(lambda: 0)
    no_by_location = defaultdict(lambda: 0)
    resp_by_category = ResponseCategory.objects.filter(response__in=head_teacher_poll.responses.filter(
        contact__reporting_location__in=locations,
        contact__in=head_t_deploy.values_list('connection__contact',
                                              flat=True))).values_list(*fields).annotate(value=Count('pk'))
    for date_week in date_weeks:
        resp_by_time = resp_by_category.filter(response__date__range=date_week)
        calculate_yes_and_no_for_time(yes_by_time,no_by_time,resp_by_time)
        calculate_yes_and_no_for_location(yes_by_location,no_by_location,resp_by_time)

    absent_percent_by_time = [compute_percent(yes_by_time[i], (yes_by_time[i] + no_by_time[i])) for i in range(len(yes_by_time))]
    absent_percent_by_location = {}
    for key in yes_by_location:
        absent_percent_by_location[key] = compute_percent(yes_by_location[key], yes_by_location[key]+no_by_location[key])
    return absent_percent_by_location, absent_percent_by_time

def compute_percent(x, y):
    try:
        return (100 * (y-x)) / y
    except ZeroDivisionError:
        return 0