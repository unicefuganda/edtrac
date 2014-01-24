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

def schedule(connection, sender, get_day = date.today, roster = getattr(settings, 'POLL_DATES', {})):
    ScriptProgress.objects.filter(connection=connection, script=sender.script).delete()
    time = next_scheduled(sender.script.slug, roster=roster, get_day=get_day)

    if time:
        progress = ScriptProgress.objects.create(connection=connection, script=sender.script)
        progress.set_time(time)

def _at(date, oclock):
    return datetime.combine(date, time(oclock, 0, 0))

def _first(predicate, sequence):
    filtered = filter(predicate, sequence)
    return filtered[0] if filtered else None
