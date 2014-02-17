#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.db import models
class Location(models.Model):
    """
    Location - the main concept of a location.  Currently covers MOHSW, Regions, Districts and Facilities.
    This could/should be broken out into subclasses.
    """
    status = models.NullBooleanField(default=True,null=True,blank=True)
    code = models.CharField(max_length=100, blank=False, null=False)
    is_active = models.NullBooleanField(default=True,null=True,blank=True)
    class Meta:
        abstract = True

