from django.core.management.base import BaseCommand
from optparse import make_option
from rapidsms_httprouter.router import get_router
from rapidsms.models import Connection

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-p", "--phone", dest="phone"),
        make_option("-t", "--text", dest="text"),
    )

    def handle(self, **options):
        if not options['phone']:
            phone = raw_input('Phone number you wish the message to appear to come from: ')
        else:
            phone = options['phone']

        if not options['text']:
            text = raw_input('Text of the message: ')
        else:
            text = options['text']

	connection  = Connection.object.get(identity = phone)
        router = get_router()
        handled = router.handle_incoming(connection.backend.name, connection.identity, text)
        self.stdout.write('Done!\n')
