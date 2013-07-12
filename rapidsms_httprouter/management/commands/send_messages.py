import traceback
import time
from django.core.management.base import BaseCommand
from rapidsms.models import Backend, Connection, Contact
from rapidsms_httprouter.models import Message, MessageBatch
from rapidsms_httprouter.router import get_router
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction, close_connection
from urllib import quote_plus
from urllib2 import urlopen
from rapidsms.log.mixin import LoggerMixin

class Command(BaseCommand, LoggerMixin):

    help = """sends messages from all project DBs
    """

    def fetch_url(self, url):
        """
        Wrapper around url open, mostly here so we can monkey patch over it in unit tests.
        """
        response = urlopen(url, timeout=15)
        return response.getcode()


    def build_send_url(self, router_url, backend, recipients, text, priority=1, **kwargs):
        """
        Constructs an appropriate send url for the given message.
        """
        # first build up our list of parameters
        params = {
            'backend': backend,
            'recipient': recipients,
            'text': text,
            'priority': priority,
        }

        # make sure our parameters are URL encoded
        params.update(kwargs)
        for k, v in params.items():
            try:
                params[k] = quote_plus(str(v))
            except UnicodeEncodeError:
                params[k] = quote_plus(str(v.encode('UTF-8')))

        # is this actually a dict?  if so, we want to look up the appropriate backend
        if type(router_url) is dict:
            router_dict = router_url
            backend_name = backend

            # is there an entry for this backend?
            if backend_name in router_dict:
                router_url = router_dict[backend_name]

            # if not, look for a default backend 
            elif 'default' in router_dict:
                router_url = router_dict['default']

            # none?  blow the hell up
            else:
                self.error("No router url mapping found for backend '%s', check your settings.ROUTER_URL setting" % backend_name)
                raise Exception("No router url mapping found for backend '%s', check your settings.ROUTER_URL setting" % backend_name)

        # return our built up url with all our variables substituted in
        full_url = router_url % params

        return full_url


    def send_backend_chunk(self, router_url, pks, backend_name, priority):
        msgs = Message.objects.using(self.db_key).filter(pk__in=pks).exclude(connection__identity__iregex="[a-z]")
        try:
            url = self.build_send_url(router_url, backend_name, ' '.join(msgs.values_list('connection__identity', flat=True)), msgs[0].text, priority=str(priority))
            status_code = self.fetch_url(url)

            # kannel likes to send 202 responses, really any
            # 2xx value means things went okay
            if int(status_code / 100) == 2:
                self.info("SMS%s SENT" % pks)
                msgs.update(status='S')
            else:
                self.info("SMS%s Message not sent, got status: %s .. queued for later delivery." % (pks, status_code))
                msgs.update(status='Q')

        except Exception as e:
            self.error("SMS%s Message not sent: %s .. queued for later delivery." % (pks, str(e)))
            msgs.update(status='Q')


    def send_all(self, router_url, to_send, priority):
        pks = []
        if len(to_send):
            backend_name = to_send[0].connection.backend.name
            for msg in to_send:
                if backend_name != msg.connection.backend.name:
                    # send all of the same backend
                    self.send_backend_chunk(router_url, pks, backend_name, priority)
                    # reset the loop status variables to build the next chunk of messages with the same backend
                    backend_name = msg.connection.backend.name
                    pks = [msg.pk]
                else:
                    pks.append(msg.pk)
            self.send_backend_chunk(router_url, pks, backend_name, priority)

    def send_individual(self, router_url, priority=1):
        to_process = Message.objects.using(self.db_key).filter(direction='O',
                          status__in=['Q'], batch=None).order_by('priority', 'status', 'connection__backend__name', 'id') #Order by ID so that they are FIFO in absence of any other priority
        if len(to_process):
            self.debug("found [%d] individual messages to proccess, sending the first one..." % len(to_process))
            self.send_all(router_url, [to_process[0]], priority)
        else:
            self.debug("found no individual messages to process")


    def process_messages_for_db(self, CHUNK_SIZE, db_key, router_url):
        self.db_key = db_key
        self.debug("looking for MessageBatch's to process with db [%s]" % str(db_key))
        to_process = MessageBatch.objects.using(db_key).filter(status='Q')

        if to_process.count():
            self.info("found [%d] batches with status [Q] in db [%s] to process" % (to_process.count(), db_key))
            batch = to_process[0]
            priority = batch.priority
            to_process = batch.messages.using(db_key).filter(direction='O',
                status__in=['Q']).order_by('priority', 'status', 'connection__backend__name')[:CHUNK_SIZE]
            self.info("chunk of [%d] messages found in db [%s]" % (to_process.count(), db_key))
            if to_process.count():
                self.debug("found message batch [pk=%d] [name=%s] with Queued messages to send" % (batch.pk, batch.name))
                self.send_all(router_url, to_process, priority)
            elif batch.messages.using(db_key).filter(status__in=['S', 'C']).count() == batch.messages.using(db_key).count():
                batch.status = 'S'
                batch.save()
                self.info("No more messages in MessageBatch [%d] status set to 'S'" % batch.pk)
            else:
                self.debug("Looking to see if there are any messages without a batch to send")
                self.send_individual(router_url)
        else:
            self.debug("No batches with status 'Q' found, reverting to individual message sending")
            self.send_individual(router_url)
        transaction.commit(using=db_key)

    def handle(self, **options):
        """

        """
        DB_KEYS = settings.DATABASES.keys()
        DB_KEYS.remove('geoserver') # TODO - We should probably send the list of dbs we want as parameters
        #DBS.remove('default') # skip the dummy -we now check default DB as well
        CHUNK_SIZE = getattr(settings, 'MESSAGE_CHUNK_SIZE', 400)
        self.info("starting up")
        recipients = getattr(settings, 'ADMINS', None)
        if recipients:
            recipients = [email for name, email in recipients]

        while (True):
            self.debug("send_messages started.")
            for db_key in DB_KEYS:
                try:
                    router_url = settings.DATABASES[db_key]['ROUTER_URL']

                    self.debug("servicing db [%s] with router_url [%s]" % (db_key, router_url))

                    transaction.enter_transaction_management(using=db_key)

                    self.process_messages_for_db(CHUNK_SIZE, db_key, router_url)

                except Exception, exc:
                    print exc
                    transaction.rollback(using=db_key)
                    self.critical(traceback.format_exc(exc))
                    if recipients:
                        send_mail('[Django] Error: messenger command', str(traceback.format_exc(exc)), 'root@uganda.rapidsms.org', recipients, fail_silently=True)
                    continue

            # yield from the messages table, messenger can cause
            # deadlocks if it's contanstly polling the messages table
            close_connection()
            time.sleep(0.5)



