import datetime
from poll.models import gettext_db, Response
from rapidsms.apps.base import AppBase
from rapidsms_httprouter.models import Message
from script.models import Script, ScriptProgress, ScriptSession, ScriptStep
from django.conf import settings
from script.utils.incoming import incoming_progress
from unregister.models import Blacklist
from uganda_common.utils import handle_dongle_sms
import logging
logger = logging.getLogger(__name__)
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
                ScriptProgress.objects.filter(connection=message.connection).delete() # delete all script progress since the user has quit
                ScriptSession.objects.filter(connection=message.connection, end_time=None).delete() # the non closed out sessions need to be expunged as well
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

        else:
            try:
                progress = ScriptProgress.objects.filter(connection=message.connection, time__lte=datetime.datetime.now()).order_by('-time')
                response_message_string = {"n":"The answer you have provided is not in the correct format. use figures like 3 to answer the question",
                                 "t":"The answer you have provided is not in the correct format. please follow instructions that were given to you"}
                if progress.count():
                    progress = progress[0]
                    script_last_step = ScriptStep.objects.filter(script=progress.script).order_by('-order')[0]
                    if progress.step and progress.step.order == script_last_step.order and progress.status == 'C':
                        return False
                    else:
                        response = incoming_progress(message)
                        if not progress.script.slug == 'edtrac_autoreg':
                            r = Response.objects.filter(contact__connection=message.connection,date__lte=datetime.datetime.now(),message__text=message.text).latest('date')
                            if r is not None:
                                if r.has_errors:
                                    progress.status = ScriptProgress.PENDING
                                    progress.save()
                                    Message.mass_text(response_message_string[r.poll.type], [message.connection])
                                    Message.mass_text(r.poll.question , [message.connection])
                        if response:
                            message.respond(gettext_db(response,progress.language))
                        return True
            except ScriptProgress.DoesNotExist:
                logger.debug("\nScript Progress object not found for message %s with connection %s" % (message,message.connection))
        return False
