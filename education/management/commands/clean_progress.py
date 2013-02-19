'''
Created on Feb 19, 2013

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
        make_option("-s", "--script", dest="script"),
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
        if not options['script']:
            script = raw_input('Slug of script you wish to reschedule -- edtrac_p3_enrollment_headteacher_termly')
        else:
            script = options['script']
        
        connections = Connection.objects.filter(contact__emisreporter__groups__name__in=[group])
        script = Script.objects.get(slug=script)
        for connection in connections:
            try:
                Blacklist.objects.get(connection=connection)
                print '%s blacklisted! ' % connection.identity
            except Blacklist.DoesNotExist:
                try:
                    ScriptProgress.objects.filter(connection=connection, script=script).exclude(step=None)
                except ScriptProgress.DoesNotExist:
                    if date:
                        d = _next_term_question_date(date=date)
                    else:
                        if group == 'SMC':
                            d = _next_term_question_date(True)
                        else:
                            d = _next_term_question_date(False)
                            
                    sp = ScriptProgress.objects.create(script=script, connection=connection)
                    sp.set_time(d)
                    print 'ScriptProgress for %s created!!' % connection
                except ScriptProgress.MultipleObjectsReturned:
                    sps = ScriptProgress.objects.filter(connection=connection, script=script)
                    i = 0
                    for i in range(1, len(sps)):
                        sps[i].delete()
                        print 'Duplicate progress for %s deleted!!' % connection
        
        self.stdout.write('\n')
        self.stdout.write('Done')