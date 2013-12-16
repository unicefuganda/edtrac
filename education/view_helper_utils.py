from __future__ import division
from education.models import *
from poll.models import Poll
from .reports import *
from education.results import NumericResponsesFor, collapse
from education.absenteeism_view_helper import *

def get_aggregated_report_for_district(locations, time_range, config_list):
    collective_result = {}
    school_with_no_zero_by_indicator = {}
    enrollment_by_indicator = {}
    attendance_by_indicator = {}

    # Get term range from settings file (config file)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    indicator_list = ['P3 Pupils', 'P6 Pupils', 'Teachers']
    # Initialize chart data and school percent List / dict holder
    for indicator in indicator_list:
        enrollment_by_indicator[indicator] = 0
        attendance_by_indicator[indicator] = []
        school_with_no_zero_by_indicator[indicator] = 0

    enrollment_by_indicator['Head Teachers'] = 0
    attendance_by_indicator['Head Teachers'] = []
    school_with_no_zero_by_indicator['Head Teachers'] = 0

    # update attendance by indicator with current date ranges (enable present computation along date x-axis)
    for _date in time_range:
        for v in attendance_by_indicator.values():
            v.append({'week': _date, 'present': 0, 'enrollment': 0, 'percent': 0})

    schoolSource = School.objects.filter(location__in=locations)
    for school in schoolSource:
        has_enrollment = False
        config_set_result = {}
        for config in config_list:
            if config.get('collective_dict_key') in indicator_list:
                enrollment_polls = Poll.objects.filter(name__in=[config.get('enrollment_poll')[0]])
                attendance_polls = Poll.objects.filter(name__in=[config.get('attendance_poll')[0]])
                enroll_data = get_numeric_data_by_school(enrollment_polls[0],[school],term_range)
                enrollment_by_indicator[config.get('collective_dict_key')] += sum(enroll_data)
                enroll_indicator_total = sum(enroll_data)
                week_count = 0
                weekly_results = []
                for week in time_range:
                    week_count += 1
                    attend_week_total = sum(get_numeric_data_by_school(attendance_polls[0], [school], week))
                    week_percent = compute_absent_values(attend_week_total, enroll_indicator_total)
                    weekly_results.append(week_percent)

                    if not is_empty(enroll_data):
                        for k, v in attendance_by_indicator.items():
                            if k == config.get('collective_dict_key'):
                                for val in v:
                                    if val['week'] == week:
                                        val['percent'] = val['percent'] + week_percent
                                        val['present'] = val['present'] + attend_week_total
                                        val['enrollment'] = enrollment_by_indicator[config.get('collective_dict_key')]

                if not is_empty(enroll_data):
                    has_enrollment = True
                    school_with_no_zero_by_indicator[config.get('collective_dict_key')] +=1
                    config_set_result[config.get('collective_dict_key')] = round(sum(weekly_results)/len(time_range),2)

            else: # Head teachers
                deployedHeadTeachers = get_deployed_head_Teachers_by_school([school],locations)
                enrollment_by_indicator[config.get('collective_dict_key')] += deployedHeadTeachers
                attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])
                weekly_present = []
                weekly_percent = []
                for week in time_range:
                    present, absent = get_count_for_yes_no_by_school(attendance_polls,[school], week)
                    week_percent = compute_absent_values(present, deployedHeadTeachers)
                    weekly_present.append(present)
                    weekly_percent.append(week_percent)

                    if deployedHeadTeachers == 1:
                        for k, v in attendance_by_indicator.items():
                            if k == config.get('collective_dict_key'):
                                for val in v:
                                    if val['week'] == week:
                                        val['percent'] = val['percent'] + week_percent
                                        val['present'] = val['present'] + attend_week_total
                                        val['enrollment'] = enrollment_by_indicator[config.get('collective_dict_key')]


                if deployedHeadTeachers == 1:
                    school_with_no_zero_by_indicator[config.get('collective_dict_key')] += 1
                    has_enrollment = True
                    percent_absent = compute_absent_values(sum(weekly_present) / len(time_range), deployedHeadTeachers)
                    config_set_result[config.get('collective_dict_key')] = round(percent_absent, 2)

        if has_enrollment:
            collective_result[school.name] = config_set_result

    time_data_model = []
    school_data = {}

    for k,v in school_with_no_zero_by_indicator.items():
        school_data[k] = round((v*100)/len(schoolSource),2)

    # clean up collective_dict
    indicator_list = ['P3 Pupils', 'P6 Pupils', 'Teachers','Head Teachers']
    for k,v in collective_result.items():
        for item in indicator_list:
            v.setdefault(item,'--')

    # model percentage
    for key, entry in attendance_by_indicator.items():
        data = []
        for item in entry:
            percent = round(compute_absent_values(item['present'], item['enrollment']), 2)
            data.append(percent)
        time_data_model.append({'name': key, 'data': data})

    chart_results_model = time_data_model

    return collective_result, chart_results_model, school_data, []


def get_aggregated_report_data(locations, time_range, config_list):
    location_absenteeism_percent_values = {}
    school_report = []
    enrollment_by_indicator = {}
    attendance_by_indicator = {}

    # Get term range from settings file (config file)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]

    indicator_list = ['P3 Pupils', 'P6 Pupils', 'Teachers']
    # Initialize chart data and school percent List / dict holder
    for indicator in indicator_list:
        school_report.append({indicator: [0] * len(time_range)})
        enrollment_by_indicator[indicator] = 0
        attendance_by_indicator[indicator] = []

    school_report.append({'Head Teachers': [0] * len(time_range)})
    enrollment_by_indicator['Head Teachers'] = 0
    attendance_by_indicator['Head Teachers'] = []

    # update attendance by indicator with current date ranges (enable present computation along date x-axis)
    for _date in time_range:
        for v in attendance_by_indicator.values():
            v.append({'week': _date, 'present': 0, 'enrollment': 0, 'percent': 0})

    location_absenteeism_percent_values = {}
    for config in config_list:
        if config.get('collective_dict_key') in indicator_list:
            enrollment_polls = Poll.objects.filter(name__in = [config.get('enrollment_poll')[0]])
            attendance_polls = Poll.objects.filter(name__in = [config.get('attendance_poll')[0]])
            # get both enroll list and schools that responded
            enroll_indicator_totals  = get_numeric_data_all_locations(enrollment_polls[0], term_range)
            totalCount = sum(enroll_indicator_totals.values())
            enrollment_by_indicator[config.get('collective_dict_key')] = totalCount

            weekly_school_count = []
            for week in time_range:
                # get attendance total for week by indicator from config file
                attendance_data_totals = get_numeric_data_all_locations(attendance_polls[0], week)
                attend_week_total = sum(attendance_data_totals.values())
                # get schools that Responded
                schools_that_responded = len(attendance_data_totals)
                week_percent = compute_absent_values(attend_week_total, totalCount)
                weekly_school_count.append(schools_that_responded)

                #Loop through locations and determine weekly location absenteeism values
                for location in locations:
                    location_enrollment = 0
                    location_attendance = 0
                    if location.name not in location_absenteeism_percent_values:
                        location_absenteeism_percent_values[location.name] = {}
                    if config.get('collective_dict_key') not in location_absenteeism_percent_values[location.name]:
                        location_absenteeism_percent_values[location.name][config.get('collective_dict_key')] = 0

                    if location.id in enroll_indicator_totals:
                        location_enrollment = enroll_indicator_totals[location.id]
                        if location.id in attendance_data_totals:
                            location_attendance = attendance_data_totals[location.id]
                        location_absenteeism_percent_values[location.name][config.get('collective_dict_key')] += compute_absent_values(location_attendance, location_enrollment)

                # update attendance by indicator collection with values per week
                for k, v in attendance_by_indicator.items():
                    if k == config.get('collective_dict_key'):
                        for val in v:
                            if val['week'] == week:
                                val['percent'] = week_percent
                                val['present'] = attend_week_total
                                val['enrollment'] = enrollment_by_indicator[config.get('collective_dict_key')]

            # update school reporting summary collection
            for item in school_report:
                for k, v in item.items():
                    if k == config.get('collective_dict_key'):
                        item[k] = [sum(a) for a in zip(*[v, weekly_school_count])]

        else: # used to compute head teachers absenteeism
            headteachersSource = EmisReporter.objects.filter(reporting_location__in=locations, groups__name="Head Teachers").exclude(schools=None).select_related()
            enroll_indicator_totals = get_all_deployed_head_teachers(headteachersSource)
            totalCount = sum(enroll_indicator_totals.values())
            enrollment_by_indicator[config.get('collective_dict_key')] = totalCount
            attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])

            weekly_school_count = []
            for week in time_range:
                present_data_totals, absent_data_totals = get_count_for_yes_no_response_all_locations(attendance_polls, week)
                schools_that_responded = len(present_data_totals) + len(absent_data_totals)

                week_percent = compute_absent_values(sum(present_data_totals.values()), totalCount)
                weekly_school_count.append(schools_that_responded)

                #Loop through locations and determine weekly location absenteeism values
                for location in locations:
                    location_enrollment = 0
                    location_attendance = 0
                    if location.name not in location_absenteeism_percent_values:
                        location_absenteeism_percent_values[location.name] = {}
                    if config.get('collective_dict_key') not in location_absenteeism_percent_values[location.name]:
                        location_absenteeism_percent_values[location.name][config.get('collective_dict_key')] = 0

                    if location.id in enroll_indicator_totals:
                        location_enrollment = enroll_indicator_totals[location.id]
                        if location.id in present_data_totals:
                            location_attendance = present_data_totals[location.id]
                        location_absenteeism_percent_values[location.name][config.get('collective_dict_key')] += compute_absent_values(location_attendance, location_enrollment)

                # update attendance by indicator collection with values per week
                for k, v in attendance_by_indicator.items():
                    if k == config.get('collective_dict_key'):
                        for val in v:
                            if val['week'] == week:
                                val['percent'] = week_percent
                                val['present'] = sum(present_data_totals.values())
                                val['enrollment'] = enrollment_by_indicator[config.get('collective_dict_key')]

            for item in school_report:
                for k, v in item.items():
                    if k == config.get('collective_dict_key'):
                        item[k] = [sum(a) for a in zip(*[v, weekly_school_count])]

        # adds average percentage to dict_key
        for location, location_absenteeism_percent in location_absenteeism_percent_values.items():
            location_absenteeism_percent_values[location][config.get('collective_dict_key')] = round(location_absenteeism_percent[config.get('collective_dict_key')] / len(time_range),2)

    #absenteeism computation model : problem : hides some facts a long each location and computes at global count across all locations
    # get sum of present values for all locations, sum of  enrollment values for all locations, all accross each indicator
    time_data_model = []
    for key, entry in attendance_by_indicator.items():
        data = [round(compute_absent_values(item['present'], item['enrollment']), 2) for item in entry]
        time_data_model.append({'name': key, 'data': data})

    # get school response average
    schoolSource = School.objects.filter(location__in=locations).select_related()
    schools_total = len(schoolSource)
    school_data = {}
    for item in school_report:
        for k, v in item.items():
            school_data[k] = round(((sum(v) / len(time_range)) / schools_total) * 100, 2)

    chart_results_model = time_data_model

    return location_absenteeism_percent_values, chart_results_model, school_data, []


def get_aggregated_report_data_single_indicator(locations, time_range, config_list):
    collective_result = {}
    location_absenteeism_percent_values = {}
    avg_school_responses = []

    # Get term range from settings file (config file)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    headteachersSource = EmisReporter.objects.filter(reporting_location__in=locations, groups__name="Head Teachers").exclude(schools=None).select_related()

    weekly_present_result = []
    weekly_school_responses = []

    if config_list[0].get('collective_dict_key') not in  ['Male Head Teachers', 'Female Head Teachers', 'Head Teachers']:
        enrollment_polls = Poll.objects.filter(name__in=config_list[0].get('enrollment_poll'))
        attendance_polls = Poll.objects.filter(name__in=config_list[0].get('attendance_poll'))

        # get total enrollment numbers
        enroll_indicator_totals  = get_numeric_data_all_locations(enrollment_polls[0], term_range)
        totalCount = sum(enroll_indicator_totals.values())

        for week in time_range:
            # get attendance total for week by indicator from config file
            attendance_data_totals = get_numeric_data_all_locations(attendance_polls[0], week)
            weekly_present_result.append(sum(attendance_data_totals.values()))
            # get number of schools that Responded
            weekly_school_responses.append(len(attendance_data_totals))

            #Loop through locations and determine weekly location absenteeism values
            for location in locations:
                location_enrollment = 0
                location_attendance = 0
                if location.name not in location_absenteeism_percent_values:
                    location_absenteeism_percent_values[location.name] = 0

                if location.id in enroll_indicator_totals:
                    location_enrollment = enroll_indicator_totals[location.id]
                    if location.id in attendance_data_totals:
                        location_attendance = attendance_data_totals[location.id]
                    location_absenteeism_percent_values[location.name] += compute_absent_values(location_attendance, location_enrollment)

    elif config_list[0].get('collective_dict_key') in ['Male Head Teachers', 'Female Head Teachers']:
        enroll_indicator_totals = get_all_gender_deployed_head_teachers(headteachersSource, config_list[0].get('gender'))
        totalCount = sum(enroll_indicator_totals.values())

        for week in time_range:
            present_data_totals = gendered_text_responses_all_locations(week, ['Yes', 'YES', 'yes'], config_list[0].get('gender'))
            weekly_present_result.append(sum(present_data_totals.values()))
            absent_data_totals = gendered_text_responses_all_locations(week, ['No', 'NO', 'no'], config_list[0].get('gender'))
            total_responses = sum(present_data_totals.values()) + sum(absent_data_totals.values())
            weekly_school_responses.append(total_responses)

            #Loop through locations and determine weekly location absenteeism values
            for location in locations:
                location_enrollment = 0
                location_attendance = 0
                if location.name not in location_absenteeism_percent_values:
                    location_absenteeism_percent_values[location.name] = 0

                if location.id in enroll_indicator_totals:
                    location_enrollment = enroll_indicator_totals[location.id]
                    if location.id in present_data_totals:
                        location_attendance = present_data_totals[location.id]
                    location_absenteeism_percent_values[location.name] += compute_absent_values(location_attendance, location_enrollment)

    else: # compute head teacher absenteeism
        enroll_indicator_totals = get_all_deployed_head_teachers(headteachersSource)
        totalCount = sum(enroll_indicator_totals.values())
        attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])

        for week in time_range:
            present_data_totals, absent_data_totals = get_count_for_yes_no_response_all_locations(attendance_polls, week)
            weekly_present_result.append(sum(present_data_totals.values()))
            schools_that_responded = len(present_data_totals) + len(absent_data_totals)
            weekly_school_responses.append(schools_that_responded)

            #Loop through locations and determine weekly location absenteeism values
            for location in locations:
                location_enrollment = 0
                location_attendance = 0
                if location.name not in location_absenteeism_percent_values:
                    location_absenteeism_percent_values[location.name] = 0

                if location.id in enroll_indicator_totals:
                    location_enrollment = enroll_indicator_totals[location.id]
                    if location.id in present_data_totals:
                        location_attendance = present_data_totals[location.id]
                    location_absenteeism_percent_values[location.name] += compute_absent_values(location_attendance, location_enrollment)

    aggregated_enrollment = [totalCount]
    aggregated_attendance = weekly_present_result
    avg_school_responses.append(sum(weekly_school_responses) / len(time_range))

    # adds average percentage to dict_key
    collective_result[config_list[0].get('collective_dict_key')] = []
    for location, location_absenteeism_percent in location_absenteeism_percent_values.items():
        collective_result[config_list[0].get('collective_dict_key')].append({location : round(location_absenteeism_percent / len(time_range),2)})

    # percentage of schools that responded : add up weekly response average by selected locations and divide by total number of schools
    schoolSource = School.objects.filter(location__in=locations).select_related()
    school_percent = round((sum(avg_school_responses) / len(schoolSource)) * 100, 2)

    chart_results_model = time_data_model(aggregated_enrollment, aggregated_attendance, config_list)

    return collective_result, chart_results_model, school_percent, {}

# Model : get percentage for aggregated results i.e. total enrollment, total attendance by week
def time_data_model(aggregated_enrollment, aggregated_attendance, config_list):
    output = [compute_absent_values(a,sum(aggregated_enrollment)) for a in aggregated_attendance]
    return [{'name' :config_list[0].get('collective_dict_key'), 'data' : output }]


def compute_absenteeism_summary(indicator, locations, get_time=datetime.datetime.now):
    date_weeks = get_week_date(depth=2, get_time=get_time)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    current_week_date_range = date_weeks[0]
    previous_week_date_range = date_weeks[1]

    config_list = get_polls_for_keyword(indicator)
    poll_enrollment = Poll.objects.get(name=config_list[0].get('enrollment_poll')[0])
    poll_attendance = Poll.objects.get(name=config_list[0].get('attendance_poll')[0])

    enrollment_total = get_numeric_data(poll_enrollment, locations, term_range)
    current_week_present_total = get_numeric_data(poll_attendance, locations, current_week_date_range)
    previous_week_present_total= get_numeric_data(poll_attendance, locations, previous_week_date_range)

    absent_current_week = round(compute_absent_values(current_week_present_total, enrollment_total), 2)
    absent_previous_week = round(compute_absent_values(previous_week_present_total, enrollment_total), 2)

    return (absent_current_week, absent_previous_week)


def get_count_for_yes_no_response(polls, locations, time_range):
    yes_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['Yes', 'YES', 'yes'],
                                      contact__reporting_location__in = locations) \
                              .values('contact__reporting_location__id').count()
    no_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['No', 'NO', 'no'],
                                      contact__reporting_location__in = locations) \
                              .values('contact__reporting_location__id').count()
    if not yes_result:
        yes_result = 0
    if not no_result:
        no_result = 0

    return yes_result, no_result

def get_count_for_yes_no_response_all_locations(polls, time_range):
    yes_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['Yes', 'YES', 'yes']) \
                              .values('contact__reporting_location__id').annotate(total = Count('contact__reporting_location__id'))
    no_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['No', 'NO', 'no']) \
                              .values('contact__reporting_location__id').annotate(total = Count('contact__reporting_location__id'))

    yes_totals = [(result['contact__reporting_location__id'], result['total'] or 0) for result in yes_result]
    no_totals = [(result['contact__reporting_location__id'], result['total'] or 0) for result in no_result]

    return collapse(yes_totals), collapse(no_totals)


def get_count_for_yes_no_by_school(polls, School, time_range):
    yes_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['Yes', 'YES', 'yes'],
                                      contact__emisreporter__schools__in=School,) \
                              .values('contact__reporting_location__id').count()
    no_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['No', 'NO', 'no'],
                                      contact__emisreporter__schools__in=School,) \
                              .values('contact__reporting_location__id').count()
    if not yes_result:
        yes_result = 0
    if not no_result:
        no_result = 0

    return yes_result, no_result


#  Function called to populate in-memory Data, reduces on number of db queries per request.
def get_record_collection(locations, time_range):
    try:
        return Response.objects.filter(date__range = time_range,
                                       has_errors = False,
                                       contact__reporting_location__in = locations,
                                       message__direction = 'I').select_related()
    except:
        return [] # Log database errors (or lookup db error exceptions and be specific on exception)

def get_deployed_head_Teachers_by_school(school, locations):
    heads = EmisReporter.objects.filter(reporting_location__in = locations,
                                        schools__in = school,
                                        groups__name = 'SMC')
    return heads.distinct().count()


def get_deployed_head_Teachers(dataSource, locations):
    return get_deployed_head_Teachers_by_school(dataSource.values_list('schools', flat=True), locations)

def get_all_deployed_head_teachers(dataSource):
    heads = EmisReporter.objects.filter(schools__in = dataSource.values_list('schools', flat=True),
                                        groups__name = 'SMC').values('reporting_location') \
                            .order_by().annotate(total = Count('reporting_location'))

    location_totals = [(result['reporting_location'], result['total'] or 0) for result in heads]
    return collapse(location_totals)

def get_all_gender_deployed_head_teachers(dataSource, gender):
    gendered_heads = EmisReporter.objects.filter(schools__in = dataSource.values_list('schools', flat=True),
                                        groups__name = 'SMC', gender = gender,).values('reporting_location') \
                            .order_by().annotate(total = Count('reporting_location'))


    location_totals = [(result['reporting_location'], result['total'] or 0) for result in gendered_heads]
    return collapse(location_totals)

def get_numeric_data(poll, locations, time_range):
    return NumericResponsesFor(poll).forDateRange(time_range).forLocations(locations).total()

def get_numeric_data_for_location(poll, locations, time_range):
    return NumericResponsesFor(poll).forDateRange(time_range).forLocations(locations).groupByLocation()

def get_numeric_data_all_locations(poll, time_range):
    return NumericResponsesFor(poll).forDateRange(time_range).groupByLocation()

def get_numeric_enrollment_data(poll, locations, time_range):
    results = NumericResponsesFor(poll).forDateRange(time_range) \
                                       .forLocations(locations) \
                                       .excludeZeros() \
                                       .groupBySchools()

    return sum(results.values()), results.keys()

def get_numeric_data_by_school(poll, schools, time_range):
    return NumericResponsesFor(poll).forDateRange(time_range) \
                                    .forSchools(schools) \
                                    .groupBySchools() \
                                    .values()

def compute_absent_values(present, enrollment):
    if enrollment == 0:
        return 0
    else:
        return round(((enrollment - present) * 100 / enrollment), 2)

def gendered_text_responses(date_weeks, locations, options, gender):
    poll = Poll.objects.get(name='edtrac_head_teachers_attendance')
    gendered_schools = EmisReporter.objects.filter(reporting_location__in = locations,
                                                   gender = gender,
                                                   groups__name = "Head Teachers") \
                                           .exclude(schools = None) \
                                           .values('reporting_location__id')

    result =  Response.objects.filter(poll = poll,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = date_weeks,
                                      eav_values__value_text__in = options,
                                      contact__reporting_location__id__in = gendered_schools) \
                              .values('contact__reporting_location__id').count()
    return result or 0

def gendered_text_responses_all_locations(date_weeks, options, gender):
    poll = Poll.objects.get(name='edtrac_head_teachers_attendance')
    gendered_schools = EmisReporter.objects.filter(gender = gender,
                                                   groups__name = "Head Teachers") \
                                           .exclude(schools = None) \
                                           .values('reporting_location__id')

    results =  Response.objects.filter(poll = poll,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = date_weeks,
                                      eav_values__value_text__in = options,
                                      contact__reporting_location__id__in = gendered_schools) \
                              .values('contact__reporting_location__id')\
                              .annotate(total = Count('contact__reporting_location__id'))
    location_totals = [(result['contact__reporting_location__id'], result['total'] or 0) for result in results]
    return collapse(location_totals)