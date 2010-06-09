#!/usr/bin/env python
# vim: et ts=4 sw=4


# inherit everything from rapidsms, as default
# (this is optional. you can provide your own.)
from rapidsms.djangoproject.settings import *


# then add your django settings:

DATABASE_ENGINE = "sqlite3"
DATABASE_NAME = "db.sqlite3"

INSTALLED_APPS = (
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "django.contrib.auth",

    "rapidsms",

    # enable admin using the rapidsms hack
    "rapidsms.contrib.djangoadmin",
    "django.contrib.admin",

    "xforms"
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

# default login redirect is back home
LOGIN_REDIRECT_URL = "/"
