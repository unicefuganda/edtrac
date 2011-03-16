import rapidsms
import datetime

from rapidsms.apps.base import AppBase
from .models import Poll
from django.db.models import Q

class App (AppBase):

    def handle (self, message):
        # see if this contact matches any of our polls
        if (message.connection.contact):
            try:
                poll = Poll.objects.filter(contacts=message.connection.contact).exclude(start_date=None).filter(Q(end_date=None) | (~Q(end_date=None) & Q(end_date__gt=datetime.datetime.now()))).latest('start_date')
                response_obj, response_msg = poll.process_response(message)
                if hasattr(message, 'db_message'):
                    # if no other app handles this message, we want
                    # the handled_by field set appropriately,
                    # it won't since this app returns false
                    db_message = message.db_message
                    db_message.handled_by = 'poll'
                    db_message.save()
                message.respond(response_msg)
                # play nice, let other things handle responses
                return False
            except Poll.DoesNotExist:
                pass

        return False