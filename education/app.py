from rapidsms.apps.base import AppBase
from script.models import Script, ScriptProgress
from django.conf import settings
from unregister.models import Blacklist
from .models import EmisReporter

class App (AppBase):

    def handle (self, message):
        if message.text.strip().lower() in [i.lower() for i in getattr(settings, 'OPT_OUT_WORDS', ['quit'])]:
            Blacklist.objects.create(connection=message.connection)
            if (message.connection.contact):
                reporter = EmisReporter.objects.get(connection=message.connection)
                message.connection.contact.active = False
                message.connection.contact.save()
                reporter.active = False
                reporter.save()
            message.respond(getattr(settings, 'OPT_OUT_CONFIRMATION', 'Thank you for your contribution as a education monitoring reporter, to rejoin the system send JOIN to 6200'))
            return True
        elif message.text.strip().lower() in [i.lower() for i in getattr(settings, 'OPT_IN_WORDS', ['join'])]:
            if not message.connection.contact:
                ScriptProgress.objects.create(script=Script.objects.get(slug="emis_autoreg"), \
                                          connection=message.connection)
            elif Blacklist.objects.filter(connection=message.connection).count():
                Blacklist.objects.filter(connection=message.connection).delete()
                if not ScriptProgress.objects.filter(script__slug='emis_autoreg', connection=message.connection).count():
                    ScriptProgress.objects.create(script=Script.objects.get(slug="emis_autoreg"), \
                                          connection=message.connection)
            else:
                message.respond("You are already in the system and do not need to 'Join' again.")
            return True
        elif Blacklist.objects.filter(connection=message.connection).count():
            return True
        return False