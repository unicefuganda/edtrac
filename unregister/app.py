import rapidsms

from rapidsms.apps.base import AppBase
from .models import Blacklist
from django.conf import settings

class App (AppBase):

    def handle (self, message):
        if Blacklist.objects.filter(connection=message.connection).count():
            return True
        elif message.text.strip() in settings.OPT_OUT_WORDS:
            Blacklist.objects.create(connection=message.connection)
            message.respond(settings.OPT_OUT_CONFIRMATION)
            return True
        return False

    def outgoing(self, msg):
        if Blacklist.objects.filter(connection=msg.connection).count():
            return False
        return True    