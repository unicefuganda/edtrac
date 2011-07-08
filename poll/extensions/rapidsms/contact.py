from django.db import models

from rapidsms.contrib.locations.models import Location

class LocatedContact(models.Model):
    """
    This extension for Contacts allows developers to tie a Contact to
    the Area object they're reporting from.  This extension
    depends on the simple_locations app.
    """
    reporting_location = models.ForeignKey(Location, blank=True, null=True)

    class Meta:
        abstract = True
