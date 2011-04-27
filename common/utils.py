import datetime
import time

def previous_calendar_week():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    return time.mktime(start_date.timetuple()), time.mktime(end_date.timetuple())


def previous_calendar_month():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)
    return time.mktime(start_date.timetuple()), time.mktime(end_date.timetuple())


def previous_calendar_quarter():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=90)
    return time.mktime(start_date.timetuple()), time.mktime(end_date.timetuple())

TIME_RANGES = {
    'w': previous_calendar_week,
    'm': previous_calendar_month,
    'q': previous_calendar_quarter

}
