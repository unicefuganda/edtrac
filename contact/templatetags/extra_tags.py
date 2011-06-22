from django import template


def flags(msg):
    if len(msg.flags.all()) > 0:
        return True
    else:
        return False

register = template.Library()
register.filter('flags', flags)
