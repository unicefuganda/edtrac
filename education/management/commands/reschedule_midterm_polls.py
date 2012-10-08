'''
Created on Nov 1, 2011

@author: asseym
'''

from django.core.management.base import BaseCommand
from education.models import reschedule_midterm_polls
from optparse import OptionParser, make_option

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-d", "--date", dest="date"),
        make_option("-g", "--group", dest="group"),
    )
    
    def handle(self, **options):
        if not options['date']:
            date = raw_input('Date when questions should be sent out -- YYYY-MM-DD:')
        else:
            date = options['date']
        if not options['group']:
            group = raw_input('Group -- SMC or Head Teachers:')
        else:
            group = 'all'

        reschedule_midterm_polls(grp=group, date=date)
        self.stdout.write('')
        self.stdout.write('done!')
