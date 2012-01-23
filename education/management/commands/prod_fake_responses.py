from django.core.management.base import BaseCommand

def fake_incoming_message(message, connection):
    from rapidsms.messages.incoming import IncomingMessage
    incomingmessage = IncomingMessage(connection, message)
    incomingmessage.db_message = Message.objects.create(direction='I', connection=connection, text=message)
    return incomingmessage

def fake_poll_responses(poll_tuple, grp):
    from education.models import EmisReporter
    import random
    yesno_resp = ['yes', 'no']

    text_resp = ['0%', '25%', '50%', '75%', '100%']

    poll = Poll.objects.get(name=poll_tuple[1])
    rep_count = EmisReporter.objects.filter(groups__name=grp).count()

    for rep in EmisReporter.objects.filter(groups__name=grp):
        if rep.default_connection:
            if poll_tuple[0] == Poll.TYPE_NUMERIC:
                import pdb; pdb.set_trace()
                poll.process_response(fake_incoming_message('%s' % random.randint(0,90), rep.default_connection))
            elif poll_tuple[0] == Poll.TYPE_TEXT:
            #            if poll.categories.values_list('name', flat=True)[0] in ['yes', 'no', 'unknown']:
            #                resp = random.choice(yesno_resp)
            #            else:
                resp = random.choice(text_resp)
                poll.process_response(fake_incoming_message(resp, rep.default_connection))
            elif poll_tuple[0] == Poll.TYPE_CHOICES:
                pass
        else:
            pass

class Command(BaseCommand):
    def handle(self, *args, **options):
        poll_name = options.get('poll_name')
        grp = options.get('group')
        poll = Poll.objects.get(name=poll_name)
        from poll.models import Poll
        self.stdout('about to start creating fake responses')
        fake_poll_responses(
            (poll.type, poll.name),
            grp
        )
        self.stdout('finished creating fake responses...!')