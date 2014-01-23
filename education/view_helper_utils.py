from __future__ import division
from education.models import *
from poll.models import Poll
from .reports import *
from education.results import NumericResponsesFor,collapse
from education.absenteeism_view_helper import *


def get_aggregated_report_for_district(locations, time_range, config_list):
    school_absenteeism_percent_values = {}
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
    for config in config_list:
        if config.get('collective_dict_key') in indicator_list:
            enrollment_polls = Poll.objects.filter(name__in=[config.get('enrollment_poll')[0]])
            attendance_polls = Poll.objects.filter(name__in=[config.get('attendance_poll')[0]])

            # get enroll list
            enroll_indicator_totals  = get_numeric_data_all_schools_for_locations(enrollment_polls, locations, term_range)
            totalCount = sum(enroll_indicator_totals.values())
            enrollment_by_indicator[config.get('collective_dict_key')] = totalCount

            for week in time_range:
                attendance_data_totals = get_numeric_data_all_schools_for_locations(attendance_polls, locations, week)
                attend_week_total = sum(attendance_data_totals.values())
                school_with_no_zero_by_indicator[config.get('collective_dict_key')] += len(attendance_data_totals)
                week_percent = compute_absent_values(attend_week_total, totalCount)

                #Loop through schools and determine weekly location absenteeism values
                for school in schoolSource:
                    school_enrollment = 0
                    school_attendance = 0
                    if school.name not in school_absenteeism_percent_values:
                        school_absenteeism_percent_values[school.name] = {}
                    if config.get('collective_dict_key') not in school_absenteeism_percent_values[school.name]:
                        school_absenteeism_percent_values[school.name][config.get('collective_dict_key')] = 0

                    if school.id in enroll_indicator_totals:
                        school_enrollment = enroll_indicator_totals[school.id]
                        if school.id in attendance_data_totals:
                            school_attendance = attendance_data_totals[school.id]
                        school_absenteeism_percent_values[school.name][config.get('collective_dict_key')] += compute_absent_values(school_attendance, school_enrollment)
                    school_absenteeism_percent_values[school.name]['id'] = school.id

                # update attendance by indicator collection with values per week
                for k, v in attendance_by_indicator.items():
                    if k == config.get('collective_dict_key'):
                        for val in v:
                            if val['week'] == week:
                                val['percent'] = week_percent
                                val['present'] = attend_week_total
                                val['enrollment'] = enrollment_by_indicator[config.get('collective_dict_key')]

        else: # Head teachers
            headteachersSource = EmisReporter.objects.filter(reporting_location__in=locations, groups__name="Head Teachers").exclude(schools=None).select_related()
            enroll_indicator_totals = get_count_deployed_head_teachers_by_school(headteachersSource)
            totalCount = sum(enroll_indicator_totals.values())
            enrollment_by_indicator[config.get('collective_dict_key')] = totalCount
            attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])

            for week in time_range:
                present_data_totals, no_data_totals = get_count_for_yes_no_response_by_school(attendance_polls, locations, week)
                schools_that_responded = len(present_data_totals) + len(no_data_totals)

                school_with_no_zero_by_indicator[config.get('collective_dict_key')] += schools_that_responded

                week_percent = compute_absent_values(sum(present_data_totals.values()), totalCount)

                #Loop through schools and determine weekly location absenteeism values
                for school in schoolSource:
                    school_enrollment = 0
                    school_attendance = 0
                    if school.name not in school_absenteeism_percent_values:
                        school_absenteeism_percent_values[school.name] = {}
                    if config.get('collective_dict_key') not in school_absenteeism_percent_values[school.name]:
                        school_absenteeism_percent_values[school.name][config.get('collective_dict_key')] = 0

                    if school.id in enroll_indicator_totals:
                        school_enrollment = enroll_indicator_totals[school.id]
                        if school.id in present_data_totals:
                            school_attendance = present_data_totals[school.id]
                        school_absenteeism_percent_values[school.name][config.get('collective_dict_key')] += compute_absent_values(school_attendance, school_enrollment)

                for k, v in attendance_by_indicator.items():
                    if k == config.get('collective_dict_key'):
                        for val in v:
                            if val['week'] == week:
                                val['percent'] = week_percent
                                val['present'] = sum(present_data_totals.values())
                                val['enrollment'] = enrollment_by_indicator[config.get('collective_dict_key')]

        # adds average percentage to dict_key
        for school, school_absenteeism_percent in school_absenteeism_percent_values.items():
            school_absenteeism_percent_values[school][config.get('collective_dict_key')] = round(school_absenteeism_percent[config.get('collective_dict_key')] / len(time_range),2)

    time_data_model = []
    school_data = {}
    for k,v in school_with_no_zero_by_indicator.items():
        school_data[k] = round((v*100)/len(schoolSource),2)

    ## clean up collective_dict
    #indicator_list = ['P3 Pupils', 'P6 Pupils', 'Teachers','Head Teachers']
    #for k,v in collective_result.items():
    #    for item in indicator_list:
    #        v.setdefault(item,'--')

    # model percentage
    for key, entry in attendance_by_indicator.items():
        data = []
        for item in entry:
            percent = round(compute_absent_values(item['present'], item['enrollment']), 2)
            data.append(percent)
        time_data_model.append({'name': key, 'data': data})

    chart_results_model = time_data_model

    return school_absenteeism_percent_values, chart_results_model, school_data, []


def weekly_school_absenteeism(attendance_data_totals, enroll_indicator_totals, schoolSource,
                                 school_absenteeism_percent_values):
    for school in schoolSource:
        if school.name not in school_absenteeism_percent_values:
            school_absenteeism_percent_values[school.name] = {}
            school_absenteeism_percent_values[school.name]['absenteeism'] = 0

        if school.id in enroll_indicator_totals:
            school_enrollment = enroll_indicator_totals[school.id]
            school_attendance = attendance_data_totals[school.id] if school.id in attendance_data_totals else 0
            school_absenteeism_percent_values[school.name]['absenteeism'] += compute_absent_values(school_attendance,
                                                                                                   school_enrollment)

        school_absenteeism_percent_values[school.name]['id'] = school.id


def get_aggregated_report_for_district_single_indicator(locations, time_range, config_list):
    school_absenteeism_percent_values = {}
    collective_result = {}
    avg_school_responses = []

    # Get term range from settings file (config file)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    
    schoolSource = School.objects.filter(location__in=locations)
    
    # school_absenteeism_percent_values[school][config.get('collective_dict_key')] = round(school_absenteeism_percent[config.get('collective_dict_key')] / len(time_range),2)

    weekly_present_result = []
    weekly_school_responses = []

    if config_list[0].get('collective_dict_key') not in  ['Male Head Teachers', 'Female Head Teachers', 'Head Teachers']:
        
        enrollment_polls = Poll.objects.filter(name__in=config_list[0].get('enrollment_poll'))
        attendance_polls = Poll.objects.filter(name__in=config_list[0].get('attendance_poll'))

        # get total enrollment numbers
        enroll_indicator_totals  = get_numeric_data_all_schools_for_locations(enrollment_polls, locations, term_range)
        totalCount = sum(enroll_indicator_totals.values())

        for week in time_range:
            attendance_data_totals = get_numeric_data_all_schools_for_locations(attendance_polls, locations, week)
            weekly_present_result.append(sum(attendance_data_totals.values()))
            
            weekly_school_absenteeism(attendance_data_totals, enroll_indicator_totals, schoolSource,
                                         school_absenteeism_percent_values)

    elif config_list[0].get('collective_dict_key') in ['Male Head Teachers', 'Female Head Teachers']:
        headteachersSource = EmisReporter.objects.filter(reporting_location__in=locations, groups__name="Head Teachers").exclude(schools=None).select_related()
        enroll_indicator_totals = get_count_deployed_head_teachers_by_school(headteachersSource)
        totalCount = sum(enroll_indicator_totals.values())

        for week in time_range:
            present_data_totals_schools = gendered_text_responses_by_school(week, locations, ['Yes', 'YES', 'yes'], config_list[0].get('gender'))
            weekly_present_result.append(sum(present_data_totals_schools.values()))
            absent_data_totals_schools = gendered_text_responses_by_school(week, locations, ['No', 'NO', 'no'], config_list[0].get('gender'))
            schools_that_responded = len(present_data_totals_schools) + len(absent_data_totals_schools)
            weekly_school_responses.append(schools_that_responded)

            weekly_school_absenteeism(present_data_totals_schools, enroll_indicator_totals, schoolSource,
                                         school_absenteeism_percent_values)
    
    else:
        headteachersSource = EmisReporter.objects.filter(reporting_location__in=locations, groups__name="Head Teachers").exclude(schools=None).select_related()
        enroll_indicator_totals = get_count_deployed_head_teachers_by_school(headteachersSource)
        totalCount = sum(enroll_indicator_totals.values())
        attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])

        for week in time_range:
            present_data_totals, no_data_totals = get_count_for_yes_no_response_by_school(attendance_polls, locations, week)
            weekly_present_result.append(sum(present_data_totals.values()))
            schools_that_responded = len(present_data_totals) + len(no_data_totals)
            weekly_school_responses.append(schools_that_responded)

            weekly_school_absenteeism(present_data_totals, enroll_indicator_totals, schoolSource,
                                         school_absenteeism_percent_values)

    aggregated_enrollment = [totalCount]
    aggregated_attendance = weekly_present_result
    avg_school_responses.append(sum(weekly_school_responses) / len(time_range))

    # adds average percentage to dict_key
    indicator = config_list[0].get('collective_dict_key');
    collective_result = {}
    for school_name, school_dict in school_absenteeism_percent_values.items():
        collective_result[school_name] = { indicator: (round(school_dict['absenteeism'] / len(time_range),2)) , 'school_id': school_dict['id'] }

    # percentage of schools that responded : add up weekly response average by selected locations and divide by total number of schools
    schoolSource = School.objects.filter(location__in=locations).select_related()
    school_percent = round((sum(avg_school_responses) / len(schoolSource)) * 100, 2)

    chart_results_model = time_data_model(aggregated_enrollment, aggregated_attendance, config_list)

    return collective_result, chart_results_model, school_percent, {}

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

    for config in config_list:
        if config.get('collective_dict_key') in indicator_list:
            enrollment_polls = Poll.objects.filter(name__in = [config.get('enrollment_poll')[0]])
            attendance_polls = Poll.objects.filter(name__in = [config.get('attendance_poll')[0]])
            # get both enroll list and schools that responded
            enroll_indicator_totals  = get_numeric_data_for_location(enrollment_polls, locations, term_range)
            totalCount = sum(enroll_indicator_totals.values())
            enrollment_by_indicator[config.get('collective_dict_key')] = totalCount

            weekly_school_count = []
            for week in time_range:
                # get attendance total for week by indicator from config file
                attendance_data_totals = get_numeric_data_for_location(attendance_polls, locations, week)
                attend_week_total = sum(attendance_data_totals.values())
                # get schools that Responded
                schools_that_responded_data = get_numeric_data_all_schools_for_locations(attendance_polls, locations, week)
                schools_that_responded = sum(schools_that_responded_data.values())
                week_percent = compute_absent_values(attend_week_total, totalCount)
                weekly_school_count.append(schools_that_responded)

                #Loop through locations and determine weekly location absenteeism values
                for location in locations:
                    location_enrollment = 0
                    if location.name not in location_absenteeism_percent_values:
                        location_absenteeism_percent_values[location.name] = {}
                    if config.get('collective_dict_key') not in location_absenteeism_percent_values[location.name]:
                        location_absenteeism_percent_values[location.name][config.get('collective_dict_key')] = 0

                    if location.id in enroll_indicator_totals:
                        location_enrollment = enroll_indicator_totals[location.id]
                        location_attendance = attendance_data_totals[location.id] if location.id in attendance_data_totals else 0
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
            enroll_indicator_totals = get_count_deployed_head_teachers_by_location(headteachersSource)
            totalCount = sum(enroll_indicator_totals.values())
            enrollment_by_indicator[config.get('collective_dict_key')] = totalCount
            attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])

            weekly_school_count = []
            for week in time_range:
                present_data_totals, absent_data_totals = get_count_for_yes_no_response_by_location(attendance_polls, locations, week)
                yes_schools, no_schools = get_count_for_yes_no_response_by_school(attendance_polls, locations, week)
                schools_that_responded = len(yes_schools) + len(no_schools)

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
                        location_attendance = present_data_totals[location.id] if location.id in present_data_totals else 0
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
        enroll_indicator_totals  = get_numeric_data_for_location(enrollment_polls, locations, term_range)
        totalCount = sum(enroll_indicator_totals.values())

        for week in time_range:
            # get attendance total for week by indicator from config file
            attendance_data_totals = get_numeric_data_for_location(attendance_polls, locations, week)
            weekly_present_result.append(sum(attendance_data_totals.values()))
            # get number of schools that Responded
            schools_that_responded_data = get_numeric_data_all_schools_for_locations(attendance_polls, locations, week)
            schools_that_responded = sum(schools_that_responded_data.values())
            weekly_school_responses.append(schools_that_responded)

            #Loop through locations and determine weekly location absenteeism values
            for location in locations:
                location_enrollment = 0
                location_attendance = 0
                if location.name not in location_absenteeism_percent_values:
                    location_absenteeism_percent_values[location.name] = 0

                if location.id in enroll_indicator_totals:
                    location_enrollment = enroll_indicator_totals[location.id]
                    location_attendance = attendance_data_totals[location.id] if location.id in attendance_data_totals else 0
                    location_absenteeism_percent_values[location.name] += compute_absent_values(location_attendance, location_enrollment)

    elif config_list[0].get('collective_dict_key') in ['Male Head Teachers', 'Female Head Teachers']:
        enroll_indicator_totals = get_count_gender_deployed_head_teachers_by_location(headteachersSource, config_list[0].get('gender'))
        totalCount = sum(enroll_indicator_totals.values())

        for week in time_range:
            present_data_totals = gendered_text_responses_by_location(week, locations,  ['Yes', 'YES', 'yes'], config_list[0].get('gender'))
            weekly_present_result.append(sum(present_data_totals.values()))
            absent_data_totals = gendered_text_responses_by_location(week, locations, ['No', 'NO', 'no'], config_list[0].get('gender'))
            total_responses = sum(present_data_totals.values()) + sum(absent_data_totals.values())

            present_data_totals_schools = gendered_text_responses_by_school(week, locations, ['Yes', 'YES', 'yes'], config_list[0].get('gender'))
            absent_data_totals_schools = gendered_text_responses_by_school(week, locations, ['No', 'NO', 'no'], config_list[0].get('gender'))
            schools_that_responded = len(present_data_totals_schools) + len(absent_data_totals_schools)
            weekly_school_responses.append(schools_that_responded)

            #Loop through locations and determine weekly location absenteeism values
            for location in locations:
                location_enrollment = 0
                location_attendance = 0
                if location.name not in location_absenteeism_percent_values:
                    location_absenteeism_percent_values[location.name] = 0

                if location.id in enroll_indicator_totals:
                    location_enrollment = enroll_indicator_totals[location.id]
                    location_attendance = present_data_totals[location.id] if location.id in present_data_totals else 0
                    location_absenteeism_percent_values[location.name] += compute_absent_values(location_attendance, location_enrollment)

    else: # compute head teacher absenteeism
        enroll_indicator_totals = get_count_deployed_head_teachers_by_location(headteachersSource)
        totalCount = sum(enroll_indicator_totals.values())
        attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])

        for week in time_range:
            present_data_totals, absent_data_totals = get_count_for_yes_no_response_by_location(attendance_polls, locations, week)
            weekly_present_result.append(sum(present_data_totals.values()))

            yes_schools, no_schools = get_count_for_yes_no_response_by_school(attendance_polls, locations, week)
            schools_that_responded = len(yes_schools) + len(no_schools)
            weekly_school_responses.append(schools_that_responded)

            #Loop through locations and determine weekly location absenteeism values
            for location in locations:
                location_enrollment = 0
                location_attendance = 0
                if location.name not in location_absenteeism_percent_values:
                    location_absenteeism_percent_values[location.name] = 0

                if location.id in enroll_indicator_totals:
                    location_enrollment = enroll_indicator_totals[location.id]
                    location_attendance = present_data_totals[location.id] if location.id in present_data_totals else 0
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
    poll_enrollment = Poll.objects.filter(name=config_list[0].get('enrollment_poll')[0])
    poll_attendance = Poll.objects.filter(name=config_list[0].get('attendance_poll')[0])

    enrollment_total = get_numeric_data(poll_enrollment, locations, term_range)
    current_week_present_total = get_numeric_data(poll_attendance, locations, current_week_date_range)
    previous_week_present_total= get_numeric_data(poll_attendance, locations, previous_week_date_range)

    absent_current_week = round(compute_absent_values(current_week_present_total, enrollment_total), 2)
    absent_previous_week = round(compute_absent_values(previous_week_present_total, enrollment_total), 2)

    return (absent_current_week, absent_previous_week)


def get_count_for_yes_no_response_by_location(polls, locations, time_range):
    yes_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['Yes', 'YES', 'yes'],
                                      contact__reporting_location__in = locations) \
                              .values('contact__reporting_location__id').annotate(total = Count('contact__reporting_location__id'))
    no_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['No', 'NO', 'no'],
                                      contact__reporting_location__in = locations) \
                              .values('contact__reporting_location__id').annotate(total = Count('contact__reporting_location__id'))

    yes_totals = [(result['contact__reporting_location__id'], result['total'] or 0) for result in yes_result]
    no_totals = [(result['contact__reporting_location__id'], result['total'] or 0) for result in no_result]

    return collapse(yes_totals), collapse(no_totals)


def get_count_for_yes_no_response_by_school(polls, locations, time_range):
    yes_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['Yes', 'YES', 'yes'],
                                      contact__reporting_location__in = locations) \
                              .values('contact__emisreporter__schools').annotate(total = Count('contact__emisreporter__schools'))
    no_result =  Response.objects.filter(poll__in = polls,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = time_range,
                                      eav_values__value_text__in = ['No', 'NO', 'no'],
                                      contact__reporting_location__in = locations) \
                              .values('contact__emisreporter__schools').annotate(total = Count('contact__emisreporter__schools'))

    yes_totals = [(result['contact__emisreporter__schools'], result['total'] or 0) for result in yes_result]
    no_totals = [(result['contact__emisreporter__schools'], result['total'] or 0) for result in no_result]

    return collapse(yes_totals), collapse(no_totals)

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
                                        groups__name = 'Head Teachers')
    return heads.distinct().count()


def get_deployed_head_Teachers(dataSource, locations):
    return get_deployed_head_Teachers_by_school(dataSource.values_list('schools', flat=True), locations)

def get_count_deployed_head_teachers_by_location(dataSource):
    heads = EmisReporter.objects.filter(schools__in = dataSource.values_list('schools', flat=True),
                                        groups__name = 'Head Teachers').values('reporting_location') \
                            .order_by().annotate(total = Count('reporting_location'))

    location_totals = [(result['reporting_location'], result['total'] or 0) for result in heads]
    return collapse(location_totals)

def get_count_deployed_head_teachers_by_school(dataSource):
    heads = EmisReporter.objects.filter(schools__in = dataSource.values_list('schools', flat=True),
                                        groups__name = 'Head Teachers').values('schools') \
                            .order_by().annotate(total = Count('schools'))

    school_totals = [(result['schools'], result['total'] or 0) for result in heads]
    return collapse(school_totals)

def get_count_gender_deployed_head_teachers_by_location(dataSource, gender):
    gendered_heads = EmisReporter.objects.filter(schools__in = dataSource.values_list('schools', flat=True),
                                        groups__name = 'Head Teachers', gender = gender,).values('reporting_location') \
                            .order_by().annotate(total = Count('reporting_location'))

    location_totals = [(result['reporting_location'], result['total'] or 0) for result in gendered_heads]
    return collapse(location_totals)

def get_numeric_data(polls, locations, time_range):
    return NumericResponsesFor(polls).forDateRange(time_range).forLocations(locations).total()

def get_numeric_data_for_location(polls, locations, time_range):
    return NumericResponsesFor(polls).forDateRange(time_range).forLocations(locations).groupByLocation()

def get_numeric_enrollment_data(polls, locations, time_range):
    results = NumericResponsesFor(polls).forDateRange(time_range) \
                                       .forLocations(locations) \
                                       .excludeZeros() \
                                       .groupBySchools()

    return sum(results.values()), results.keys()

def get_numeric_data_by_school(polls, schools, time_range):
    return NumericResponsesFor(polls).forDateRange(time_range) \
                                    .forSchools(schools) \
                                    .groupBySchools() \
                                    .values()


def get_numeric_data_all_schools_for_locations(polls, locations, time_range):
    return NumericResponsesFor(polls).forDateRange(time_range) \
                                    .forLocations(locations) \
                                    .groupBySchools()

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

def gendered_text_responses_by_location(date_weeks, locations, options, gender):
    poll = Poll.objects.get(name='edtrac_head_teachers_attendance')
    gendered_schools = EmisReporter.objects.filter(reporting_location__in = locations,
                                                   gender = gender,
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

def gendered_text_responses_by_school(date_weeks, locations, options, gender):
    poll = Poll.objects.get(name='edtrac_head_teachers_attendance')
    gendered_schools = EmisReporter.objects.filter(reporting_location__in = locations,
                                                   gender = gender,
                                                   groups__name = "Head Teachers") \
                                           .exclude(schools = None) \
                                           .values('reporting_location__id')

    results =  Response.objects.filter(poll = poll,
                                      has_errors = False,
                                      message__direction = 'I',
                                      date__range = date_weeks,
                                      eav_values__value_text__in = options,
                                      contact__reporting_location__id__in = gendered_schools) \
                              .values('contact__emisreporter__schools')\
                              .annotate(total = Count('contact__emisreporter__schools'))
    school_totals = [(result['contact__emisreporter__schools'], result['total'] or 0) for result in results]
    return collapse(school_totals)