import rapidsms

from rapidsms.apps.base import AppBase
from .models import Blacklist
from django.conf import settings
import re
class App (AppBase):

    def handle (self, message):
        #make sure the message is striped for example we want a user sendingh in "quit" to be seen as quit
        msg_txt=' '.join(re.findall(r'\w+',message.text.lower()))
        if msg_txt in getattr(settings,'OPT_IN_WORDS',[]) and Blacklist.objects.filter(connection=message.connection).count():
            for b in Blacklist.objects.filter(connection=message.connection):
                b.delete()
            message.respond(getattr(settings,'OPT_IN_CONFIRMATION',''))
            return True
        elif Blacklist.objects.filter(connection=message.connection).count():
            return True
        elif msg_txt in getattr(settings,'OPT_OUT_WORDS',[]):
            Blacklist.objects.create(connection=message.connection)
            message.respond(getattr(settings,'OPT_OUT_CONFIRMATION',''))
            return True
        return False

    def outgoing(self, msg):
        if Blacklist.objects.filter(connection=msg.connection).count():
            return False
        return True    