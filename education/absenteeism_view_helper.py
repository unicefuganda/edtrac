# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from collections import defaultdict
from datetime import timedelta
from django.conf import settings

from django.db.models import Sum, Count

from education.models import EmisReporter
from education.reports import get_week_date
from poll.models import Poll, ResponseCategory


def get_aggregated_report(locations, config_list, date_weeks):
    by_location = []
    by_time = []
    for config in config_list:
        a,b = get_responses_by_location(locations, config['attendance_poll'], config['enrollment_poll'], date_weeks)
        by_location.append((a, config['collective_dict_key']))
        by_time.append((b, config['time_data_name']))

    return get_collective_result(by_location, by_time)

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


def get_aggregated_result(result,dict_to_add ):
    for key in dict_to_add:
        result[key]+=dict_to_add[key]


def get_aggregated_list(result, list_to_add):
    if len(result)==0:
        result.extend(list_to_add)
    else:
        for index,value in enumerate(result):
            result[index] += list_to_add[index]


def get_responses_by_location(locations, attendance_poll_names, enrollment_poll_names, date_weeks):
    total_enrollment=0
    total_enrollment_by_location = defaultdict(lambda :0)
    total_present_by_location = defaultdict(lambda :0)
    total_present_by_time = []
    for index, attendance_poll_name in enumerate(attendance_poll_names):
        filtered_responses, filtered_enrollment = get_responses_over_depth(attendance_poll_name, enrollment_poll_names[index],
                                                                       list(locations), date_weeks)

        transformed_enrollment = transform([filtered_enrollment])
        get_aggregated_result(total_enrollment_by_location,get_aggregation_by_location(transformed_enrollment))
        total_enrollment+= sum(total_enrollment_by_location.values())

        transformed_responses = transform(filtered_responses)
        get_aggregated_result(total_present_by_location,get_aggregation_by_location(transformed_responses))
        get_aggregated_list(total_present_by_time,get_aggregation_by_time(transformed_responses))

    absent_by_time = [round(compute_percent(i,total_enrollment),2) for i in total_present_by_time]

    absent_by_location = {}
    for key in total_present_by_location:
        absent_by_location[key] = round(compute_percent(total_present_by_location[key],total_enrollment_by_location[key]*len(date_weeks)),2)

    return absent_by_location, absent_by_time


def get_district_responses(locations, poll):
    q = poll.responses.filter(contact__reporting_location__in=locations).values('contact__reporting_location__name')
    return q.annotate(Sum('eav_values__value_float'))


def filter_over_time_range(time_range, responses):
    return responses.filter(date__range=time_range)


def get_responses_over_depth(attendance_poll_name, enrollment_poll_name, locations, date_weeks):
    attedance_poll = Poll.objects.get(name=attendance_poll_name)
    district_responses = get_district_responses(locations, attedance_poll)

    enrollment_poll = Poll.objects.get(name=enrollment_poll_name)
    district_enrollment = get_district_responses(locations, enrollment_poll)

    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
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


def get_head_teachers_absent_over_time(locations, gender, date_weeks):
    fields = ['category__name', 'response__contact__reporting_location__name']
    head_teachers = EmisReporter.objects.filter(reporting_location__in=locations, groups__name="Head Teachers",
                                                gender__iexact=gender).exclude(schools=None)
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

    print yes_by_location, no_by_location
    print yes_by_time, no_by_time
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

def get_collective_result(location_configs, time_configs):
    location_result = defaultdict(lambda: {})
    for config in location_configs:
        location_data = config[0]
        key_name = config[1]
        for key in location_data:
            location_result[key].update({str(key_name):location_data[key]})
    time_result = [dict(name=str(config[1]), data=config[0]) for config in time_configs]
    return dict(location_result), time_result


def get_date_range(from_date, to_date):
    week_range=[]
    first_week = (from_date , from_date + timedelta(days=7))
    week_range.append(first_week)
    from_date = from_date + timedelta(days=7)
    while from_date < to_date:
        week_range.append((from_date + timedelta(days=1) , from_date + timedelta(days=8)))
        from_date = from_date+timedelta(days=7)
    return week_range


def get_polls_for_keyword(indicator):
    attendance_poll_dict = dict(P3Boys=['edtrac_boysp3_attendance'], P3Girls=['edtrac_girlsp3_attendance'],
                                P3Pupils=['edtrac_boysp3_attendance', 'edtrac_girlsp3_attendance'],
                                P6Boys=['edtrac_boysp6_attendance'], P6Girls=['edtrac_girlsp6_attendance'],
                                P6Pupils=['edtrac_boysp6_attendance', 'edtrac_girlsp6_attendance'])

    enrollment_poll_dict = dict(P3Boys=['edtrac_boysp3_enrollment'], P3Girls=['edtrac_girlsp3_enrollment'],
                                P3Pupils=['edtrac_boysp3_enrollment', 'edtrac_girlsp3_enrollment'],
                                P6Boys=['edtrac_boysp6_enrollment'], P6Girls=['edtrac_girlsp6_enrollment'],
                                P6Pupils=['edtrac_boysp6_enrollment', 'edtrac_girlsp6_enrollment'])
    collective_key_dict = dict(P3Boys='p3_boys', P3Girls='p3_girls', P3Pupils='p3_pupils',
                               P6Boys='p6_boys', P6Girls='p6_girls', P6Pupils='p6_pupils')

    time_data_dict = dict(P3Boys='P3_Boys', P3Girls='P3_Girls', P3Pupils='P3_Pupils',
                          P6Boys='P6_Boys', P6Girls='P6_Girls', P6Pupils='P6_Pupils')

    config_list = [
        dict(attendance_poll=attendance_poll_dict[indicator], collective_dict_key=collective_key_dict[indicator],
             enrollment_poll=enrollment_poll_dict[indicator], time_data_name=time_data_dict[indicator])]
    return config_list