import datetime

from django.core.management.base import BaseCommand
import traceback
from rapidsms.models import Contact, Connection, Backend

from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import HttpRouter

from django.db import transaction

from rapidsms.messages.outgoing import OutgoingMessage

from script.utils.outgoing import check_progress
from script.models import ScriptProgress, Email
from optparse import OptionParser, make_option
import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.template import Context, Template

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-e", "--early", dest="e"),
        make_option("-l", "--late", dest="l")
    )

    @transaction.commit_manually
    def handle(self, **options):
        current = datetime.datetime.now()
        recipients = getattr(settings, 'ADMINS', None)
        if recipients:
            recipients = [email for name,email in recipients]
        if current.hour in range(int(options['e']),int(options['l'])):
                router = HttpRouter()
                for connection in ScriptProgress.objects.values_list('connection', flat=True).distinct():
                    try:
                        connection=Connection.objects.get(pk=connection)
                        response = check_progress(connection)
                        if response:
                            if type(response) == Email and connection.contact and connection.contact.user:
                                response.recipients.clear()
                                response.recipients.add(connection.contact.user)
                                response.send(context={'connection':connection})
                            else:
                                template = Template(response)
                                context = Context({'connection':connection})
                                router.add_outgoing(connection, template.render(context))
                        transaction.commit()
                        if datetime.datetime.now() - current > datetime.timedelta(seconds=35):
                            return
                    except Exception, exc:
                        transaction.rollback()
                        print traceback.format_exc(exc)
                        if recipients:
                            send_mail('[Django] Error: check_script_progress cron', str(traceback.format_exc(exc)), 'root@uganda.rapidsms.org', recipients, fail_silently=True)
                        continue