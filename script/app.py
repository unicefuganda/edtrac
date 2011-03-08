import rapidsms
import datetime

from rapidsms.apps.base import AppBase
from script.utils import incoming_progress
from .models import *

class App (AppBase):

    def handle (self, message):
        try:
            progress = ScriptProgress.objects.get(connection=message.connection)
            script_last_step = Script.objects.get(slug=progress.script).order_by('-order')[0]
            if progress.step < script_last_step or progress.status == 'C':
                return False
            else:
                response = utils.incoming_progress(message)
                if response:
                    message.respond(response)
                return True
        except ScriptProgress.DoesNotExist:
            pass

        return False
