'''
Created on Feb 8, 2013

@author: raybesiga
'''

from django.core.management.base import BaseCommand
from education.models import reschedule_termly_script
from optparse import OptionParser, make_option

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-d", "--date", dest="date"),
        make_option("-g", "--group", dest="group"),
        make_option("-s", "--slug", dest="slug"),
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
        if not options['slug']:
            slug = raw_input('Slug of script you wish to reschedule -- edtrac_teacher_deployment_headteacher_termly')
        else:
            slug = 'edtrac_teacher_deployment_headteacher_termly'

        reschedule_termly_script(grp=group, date=date, slug=slug)
        self.stdout.write('')
        self.stdout.write('done!')
