from datetime import date, time, timedelta, datetime
from django.conf import settings
from script.models import Script, ScriptProgress

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
    return _at(date, 10) if date else None

def schedule(connection, script, get_day = date.today, roster = getattr(settings, 'POLL_DATES', {})):
    """
    Schedules the script for the current connection according to roster.
    """
    time = next_scheduled(script.slug, roster=roster, get_day=get_day)
    schedule_at(connection, script, time)

def schedule_at(connection, script, time):
    """
    Schedules the script for the current connection, if time is set.
    """
    ScriptProgress.objects.filter(connection=connection, script=script).delete()
    if time:
        progress = ScriptProgress.objects.create(connection=connection, script=script)
        progress.set_time(time)

def schedule_all(connection, groups=getattr(settings, 'GROUPS', {}), get_day = date.today, roster = getattr(settings, 'POLL_DATES', {})):
    group = connection.contact.groups.all()[0]
    scripts = Script.objects.filter(slug = group.name)
    for script in scripts:
        schedule(connection, script, get_day=get_day, roster=roster)

def _at(date, oclock):
    return datetime.combine(date, time(oclock, 0, 0))

def _first(predicate, sequence):
    filtered = filter(predicate, sequence)
    return filtered[0] if filtered else None
