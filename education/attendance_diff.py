# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import dateutils
from django.conf import settings
from education.utils import _this_thursday
from poll.models import Response


def get_attd_diff(boys_absent_percent_previous_week, boys_absent_percent_this_week):
    if boys_absent_percent_this_week > boys_absent_percent_previous_week:
        return (boys_absent_percent_this_week - boys_absent_percent_previous_week), 'dropped'
    return (boys_absent_percent_previous_week - boys_absent_percent_this_week), 'improved'


def calculate_attendance_diff(connection,progress):
    boys_absent_percent_previous_week =0
    boys_absent_percent_this_week =0
    girls_absent_percent_previous_week =0
    girls_absent_percent_this_week =0
    boys_enrolled , girls_enrolled = get_enrolled_boys_and_girls(connection)
    this_thursday = _this_thursday()
    current_week = [dateutils.increment(this_thursday,days=-7),dateutils.increment(this_thursday,days=-1)]
    previous_week = [dateutils.increment(this_thursday,days=-14),dateutils.increment(this_thursday,days=-8)]
    for step in progress.script.steps.all():
        present_this_week = Response.objects.filter(poll= step.poll,contact__connection=connection,date__range=current_week)
        if present_this_week.exists():
            present_this_week = int(present_this_week.latest('date').message.text)
        else:
            present_this_week = 0

        present_previous_week = Response.objects.filter(poll= step.poll,contact__connection=connection,date__range=previous_week)
        if present_previous_week.exists():
            present_previous_week= int(present_previous_week.latest('date').message.text)
        else:
            present_previous_week = 0

        if step.poll.name == 'edtrac_boysp3_attendance':
            boys_absent_percent_this_week = calculate_percent((boys_enrolled-present_this_week),boys_enrolled)
            boys_absent_percent_previous_week = calculate_percent((boys_enrolled-present_previous_week),boys_enrolled)

        if step.poll.name == 'edtrac_girlsp3_attendance':
            girls_absent_percent_this_week = calculate_percent((girls_enrolled-present_this_week),girls_enrolled)
            girls_absent_percent_previous_week = calculate_percent((girls_enrolled-present_previous_week),girls_enrolled)

    boys_attd_diff =  get_attd_diff(boys_absent_percent_previous_week, boys_absent_percent_this_week)
    girls_attd_diff =  get_attd_diff(girls_absent_percent_previous_week, girls_absent_percent_this_week)

    return dict(boysp3 = boys_attd_diff , girlsp3 = girls_attd_diff)

def calculate_attendance_difference_for_p6(connection,progress):
    boys_absent_percent_previous_week =0
    boys_absent_percent_this_week =0
    girls_absent_percent_previous_week =0
    girls_absent_percent_this_week =0
    boys_enrolled , girls_enrolled = get_enrolled_p6_boys_and_girls(connection)
    print 'Boys enrolled : '+ str(girls_enrolled)
    this_thursday = _this_thursday()
    current_week = [dateutils.increment(this_thursday,days=-7),dateutils.increment(this_thursday,days=-1)]
    previous_week = [dateutils.increment(this_thursday,days=-14),dateutils.increment(this_thursday,days=-8)]
    for step in progress.script.steps.all():
        present_this_week = Response.objects.filter(poll= step.poll,contact__connection=connection,date__range=current_week)
        if present_this_week.exists():
            present_this_week = int(present_this_week.latest('date').message.text)
            print step.poll.name + ' : '+str(present_this_week)
        else:
            present_this_week = 0
        present_previous_week = Response.objects.filter(poll= step.poll,contact__connection=connection,date__range=previous_week)
        if present_previous_week.exists():
            present_previous_week= int(present_previous_week.latest('date').message.text)
        else:
            present_previous_week = 0

        if step.poll.name == 'edtrac_boysp6_attendance':
            boys_absent_percent_this_week = calculate_percent((boys_enrolled-present_this_week),boys_enrolled)
            boys_absent_percent_previous_week = calculate_percent((boys_enrolled-present_previous_week),boys_enrolled)


        if step.poll.name == 'edtrac_girlsp6_attendance':
            girls_absent_percent_this_week = calculate_percent((girls_enrolled-present_this_week),girls_enrolled)
            girls_absent_percent_previous_week = calculate_percent((girls_enrolled-present_previous_week),girls_enrolled)



    boys_attd_diff =  get_attd_diff(boys_absent_percent_previous_week, boys_absent_percent_this_week)
    girls_attd_diff =  get_attd_diff(girls_absent_percent_previous_week, girls_absent_percent_this_week)


    return dict(boysp6 = boys_attd_diff , girlsp6 = girls_attd_diff)



def calculate_percent(numerator, denominator):
    try:
        return 100 * numerator/denominator
    except ZeroDivisionError:
        return 0

def get_enrolled_boys_and_girls(connection):
    term_start = getattr(settings, "SCHOOL_TERM_START")
    term_end = getattr(settings, "SCHOOL_TERM_END")
    boys_enrolled = get_enrolled_pupils(connection, "edtrac_boysp3_enrollment", term_start, term_end)
    girls_enrolled = get_enrolled_pupils(connection, "edtrac_girlsp3_enrollment", term_start, term_end)
    return boys_enrolled , girls_enrolled

def get_enrolled_p6_boys_and_girls(connection):
    term_start = getattr(settings, "SCHOOL_TERM_START")
    term_end = getattr(settings, "SCHOOL_TERM_END")
    # I removed the start term and end term date range and it worked. we need to look at the settings and make sure they
    # are within range (jude)0
    #boys_enrolled = Response.objects.filter(poll__name="edtrac_boysp6_enrollment", contact__connection=connection,
     #                                       date__range=[term_start, term_end])
    boys_enrolled = get_enrolled_pupils(connection, "edtrac_boysp6_enrollment", term_start, term_end)

    if boys_enrolled.exists():
        boys_enrolled = int(boys_enrolled.latest('date').message.text)
    else:
        boys_enrolled = 0

    girls_enrolled = Response.objects.filter(poll__name="edtrac_girlsp6_enrollment", contact__connection=connection,
                                             date__range=[term_start, term_end])
    if girls_enrolled.exists():
        girls_enrolled = int(girls_enrolled.latest('date').message.text)
    else:
        girls_enrolled = 0

    return boys_enrolled , girls_enrolled

def get_enrolled_pupils(connection, poll_name, term_start_date = None, term_end_date = None):
    boys_enrolled = Response.objects.filter(poll__name=poll_name, contact__connection=connection,
        date__range=[term_start_date, term_end_date])
    if boys_enrolled.exists():
        boys_enrolled = int(boys_enrolled.latest('date').message.text)
    else:
        boys_enrolled = 0
    return boys_enrolled