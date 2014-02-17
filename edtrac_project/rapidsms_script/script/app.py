from rapidsms.apps.base import AppBase
from script.utils.incoming import incoming_progress
from .models import *
from poll.models import gettext_db
import logging
logger = logging.getLogger(__name__)
class App (AppBase):

    def handle (self, message):
        try:
            progress = ScriptProgress.objects.filter(connection=message.connection, time__lte=datetime.datetime.now()).order_by('-time')
            if progress.count():
                progress = progress[0]
                script_last_step = ScriptStep.objects.filter(script=progress.script).order_by('-order')[0]
                if progress.step and progress.step.order == script_last_step.order and progress.status == 'C':
                    return False
                else:
                    response = incoming_progress(message)
                    if response:
                        message.respond(gettext_db(response,progress.language))
                    return True
        except ScriptProgress.DoesNotExist:
            logger.debug("\nScript Progress object not found for message %s with connection %s" % (message,message.connection))
            pass

        return False
