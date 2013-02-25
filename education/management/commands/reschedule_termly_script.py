'''
Created on Feb 8, 2013

@author: raybesiga
'''

from django.core.management.base import BaseCommand
from education.models import reschedule_termly_script
from optparse import OptionParser, make_option
from education.utils import _next_term_question_date
from rapidsms.models import Connection
from unregister.models import Blacklist
from script.models import Script, ScriptProgress

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
            slug = raw_input('Slug of script you wish to reschedule -- edtrac_p3_enrollment_headteacher_termly')
        else:
            slug = options['slug']
            
        reschedule_termly_script(grp=group, date=date, slug=slug)    
        self.stdout.write('')
        self.stdout.write('done!')

#        reschedule_termly_script(grp=group, date=date, slug=slug)
#        self.stdout.write('')
#        self.stdout.write('done!')
        
#        connections = Connection.objects.filter(contact__emisreporter__groups__name__in=[group])
#        script = Script.objects.get(slug=slug)
#        for connection in connections:
#            try:
#                Blacklist.objects.get(connection=connection)
#                print '%s blacklisted! ' % connection.identity
#            except Blacklist.DoesNotExist:
#                try:
#                    ScriptProgress.objects.get(connection=connection, script=script)
#                except ScriptProgress.DoesNotExist:
#                    sp = ScriptProgress.objects.create(script=script, connection=connection)
#                    print 'ScriptProgress for %s created!!' % connection
#                except ScriptProgress.MultipleObjectsReturned:
#                    sps = ScriptProgress.objects.filter(connection=connection, script=script)
#                    i = 0
#                    for i in range(1, len(sps)):
#                        sps[i].delete()
#                        print 'Duplicate progress for %s deleted!!' % connection
#        
#        self.stdout.write('\n')
#        self.stdout.write('Done')
        
