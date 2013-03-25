# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from collections import defaultdict
from datetime import timedelta
from django.conf import settings

from django.db.models import Sum, Count

from education.models import EmisReporter, School
from education.reports import get_week_date
from education.utils import is_empty
from poll.models import Poll, ResponseCategory, Response


def get_aggregated_report(locations, config_list, date_weeks):
    by_location = []
    by_time = []
    for config in config_list:
        a, b = config['func'](locations, config, date_weeks)
        by_location.append((a, config['collective_dict_key']))
        by_time.append((b, config['time_data_name']))

    return get_collective_result(by_location, by_time)


def get_aggregation_by_time(filtered_responses):
    aggregated_list = []
    for responses in filtered_responses:
        sum_value = 0
        for response in responses:
            if response.values()[0] is not None:
                sum_value += response.values()[0]
        aggregated_list.append(sum_value)
    return aggregated_list


def get_aggregation_by_location(filtered_responses):
    aggregated_dict = defaultdict(lambda: 0)
    for responses in filtered_responses:
        for response in responses:
            for key in response:
                if response[key] is not None:
                    aggregated_dict[key] += response[key]
    return aggregated_dict


def _make_transformed_list_of_dict(data):
    return [{item['contact__reporting_location__name']: item['eav_values__value_float__sum']} for item in data if
            item['eav_values__value_float__sum'] is not None]


def transform(untransformed_data):
    return [_make_transformed_list_of_dict(data) for data in untransformed_data]


def get_aggregated_result(result, dict_to_add ):
    for key in dict_to_add:
        result[key] += dict_to_add[key]


def get_aggregated_list(result, list_to_add):
    if len(result) == 0:
        result.extend(list_to_add)
    else:
        for index, value in enumerate(result):
            result[index] += list_to_add[index]


def _transform(responses):
    ret = []
    for response in responses:
        temp = []
        for item in response:
            temp.append({item[0]: item[1]})
        ret.append(temp)
    return ret


def get_responses_by_location(locations, config_list, date_weeks):
    attendance_poll_names = config_list['attendance_poll']
    enrollment_poll_names = config_list['enrollment_poll']
    total_enrollment = 0
    total_enrollment_by_location = defaultdict(lambda: 0)
    total_present_by_location = defaultdict(lambda: 0)
    total_present_by_time = []
    for index, attendance_poll_name in enumerate(attendance_poll_names):

        if len(locations) == 1:
            res = [filter_over_time_range(date_range, get_school_responses(locations[0], attendance_poll_name)) for
                   date_range in date_weeks]
            tr_res = _transform(res)
            get_aggregated_result(total_present_by_location, get_aggregation_by_location(tr_res))

            en = get_school_responses(locations[0], enrollment_poll_names[index])
            tr_en = _transform([en])
            get_aggregated_result(total_enrollment_by_location, get_aggregation_by_location(tr_en))
            total_enrollment += sum(total_enrollment_by_location.values())
            get_aggregated_list(total_present_by_time, get_aggregation_by_time(tr_res))
        else:
            filtered_responses, filtered_enrollment = get_responses_over_depth(attendance_poll_name,
                                                                               enrollment_poll_names[index],
                                                                               list(locations), date_weeks)

            transformed_responses = transform(filtered_responses)
            get_aggregated_result(total_present_by_location, get_aggregation_by_location(transformed_responses))

            transformed_enrollment = transform([filtered_enrollment])
            get_aggregated_result(total_enrollment_by_location, get_aggregation_by_location(transformed_enrollment))
            total_enrollment += sum(total_enrollment_by_location.values())

            get_aggregated_list(total_present_by_time, get_aggregation_by_time(transformed_responses))
    absent_by_time = [round(compute_percent(i, total_enrollment), 2) for i in total_present_by_time]

    absent_by_location = {}
    for key in total_present_by_location:
        absent_by_location[key] = round(
            compute_percent(total_present_by_location[key], total_enrollment_by_location[key] * len(date_weeks)), 2)

    return absent_by_location, absent_by_time


def get_school_responses(location, poll_name):
    poll = Poll.objects.get(name=poll_name)
    schools = School.objects.filter(location=location)
    a_set = set()
    for school in schools:
        a_set.add(poll.responses.filter(contact__reporting_location=location,
                                        contact__in=school.emisreporter_set.all()).values('id'))
    temp = [i for i in a_set if not is_empty(i)]
    a_set = [item['id'] for sublist in temp for item in sublist]
    to_ret = Response.objects.filter(pk__in=a_set).values_list('contact__emisreporter__schools__name').annotate(
        Sum('eav_values__value_float'))
    return to_ret


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
    yes_count, no_count = 0, 0
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


def get_head_teachers_absent_over_time(locations, config, date_weeks):
    gender = config.get('gender')
    fields = ['category__name', 'response__contact__reporting_location__name']
    head_teachers = EmisReporter.objects.filter(reporting_location__in=locations, groups__name="Head Teachers").exclude(
        schools=None)
    if gender is not None:
        head_teachers = head_teachers.filter(gender__iexact=gender)
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
        calculate_yes_and_no_for_time(yes_by_time, no_by_time, resp_by_time)
        calculate_yes_and_no_for_location(yes_by_location, no_by_location, resp_by_time)

    absent_percent_by_time = [compute_percent(yes_by_time[i], (yes_by_time[i] + no_by_time[i])) for i in
                              range(len(yes_by_time))]
    absent_percent_by_location = {}
    for key in yes_by_location:
        absent_percent_by_location[key] = compute_percent(yes_by_location[key],
                                                          yes_by_location[key] + no_by_location[key])
    return absent_percent_by_location, absent_percent_by_time


def compute_percent(x, y):
    try:
        return (100 * (y - x)) / y
    except ZeroDivisionError:
        return 0


def get_collective_result(location_configs, time_configs):
    location_result = defaultdict(lambda: {})
    for config in location_configs:
        location_data = config[0]
        key_name = config[1]
        for key in location_data:
            location_result[key].update({str(key_name): location_data[key]})
    time_result = [dict(name=str(config[1]), data=config[0]) for config in time_configs]
    return dict(location_result), time_result


def get_date_range(from_date, to_date, depth=4):
    if from_date is None and to_date is None:
        return get_week_date(depth)
    week_range = []
    first_week = (from_date, from_date + timedelta(days=7))
    week_range.append(first_week)
    from_date = from_date + timedelta(days=7)
    while from_date < to_date:
        week_range.append((from_date + timedelta(days=1), from_date + timedelta(days=8)))
        from_date = from_date + timedelta(days=7)
    return week_range


def get_polls_for_keyword(indicator):
    attendance_poll_dict = dict(P3Boys=['edtrac_boysp3_attendance'], P3Girls=['edtrac_girlsp3_attendance'],
                                P3Pupils=['edtrac_boysp3_attendance', 'edtrac_girlsp3_attendance'],
                                P6Boys=['edtrac_boysp6_attendance'], P6Girls=['edtrac_girlsp6_attendance'],
                                P6Pupils=['edtrac_boysp6_attendance', 'edtrac_girlsp6_attendance'],
                                MaleTeachers=['edtrac_m_teachers_attendance'],
                                FemaleTeachers=['edtrac_f_teachers_attendance'],
                                Teachers=['edtrac_m_teachers_attendance', 'edtrac_f_teachers_attendance'])

    enrollment_poll_dict = dict(P3Boys=['edtrac_boysp3_enrollment'], P3Girls=['edtrac_girlsp3_enrollment'],
                                P3Pupils=['edtrac_boysp3_enrollment', 'edtrac_girlsp3_enrollment'],
                                P6Boys=['edtrac_boysp6_enrollment'], P6Girls=['edtrac_girlsp6_enrollment'],
                                P6Pupils=['edtrac_boysp6_enrollment', 'edtrac_girlsp6_enrollment'],
                                MaleTeachers=['edtrac_m_teachers_deployment'],
                                FemaleTeachers=['edtrac_f_teachers_deployment'],
                                Teachers=['edtrac_m_teachers_deployment', 'edtrac_f_teachers_deployment'])

    collective_key_dict = dict(P3Boys='p3_boys', P3Girls='p3_girls', P3Pupils='p3_pupils',
                               P6Boys='p6_boys', P6Girls='p6_girls', P6Pupils='p6_pupils',
                               MaleTeachers='m_teachers', FemaleTeachers='f_teachers', Teachers='teachers',
                               MaleHeadTeachers='m_h_teachers', FemaleHeadTeachers='f_h_teachers',
                               HeadTeachers='h_teachers')

    time_data_dict = dict(P3Boys='P3_Boys', P3Girls='P3_Girls', P3Pupils='P3_Pupils',
                          P6Boys='P6_Boys', P6Girls='P6_Girls', P6Pupils='P6_Pupils',
                          MaleTeachers='M_Teachers', FemaleTeachers='F_Teachers', Teachers='Teachers',
                          FemaleHeadTeachers='F_H_Teachers', MaleHeadTeachers='M_H_Teachers', HeadTeachers='H_Teachers')

    gender_dict = dict(FemaleHeadTeachers='F', MaleHeadTeachers='M')

    if indicator == 'all':
        list_of_values = ['P3Pupils', 'P6Pupils', 'Teachers', 'HeadTeachers']
        config_list = sum([get_polls_for_keyword(v) for v in list_of_values], [])
    elif indicator in ['MaleHeadTeachers', 'FemaleHeadTeachers']:
        config_list = [dict(func=get_head_teachers_absent_over_time, gender=gender_dict[indicator],
                            collective_dict_key=collective_key_dict[indicator],
                            time_data_name=time_data_dict[indicator])]
    elif indicator in ['HeadTeachers']:
        config_list = [dict(func=get_head_teachers_absent_over_time,
                            collective_dict_key=collective_key_dict[indicator],
                            time_data_name=time_data_dict[indicator])]
    else:
        config_list = [
            dict(attendance_poll=attendance_poll_dict[indicator], collective_dict_key=collective_key_dict[indicator],
                 enrollment_poll=enrollment_poll_dict[indicator], time_data_name=time_data_dict[indicator],
                 func=get_responses_by_location)]
    return config_list