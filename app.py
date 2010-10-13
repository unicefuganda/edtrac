import rapidsms

from rapidsms.apps.base import AppBase
from .models import Poll

class App (AppBase):

    def handle (self, message):
        # see if this contact matches any of our polls
        if (message.connection.contact):
            try:
                poll = Poll.objects.filter(contacts=message.connection.contact).exclude(started=None).latest('started')
                response = poll.process_response(message)    
                message.respond(response)
                return True
            except Poll.DoesNotExist:
                pass

        return False