#!/usr/bin/env python
# vim: et ts=4 sw=4

# inherit everything from rapidsms, as default
# (this is optional. you can provide your own.)
from rapidsms.djangoproject.settings import *

# then add your django settings:

DATABASE_ENGINE = "sqlite3"
DATABASE_NAME = "db.sqlite3"

AJAX_PROXY_HOST='localhost'
AJAX_PROXY_PORT=8001

INSTALLED_APPS = (
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "django.contrib.auth",

    "rapidsms",
    "django.contrib.admin",

    "rapidsms.contrib.ajax",
    "rapidsms.contrib.httptester",

    "xforms",
    "test_extensions"
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

# default login redirect is back home
LOGIN_REDIRECT_URL = "/"

# default backends
INSTALLED_BACKENDS = {
    "message_tester" : {"ENGINE": "rapidsms.backends.bucket" } 
}

# configure our tabs
TABS = [
    ('rapidsms.views.dashboard', 'Dashboard'),
    ('rapidsms.contrib.httptester.views.generate_identity', 'Message Tester'),
#    ('rapidsms.contrib.messagelog.views.message_log', 'Message Log'),
    ('xforms.views.xforms', 'XForms'),
]
