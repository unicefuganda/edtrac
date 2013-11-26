from .base import *
import djcelery

# ROUTER_PASSWORD = 'p73TestP'
ROUTER_WORKERS = 1
DEBUG = True
TEMPLATE_DEBUG = DEBUG

EMAIL_HOST_USER = 'no-reply@uganda.rapidsms.org'
EMAIL_HOST = '127.0.0.1'
ADMINS = (
    ('Martin Atukunda', 'matlads@localhost'),
)

SMS_APPS += [
    "rapidsms_xforms",
]

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'reversion.middleware.RevisionMiddleware',
)

INSTALLED_APPS += (
    "debug_toolbar",
    # "latrine_stances",
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'edtrac',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}


BAD_WORDS = ['fuck', 'shit', 'ass', 'damn', 'hell', 'nigger', 'cunt', 'fucker', 'fucking', 'motherfucker', 'shithead',
             'tomanyiira', 'koma nyoko', 'ttumbavu', 'mussilu', 'bassilu', "wakalyaab'ewammwe", 'mbwa gwe', 'ebinyo',
             'mmana']

SITE_ID = 2
import datetime

TRAINING_MODE = False
#All term schedulled polls are computed based on these dates
#these dates are necessary for the system to work properly and
#should be entered every beginning of year. See _next_term_question_date()
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

WORKER_SLEEP_SHORT = 0.1
WORKER_SLEEP_LONG = 0.25

LOGIN_URL = '/account/login/'
COUNTRY_CALLING_CODE = '256'
BACKEND_PREFIXES = [('', 'yo6200')]

#GEOSERVER_URL = "http://edtrac.unicefuganda.org/geoserver/"
GEOSERVER_URL = "http://cvs.rapidsms.org/geoserver/"
#gettext = lambda s:s
#LANGUAGES = (('en', gettext('English'))
MODEM_NUMBERS = ['256777773260', '256752145316', '256711957281', '256790403038', '256701205129', '256792197598']
#model containing blacklisted contacts
BLACKLIST_MODEL = "unregister.Blacklist"

SECRET_KEY = 'da9ajla_)98J'
STATIC_URL = '/static/'
TEMPLATE_CONTEXT_PROCESSORS += [
    'django.contrib.messages.context_processors.messages'
]

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}
