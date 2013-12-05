#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
# encoding=utf-8

# -------------------------------------------------------------------- #
#                          PATH CONFIGURATION                          #
# -------------------------------------------------------------------- #
import sys
import os
import djcelery
from datetime import timedelta

filedir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(filedir))
sys.path.append(os.path.join(filedir, 'rapidsms', 'lib'))
sys.path.append(os.path.join(filedir, 'rapidsms_auth'))
sys.path.append(os.path.join(filedir, 'rapidsms_contact'))
sys.path.append(os.path.join(filedir, 'rapidsms_generic'))
sys.path.append(os.path.join(filedir, 'rapidsms_httprouter_src'))
sys.path.append(os.path.join(filedir, 'rapidsms_polls'))
sys.path.append(os.path.join(filedir, 'rapidsms_script'))
sys.path.append(os.path.join(filedir, 'rapidsms_uregister'))
sys.path.append(os.path.join(filedir, 'rapidsms_xforms_src'))
sys.path.append(os.path.join(filedir, 'django_eav'))
sys.path.append(os.path.join(filedir, 'rapidsms_uganda_common'))
sys.path.append(os.path.join(filedir, 'rapidsms_unregister'))
sys.path.append(os.path.join(filedir, 'rapidsms_edtrac'))
sys.path.append(os.path.join(filedir, 'rapidsms_geoserver'))
sys.path.append(os.path.join(filedir, 'django_reversion', 'src'))
sys.path.append(os.path.join(filedir, 'monitor_src'))
sys.path.append(os.path.join(filedir, 'django_simple_autocomplete'))
sys.path.append(os.path.join(filedir, 'endless'))

# -------------------------------------------------------------------- #
#                          MAIN CONFIGURATION                          #
# -------------------------------------------------------------------- #
#TIME_ZONE = "Africa/Kampala"
TIME_ZONE = None
ACTIVATION_CODE = '+START'
OPT_IN_WORDS = ['join']
OPT_OUT_WORDS = ['quit']
OPT_OUT_MESSAGE = 'You have just quit.If you want to re-register,or register to a new location,please send the word JOIN to 6767.'

# Responses bigger than this will be deemed to be errors.
PLAUSIBLY_LARGE = 5000
INVALID_RESPONSE = lambda response: (response.poll.type == 'n') \
                                and (response.eav.poll_number_value > PLAUSIBLY_LARGE)

# map bounding box
MIN_LON = '29.55322265625'
MAX_LON = '33.92578125'
MIN_LAT = '-1.0326589311777759'
MAX_LAT = '4.280680030820496'
# map categorized color pallete
CATEGORY_COLORS = ['#AA4643', '#4572A7', '#89A54E', '#80699B', '#3D96AE', '#DB843D', '#92A8CD', '#A47D7C', '#B5CA92']

# Modem numbers used by QoS
MODEM_NUMBERS = ['256777773260', '256752145316', '256711957281', '256790403038', '256701205129']

# you should configure your database here before doing any real work.
# see: http://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'edtrac',
        'USER': 'postgres',
        'HOST': 'dbserver',
    }
}
# the rapidsms backend configuration is designed to resemble django's
# database configuration, as a nested dict of (name, configuration).
#
# the ENGINE option specifies the module of the backend; the most common
# backend types (for a GSM modem or an SMPP server) are bundled with
# rapidsms, but you may choose to write your own.
#
# all other options are passed to the Backend when it is instantiated,
# to configure it. see the documentation in those modules for a list of
# the valid options for each.
INSTALLED_BACKENDS = {
    "message_tester": {
        "ENGINE": "rapidsms.backends.bucket",
    },
}


# to help you get started quickly, many django/rapidsms apps are enabled
# by default. you may wish to remove some and/or add your own.
INSTALLED_APPS = [

    "djtables",
    "mptt",
    "uni_form",
    # "debug_toolbar",
    "django_extensions",
    "rapidsms.contrib.handlers",
    "rapidsms.contrib.locations",
    "rapidsms.contrib.locations.nested",

    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "django.contrib.humanize",
    "script",
    "poll",
    "education",
    # the rapidsms contrib apps.
    "rapidsms.contrib.default",
    "eav",
    "auth",
    "rapidsms_httprouter",
    "uganda_common",
    "generic",
    "generic.reporting",
    "contact",
    "unregister",
    "rapidsms",
    "rapidsms_xforms",
    "reversion",
    "geoserver",
    "endless_pagination",
    "simple_autocomplete",
    "monitor",
    #leave south at the end of this list
    "south",

]

INSTALLED_APPS += ['celery', "djcelery"]

djcelery.setup_loader()
CELERY_ALWAYS_EAGER = True
TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'
BROKER_URL = "amqp://guest:guest@localhost:5672"
SIMPLE_AUTOCOMPLETE_MODELS = ('rapidsms.models.Connection')
#CELERY_ENABLE_UTC = True # enable this when rapidsms is stable on django 1.4
CELERY_TIMEZONE = 'Africa/Kampala'

CELERYBEAT_SCHEDULE = {
    'runs-every-5-minutes': {
        'task': 'tasks.CreateRecordEnrolledDeployedQuestionsAnswered',
        'schedule': timedelta(minutes=5)
    },
}


SMS_APPS = [
    "monitor",
    "education",
    "script",
    "poll"
]

# this rapidsms-specific setting defines which views are linked by the
# tabbed navigation. when adding an app to INSTALLED_APPS, you may wish
# to add it here, also, to expose it in the rapidsms ui.
RAPIDSMS_TABS = [
    # ('stats', 'Stats'),
    ("rapidsms-dashboard", 'Home')
]

gettext = lambda s: s
LANGUAGES = (('en', gettext('English')),)

"""
AUTHENTICATED_TABS = [
    ('deo-dashboard', 'District Summaries'),
    ('emis-messagelog', 'Messages'),
    ('emis-contact', 'Reporters'),
    ("emis-schools", "Schools"),
    ("emis-othermessages", "Other Messages"),
]
"""
AUTH_PROFILE_MODULE = 'education.UserProfile'

# -------------------------------------------------------------------- #
#                         BORING CONFIGURATION                         #
# -------------------------------------------------------------------- #


# debug mode is turned on as default, since rapidsms is under heavy
# development at the moment, and full stack traces are very useful
# when reporting bugs. don't forget to turn this off in production.
DEBUG = TEMPLATE_DEBUG = False


# after login (which is handled by django.contrib.auth), redirect to the
# dashboard rather than 'accounts/profile' (the default).
LOGIN_REDIRECT_URL = "/"
INTERNAL_IPS = ('127.0.0.1',)


# use django-nose to run tests. rapidsms contains lots of packages and
# modules which django does not find automatically, and importing them
# all manually is tiresome and error-prone.
TEST_RUNNER = "django_nose.NoseTestSuiteRunner"
SKIP_SOUTH_TESTS = True
SOUTH_TESTS_MIGRATE = False

# for some reason this setting is blank in django's global_settings.py,
# but it is needed for static assets to be linkable.
MEDIA_URL = "/static/"
ADMIN_MEDIA_PREFIX = "/static/media/"
# this is required for the django.contrib.sites tests to run, but also
# not included in global_settings.py, and is almost always ``1``.
# see: http://docs.djangoproject.com/en/dev/ref/contrib/sites/
SITE_ID = 1

SOUTH_TESTS_MIGRATE = False
# the default log settings are very noisy.
LOG_LEVEL = "DEBUG"
LOG_FILE = "rapidsms.log"
LOG_FORMAT = "[%(name)s]: %(message)s"
LOG_SIZE = 8192  # 8192 bits = 8 kb
LOG_BACKUPS = 256  # number of logs to keep


# this is used for geoserver to tell which website this viz should be for (and prevents clashing of
# polls across different websites with the same id
DEPLOYMENT_ID = 6

# these weird dependencies should be handled by their respective apps,
# but they're not, so here they are. most of them are for django admin.
TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    #"logistics.context_processors.base_template",
    "uganda_common.context_processors.authtabs",
    "generic.context_processors.map_params",
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'reversion.middleware.RevisionMiddleware',
)

#
#DEBUG_TOOLBAR_CONFIG = {
#    'INTERCEPT_REDIRECTS': False,
#}
# -------------------------------------------------------------------- #
#                           HERE BE DRAGONS!                           #
#        these settings are pure hackery, and will go away soon        #
# -------------------------------------------------------------------- #


# these apps should not be started by rapidsms in your tests, however,
# the models and bootstrap will still be available through django.
TEST_EXCLUDED_APPS = [
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rapidsms.contrib.ajax",
    "rapidsms.contrib.httptester",
]

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader'
)

# the project-level url patterns
ROOT_URLCONF = "urls"
XFORMS_HOST = 'edutrac.unicefuganda.org:8000'
MAP_KEY = "ABQIAAAAmd7V71yw9ZddA0s8Z3wSKBS0unaJrFIrP1vn6ZXHpuhFyvYAGhQprSjp88j18w-K_X23JU31jBikVg"
COUNTRY = "UG"
MESSAGELOG_APP = 'rapidsms_httprouter'
