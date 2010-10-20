from django.db import models

from rapidsms.models import ContactBase

from simple_locations.models import Area

class LocatedContact(models.Model):
    """
    This extension for Contacts allows developers to tie a Contact to
    the Area object they're reporting from.  This extension
    depends on the simple_locations app.
    """
    reporting_location = models.ForeignKey(Area, blank=True, null=True)

    class Meta:
        abstract = True