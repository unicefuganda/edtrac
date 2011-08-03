import rapidsms
import datetime

from rapidsms.apps.base import AppBase
from script.utils.incoming import incoming_progress
from .models import *

class App (AppBase):

    def handle (self, message):
        try:
            progress = ScriptProgress.objects.filter(connection=message.connection).order_by('-time')
            if progress.count():
                progress = progress[0]
                script_last_step = ScriptStep.objects.filter(script=progress.script).order_by('-order')[0]
                if progress.step and progress.step.order == script_last_step.order and progress.status == 'C':
                    return False
                else:
                    response = incoming_progress(message)
                    if response:
                        message.respond(response)
                    return True
        except ScriptProgress.DoesNotExist:
            pass

        return False
