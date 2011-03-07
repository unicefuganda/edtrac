from eav.models import Attribute
from django.contrib.sites.models import Site
from django.conf import settings

site_table_created=False

def init_attributes(sender, **kwargs):
    global site_table_created
    if sender.__name__ == 'django.contrib.sites.models':
        site_table_created = True

    if site_table_created:
        if settings.SITE_ID and Site.objects.filter(pk=settings.SITE_ID).count():
            Attribute.objects.get_or_create(slug="poll_number_value", 
                defaults={
                    "slug": "poll_number_value",
                    "name": "Number",
                    "description": "A response value for a Poll with expected numeric responses",
                    "datatype": "float",
                }
            )
            Attribute.objects.get_or_create(slug='poll_text_value',
                defaults={
                    "name": "Text",
                    "description": "A response value for a Poll with expected text responses",
                    "datatype": "text",              
                }
            )
            Attribute.objects.get_or_create(slug='poll_location_value',
                defaults={
                    "name": "Location",
                    "description": "A response value for a Poll with expected location-based responses",
                    "datatype": "object",
                }
            )
            Attribute.objects.get_or_create(slug='contact_location',
                defaults={
                    "name": "Location",
                    "description": "The location associated with a particular contact",
                    "datatype": "object",
                }
            )