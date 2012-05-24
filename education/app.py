import difflib
from rapidsms.apps.base import AppBase
from script.models import Script, ScriptProgress
from django.conf import settings
from unregister.models import Blacklist
from uganda_common.utils import handle_dongle_sms
from education.utils import poll_to_xform_submissions
from rapidsms_xforms.models import xform_received

class App (AppBase):

    def handle (self, message):
        if handle_dongle_sms(message):
            return True

        if message.text.strip().lower() in [i.lower() for i in getattr(settings, 'OPT_OUT_WORDS', ['quit'])]:

            if Blacklist.objects.filter(connection=message.connection).exists():
                message.respond('You cannot send Quit to 6200 (EduTrac) more than once.')
                return True
            else:
                if ScriptProgress.objects.filter(connection=message.connection, script__slug='edtrac_autoreg').exists():
                    # user is attempting to quit before completing registration
                    message.respond('Your registration is not complete, you can not quit at this point')
                    return True

                Blacklist.objects.create(connection=message.connection)
                ScriptProgress.objects.exclude(script__slug="edtrac_autoreg").filter(connection=message.connection).delete() # delete other script progress only place reporter to right one
                if (message.connection.contact):
                    message.connection.contact.active = False
                    message.connection.contact.save()
                message.respond(getattr(settings, 'OPT_OUT_CONFIRMATION', 'Thank you for your contribution to EduTrac. To rejoin the system, send join to 6200'))
                return True

        elif message.text.strip().lower() in [i.lower() for i in getattr(settings, 'OPT_IN_WORDS', ['join'])]:
            if not message.connection.contact:
                if ScriptProgress.objects.filter(script__slug='edtrac_autoreg', connection=message.connection).count() == 0:
                    ScriptProgress.objects.create(script=Script.objects.get(slug="edtrac_autoreg"),\
                        connection=message.connection)
                else:
                    message.respond("Your registration is not complete yet, you do not need to 'Join' again.")
            elif Blacklist.objects.filter(connection=message.connection).count():
                Blacklist.objects.filter(connection=message.connection).delete()
                if not ScriptProgress.objects.filter(script__slug='edtrac_autoreg', connection=message.connection).count():
                    ScriptProgress.objects.create(script=Script.objects.get(slug="edtrac_autoreg"),\
                        connection=message.connection)
            else:
                message.respond("You are already in the system and do not need to 'Join' again.")
            return True

        elif Blacklist.objects.filter(connection=message.connection).count():
            return True
            # when all else fails, quit!
        return False
