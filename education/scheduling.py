from datetime import date, time, timedelta, datetime
from django.conf import settings
from script.models import Script, ScriptProgress
from rapidsms.models import Connection
from django.contrib.auth.models import Group

def upcoming(dates, get_day = date.today):
    """
    Returns the next date, or None.
    """
    return _first(lambda d: d > get_day(), dates)

def current_period(dates, get_day = date.today):
    """
    Returns a tuple of the current period, with a non-inclusive end date.

    Either element in the tuple may be None, for open intervals.
    """
    start = _first(lambda d: d <= get_day(), dates)
    end = _first(lambda d: d > get_day(), dates)
    return (start, end - timedelta(days=1) if end else None)

def next_scheduled(poll_id, roster=getattr(settings, 'POLL_DATES', {}), get_day = date.today):
    """
    Returns the datetime the specified poll should next run on.
    """
    dates = roster.get(poll_id) or []
    date = upcoming(dates, get_day = get_day)
    return at(date, 10) if date else None

def schedule(connection, script, get_day = date.today, roster = getattr(settings, 'POLL_DATES', {})):
    """
    Schedules the script for the current connection according to roster.
    """
    time = next_scheduled(script.slug, roster=roster, get_day=get_day)
    schedule_at(connection, script, time)

def schedule_script(script, get_day = date.today, groups=getattr(settings, 'GROUPS', {}), roster = getattr(settings, 'POLL_DATES', {})):
    """
    Schedules the script for each connection belonging to a subscribed group.
    """
    names = [name for name in groups.keys() if script.slug in groups.get(name)]
    connections = Connection.objects.filter(contact__groups__name__in = names)

    for connection in connections:
        schedule(connection, script, get_day=get_day, roster=roster)

def schedule_at(connection, script, time):
    """
    Schedules the script for the connection, if time is set.
    """
    ScriptProgress.objects.filter(connection=connection, script=script).delete()
    if time:
        progress = ScriptProgress.objects.create(connection=connection, script=script)
        progress.set_time(time)

def schedule_all(connection, groups=getattr(settings, 'GROUPS', {}), get_day = date.today, roster = getattr(settings, 'POLL_DATES', {})):
    """
    Schedules all scripts the connection is subscribed to.
    """
    scripts = Script.objects.filter(slug__in = scripts_for(connection, groups=groups))
    for script in scripts:
        schedule(connection, script, get_day=get_day, roster=roster)

def scripts_for(connection, groups = getattr(settings, 'GROUPS', {})):
    """
    Returns slugs for all the scripts the connection is subscribed to.
    """
    names = [group.name for group in connection.contact.groups.all()]
    grade = connection.contact.emisreporter.grade

    if 'Teachers' in names and grade:
        names.append(grade.lower())

    slug_lists = [groups.get(name) or [] for name in names]
    return reduce(list.__add__, slug_lists)

def at(date, oclock):
    return datetime.combine(date, time(oclock, 0, 0))

def _first(predicate, sequence):
    filtered = filter(predicate, sequence)
    return filtered[0] if filtered else None
