from django import template
from contact.models import MessageFlag


def flags(msg):
    if MessageFlag.objects.filter(message__pk=msg.pk).count() > 0:
        return True
    else:
        return False

register = template.Library()
register.filter('flags', flags)
