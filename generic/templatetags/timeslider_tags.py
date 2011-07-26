#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import datetime
from django import template

register = template.Library()


@register.filter
def to_date(timestamp):
    """
    Turns a timestamp (milliseconds since 1970) into a 
    python Date object
    """
    return datetime.datetime.fromtimestamp(float(timestamp))


@register.filter
def year(date):
    """
    Gets the year (integer) from a date object.
    Necessary to pipe through the to_date filter.
    Example:
    {{ some_timestamp|to_date|year }}
    
    This doesn't work, unfortunately:
    {{ some_timestamp|to_date.year }}
    """
    return date.year


@register.filter
def month(date):
    """
    Gets the month (integer) from a date object.
    Necessary to pipe through the to_date filter.
    Example:
    {{ some_timestamp|to_date|month }}
    
    This doesn't work, unfortunately:
    {{ some_timestamp|to_date.month }}
    """
    return date.month


@register.filter
def day(date):
    """
    Gets the day of month (integer) from a date
    object.
    Necessary to pipe through the to_date filter.
    Example:
    {{ some_timestamp|to_date|day }}
    
    This doesn't work, unfortunately:
    {{ some_timestamp|to_date.day }}
    """
    return date.day



 