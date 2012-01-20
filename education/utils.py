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
        script_slug = "edtrac_%s" % group.name.lower().replace(' ', '_') + '_weekly'   
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
        d = _next_thursday(sp)    
        sp.set_time(d)
    
def _schedule_monthly_script(group, connection, script_slug, day_offset, role_names):
    if group.name in role_names:
        d = _date_of_monthday(day_offset)
        sp = ScriptProgress.objects.create(connection=connection, script=Script.objects.get(slug=script_slug))
        sp.set_time(d)

def _schedule_termly_script(group, connection, script_slug, role_names, date=None):
    d = None
    if date:
        now = datetime.datetime.now()
        dl = date.split('-')
        d = datetime.datetime(int(dl[0]), int(dl[1]), int(dl[2]), now.hour, now.minute, now.second, now.microsecond)
    if group.name in role_names:
        d = d if d else _next_midterm()
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

def fake_incoming_message(message, connection):
    from rapidsms.messages.incoming import IncomingMessage
    incomingmessage = IncomingMessage(connection, message)
    incomingmessage.db_message = Message.objects.create(direction='I', connection=connection, text=message)
    return incomingmessage
    
def fake_poll_responses(poll_tuple, grp):
    from education.models import EmisReporter
    import random
    yesno_resp = ['yes', 'no']
    text_resp = ['text response', 'text response2', 'text response3']
    poll = Poll.objects.get(name=poll_tuple[1])
    rep_count = EmisReporter.objects.filter(groups__name=grp).count()
    for rep in EmisReporter.objects.filter(groups__name=grp)[:random.randint(0, rep_count)]:
        if poll_tuple[0] == Poll.TYPE_NUMERIC:
            poll.process_response(fake_incoming_message(random.randint(0,90), rep.default_connection))
        else:
            if poll.categories.values_list('name', flat=True)[0] in ['yes', 'no', 'unknown']:
                resp = random.choice(yesno_resp)
            else:
                resp = random.choice(text_resp)
            poll.process_response(fake_incoming_message(resp, rep.default_connection))
