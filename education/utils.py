'''
Created on Sep 15, 2011

@author: asseym
'''
from __future__ import division
from dateutil.relativedelta import relativedelta
from script.models import Script, ScriptSession, ScriptProgress
from rapidsms.models import Connection
from datetime import datetime,date
import calendar
import dateutils
from contact.models import MessageFlag
from rapidsms.models import Contact
from rapidsms.contrib.locations.models import Location
from poll.models import Poll
from script.models import ScriptStep
from django.db.models import Count
from django.contrib.auth.models import Group
from django.conf import settings
from unregister.models import Blacklist

def is_empty(arg):
    """
    Generalizes 'empty' checks on Strings, sequences, and dicts.

    Returns 'True' for None, empty strings, strings with just white-space,
    and sequences with len == 0
    """

    if arg is None:
        return True

    if isinstance(arg, basestring):
        arg = arg.strip()

    try:
        if not len(arg):
            return True
    except TypeError:
        # wasn't a sequence
        pass

    return False

def time_to_10am(d):
    return datetime.datetime(d.year, d.month, d.day, 10, 0, 0, 0)

def previous_calendar_week(t=None):
    """
    To education monitoring, a week runs between Thursdays, 
    Thursday marks the beginning of a new week of data submission
    Data for a new week is accepted until Wednesday evening of the following week
    """
    d = t if t else datetime.datetime.now()
    if not d.weekday() == 3:
        # last Thursday == next Thursday minus 7 days.
        last_thursday = d + (datetime.timedelta((3-d.weekday())%7) - (datetime.timedelta(days=7)))
    else:
        last_thursday = d
    end_date = last_thursday + datetime.timedelta(days=6)
    return (last_thursday.date(), end_date)

def is_weekend(date):
    """
    Find out if supplied date is a Saturday or Sunday, return True/False
    """
    return date.weekday() in [5, 6]

def next_relativedate(day_offset, month_offset=0, xdate = datetime.datetime.now()):
    """
    Find the date corresponding to day_offset of the month for example 25th day of of month
    you can also give month offsets, ie date of the 25th day of the next month
    """
#    d = datetime.datetime.now()
    d = xdate
    
    if month_offset:
        d = d + datetime.timedelta(month_offset*31)
        
    day = calendar.mdays[d.month] if day_offset == 'last' else day_offset
    if d.day >= day:
        d = d + dateutils.relativedelta(day=31)
    else:
        d = datetime.datetime(d.year, d.month, 1, d.hour, d.minute, d.second, d.microsecond)
    d = time_to_10am(d)
    return d + datetime.timedelta(day)

def _next_thursday(sp=None, **kwargs):
    """
    Next Thursday is the very next Thursday of the week which is not a school holiday
    """
    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    if sp:
        d = time_to_10am(sp.time)
    elif kwargs.get('time_set'):
        d = time_to_10am(kwargs.has_key('time_set'))
    else:
        d = time_to_10am(datetime.datetime.now())

    if d.weekday() == 3: # if a thursday
        d = d + datetime.timedelta(days = 7)
    elif d.weekday() < 3:
        d = d + datetime.timedelta(days = (3 - d.weekday()))
    else:
        d = d + (datetime.timedelta(days = (7 - d.weekday()) + 3))

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
            d = d + datetime.timedelta(days = 7)
    return d


def _this_thursday(sp=None, **kwargs):
    """
    This Thursday of the week which is not a school holiday
    """
    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    time_schedule = kwargs.get('time_set') if kwargs.has_key('time_set') else datetime.datetime.now()
    d = sp.time if sp else time_schedule
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
            d = d + datetime.timedelta(1) # try next day
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
    If the 'day_offset' day of the month falls in holiday period, 'day_offset' day of
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
            d = next_relativedate(day_offset, 0, d)
            if is_weekend(d):
                d = d + datetime.timedelta((0 - d.weekday()) % 7)
    return d

def _next_term_question_date(rght=None):
    """
    The termly questions are sent out on the 12th day of each term and computed based on the beginning of term date
    """

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
    #Short curcuit scheduling teachers without grades
    if group.name == 'Teachers':
        if not connection.contact.emisreporter.grade:
            return
        
    if group.name in grps:
        script_slug = "edtrac_%s" % group.name.lower().replace(' ', '_') + '_weekly'
        #Since script_was_completed is sent before progress is deleted, chances are you will find connection and script existing
        if ScriptProgress.objects.filter(connection=connection, script__slug=script_slug).exists():
            sp = ScriptProgress.objects.filter(connection=connection, script__slug=script_slug)[0]
            d = _next_thursday(sp=sp)
        else:
            d = _next_thursday()
    else:
        #Reporter is not in group that receives weekly messages so, we don't schedule them for any weekly messages
        return
    
    #create new scriptprogress regardless
    sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
    sp.set_time(d)

def _schedule_teacher_weekly_scripts(group, connection, grps):
    """
    This method is called within a loop over several connections or for an individual connection
    and it sets the start time for a script to _next_thursday() relative to either current date
    or the date that is currently in ScriptProgress for teachers
    """
    #Short curcuit scheduling teachers without grades
    if group.name == 'Teachers':
        if connection.contact.emisreporter.grade in ['p3', 'P3'] and connection.contact.emisreporter.schools.exists():
                # get rid of any existing script progress; this is a one time thing
                ScriptProgress.objects.filter(connection=connection,script=Script.objects.get(slug='edtrac_p3_teachers_weekly')).delete()
                sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug='edtrac_p3_teachers_weekly'))
                d = _next_thursday(sp=sp)
                sp.set_time(d)
        elif connection.contact.emisreporter.grade in ['p6', 'P6'] and connection.contact.emisreporter.schools.exists():
            # get rid of existing ScriptProgresses and assign it to p6 teachers
            ScriptProgress.objects.filter(connection=connection,script=Script.objects.get(slug='edtrac_p6_teachers_weekly')).delete()
            sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug='edtrac_p6_teachers_weekly'))
            d = _next_thursday(sp=sp)
            sp.set_time(d)
        else:
            pass
        
        
    if group.name in grps:
        script_slug = "edtrac_%s" % group.name.lower().replace(' ', '_') + '_weekly'
        #Since script_was_completed is sent before progress is deleted, chances are you will find connection and script existing
        if ScriptProgress.objects.filter(connection=connection, script__slug=script_slug).exists():
            sp = ScriptProgress.objects.filter(connection=connection, script__slug=script_slug)[0]
            d = _next_thursday(sp=sp)
        else:
            d = _next_thursday()
    else:
        #Reporter is not in group that receives weekly messages so, we don't schedule them for any weekly messages
        return
    
    #create new scriptprogress regardless
#    sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
#    sp.set_time(d)



def _schedule_weekly_scripts_now(group, connection, grps):
    """
    This method is called within a loop over several connections or for an individual connection
    and it sets the start time for a script to _next_thursday() relative to either current date
    or the date that is currently in ScriptProgress
    """
    if group.name in grps:
        script_slug = "edtrac_%s" % group.name.lower().replace(' ', '_') + '_weekly'
        now = datetime.datetime.now()
        time_set = None
        if now.hour > 10:
            time_set = now - datetime.timedelta(hours = now.hour - 10)
        elif now.hour < 10:
            time_set = now + datetime.timedelta(hours = 10 - now.hour)
        else:
            time_set = now
        time_set = time_set if time_set.second == 0 else time_set - datetime.timedelta(seconds = time_set.second)
        time_set = time_set if time_set.minute == 0 else time_set - datetime.timedelta(minutes = time_set.minute)
        d = _this_thursday(time_set=time_set)
        #if reporter is a teacher set in the script session only if this reporter has a grade
        if connection.contact.emisreporter.groups.filter(name='Teachers').exists():
            if connection.contact.emisreporter.grade and connection.contact.emisreporter.schools.exists():
                # get rid of any existing script progress; this is a one time thing
                ScriptProgress.objects.filter(connection=connection,script=Script.objects.get(slug=script_slug)).delete()
                sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
                sp.set_time(d)
            else:
                pass # do nothing, jump to next iteration
        elif connection.contact.emisreporter.groups.filter(name__in = ["Head Teachers", "SMC", "GEM"]).exists() and\
             connection.contact.emisreporter.groups.filter(name__in = ["Head Teachers", "SMC", "GEM"]).count()==1 and\
             not Blacklist.objects.filter(connection=connection).exists():
            ScriptProgress.objects.filter(connection=connection,script=Script.objects.get(slug=script_slug)).delete()
            sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
            sp.set_time(d)
        else:
            pass # do nothing if reporter has no recognizable group. e.g. Other Reporters or unessential sms receiver groups like DEO/MEO, UNICEF Officials, etc.

def _schedule_weekly_script(group, connection, script_slug, role_names):
    """
    This method is called within a loop over several connections or for an individual connection
    and it sets the start time for a script to _date_of_monthday() corresponding to day_offset
    the new date is computed relative datetime.datetime.now()
    """
    if group.name in role_names:
        now  = datetime.datetime.now()
        time_set = None
        if now.hour > 10:
            time_set = now - datetime.timedelta(hours = now.hour - 10)
        elif now.hour < 10:
            time_set = now + datetime.timedelta(hours = 10 - now.hour)
        else:
            time_set = now
        time_set = time_set if time_set.second == 0 else time_set - datetime.timedelta(seconds = time_set.second)
        time_set = time_set if time_set.minute == 0 else time_set - datetime.timedelta(minutes = time_set.minute)
        d = _this_thursday(time_set=time_set)
        
        #if reporter is a teacher set in the script session only if this reporter has a grade
        if connection.contact.emisreporter.groups.filter(name='Teachers').exists():
            if connection.contact.emisreporter.grade in ['p3', 'P3'] and connection.contact.emisreporter.schools.exists():
                # get rid of any existing script progress; this is a one time thing
                ScriptProgress.objects.filter(connection=connection,script=Script.objects.get(slug=script_slug)).delete()
                sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
                sp.set_time(d)
            elif connection.contact.emisreporter.grade in ['p6', 'P6'] and connection.contact.emisreporter.schools.exists():
                # get rid of existing ScriptProgresses and assign it to p6 teachers
                ScriptProgress.objects.filter(connection=connection,script=Script.objects.get(slug='edtrac_p6_teachers_weekly')).delete()
                sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug='edtrac_p6_teachers_weekly'))
                sp.set_time(d)
            else:
                pass

def _schedule_weekly_report(group, connection, grps):
    if group.name in grps:
        script_slug = "edtrac_%s" % group.name.lower().replace(' ', '_') + 'report_weekly'
        connections = Connection.objects.filter(contact__in=Group.objects.get(name=group.name).contact_set.all())
        for connection in connections:
            sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
            sp.set_time( _next_wednesday(sp) )
            
def _schedule_script_now(group, connection, slug, role_names):
    if group.name in role_names:
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=slug),language='en')
        sp.set_time(datetime.datetime.now())
    
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

def _schedule_midterm_script(group, connection, script_slug, role_names, date=None):
    """
    This method is called within a loop over several connections or for an individual connection
    and it sets the start time for a script to _next_midterm() or to date passed to it as a String argument
    in the format YYYY-mm-dd
    """
#    d = None
    if date:
        now = datetime.datetime.now()
        dl = date.split('-')
        d = datetime.datetime(int(dl[0]), int(dl[1]), int(dl[2]), now.hour, now.minute, now.second, now.microsecond)
    else:
        d = _next_midterm()
    if group.name in role_names:
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
        
def _schedule_new_monthly_script(group, connection, script_slug, role_names, date=None):
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
    script_polls = ScriptStep.objects.values_list('poll', flat=True).exclude(poll=None)
    return Poll.objects.exclude(pk__in=script_polls).annotate(Count('responses'))

def get_script_polls(**kwargs):
    script_polls = ScriptStep.objects.exclude(poll=None).values_list('poll', flat=True)
    return Poll.objects.filter(pk__in=script_polls).annotate(Count('responses'))


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





## {{{ http://code.activestate.com/recipes/409413/ (r2)
"""
Descriptive statistical analysis tool.
"""

class StatisticsException(Exception):
    """Statistics Exception class."""
    pass

class Statistics(object):
    """Class for descriptive statistical analysis.

    Behavior:
       Computes numerical statistics for a given data set.

    Available public methods:

       None

    Available instance attributes:

           N: total number of elements in the data set
         sum: sum of all values (n) in the data set
         min: smallest value of the data set
         max: largest value of the data set
        mode: value(s) that appear(s) most often in the data set
        mean: arithmetic average of the data set
       range: difference between the largest and smallest value in the data set
      median: value which is in the exact middle of the data set
    variance: measure of the spread of the data set about the mean
      stddev: standard deviation - measure of the dispersion of the data set
              based on variance

    identification: Instance ID

    Raised Exceptions:

       StatisticsException

    Bases Classes:

       object (builtin)

    Example Usage:

       x = [ -1, 0, 1 ]

       try:
          stats = Statistics(x)
       except StatisticsException, mesg:
          <handle exception>

       print "N: %s" % stats.N
       print "SUM: %s" % stats.sum
       print "MIN: %s" % stats.min
       print "MAX: %s" % stats.max
       print "MODE: %s" % stats.mode
       print "MEAN: %0.2f" % stats.mean
       print "RANGE: %s" % stats.range
       print "MEDIAN: %0.2f" % stats.median
       print "VARIANCE: %0.5f" % stats.variance
       print "STDDEV: %0.5f" % stats.stddev
       print "DATA LIST: %s" % stats.sample

    """
    def __init__(self, sample=[], population=False):
        """Statistics class initializer method."""

        # Raise an exception if the data set is empty.
        if (not sample):
            raise StatisticsException, "Empty data set!: %s" % sample

        # The data set (a list).
        self.sample = sample

        # Sample/Population variance determination flag.
        self.population = population

        self.N = len(self.sample)

        self.sum = float(sum(self.sample))

        self.min = min(self.sample)

        self.max = max(self.sample)

        self.range = self.max - self.min

        self.mean = self.sum/self.N

        # Inplace sort (list is now in ascending order).
        self.sample.sort()

        self.__getMode()

        # Instance identification attribute.
        self.identification = id(self)

    def __getMode(self):
        """Determine the most repeated value(s) in the data set."""

        # Initialize a dictionary to store frequency data.
        frequency = {}

        # Build dictionary: key - data set values; item - data frequency.
        for x in self.sample:
            if (x in frequency):
                frequency[x] += 1
            else:
                frequency[x] = 1

        # Create a new list containing the values of the frequency dict.  Convert
        # the list, which may have duplicate elements, into a set.  This will
        # remove duplicate elements.  Convert the set back into a sorted list
        # (in descending order).  The first element of the new list now contains
        # the frequency of the most repeated values(s) in the data set.
        # mode = sorted(list(set(frequency.values())), reverse=True)[0]
        # Or use the builtin - max(), which returns the largest item of a
        # non-empty sequence.
        mode = max(frequency.values())

        # If the value of mode is 1, there is no mode for the given data set.
        if (mode == 1):
            self.mode = []
            return

        # Step through the frequency dictionary, looking for values equaling
        # the current value of mode.  If found, append the value and its
        # associated key to the self.mode list.
        self.mode = [(x, mode) for x in frequency if (mode == frequency[x])]

    def __getVariance(self):
        """Determine the measure of the spread of the data set about the mean.
        Sample variance is determined by default; population variance can be
        determined by setting population attribute to True.
        """

        x = 0	# Summation variable.

        # Subtract the mean from each data item and square the difference.
        # Sum all the squared deviations.
        for item in self.sample:
            x += (item - self.mean)**2.0

        try:
            if (not self.population):
                # Divide sum of squares by N-1 (sample variance).
                self.variance = x/(self.N-1)
            else:
                # Divide sum of squares by N (population variance).
                self.variance = x/self.N
        except:
            self.variance = 0

    def __getStandardDeviation(self):
        """Determine the measure of the dispersion of the data set based on the
        variance.
        """

        from math import sqrt     # Mathematical functions.

        # Take the square root of the variance.
        self.stddev = sqrt(self.variance)


def extract_key_count(list, key=None):
    """
    A utility function written to count the number of times a `key` would appear in, for example, a categorized poll.
    Examples:
        >>> extract_key_count('yes',
    """

    if list and key:

        # go through a list of dictionaries
        for dict in list:
            if dict.get('category__name') == key:
                return dict.get('value')
    else:
        return 0


def poll_to_xform_submissions(message):
    pass
    return True


def get_week_count(reference_date, d):
    week_count = 0
    test_date = d
    temp = reference_date
    if reference_date > d:
        temp = d
        test_date = reference_date
    while temp.date() <= test_date.date():
        temp = dateutils.increment(temp,days=7)
        week_count+=1
    return week_count


def get_months(start_date,end_date):
    to_ret = []
    first_day = start_date
    while start_date.month < end_date.month:
        last_day = start_date + relativedelta(day=1, months=+1, days=-1,hour=23,minute=59)
        start_date += relativedelta(months=1)
        to_ret.append([
            datetime.datetime(first_day.year, first_day.month, first_day.day,first_day.hour,first_day.minute),
            datetime.datetime(last_day.year, last_day.month, last_day.day,last_day.hour,last_day.minute)])
        first_day = start_date + relativedelta(day=1,hour=00,minute=00)
    to_ret.append([
        datetime.datetime(first_day.year, first_day.month, first_day.day,first_day.hour,first_day.minute),
        datetime.datetime(end_date.year, end_date.month, end_date.day,end_date.hour,end_date.minute)])
    return to_ret