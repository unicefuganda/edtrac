import datetime

from .base import *


DEBUG = True
TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'edtrac',
        'USER': '',
        'HOST': '',
    }
}

INSTALLED_APPS += (
   'debug_toolbar',
)

MIDDLEWARE_CLASSES += (
   'debug_toolbar.middleware.DebugToolbarMiddleware',
)


INTERNAL_IPS += ('127.0.0.1', '::1')
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False
}


FIRST_TERM_BEGINS = datetime.datetime(2013, 2, 4)
SECOND_TERM_BEGINS = datetime.datetime(2013, 5, 27)
THIRD_TERM_BEGINS = datetime.datetime(2013, 9, 16)
SCHOOL_TERM_START = datetime.datetime(2013, 2, 4)
SCHOOL_TERM_END = datetime.datetime(2013, 5, 3)

SCHOOL_HOLIDAYS = [
    # (start_of_holiday_datetime, end_of_holidate_datetime),
    # (start_of_holiday2_datetime...),
    # (,),
    # ...
    #holiday season in 2012
    (datetime.datetime(2012, 4, 21), datetime.datetime(2012, 5, 13)),
    (datetime.datetime(2012, 8, 4), datetime.datetime(2012, 9, 2)),
    (datetime.datetime(2012, 12, 1), datetime.datetime(2013, 1, 30)),
    #public holidays
    (datetime.datetime(2012, 3, 8), '1d'), #Women's day
    (datetime.datetime(2012, 2, 26), '1d'), #Liberation day
    (datetime.datetime(2012, 4, 6), datetime.datetime(2012, 4, 9)), #Easter holiday
    (datetime.datetime(2012, 8, 19), '1d'), #Idd El Fitri
    (datetime.datetime(2012, 5, 1), '1d'), #Labor day
    (datetime.datetime(2012, 6, 3), '1d'), #Uganda Martyrs' Day
    (datetime.datetime(2012, 6, 9), '1d'), #Heroe's day
    (datetime.datetime(2012, 10, 26), '1d'), #Idd Adhua
    (datetime.datetime(2012, 10, 9), '1d'), #Independence Day
    (datetime.datetime(2012, 12, 25), datetime.datetime(2012, 12, 26)), #xmas holiday
]
