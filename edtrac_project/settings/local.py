import datetime

from .base import *


DEBUG = True
TEMPLATE_DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'edtrac',
        'USER': 'postgres',
        'HOST': 'localhost',
    }
}

INSTALLED_APPS += (
   'django.contrib.staticfiles',
   'debug_toolbar',
)

MIDDLEWARE_CLASSES += (
   'debug_toolbar.middleware.DebugToolbarMiddleware',
)

STATIC_URL = '/assets/'

INTERNAL_IPS += ('127.0.0.1', '::1')
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False
}

#All term schedulled polls are computed based on these dates
#these dates are necessary for the system to work properly and
#should be entered every beginning of year. See _next_term_question_date()
FIRST_TERM_BEGINS =  datetime.datetime(2013, 2, 4)
SECOND_TERM_BEGINS =  datetime.datetime(2013, 5, 27)
THIRD_TERM_BEGINS =  datetime.datetime(2013, 9, 16)

#second term start and end dates

SCHOOL_TERM_START=datetime.datetime(2013, 5,27)
SCHOOL_TERM_END = datetime.datetime(2013, 8,23)

SCHOOL_HOLIDAYS=[
    # (start_of_holiday_datetime, end_of_holidate_datetime),
    # (start_of_holiday2_datetime...),
    # (,),
    # ...
    #holiday season in 2013
    (datetime.datetime(2013, 5, 4), datetime.datetime(2013, 5, 26)),
    (datetime.datetime(2013, 8, 24), datetime.datetime(2013, 9, 15)),
    (datetime.datetime(2013, 12, 7), datetime.datetime(2014, 2, 2)),
    #public holidays
    (datetime.datetime(2013, 3, 8), '1d'), #Women's day
    (datetime.datetime(2013, 1, 26), '1d'), #Liberation day
    (datetime.datetime(2013, 3, 29), datetime.datetime(2013, 4, 1)), #Easter holiday
    (datetime.datetime(2013, 8, 8), '1d'), #Idd El Fitri
    (datetime.datetime(2013, 5, 1), '1d'), #Labor day
    (datetime.datetime(2013, 6, 3), '1d'), #Uganda Martyrs' Day
    (datetime.datetime(2013, 6, 9), '1d'), #Heroe's day
    (datetime.datetime(2013, 10, 15), '1d'), #Idd Adhua
    (datetime.datetime(2013, 10, 9), '1d'), #Independence Day
    (datetime.datetime(2013, 12, 25), datetime.datetime(2013, 12, 26)), #xmas holiday
]
