# settings/production.py
import copy
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
    ('Kenneth', 'kbonky@gmail.com'),
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

LOGGING['handlers']['sentry'] = {
    'level': 'ERROR',
    'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
}
LOGGING['root'] = {
    'level': 'WARNING',
    'handlers': ['sentry'],
}
LOGGING['loggers']['raven'] = {
    'level': 'DEBUG',
    'handlers': ['console'],
    'propagate': False,
}
LOGGING['loggers']['sentry.errors'] = {
    'level': 'DEBUG',
    'handlers': ['console'],
    'propagate': False,
}

# raven docs say to put SentryResponseErrorIdMiddleware
# 'as high in the chain as possible'
# so this will insert raven into the top of the base
# settings.py file's MIDDLEWARE_CLASSES
TEMP = list(copy.copy(MIDDLEWARE_CLASSES))
TEMP.insert(0, 'raven.contrib.django.raven_compat.'
               'middleware.SentryResponseErrorIdMiddleware')
TEMP.append('raven.contrib.django.raven_compat.'
            'middleware.Sentry404CatchMiddleware')
MIDDLEWARE_CLASSES = tuple(TEMP)

INSTALLED_APPS += ["raven.contrib.django.raven_compat"]


RAVEN_CONFIG = {
    'dsn': 'https://879136a6744145b4b063231c453b286f:cd7b0c58e2864259befbcb974687e82c@sentry.unicefuganda.org/10728',
}
