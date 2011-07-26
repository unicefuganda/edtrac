#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import datetime
from django import template

register = template.Library()


@register.filter
def to_date(timestamp):
   return datetime.datetime.fromtimestamp(float(timestamp) / 1000)


@register.filter
def year(date):
    return date.year


@register.filter
def month(date):
    return date.month


@register.filter
def day(date):
    return date.day



 