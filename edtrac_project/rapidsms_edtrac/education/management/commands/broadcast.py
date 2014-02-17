from django.core.management.base import BaseCommand
from optparse import make_option
from education.send import broadcast

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-t", "--text", dest="text"),
    )

    def handle(self, **options):
        text = options['text'] or raw_input('Text of the message: ')
        broadcast(text)
        self.stdout.write('Done!\n')
