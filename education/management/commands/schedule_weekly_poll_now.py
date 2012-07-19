
from django.core.management.base import BaseCommand
from education.models import reschedule_weekly_polls_now
from optparse import OptionParser, make_option

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-g", "--group", dest="group"),
        )
    def handle(self, **options):
        if not options['group']:
            group = raw_input('For which group? -- Teachers, SMC, Head Teachers:')
        else:
            group = options['group']
        reschedule_weekly_polls_now(group)
        self.stdout.write('')
        self.stdout.write('Done')
