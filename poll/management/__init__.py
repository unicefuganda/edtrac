from django.db.models.signals import post_syncdb
from django.contrib.sites.models import Site
from django.conf import settings
from django.db import connection
from eav.models import Attribute

def create_attributes(app):

    if not db_table_exists("eav_attribute"):
        return

    Attribute.on_site.get_or_create(slug="poll_number_value",
        defaults={
            "slug": "poll_number_value",
            "name": "Number",
            "description": "A response value for a Poll with expected numeric responses",
            "datatype": "float",
        }
    )
    Attribute.on_site.get_or_create(slug='poll_text_value',
        defaults={
            "name": "Text",
            "description": "A response value for a Poll with expected text responses",
            "datatype": "text",
        }
    )
    Attribute.on_site.get_or_create(slug='poll_location_value',
        defaults={
            "name": "Location",
            "description": "A response value for a Poll with expected location-based responses",
            "datatype": "object",
        }
    )
    Attribute.on_site.get_or_create(slug='contact_location',
        defaults={
            "name": "Location",
            "description": "The location associated with a particular contact",
            "datatype": "object",
        }
    )

def init_attributes(sender, **kwargs):
    site_table_created = False

    if sender.__name__ == 'django.contrib.sites.models':
        site_table_created = True
    elif 'django.contrib.sites' not in settings.INSTALLED_APPS:
        site_table_created = True

    if site_table_created:
        if 'django.contrib.sites' not in settings.INSTALLED_APPS or (getattr(settings, 'SITE_ID', False) and Site.objects.filter(pk=settings.SITE_ID).count()):
            create_attributes(sender)

def db_table_exists(table_name):
    return table_name in connection.introspection.table_names()

post_syncdb.connect(init_attributes, weak=True)
