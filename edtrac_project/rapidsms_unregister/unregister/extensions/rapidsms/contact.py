from django.db import models

from rapidsms.models import ContactBase

class ActivatedcContact(models.Model):
    """
    This extension for Contacts allows developers to tie a Contact to
    the Location object they're reporting from.
    """
    active = models.BooleanField(default=False)

    class Meta:
        abstract = True