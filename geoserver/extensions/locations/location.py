#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8


from django.db import models
from rapidsms.contrib.locations.models import LocationType


class UUIDLocation(models.Model):
    """
    rapidsms.contrib.locations.nested makes the following assumptions about the
    needs of a deployment for its locations models:
        * They are concrete, heirarchical, and follow the same structure at every
          level (e.g. districts, subcounties, parishes, and towns are all
          more-or-less the same and serve solely as administrative boundaries.
        * They must be used for aggregation, and querying a subtree must be fast.
    This abstract class allows the default Location class in
    rapidsms.contrib.locations to inherit two additional fields:
     * type :
           As NestedLocations are concrete, they will have instances that
           may need to be differentiated by type.
     * tree_parent :
           As NestedLocations are uniformely typed, the need to have
           a non-generic relation to their parents.
    The MetaOverride attribute makes the base Location model concrete.
    """
    code = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

