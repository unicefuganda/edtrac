import datetime
import logging

from django.core.management.base import BaseCommand
import traceback
from rapidsms.models import Contact, Connection, Backend

from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router

from django.db import transaction

from rapidsms.messages.outgoing import OutgoingMessage

from script.utils.outgoing import check_progress
from script.models import ScriptProgress, Email
from optparse import OptionParser, make_option
import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.template import Context, Template

# Make sure a NullHandler is available
# This was added in Python 2.7/3.2
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass


logging.basicConfig(filename="script.log",level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(
              "script.log", maxBytes=5242880, backupCount=5)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
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
                router = get_router()
                for connection in ScriptProgress.objects.values_list('connection', flat=True).distinct():
                    try:
                        log_str=" PK:"+str(connection)
                        connection=Connection.objects.get(pk=connection)
                        script_p=ScriptProgress.objects.get(connection=connection)
                        log_str=log_str+" Step Before: "+str(script_p.step)
                        if script_p.step:
                            log_str=log_str+" start offset: "+str(script_p.step.start_offset)
                            
                        response = check_progress(connection)
                        log_str=log_str+" Step After: "+str(script_p.step)
                        log_str=log_str+"Response: "+str(response)
                        logger.info(log_str)
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
                        logger.debug(str(exc))
                        if recipients:
                            send_mail('[Django] Error: check_script_progress cron', str(traceback.format_exc(exc)), 'root@uganda.rapidsms.org', recipients, fail_silently=True)
                        continue