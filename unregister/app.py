import rapidsms

from rapidsms.apps.base import AppBase
from .models import Blacklist

class App (AppBase):

    def handle (self, message):
        if Blacklist.objects.filter(connection=message.connection).count():
            return True
        return False

    def outgoing(self, msg):
        if Blacklist.objects.filter(connection=msg.connection).count():
            return False
        return True    