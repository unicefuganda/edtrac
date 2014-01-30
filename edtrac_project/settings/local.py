import datetime

from .base import *

SITE_ID = 5
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
