from celery.task import Task, task
from .models import Message
from rapidsms.models import Backend, Connection
from rapidsms.apps.base import AppBase
from rapidsms.messages.incoming import IncomingMessage
from rapidsms.messages.outgoing import OutgoingMessage
from rapidsms.log.mixin import LoggerMixin
from threading import Lock, Thread

from urllib import quote_plus
from urllib2 import urlopen
import time
import re



@task
def handle_incoming(router,backend, sender, text,**kwargs):
    """
        Handles an incoming message.
        """
    # create our db message for logging
    db_message = router.add_message(backend, sender, text, 'I', 'R')

    # and our rapidsms transient message for processing
    msg = IncomingMessage(db_message.connection, text, db_message.date)

    # add an extra property to IncomingMessage, so httprouter-aware
    # apps can make use of it during the handling phase
    msg.db_message = db_message

    router.info("SMS[%d] IN (%s) : %s" % (db_message.id, msg.connection, msg.text))
    try:
        for phase in router.incoming_phases:
            router.debug("In %s phase" % phase)
            if phase == "default":
                if msg.handled:
                    router.debug("Skipping phase")
                    break

            for app in router.apps:
                router.debug("In %s app" % app)
                handled = False

                try:
                    func = getattr(app, phase)
                    handled = func(msg)

                except Exception, err:
                    import traceback
                    traceback.print_exc(err)
                    app.exception()

                # during the _filter_ phase, an app can return True
                # to abort ALL further processing of this message
                if phase == "filter":
                    if handled is True:
                        router.warning("Message filtered")
                        raise(StopIteration)

                # during the _handle_ phase, apps can return True
                # to "short-circuit" this phase, preventing any
                # further apps from receiving the message
                elif phase == "handle":
                    if handled is True:
                        router.debug("Short-circuited")
                        # mark the message handled to avoid the
                        # default phase firing unnecessarily
                        msg.handled = True
                        db_message.application = app
                        db_message.save()
                        break

                elif phase == "default":
                    # allow default phase of apps to short circuit
                    # for prioritized contextual responses.
                    if handled is True:
                        router.debug("Short-circuited default")
                        break

    except StopIteration:
        pass

    db_message.status = 'H'
    db_message.save()

    db_responses = []

    # now send the message responses
    while msg.responses:
        response = msg.responses.pop(0)
        router.handle_outgoing(response, db_message, db_message.application)

    # we are no longer interested in this message... but some crazy
    # synchronous backends might be, so mark it as processed.
    msg.processed = True

    return db_message

