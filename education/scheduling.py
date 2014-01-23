from datetime import date, timedelta

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

def _first(predicate, sequence):
    filtered = filter(predicate, sequence)
    return filtered[0] if filtered else None

