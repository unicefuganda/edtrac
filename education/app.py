from rapidsms.apps.base import AppBase
from script.models import Script, ScriptProgress
from django.conf import settings
from unregister.models import Blacklist
from .models import EmisReporter

class App (AppBase):

    def handle (self, message):
        if message.text.strip().lower() in [i.lower() for i in getattr(settings, 'OPT_OUT_WORDS', ['quit'])]:
            if Blacklist.objects.filter(connection=message.connection).exists():
                message.respond('You cannot send Quit to 6200 (EduTrac) more than once.')
                return
            else:
                # create a Blacklist object
                Blacklist.objects.create(connection=message.connection)

                if (message.connection.contact):
                    reporter = EmisReporter.objects.get(connection=message.connection)
                    message.connection.contact.active = False
                    message.connection.contact.save()
                    reporter.active = False
                    reporter.save()
                message.respond(getattr(settings, 'OPT_OUT_CONFIRMATION', 'Thank you for your contribution to EduTrac. To rejoin the system, send join to 6200'))
                return True

        elif message.text.strip().lower() in [i.lower() for i in getattr(settings, 'OPT_IN_WORDS', ['join'])]:

            # check if incoming connection is Blacklisted (previously quit)
            if Blacklist.objects.filter(connection=message.connection).exists():
                Blacklist.objects.filter(connection=message.connection).delete()
                # create a ScriptProgress object if it does not exist
                # this throws the user back to autoreg
                if not ScriptProgress.objects.filter(script__slug='edtrac_autoreg', connection=message.connection).exists():
                    ScriptProgress.objects.create(script=Script.objects.get(slug="edtrac_autoreg"),\
                        connection=message.connection, language="en")
                else:
                    # what if we deleted existing progresses and recreated them?
                    ScriptProgress.objects.filter(script=Script.objects.get(slug="edtrac_autoreg"),\
                        connection = message.connection, language="en").delete()
                    # recreating or getting an existing in case it creeps in
                    ScriptProgress.objects.get_or_create(script=Script.objects.get(slug="edtrac_autoreg"),\
                        connection=message.connection, language="en")
            # For users joining edtrac the first time
            else:
                # check that the user is not in the system
                if not message.connection.contact:
                    # dump the user into autoreg
                    ScriptProgress.objects.get_or_create(script=Script.objects.get(slug="edtrac_autoreg"), \
                        connection=message.connection, language="en")
                else:
                    # otherwise, chances are this user already exists in the system
                    message.respond("You are already in the system and do not need to 'Join' again.")
            # quit this.
            return True

        elif Blacklist.objects.filter(connection=message.connection).count():
            return True
        # when all else fails, quit!
        return False