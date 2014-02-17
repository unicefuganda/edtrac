#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

from django.contrib import admin
from .models import Location, LocationType


class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')
    list_filter = ('type', )
    model = Location
    search_field = ['name']


class LocationTypeAdmin(admin.ModelAdmin):
    model = LocationType


admin.site.register(Location, LocationAdmin)
admin.site.register(LocationType, LocationTypeAdmin)
