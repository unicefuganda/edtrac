'''
Created on Sep 7, 2012

@author: asseym
'''
from django.core.management.base import BaseCommand
from optparse import OptionParser, make_option
from education.utils import _next_term_question_date
from rapidsms.models import Connection
from unregister.models import Blacklist
from script.models import Script, ScriptProgress

class Command(BaseCommand):
    
    option_list = BaseCommand.option_list + (
        make_option("-g", "--group", dest="group"),
        make_option("-s", "--script_name", dest="script_name"),
        make_option("-d", "--date", dest="date"),
    )
    def handle(self, **options):
        if not options['group']:
            group = raw_input('For which group? -- e.g SMC, Head Teachers, GEM:')
        else:
            group = options['group']
        group = None if options['group'] == 'All' else group
        if not options['script_name']:
            script_name = raw_input('For which script? -- e.g edtrac_smc_monthly:')
        else:
            script_name = options['script_name']
        if not options['date']:
            date = raw_input('Date for sending out questions? -- in the format yyyy-mm-dd:')
        else:
            date = options['date']
        
        connections = Connection.objects.filter(contact__emisreporter__groups__name__in=[group])
        script = Script.objects.get(slug=script_name)
        for connection in connections:
            try:
                Blacklist.objects.get(connection=connection)
                print '%s blacklisted! ' % connection.identity
            except Blacklist.DoesNotExist:
                try:
                    ScriptProgress.objects.get(connection=connection, script=script)
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