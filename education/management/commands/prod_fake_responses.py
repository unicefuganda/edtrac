from django.core.management.base import BaseCommand
from poll.models import Poll
from rapidsms.messages.incoming import IncomingMessage
from education.models import EmisReporter
from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router
import random


def fake_incoming_message(message, connection):
    incomingmessage = IncomingMessage(connection, message)
    #router = get_router()
    #router.handle_incoming(connection.backend.name, connection.identity, message)
    
    incomingmessage.db_message = Message.objects.create(direction='I', connection=connection, text=message)
    incomingmessage.db_message.handled_by = 'poll'
    return incomingmessage

def fake_poll_responses(poll_tuple, grp):
    yesno_resp = ['yes', 'no']
    text_resp = ['0%', '25%', '50%', '75%', '100%']
    poll = Poll.objects.get(name=poll_tuple[1])
    rep_count = EmisReporter.objects.filter(groups__name=grp).count()

    for rep in EmisReporter.objects.filter(groups__name=grp)[:rep_count/4]:
        if not rep.default_connection == None:
            if poll_tuple[0] == Poll.TYPE_NUMERIC:
                poll.process_response(fake_incoming_message('%s' % random.randint(0,90), rep.default_connection))
            elif poll_tuple[0] == Poll.TYPE_TEXT:
            #            if poll.categories.values_list('name', flat=True)[0] in ['yes', 'no', 'unknown']:
            #                resp = random.choice(yesno_resp)
            #            else:
                resp = random.choice(text_resp)
                poll.process_response(fake_incoming_message(resp, rep.default_connection))
            elif poll_tuple[0] == Poll.TYPE_CHOICES:
                pass
        #just ignore folks with no default connection
        pass

class Command(BaseCommand):
    def handle(self, *args, **options):
        poll_name = args[0]
        grp = args[1]
        poll = Poll.objects.get(name=poll_name)
        fake_poll_responses(
            (poll.type, poll.name),
            grp
        )
        print "finished creating responses"