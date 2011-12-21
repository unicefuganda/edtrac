'''
Created on Nov 1, 2011

@author: asseym
'''

from django.core.management.base import BaseCommand
from education.models import reschedule_termly_polls
from optparse import OptionParser, make_option

class Command(BaseCommand):
    
    option_list = BaseCommand.option_list + (
        make_option("-d", "--date", dest="date"),
    )
    def handle(self, **options):
        if not options['date']:
            date = raw_input('Date when questions should be sent out -- YYYY-MM-DD:')
        else:
            date = options['date']
        reschedule_termly_polls(date)
        self.stdout.write('')
        self.stdout.write('done!')
