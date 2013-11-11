from __future__ import division
import re
#from .forms import *
from education.models import *
from poll.models import Poll
from .reports import *
from education.absenteeism_view_helper import *

def get_aggregated_report_for_district(locations, time_range, config_list,report_mode = None):
    collective_result = {}
    chart_data = []
    head_teacher_set = []
    tmp_data = []
    school_report = []
    computation_logger = {}
    computation_logger_headTeachers = {}
    school_with_no_zero_result = []
    school_with_no_zero_by_indicator = {}
    schools_by_location = []
    high_chart_tooltip = []
    attendance_total = [] # used for logging present values extracted from incoming messages (don't delete)
    percent_by_indicator = {} # used for logging percent values extracted from incoming messages (don't delete)
    enrollment_by_indicator = {}
    attendance_by_indicator = {}

    # Get term range from settings file (config file)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    indicator_list = ['P3 Pupils', 'P6 Pupils', 'Teachers']
    # Initialize chart data and school percent List / dict holder
    for indicator in indicator_list:
        chart_data.append({indicator: [0] * len(time_range)})
        school_report.append({indicator: [0] * len(time_range)})
        high_chart_tooltip.append({indicator: []})
        enrollment_by_indicator[indicator] = 0
        attendance_by_indicator[indicator] = []
        percent_by_indicator[indicator] = []
        school_with_no_zero_by_indicator[indicator] = 0

    chart_data.append({'Head Teachers': [0] * len(time_range)})
    school_report.append({'Head Teachers': [0] * len(time_range)})
    high_chart_tooltip.append({'Head Teachers': []})
    enrollment_by_indicator['Head Teachers'] = 0
    attendance_by_indicator['Head Teachers'] = []
    school_with_no_zero_by_indicator['Head Teachers'] = 0

    # update tooltip list with current date ranges (high chart x - axis values)
    for _date in time_range:
        for tip in high_chart_tooltip:
            for k, v in tip.items():
                v.append({'date_range': _date, 'enrollment': 0, 'present': 0})

    # update attendance by indicator with current date ranges (enable present computation along date x-axis)
    for _date in time_range:
        for k, v in attendance_by_indicator.items():
            v.append({'week': _date, 'present': 0, 'enrollment': 0, 'percent': 0})

    if locations:
        headteachersSource = EmisReporter.objects.filter(reporting_location__in=locations,groups__name="Head Teachers").exclude(schools=None).select_related()
        schoolSource = School.objects.filter(location__in=locations)
        for school in schoolSource:
            has_enrollment = False
            config_set_result = {}
            school_logger = []
            for config in config_list:
                if config.get('collective_dict_key') in indicator_list:
                    enrollment_polls = Poll.objects.filter(name__in=[config.get('enrollment_poll')[0]])
                    attendance_polls = Poll.objects.filter(name__in=[config.get('attendance_poll')[0]])
                    enroll_data = get_numeric_data_by_school(enrollment_polls,[school],term_range)
                    enrollment_by_indicator[config.get('collective_dict_key')] += sum(enroll_data)
                    enroll_indicator_total = sum(enroll_data)
                    week_count = 0
                    weekly_results = []
                    week_logger = []
                    for week in time_range:
                        week_count += 1
                        attend_week_total = sum(get_numeric_data_by_school(attendance_polls, [school], week))
                        week_percent = compute_absent_values(attend_week_total, enroll_indicator_total)
                        weekly_results.append(week_percent)
                        week_logger.append({'present' :attend_week_total, 'enrollment' : enroll_indicator_total, 'percent' : week_percent})

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
                        school_logger.append({config.get('collective_dict_key') :week_logger })


                        for item in chart_data:
                            for k, v in item.items():
                                if k == config.get('collective_dict_key'):
                                    item[k] = [sum(a) for a in zip(*[v, weekly_results])]
                else: # Head teachers
                    deployedHeadTeachers = get_deployed_head_Teachers_by_school([school],locations)
                    enrollment_by_indicator[config.get('collective_dict_key')] += deployedHeadTeachers
                    attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])
                    weekly_present = []
                    weekly_percent = []
                    week_logger = []
                    for week in time_range:
                        present, absent = get_count_for_yes_no_by_school(attendance_polls,[school], week)
                        week_percent = compute_absent_values(present, deployedHeadTeachers)
                        weekly_present.append(present)
                        weekly_percent.append(week_percent)
                        week_logger.append({'present' :present,'deployed' : deployedHeadTeachers, 'percent' : week_percent})

                        if deployedHeadTeachers == 1:
                            for k, v in attendance_by_indicator.items():
                                if k == config.get('collective_dict_key'):
                                    for val in v:
                                        if val['week'] == week:
                                            val['percent'] = val['percent'] + week_percent
                                            val['present'] = val['present'] + attend_week_total
                                            val['enrollment'] = enrollment_by_indicator[config.get('collective_dict_key')]


                    if deployedHeadTeachers ==1:
                        school_with_no_zero_by_indicator[config.get('collective_dict_key')] +=1
                        computation_logger_headTeachers[school.name] = week_logger
                        has_enrollment = True
                        percent_absent = compute_absent_values(sum(weekly_present) / len(time_range), deployedHeadTeachers)
                        config_set_result[config.get('collective_dict_key')] = round(percent_absent, 2)
                        for item in chart_data:
                            for k, v in item.items():
                                if k == 'Head Teachers':
                                    item[k] = [sum(a) for a in zip(*[v, weekly_percent])]

            if has_enrollment == True:
                collective_result[school.name] = config_set_result
                computation_logger[school.name] = school_logger
                school_with_no_zero_result.append(school)

    time_data_model1 = []
    time_data_model2 = []
    chart_results_model = []
    tooltip = []
    school_data = {}

    for k,v in school_with_no_zero_by_indicator.items():
        school_data[k] = round((v*100)/len(schoolSource),2)

    # clean up collective_dict
    indicator_list = ['P3 Pupils', 'P6 Pupils', 'Teachers','Head Teachers']
    for k,v in collective_result.items():
        for item in indicator_list:
            v.setdefault(item,'--')

    # model 1 average of percentage
    for item in chart_data:
        for k, v in item.items():
            output = []
            avg_percent = 0
            for val in v:
                if len(school_with_no_zero_result) > 0 and val > 0:
                    avg_percent = round(val / school_with_no_zero_by_indicator[k], 2)
                output.append(avg_percent)
            time_data_model1.append({'name': k, 'data': output})

    # model 2 percentage
    for key, entry in attendance_by_indicator.items():
        data = []
        for item in entry:
            percent = round(compute_absent_values(item['present'], item['enrollment']), 2)
            data.append(percent)
        time_data_model2.append({'name': key, 'data': data})

    if report_mode == None:
        chart_results_model = time_data_model1
        report_mode = 'average'
    elif report_mode == 'average':
        chart_results_model = time_data_model1
    elif report_mode == 'percent':
        chart_results_model = time_data_model2

    return collective_result, chart_results_model, school_data, tooltip,report_mode


def get_aggregated_report_data(locations, time_range, config_list,report_mode = None):
    collective_result = {}
    chart_data = []
    head_teacher_set = []
    tmp_data = []
    school_report = []
    computation_logger = []
    location_with_no_zero_result = []
    schools_by_location = []
    high_chart_tooltip = []
    attendance_total = [] # used for logging present values extracted from incoming messages (don't delete)
    percent_by_indicator = {} # used for logging percent values extracted from incoming messages (don't delete)
    enrollment_by_indicator = {}
    attendance_by_indicator = {}

    # Get term range from settings file (config file)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]

    headteachersSource = EmisReporter.objects.filter(reporting_location__in=locations,
                                                     groups__name="Head Teachers").exclude(
        schools=None).select_related()
    schoolSource = School.objects.filter(location__in=locations).select_related()
    indicator_list = ['P3 Pupils', 'P6 Pupils', 'Teachers']
    schools_total = len(schoolSource)
    # Initialize chart data and school percent List / dict holder
    for indicator in indicator_list:
        chart_data.append({indicator: [0] * len(time_range)})
        school_report.append({indicator: [0] * len(time_range)})
        high_chart_tooltip.append({indicator: []})
        enrollment_by_indicator[indicator] = 0
        attendance_by_indicator[indicator] = []
        percent_by_indicator[indicator] = []

    chart_data.append({'Head Teachers': [0] * len(time_range)})
    school_report.append({'Head Teachers': [0] * len(time_range)})
    high_chart_tooltip.append({'Head Teachers': []})
    enrollment_by_indicator['Head Teachers'] = 0
    attendance_by_indicator['Head Teachers'] = []

    # update tooltip list with current date ranges (high chart x - axis values)
    for _date in time_range:
        for tip in high_chart_tooltip:
            for k, v in tip.items():
                v.append({'date_range': _date, 'enrollment': 0, 'present': 0})

    # update attendance by indicator with current date ranges (enable present computation along date x-axis)
    for _date in time_range:
        for k, v in attendance_by_indicator.items():
            v.append({'week': _date, 'present': 0, 'enrollment': 0, 'percent': 0})

    for location in locations:
        config_set_result = {}
        has_enrollment = False
        # get school in current location
        schools_in_location = schoolSource.filter(location__in=[location])

        schools_by_location.append({'location': location, 'school_count': len(schools_in_location)})
        for config in config_list:
            if config.get('collective_dict_key') in indicator_list:
                enrollment_polls = Poll.objects.filter(name__in=[config.get('enrollment_poll')[0]])
                attendance_polls = Poll.objects.filter(name__in=[config.get('attendance_poll')[0]])
                # get both enroll list and schools that responded
                enroll_data, responsive_schools = get_numeric_enrollment_data(enrollment_polls,[location],term_range)
                if not is_empty(enroll_data):
                    has_enrollment = True
                enroll_indicator_total = sum(enroll_data)
                enrollment_by_indicator[config.get('collective_dict_key')] += enroll_indicator_total

                absenteeism_percent = 0
                week_count = 0
                weekly_results = []
                weekly_results_log = []
                weekly_school_count = []

                for week in time_range:
                    week_count += 1
                    # get attendance total for week by indicator from config file
                    attend_week_total = sum(get_numeric_data_by_school(attendance_polls, responsive_schools, week))
                    attendance_total.append(attend_week_total)
                    # get schools that Responded
                    schools_that_responded = len(get_numeric_data_by_school(attendance_polls, schools_in_location, week))
                    week_percent = compute_absent_values(attend_week_total, enroll_indicator_total)
                    absenteeism_percent += week_percent
                    weekly_school_count.append(schools_that_responded)
                    weekly_results.append(week_percent)
                    weekly_results_log.append(week_percent)
                    weekly_results_log.append('P' + str(attend_week_total))
                    weekly_results_log.append('E' + str(enroll_indicator_total))


                    # update attendance by indicator collection with values per week
                    for k, v in attendance_by_indicator.items():
                        if k == config.get('collective_dict_key'):
                            for val in v:
                                if val['week'] == week:
                                    val['percent'] = val['percent'] + week_percent
                                    val['present'] = val['present'] + attend_week_total
                                    val['enrollment'] = enrollment_by_indicator[config.get('collective_dict_key')]

                    # update tooltip collection with new values through interations
                    for tooltip in high_chart_tooltip:
                        for k, v in tooltip.items():
                            if k == config.get('collective_dict_key'):
                                for values in v:
                                    if values['date_range'] == week:
                                        values['present'] = values['present'] + attend_week_total
                                        values['enrollment'] = enrollment_by_indicator[
                                            config.get('collective_dict_key')]

                percent_by_indicator[config.get('collective_dict_key')].append(weekly_results_log)
                # update high chart data collection with new values
                for item in chart_data:
                    for k, v in item.items():
                        if k == config.get('collective_dict_key'):
                            item[k] = [sum(a) for a in zip(*[v, weekly_results])]

                # update school reporting summary collection
                for item in school_report:
                    for k, v in item.items():
                        if k == config.get('collective_dict_key'):
                            item[k] = [sum(a) for a in zip(*[v, weekly_school_count])]

                # adds average percentage to dict_key
                config_set_result[config.get('collective_dict_key')] = round(absenteeism_percent / len(time_range),2)

            else: # used to compute head teachers absenteeism
                deployedHeadTeachers = get_deployed_head_Teachers(headteachersSource, [location])
                enrollment_by_indicator[config.get('collective_dict_key')] += deployedHeadTeachers
                attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])
                weekly_present = []
                weekly_percent = []
                weekly_school_count = []
                week_logger = []
                for week in time_range:
                    present, absent = get_count_for_yes_no_response(attendance_polls, [location], week)
                    schools_that_responded = len(
                        get_numeric_data_by_school(attendance_polls, schools_in_location, week))
                    week_percent = compute_absent_values(present, deployedHeadTeachers)
                    weekly_present.append(present)
                    weekly_percent.append(week_percent)
                    weekly_school_count.append(schools_that_responded)
                    week_logger.append({'present' :present,'deployed' : deployedHeadTeachers, 'percent' : week_percent})
                    # update attendance by indicator collection with values per week
                    for k, v in attendance_by_indicator.items():
                        if k == config.get('collective_dict_key'):
                            for val in v:
                                if val['week'] == week:
                                    val['percent'] = val['percent'] + week_percent
                                    val['present'] = val['present'] + present
                                    val['enrollment'] = enrollment_by_indicator[config.get('collective_dict_key')]
                                    # update tooltip collection with new values through interations
                    for tooltip in high_chart_tooltip:
                        for k, v in tooltip.items():
                            if k == config.get('collective_dict_key'):
                                for values in v:
                                    if values['date_range'] == week:
                                        values['present'] = values['present'] + present
                                        values['enrollment'] = enrollment_by_indicator[
                                            config.get('collective_dict_key')]

                percent_absent = compute_absent_values(sum(weekly_present) / len(time_range), deployedHeadTeachers)
                computation_logger.append({location : week_logger})
                head_teacher_set.append(
                    {'Location': location, 'present': weekly_present, 'deployed': deployedHeadTeachers,
                     'percent': percent_absent})
                config_set_result[config.get('collective_dict_key')] = round(percent_absent, 2)
                for item in chart_data:
                    for k, v in item.items():
                        if k == 'Head Teachers':
                            item[k] = [sum(a) for a in zip(*[v, weekly_percent])]
                for item in school_report:
                    for k, v in item.items():
                        if k == config.get('collective_dict_key'):
                            item[k] = [sum(a) for a in zip(*[v, weekly_school_count])]

        if has_enrollment == True:
            location_with_no_zero_result.append(location)
            collective_result[location.name] = config_set_result

    time_data_model1 = []
    school_data = {}
    tip_for_time_data1 = []

    # Absenteeism Computation Model 1 : problem : some locations return very high negative values, makes the dashboard look messy (but represent actual state of data)
    # get averages to display on chart (formula : divide the aggregated percent value along each week for each indicator in each location and divide by location count )
    for item in chart_data:
        for k, v in item.items():
            output = []
            for val in v:
                avg_percent = round(val / len(location_with_no_zero_result), 2)
                output.append(avg_percent)
            time_data_model1.append({'name': k, 'data': output})

    #absenteeism computation model 2 : problem : hides some facts a long each location and computes at global count across all locations
    # get sum of present values for all locations, sum of  enrollment values for all locations, all accross each indicator
    time_data_model2 = []
    tip_for_time_data2 = []
    for key, entry in attendance_by_indicator.items():
        data = []
        tip = []
        for item in entry:
            percent = round(compute_absent_values(item['present'], item['enrollment']), 2)
            tip.append({'enrollment': item['enrollment'], 'present': item['present'], 'percent': percent})
            data.append(percent)
        time_data_model2.append({'name': key, 'data': data})
        tip_for_time_data2.append({'name': key, 'tooltip': tip})

    # get school response average
    for item in school_report:
        for k, v in item.items():
            output = []
            for val in v:
                output.append(val)
                school_data[k] = round(((sum(output) / len(time_range)) / schools_total) * 100, 2)

    tooltip = []
    chart_results_model = {}
    if report_mode == None:
        chart_results_model = time_data_model1
        report_mode = 'average'
    elif report_mode == 'average':
        chart_results_model = time_data_model1
    elif report_mode == 'percent':
        chart_results_model = time_data_model2

    return collective_result, chart_results_model, school_data, tooltip,report_mode



def get_aggregated_report_data_single_indicator(locations, time_range, config_list,report_mode = None):
    collective_result = {}
    computation_logger = [] # used for logging values used in computation (don't delete)
    location_with_no_zero_result = []
    absenteeism_percent_by_week = {}
    attendance_total_by_week = {}
    avg_percent_by_location = []
    avg_school_responses = []
    total_responsive_schools = []
    enrollment_by_location = []
    aggregated_enrollment = []
    aggregated_attendance = []

    # Get term range from settings file (config file)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    headteachersSource = EmisReporter.objects.filter(reporting_location__in=locations,groups__name="Head Teachers").exclude(schools=None).select_related()
    schoolSource = School.objects.filter(location__in=locations).select_related()

    week_position = 0
    for _date in time_range:
        absenteeism_percent_by_week[week_position] = 0
        attendance_total_by_week[week_position] = 0
        week_position += 1

    for location in locations:
        # get school in current location
        schools_in_location = schoolSource.filter(location__in=[location])
        weekly_percent_results = []
        weekly_present_result = []
        week_position = 0
        weekly_school_responses = []

        if config_list[0].get('collective_dict_key') != 'Head Teachers':
            enrollment_polls = Poll.objects.filter(name__in=config_list[0].get('enrollment_poll'))
            attendance_polls = Poll.objects.filter(name__in=config_list[0].get('attendance_poll'))
            enroll_data, responsive_schools = get_numeric_enrollment_data(enrollment_polls,[location],term_range)
            enroll_indicator_total = sum(enroll_data)
            enrollment_by_location.append(enroll_indicator_total)
            for week in time_range:
                # get attendance total for week by indicator from config file
                attend_week_total = sum(get_numeric_data_by_school(attendance_polls,responsive_schools,week))
                weekly_present_result.append(attend_week_total)
                # get schools that Responded
                # suspect (can be replaced by count of response values on weekly attendance above)
                schools_that_responded = len(get_numeric_data_by_school(attendance_polls, schools_in_location, week))
                week_percent = compute_absent_values(attend_week_total, enroll_indicator_total)
                weekly_percent_results.append(week_percent)
                absenteeism_percent_by_week[week_position] += week_percent
                weekly_school_responses.append(schools_that_responded)
                attendance_total_by_week[week_position] += attend_week_total
                week_position += 1
            if sum(weekly_percent_results) != 0:
                aggregated_enrollment.append(enroll_indicator_total)
                if is_empty(aggregated_attendance):
                    aggregated_attendance = weekly_present_result
                else:
                    aggregated_attendance = [sum(z) for z in zip(*[aggregated_attendance,weekly_present_result])]
                location_with_no_zero_result.append(location)
                avg_percent_by_location.append({location.name: round(sum(weekly_percent_results) / len(time_range),2)})

            avg_school_responses.append(sum(weekly_school_responses) / len(time_range))
            computation_logger.append({location: {'present': weekly_present_result, 'percent': weekly_percent_results,
                                                  'enrollment': enroll_indicator_total}})
        else: # compute head teacher absenteeism
            deployedHeadTeachers = get_deployed_head_Teachers(headteachersSource, [location])
            attendance_polls = Poll.objects.filter(name__in=['edtrac_head_teachers_attendance'])

            for week in time_range:
                present, absent = get_count_for_yes_no_response(attendance_polls, [location], week)
                schools_that_responded = len(get_numeric_data_by_school(attendance_polls, schools_in_location, week))
                week_percent = compute_absent_values(present, deployedHeadTeachers)
                weekly_percent_results.append(week_percent)
                weekly_present_result.append(present)
                weekly_school_responses.append(schools_that_responded)
                absenteeism_percent_by_week[week_position] += week_percent
                week_position += 1
            if sum(weekly_percent_results) != 0: # eliminate districts that have nothing to present
                location_with_no_zero_result.append(location)
                avg_percent_by_location.append({location.name: round(sum(weekly_percent_results) / len(time_range),2)})
            avg_school_responses.append(sum(weekly_school_responses) / len(time_range))
            computation_logger.append({location: {'present': weekly_present_result, 'percent': weekly_percent_results,
                                                  'enrollment': deployedHeadTeachers}})

    collective_result[config_list[0].get('collective_dict_key')] = avg_percent_by_location

    # percentage of schools that responded : add up weekly response average by selected locations and divide by total number of schools
    school_percent = round((sum(avg_school_responses) / len(schoolSource)) * 100, 2)
    #Model 1 : Average percentage computation. get total of averages by location by indicator and divide by total locations
    time_data_model1 = []
    output = []
    for k, v in absenteeism_percent_by_week.items():
        output.append(round(v / len(location_with_no_zero_result), 2))
    time_data_model1.append({'name': config_list[0].get('collective_dict_key'), 'data': output})

    # model 2 : get percentage for aggregated results i.e. total enrollment, total attendance by week
    time_data_model2 = []
    output =   [compute_absent_values(a,sum(aggregated_enrollment)) for a in aggregated_attendance]
    time_data_model2.append({'name' :config_list[0].get('collective_dict_key'), 'data' : output })


    tooltip = {}
    chart_results_model = {}
    if report_mode == None:
        chart_results_model = time_data_model1
        report_mode = 'average'
    elif report_mode == 'average':
        chart_results_model = time_data_model1
    elif report_mode == 'percent':
        chart_results_model = time_data_model2

    return collective_result, chart_results_model, school_percent,tooltip,report_mode

def compute_absenteeism_summary(indicator, locations):
    date_weeks = get_week_date(depth=2)
    term_range = [getattr(settings, 'SCHOOL_TERM_START'), getattr(settings, 'SCHOOL_TERM_END')]
    current_week_date_range = date_weeks[0]
    previous_week_date_range = date_weeks[1]
    enrollment_total = 0
    current_week_present_total = 0
    previous_week_present_total = 0
    present_by_time = []

    config_list = get_polls_for_keyword(indicator)
    poll_enrollment = Poll.objects.get(name=config_list[0].get('enrollment_poll')[0])
    poll_attendance = Poll.objects.get(name=config_list[0].get('attendance_poll')[0])

    results = get_numeric_data([poll_enrollment], locations, term_range)
    if not is_empty(results):
        enrollment_total = sum(results)

    results = get_numeric_data([poll_attendance], locations, current_week_date_range)
    if not is_empty(results):
        current_week_present_total = sum(results)

    results = get_numeric_data([poll_attendance], locations, previous_week_date_range)
    if not is_empty(results):
        previous_week_present_total = sum(results)

    absent_current_week = round(compute_absent_values(current_week_present_total, enrollment_total), 2)
    absent_previous_week = round(compute_absent_values(previous_week_present_total, enrollment_total), 2)
    present_by_time.append(absent_current_week)
    present_by_time.append(absent_previous_week)

    return present_by_time


def get_digit_value_from_message_text(messge):
    digit_value = 0
    regex = re.compile(r"(-?\d+(\.\d+)?)")
    #split the text on number regex. if the msg is of form
    #'19'or '19 years' or '19years' or 'age19'or 'ugx34.56shs' it returns a list of length 4
    msg_parts = regex.split(messge)
    if len(msg_parts) == 4:
        digit_value = round(float(msg_parts[1]), 3)
    return digit_value


def get_count_for_yes_no_response(polls, locations=None, time_range=None):
    yes = 0
    no = 0
    if time_range:
        if locations:
            responses = Response.objects.filter(date__range=time_range, poll__in=polls, has_errors=False,
                                                contact__reporting_location__in=locations, message__direction='I')
            for response in responses:
                if 'yes' in response.message.text.lower():
                    yes += 1
                if 'no' in response.message.text.lower():
                    no += 1
    return yes, no


def get_count_for_yes_no_by_school(polls, School=None, time_range=None):
    yes = 0
    no = 0
    if time_range:
        if School:
            responses = Response.objects.filter(date__range=time_range, poll__in=polls, has_errors=False,contact__emisreporter__schools__in=School, message__direction='I')
            for response in responses:
                if 'yes' in response.message.text.lower():
                    yes += 1
                if 'no' in response.message.text.lower():
                    no += 1
    return yes, no


#  Function called to populate in-memory Data, reduces on number of db queries per request.
def get_record_collection(locations, time_range):
    results = []
    try:
        if time_range:
            if locations:
                results = Response.objects.filter(date__range = time_range,
                                                  has_errors = False,
                                                  contact__reporting_location__in = locations,
                                                  message__direction = 'I').select_related()
    except:
        pass # Log database errors (or lookup db error exceptions and be specific on exception)
    return results

def get_deployed_head_Teachers_by_school(school, locations):
    heads = EmisReporter.objects.filter(reporting_location__in = locations,
                                        schools__in = school,
                                        groups__name = 'SMC')
    return heads.distinct().count()

def get_deployed_head_Teachers(dataSource, locations):
    return get_deployed_head_Teachers_by_school(dataSource.values_list('schools', flat=True),
                                                locations)

def get_attendance_data(polls, locations, time_range):
    responses = Response.objects.filter(date__range = time_range,
                                        poll__in = polls,
                                        has_errors = False,
                                        contact__reporting_location__in = locations,
                                        message__direction = 'I')
    return [get_digit_value_from_message_text(response.message.text) for response in responses]

def get_numeric_data(polls, locations, time_range):
    responses = Response.objects.filter(date__range = time_range,
                                        poll__in = polls,
                                        has_errors = False,
                                        contact__reporting_location__in = locations,
                                        message__direction = 'I')
    return [get_digit_value_from_message_text(response.message.text) for response in responses]

def get_numeric_enrollment_data(polls, locations=None, time_range=None):
    results = []
    responsive_schools = [] # get schools that have enrollment data (Inner joins return matching data)
    if time_range:
        if locations:
            responses = Response.objects.filter(date__range=time_range, poll__in=polls, has_errors=False,contact__reporting_location__in=locations, message__direction='I')
            for response in responses:
                if get_digit_value_from_message_text(response.message.text) != 0:
                    if response.contact.emisreporter.schools.all():
                        results.append(get_digit_value_from_message_text(response.message.text))
                        responsive_schools.append(response.contact.emisreporter.schools.all()[0])
    return results, responsive_schools

def get_numeric_data_by_school(polls, schools=None, time_range=None):
    results = []
    if time_range:
        if schools:
            responses = Response.objects.filter(date__range=time_range, poll__in=polls, has_errors=False,contact__emisreporter__schools__in=schools, message__direction='I')
            for response in responses:
                results.append(get_digit_value_from_message_text(response.message.text))

    return results


def compute_absent_values(present, enrollment):
    try:
        if present != 0:
            return round(((enrollment - present) * 100 / enrollment), 2)
        elif present == 0 and enrollment > 0:
            return 100
        else:
            return 0
    except ZeroDivisionError:
        return 0

