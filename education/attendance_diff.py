# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import dateutils
from django.conf import settings
from education.utils import _this_thursday
from poll.models import Response


def get_attd_difference(boys_absent_percent_previous_week, boys_absent_percent_this_week):
    if boys_absent_percent_this_week > boys_absent_percent_previous_week:
        return (boys_absent_percent_this_week - boys_absent_percent_previous_week), 'dropped'
    return (boys_absent_percent_previous_week - boys_absent_percent_this_week), 'improved'


def calculate_attendance_difference(connection, progress):
    scripts_list ={'edtrac_p3_teachers_weekly': ['edtrac_boysp3_attendance','edtrac_girlsp3_attendance','edtrac_boysp3_enrollment','edtrac_girlsp3_enrollment'],
                    'edtrac_p6_teachers_weekly': ['edtrac_boysp6_attendance','edtrac_girlsp6_attendance','edtrac_boysp6_enrollment','edtrac_girlsp6_enrollment'],
                    'edtrac_head_teachers_weekly': ['edtrac_m_teachers_attendance','edtrac_f_teachers_attendance','edtrac_m_teachers_deployment','edtrac_f_teachers_deployment']}
    to_return= {}
    for script, poll_names in scripts_list.items():
        boys_absent_percent_previous_week =0
        boys_absent_percent_this_week =0
        girls_absent_percent_previous_week =0
        girls_absent_percent_this_week =0
        boys_enrolled , girls_enrolled = get_enrolled_boys_and_girls(connection,poll_names[2],poll_names[3])
        this_thursday = _this_thursday()
        current_week = [dateutils.increment(this_thursday,days=-7),dateutils.increment(this_thursday,days=-1)]
        previous_week = [dateutils.increment(this_thursday,days=-14),dateutils.increment(this_thursday,days=-8)]
        for step in progress.script.steps.all():
            present_this_week = Response.objects.filter(poll= step.poll,contact__connection=connection,date__range=current_week, has_errors = False)
            if present_this_week.exists():
                present_this_week = int(present_this_week.latest('date').message.text)
            else:
                present_this_week = 0

            present_previous_week = Response.objects.filter(poll= step.poll,contact__connection=connection,date__range=previous_week)
            if present_previous_week.exists():
                present_previous_week= int(present_previous_week.latest('date').message.text)
            else:
                present_previous_week = 0

            if step.poll.name == poll_names[0]:
                boys_absent_percent_this_week = calculate_percent((boys_enrolled-present_this_week),boys_enrolled)
                boys_absent_percent_previous_week = calculate_percent((boys_enrolled-present_previous_week),boys_enrolled)

            if step.poll.name == poll_names[1]:
                girls_absent_percent_this_week = calculate_percent((girls_enrolled-present_this_week),girls_enrolled)
                girls_absent_percent_previous_week = calculate_percent((girls_enrolled-present_previous_week),girls_enrolled)

        boys_attendance_difference =  get_attd_difference(boys_absent_percent_previous_week, boys_absent_percent_this_week)
        girls_attendance_difference =  get_attd_difference(girls_absent_percent_previous_week, girls_absent_percent_this_week)
        to_return[poll_names[0]] = boys_attendance_difference
        to_return[poll_names[1]] = girls_attendance_difference
    return to_return

def calculate_percent(numerator, denominator):
    try:
        return 100 * numerator/denominator
    except ZeroDivisionError:
        return 0

def get_enrolled_boys_and_girls(connection, boys_enroll_poll_name, girls_enroll_poll_name):
    term_start = getattr(settings, "SCHOOL_TERM_START")
    term_end = getattr(settings, "SCHOOL_TERM_END")
    boys_enrolled = get_enrolled_pupils(connection, boys_enroll_poll_name, term_start, term_end)
    girls_enrolled = get_enrolled_pupils(connection, girls_enroll_poll_name, term_start, term_end)
    return boys_enrolled , girls_enrolled

def get_enrolled_pupils(connection, poll_name, term_start_date = None, term_end_date = None):
    boys_enrolled = Response.objects.filter(poll__name=poll_name, contact__connection=connection,
        date__range=[term_start_date, term_end_date])
    if boys_enrolled.exists():
        boys_enrolled = int(boys_enrolled.latest('date').message.text)
    else:
        boys_enrolled = 0
    return boys_enrolled