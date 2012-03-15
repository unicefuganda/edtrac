'''
Created on Sep 15, 2011

@author: asseym
'''
from __future__ import division
from script.utils.handling import find_best_response
from script.models import Script, ScriptSession, ScriptProgress
from rapidsms.models import Connection
from datetime import datetime,date
import calendar
import dateutils
import xlwt
from contact.models import MessageFlag
from rapidsms.models import Contact
from rapidsms.contrib.locations.models import Location
from poll.models import Poll
from script.models import ScriptStep
from django.db.models import Count
from django.contrib.auth.models import Group
from django.conf import settings
from uganda_common.utils import *
from django.db.models import Avg

def previous_calendar_week(t=None):
    """
    To education monitoring, a week runs between Thursdays, 
    Thursday marks the beginning of a new week of data submission
    Data for a new week is accepted until Wednesday evenning of the following week
    """
    d = t if t else datetime.datetime.now()
    if not d.weekday() == 3:
        # last Thursday == next Thursday minus 7 days.
        last_thursday = d + (datetime.timedelta((3-d.weekday())%7) - (datetime.timedelta(days=7)))
    else:
        last_thursday = d
    end_date = last_thursday + datetime.timedelta(days=7)
    return (last_thursday.date(), end_date)

def is_weekend(date):
    """
    Find out if supplied date is a Saturday or Sunday, return True/False
    """
    return date.weekday() in [5, 6]

def next_relativedate(day_offset, month_offset=0):
    """
    Find the date corresponding to day_offset of the month for example 25th day of of month
    you can also give month offsets, ie date of the 25th day of the next month
    """
    d = datetime.datetime.now()
    if month_offset:
        d = d + datetime.timedelta(month_offset*31)
        
    day = calendar.mdays[d.month] if day_offset == 'last' else day_offset
    if d.day >= day:
        d = d + dateutils.relativedelta(day=31)
    else:
        d = datetime.datetime(d.year, d.month, 1, d.hour, d.minute, d.second, d.microsecond)
    return d + datetime.timedelta(day)

def _next_thursday(sp=None):
    """
    Next Thursday is the very next Thursday of the week which is not a school holiday
    """
    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    d = sp.time if sp else datetime.datetime.now()
    if d.weekday() == 3:
        d = d + datetime.timedelta(7)
    else: 
        d = d + datetime.timedelta((3 - d.weekday()) % 7)
    in_holiday = True
    while in_holiday:
        in_holiday = False
        for start, end in holidays:
            if type(end) == str:
                if d.date() == start.date():
                    in_holiday = True
                    break
            else:
                if d >= start and d <= end:
                    in_holiday = True
                    break
        if in_holiday:
            d = d + datetime.timedelta(7)
    return d

def _next_wednesday(sp = None):
    """
    Next Wednesday is the very next Wednesday of the week which is not a school holiday
    """
    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    d = sp.time if sp else datetime.datetime.now()
    d = d + datetime.timedelta((2 - day.weekday()) % 7)
    in_holiday = True
    while in_holiday:
        in_holiday = False
        for start, end in holidays:
            if type(end) == str:
                if d.date() == start.date():
                    in_holiday = True
                    break
            else:
                if d >= start and d <= end:
                    in_holiday = True
                    break
        if in_holiday:
            day = day + datetime.timedelta(7)
    return day

def _is_wednesday():
    today = datetime.datetime.now()
    WEDNESDAY_WEEKDAY = 2
    if today.weekday() == WEDNESDAY_WEEKDAY:
        return (today, True)
    return (today, False)

def _send_report(connections=None, report=None):
    pass


def _schedule_report_sending():
    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    current_day, current_day_wednesday = _is_wednesday()
    can_send = True
    if current_day_wednesday:
        for start, end in holidays:
            if current_day >= start and current_day <= end:
                can_send = False
                break
        if can_send:
            from .reports import generate_deo_report
            from .models import EmisReporter
            all_repoters = EmisReporter.objects.filter(groups__name="DEO")
            for reporter in all_repoters:

                deo_report_connections, deo_report = generate_deo_report(location_name=reporter.reporting_location.name)
                #attendance_template = "%s% of %s% were absent this week. Attendance is %s %s than it was last week"
                attendance_template = "%s% were absent this week."
                literacy_template = "An average of %s of %s covered"

                for current_week, previous_week in deo_report:

                    if 'pupils' in key.split():
                        _send_report(connections = deo_report_connections, report= attendance_template % report)
                    elif 'progress' in key.split():
                                _send_report(connections = deo_report_connections, report = literacy_template % report)
        else:
            return
    else:
        return
    
def _date_of_monthday(day_offset):
    
    """
    Find the date corresponding to day_offset of the month for example 25th day of of month
    If the 'day_offset' day of the month is falls in holiday period, 'day_offset' day of
    the following month is returned
    """
    
    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    d = next_relativedate(day_offset)
    if is_weekend(d):
        #next monday
        d = d + datetime.timedelta((0 - d.weekday()) % 7)
        
    in_holiday = True
    while in_holiday:
        in_holiday = False
        for start, end in holidays:
            if type(end) == str:
                if d.date() == start.date():
                    in_holiday = True
                    break
            else:
                if d >= start and d <= end:
                    in_holiday = True
                    break
        if in_holiday:
            d = next_relativedate(day_offset, 1)
            if is_weekend(d):
                d = d + datetime.timedelta((0 - d.weekday()) % 7)
    return d

def _next_term_question_date(rght=None):
    """
    The termly questions are sent out on the 12th day of each term and computed based on the beginning of term date
    """
#    import pdb;pdb.set_trace()
#    delta = datetime.timedelta(days=12)
#    delta_smc = datetime.timedelta(days=68)
#    if rght:
#        delta = delta_smc
    delta = datetime.timedelta(days=68) if rght else datetime.timedelta(12)
    first_term_qn_date = getattr(settings, 'FIRST_TERM_BEGINS', datetime.datetime.now()) + delta
    second_term_qn_date = getattr(settings, 'SECOND_TERM_BEGINS', datetime.datetime.now()) + delta
    third_term_qn_date = getattr(settings, 'THIRD_TERM_BEGINS', datetime.datetime.now()) + delta
    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    d = datetime.datetime.now()
    if first_term_qn_date == second_term_qn_date == third_term_qn_date == datetime.datetime.now() + delta:
        d = d + delta
    else:
        if d <= first_term_qn_date:
            d = first_term_qn_date
        elif d > first_term_qn_date and d <= second_term_qn_date:
            d = second_term_qn_date
        else:
            d = third_term_qn_date        
    if is_weekend(d):
        d = d + datetime.timedelta((0 - d.weekday()) % 7)
    in_holiday = True
    while in_holiday:
        in_holiday = False
        for start, end in holidays:
            if type(end) == str:
                if d.date() == start.date():
                    in_holiday = True
                    break
            else:
                if d >= start and d <= end:
                    in_holiday = True
                    break
        if in_holiday:
            d = d + datetime.timedelta(days=1)
            if is_weekend(d):
                d = d + datetime.timedelta((0 - d.weekday()) % 7)
    return d

def _next_midterm():
    """
    The middle of school term is either in mid April, July or Nov for Term 1, 2 and 3 respectively.
    This function returns the approximate date of the next mid term depending on the current date.
    """

    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    d = datetime.datetime.now()
    start_of_year = datetime.datetime(d.year, 1, 1, d.hour, d.minute, d.second, d.microsecond)
    if d.month in [12, 1, 2, 3, 4]:
        #todo: handle this better/// revert after head teacher poll
        d = start_of_year + datetime.timedelta(days=58)
    elif d.month in [ 5, 6]:
        d = start_of_year + datetime.timedelta(days=((6*31)+15))
    else:
        d = start_of_year + datetime.timedelta(days=((10*31)+15))
    
    if is_weekend(d):
        d = d + datetime.timedelta((0 - d.weekday()) % 7)
    in_holiday = True
    while in_holiday:
        in_holiday = False
        for start, end in holidays:
            if type(end) == str:
                if d.date() == start.date():
                    in_holiday = True
                    break
            else:
                if d >= start and d <= end:
                    in_holiday = True
                    break
        if in_holiday:
            if is_weekend(d):
                d = d + datetime.timedelta((0 - d.weekday()) % 7)
    return d

def _schedule_weekly_scripts(group, connection, grps):
    """
    This method is called within a loop over several connections or for an individual connection
    and it sets the start time for a script to _next_thursday() relative to either current date
    or the date that is currently in ScriptProgress
    """
    if group.name in grps:
        script_slug = "edtrac_%s" % group.name.lower().replace(' ', '_') + '_weekly'
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
        d = _next_thursday()
        sp.set_time(d)

def _schedule_weekly_report(group, connection, grps):
    if group.name in grps:
        script_slug = "edtrac_%s" % group.name.lower().replace(' ', '_') + 'report_weekly'
        connections = Connection.objects.filter(contact__in=Group.objects.get(name=group.name).contact_set.all())
        for connection in connections:
            sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
            sp.set_time( _next_wednesday(sp) )
    
def _schedule_monthly_script(group, connection, script_slug, day_offset, role_names):
    """
    This method is called within a loop over several connections or for an individual connection
    and it sets the start time for a script to _date_of_monthday() corresponding to day_offset
    the new date is computed relative datetime.datetime.now()
    """
    if group.name in role_names:
        d = _date_of_monthday(day_offset)
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
        sp.set_time(d)

def _schedule_monthly_report(group, connection, script_slug, day_offset, role_names):
    """
    This is method is called within a loop of several connections or an individual connection; it stes the time
    to a particular date in the month and sends of a report as message
    """
    if group.name in role_names:
        connections = Connection.objects.filter(contact__in=Group.objects.get(name=group.name).contact_set.all())
        for connection in connections:
            d = _date_of_monthday(day_offset)
            sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
            sp.set_time(d)

def _schedule_termly_script(group, connection, script_slug, role_names, date=None):
    """
    This method is called within a loop over several connections or for an individual connection
    and it sets the start time for a script to _next_term_question_date() or _next_midterm() or to date passed to it as a String argument
    in the format YYYY-mm-dd
    """
#    d = None
    if date:
        now = datetime.datetime.now()
        dl = date.split('-')
        d = datetime.datetime(int(dl[0]), int(dl[1]), int(dl[2]), now.hour, now.minute, now.second, now.microsecond)
    else:
        d = _next_term_question_date()
        if group.name == 'SMC':
            d = _next_term_question_date(True)
    if group.name in role_names:
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
        sp.set_time(d)

def compute_total(chunkit):
    # function takes in a list of tuples (school_name,value) ---> all grades p1 to p7
    new_dict = {}
    for n, val in chunkit: new_dict[n] = 0 #placeholder
    for i in chunkit:
        if i[0] in new_dict.keys():
            new_dict[i[0]] = new_dict[i[0]] + i[1]            
    return new_dict

def previous_calendar_week_v2(date_now):
    if not date_now.weekday() == 2:
        last_wednesday = date_now + (datetime.timedelta((2-date_now.weekday())%7) - (datetime.timedelta(days=7)))
    else:
        last_wednesday = date_now
    end_date = last_wednesday + datetime.timedelta(days=7)
    return (last_wednesday, end_date)

def previous_calendar_month_week_chunks():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(29)
    month_in_fours = []
    for i in range(4):
        start_date = start_date + datetime.timedelta(7)
        if start_date < end_date:
            month_in_fours.append(list(previous_calendar_week_v2(start_date))) #might have to miss out on the thursdays???
    return month_in_fours


def get_contacts(**kwargs):
    request = kwargs.pop('request')
    if request.user.is_authenticated() and hasattr(Contact, 'groups'):
        return Contact.objects.filter(groups__in=request.user.groups.all()).distinct().annotate(Count('responses'))
    else:
        return Contact.objects.annotate(Count('responses'))

def get_polls(**kwargs):
    script_polls = ScriptStep.objects.exclude(poll=None).values_list('poll', flat=True)
    return Poll.objects.exclude(pk__in=script_polls).annotate(Count('responses'))

def get_script_polls(**kwargs):
    script_polls = ScriptStep.objects.exclude(poll=None).values_list('poll', flat=True)
    return Poll.objects.filter(pk__in=script_polls).annotate(Count('responses'))

#def retrieve_poll(request):
#    pks=request.GET.get('pks', '').split('+')
#    if pks[0] == 'l':
#        return [Poll.objects.latest('start_date')]
#    else:
#        pks=[eval(x) for x in list(str(pks[0]).rsplit())]
#        return Poll.objects.filter(pk__in=pks)

def retrieve_poll(request, pks=None):
    script_polls = ScriptStep.objects.exclude(poll=None).values_list('poll', flat=True)
    if pks == None:
        pks = request.GET.get('pks', '')
    if pks == 'l':
        return [Poll.objects.exclude(pk__in=script_polls).latest('start_date')]
    else:
        return Poll.objects.filter(pk__in=[pks]).exclude(pk__in=script_polls)

def get_flagged_messages(**kwargs):
    return MessageFlag.objects.all()



def compute_average_percentage(list_of_percentages):
    """
    Average percentage
    -> this is also a handly tool to compute averages generally while sanitizing
    """
    sanitize = []
    try:
        for i in list_of_percentages:
            if isinstance(float(i), float):
                sanitize.append(float(i))
            else:
                pass
    except ValueError:
        print "non-numeric characters used"
        pass
    if len(sanitize) <= 0:
        return 0        
    return sum(sanitize) / float(len(sanitize))


def list_poll_responses(poll, **kwargs):
    """
    pass a poll queryset and you get yourself a dict with locations vs responses (quite handy for the charts)
    dependecies: Contact and Location must be in your module; this lists all Poll responses by district
    """
    #forceful import
    from poll.models import Poll
    to_ret = {}
    """
    To get all districts
    """
    #for location in Location.objects.filter(type__name="district"):
    #    to_ret[location.__unicode__()] = compute_average_percentage([msg.text for msg in poll.responses.filter(contact__in=Contact.objects.filter(reporting_location=location))])
    
    """
    narrowed down to 3 districts (and up to 14 districts)
    """
    DISTRICT = ['Kaabong', 'Kabarole', 'Kyegegwa', 'Kotido']
    if not kwargs:
        # if no other arguments are provided
        for location in Location.objects.filter(name__in=DISTRICT):
            to_ret[location.__unicode__()] = compute_average_percentage([msg.message.text for msg in poll.responses.filter(contact__in=Contact.objects.filter(reporting_location=location))])
        return to_ret
    else:
        # filter by number of weeks
        #TODO more elegant solution to coincide with actual school term weeks
        date_filter = kwargs['weeks'] #give the date in weeks
        date_now = datetime.datetime.now()
        date_diff = date_now - datetime.timedelta(weeks=date_filter)
        all_emis_reports = EmisReporter.objects.filter(reporting_location__in=[loc for loc in Locations.objects.filter(name__in=DISTRICT)])
        for location in Location.objects.filter(name__in=DISTRICT):
            to_ret[location.__unicode__()] = compute_average_percentage([msg.message.text for msg in poll.responses.filter(date__gte=date_diff, contact__in=Contact.objects.filter(reporting_location=location))])
        return to_ret
    
def get_script_grp(script_slug):
    sl = script_slug.split('_')
    if sl[1] == 'head':
        return '%s %s' % (sl[1], sl[2])
    else:
        return sl[1]

# Themes

themes = {
    1.1 : "Name and location of our Sub-county/Division",
    1.2 : 'Physical features of our Sub-County/Division',
    1.3 : 'People in our Sub-county/Division',
    2.1 : 'Occupations of people in our Sub-county/Division and their importance',
    2.2 : 'Social Services and their importance',
    2.3 : 'Challenges in social services and their possible solutions',
    3.1 : 'Soil',
    3.2 : 'Natural causes of changes in the environment',
    3.3 : 'Changes in the environment through human activities',
    4.1 : 'Air and the Sun',
    4.2 : 'Water',
    4.3 : 'Managing Water',
    5.1 : 'Living things',
    5.2 : 'Birds and Insects',
    5.3 : 'Care for insects, birds and animals',
    6.1 : 'Plants and their habitat',
    6.2 : 'Parts of a flowering plant and their uses',
    6.3 : 'Crop-growing practices',
    7.1 : 'Saving resources',
    7.2 : 'Spending resources',
    7.3 : 'Projects',
    8.1 : 'Living in peace with others',
    8.2 : 'Child rights, needs and their importance',
    8.3 : 'Child responsibility',
    9.1 : 'Customs in our sub-county/division',
    9.2 : 'Gender',
    9.3 : 'Ways of promoting and preserving culture',
    10.1: 'Disease vectors',
    10.2: 'Diseases spread by vectors',
    10.3: 'HIV/AIDS',
    11.1: 'Concept of technology',
    11.2: 'Processing and making things from natural materials',
    11.3: 'Making things from artificial materials',
    12.1: 'Sources of energy',
    12.2: 'Ways of saving energy',
    12.3: 'Dangers of energy and ways of avoiding them'
}