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
            'NAME': 'edtrac_test',
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

SITE_ID=5

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
SPREADSHEETS_PATH = "/var/www/test_edutrac/edtrac/edtrac_project/rapidsms_edtrac/education/static/spreadsheets/"
LOG_LEVEL = "DEBUG"
LOG_SIZE = 8192  # 8192 bits = 8 kb
LOG_BACKUPS = 256  # number of logs to keep
LOG_FILE = '/var/log/edtrac/edtrac-test.log'
import logging
#logging.basicConfig(
#    level = logging.DEBUG,
#    format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
#    filename = LOG_FILE,
#)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 1800,
        'KEY_PREFIX': 'edutrac-test-',
    }
}
