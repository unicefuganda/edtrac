import datetime
import time

def previous_calendar_week():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    return (start_date,end_date)


def previous_calendar_month():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)
    return (start_date,end_date)


def previous_calendar_quarter():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=90)
    return (start_date,end_date)

TIME_RANGES = {
    'w': previous_calendar_week,
    'm': previous_calendar_month,
    'q': previous_calendar_quarter

}
