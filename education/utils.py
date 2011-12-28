'''
Created on Sep 15, 2011

@author: asseym
'''
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
from django.conf import settings
from uganda_common.utils import *
from django.db.models import Avg

def previous_calendar_week(t=None):
    """
    To education monitoring, a week runs between Thursdays, 
    Thursday marks the beginning of a new week of data submission
    Data for a new week is accepted until Wednesday evenning of the following week
    """
    d = datetime.datetime.now()
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
    Find the date corresponding to day_offset of the month
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
    d = d + datetime.timedelta((3 - d.weekday()) % 7)
    in_holiday = True
    while in_holiday:
        in_holiday = False
        for start, end in holidays:
            if d >= start and d <= end:
                in_holiday = True
                break
        if in_holiday:
            d = d + datetime.timedelta(7)
    return d
    
def _date_of_monthday(day_offset):
    
    holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])
    d = next_relativedate(day_offset)
    if is_weekend(d):
        #next monday
        d = d + datetime.timedelta((0 - d.weekday()) % 7)
        
    in_holiday = True
    while in_holiday:
        in_holiday = False
        for start, end in holidays:
            if d >= start and d <= end:
                in_holiday = True
                break
        if in_holiday:
            d = next_relativedate(day_offset, 1)
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
    start_of_year = datetime.datetime(d.year + 1, 1, 1, d.hour, d.minute, d.second, d.microsecond)
#    if d <= start_of_year + datetime.timedelta(days=((3*30)+15)):
#        d = datetime.datetime(d.year, 4, 15, d.hour, d.minute, d.second, d.microsecond)
#    elif d > start_of_year + datetime.timedelta(days=((3*30)+15)) and d <= start_of_year + datetime.timedelta(days=((6*30)+15)):
#        d = datetime.datetime(d.year, 7, 15, d.hour, d.minute, d.second, d.microsecond)
#    elif d > start_of_year + datetime.timedelta(days=((6*30)+15)) and d <= start_of_year + datetime.timedelta(days=((10*30)+15)):
#        d = datetime.datetime(d.year, 11, 15, d.hour, d.minute, d.second, d.microsecond)
#    else:
#        d = datetime.datetime(d.year, 4, 15, d.hour, d.minute, d.second, d.microsecond)

    if d.month in [12, 1, 2, 3]:
        d = start_of_year + datetime.timedelta(days=((3*31)+15))
    elif d.month in [4, 5, 6]:
        d = start_of_year + datetime.timedelta(days=((6*31)+15))
    else:
        d = start_of_year + datetime.timedelta(days=((10*31)+15))
    
    if is_weekend(d):
        d = d + datetime.timedelta((0 - d.weekday()) % 7)
    in_holiday = True
    while in_holiday:
        in_holiday = False
        for start, end in holidays:
            if d >= start and d <= end:
                in_holiday = True
                break
        if in_holiday:
            if is_weekend(d):
                d = d + datetime.timedelta((0 - d.weekday()) % 7)
    return d

def _schedule_weekly_scripts(group, connection, grps):
    if group.name in grps:
        script_slug = "emis_%s" % group.name.lower().replace(' ', '_') + '_weekly'   
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
        d = _next_thursday(sp)    
        sp.set_time(d)
    
def _schedule_monthly_script(group, connection, script_slug, day_offset, role_names):
    if group.name in role_names:
        d = _date_of_monthday(day_offset)
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
        sp.set_time(d)

def _schedule_termly_script(group, connection, script_slug, role_names):
    if group.name in role_names:
        d = _next_midterm()
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
    """Average percentage"""
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
    from education.models import EmisReporter
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