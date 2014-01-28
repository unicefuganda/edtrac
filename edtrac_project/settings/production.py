# settings/production.py
from .base import *

ROUTER_PASSWORD = 'k1pr0t1ch'
ROUTER_WORKERS = 1
DEBUG = False
TEMPLATE_DEBUG = DEBUG

EMAIL_HOST_USER = 'no-reply@uganda.rapidsms.org'
EMAIL_HOST = '127.0.0.1'
ADMINS = (
    ('Neil Couthinho', 'ncoutin@thoughtworks.com'),
    ('Chris Ford', 'cford@thoughtworks.com'),
    ('matlads', 'matlads@gmail.com'),
)
SMS_APPS = [
    "education",
    "script",
    "poll",
    "rapidsms_xforms",
]

DATABASES = {
        'default': {
            'ENGINE' : 'django.db.backends.postgresql_psycopg2',
            'NAME': 'edtrac',
            'USER': 'postgres',
            'HOST': 'dbserver',
            'PORT' : 6543
            #put a PORT in production
            },
        'geoserver':{
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "geoserver",
            "USER": "postgres",
            "HOST": "dbserver",
            'PORT': 6543,
            }
        }

BAD_WORDS=['fuck','shit','ass','damn','hell','nigger','cunt','fucker','fucking','motherfucker', 'shithead','tomanyiira','koma nyoko','ttumbavu','mussilu','bassilu',"wakalyaab'ewammwe",'mbwa gwe','ebinyo','mmana']

SITE_ID=5
import datetime
#All term schedulled polls are computed based on these dates
#these dates are necessary for the system to work properly and
#should be entered every beginning of year. See _next_term_question_date()
FIRST_TERM_BEGINS =  datetime.datetime(2013, 2, 4)
SECOND_TERM_BEGINS =  datetime.datetime(2013, 5, 27)
THIRD_TERM_BEGINS =  datetime.datetime(2013, 9, 16)

# Current term start and end dates
SCHOOL_TERM_START = SECOND_TERM_BEGINS
SCHOOL_TERM_END   = datetime.datetime(2013, 8, 23)

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

WORKER_SLEEP_SHORT=0.1
WORKER_SLEEP_LONG=0.25

LOGIN_URL = '/account/login/'
COUNTRY_CALLING_CODE = '256'
BACKEND_PREFIXES = [('','yo6200')]

#GEOSERVER_URL = "http://edtrac.unicefuganda.org/geoserver/"
GEOSERVER_URL="http://cvs.rapidsms.org/geoserver/"
#gettext = lambda s:s
#LANGUAGES = (('en', gettext('English'))
MODEM_NUMBERS = ['256777773260', '256752145316','256711957281', '256790403038','256701205129','256792197598']
#model containing blacklisted contacts
BLACKLIST_MODEL= "unregister.Blacklist"
SPREADSHEETS_PATH = "/var/www/prod_edutrac/edtrac/edtrac_project/rapidsms_edtrac/education/static/spreadsheets/"
LOG_LEVEL = "DEBUG"
LOG_SIZE = 8192  # 8192 bits = 8 kb
LOG_BACKUPS = 256  # number of logs to keep
LOG_FILE = '/var/log/edtrac/edtrac.log'
import logging
logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    filename = LOG_FILE,
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 1800,
        'KEY_PREFIX': 'edutrac-',
    }
}
