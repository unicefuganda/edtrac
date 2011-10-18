from django.core.management.base import BaseCommand
from rapidsms.models import Backend, Connection, Contact
from rapidsms_httprouter.models import Message, MessageBatch
from rapidsms_httprouter.router import get_router
from django.conf import settings
from django.db import transaction
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


    def build_send_url(self, router_url, backend, recipients, text, **kwargs):
        """
        Constructs an appropriate send url for the given message.
        """
        # first build up our list of parameters
        params = {
            'backend': backend,
            'recipient': recipients,
            'text': text,
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
            backend_name = backend.name

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


    def send_backend_chunk(self, router_url, pks, backend_name):
        msgs = Message.objects.using(self.db).filter(pk__in=pks)
        try:
            url = self.build_send_url(router_url, backend_name, ' '.join(msgs.values_list('connection__identity', flat=True)), msgs[0].text)
            status_code = self.fetch_url(url)

            # kannel likes to send 202 responses, really any
            # 2xx value means things went okay
            if int(status_code / 100) == 2:
                print "SMS%s SENT" % pks
                msgs.update(status='S')
            else:
                print "SMS%s Message not sent, got status: %s .. queued for later delivery." % (pks, status_code)
                msgs.update(status='Q')

        except Exception as e:
            print "SMS%s Message not sent: %s .. queued for later delivery." % (pks, str(e))
            msgs.update(status='Q')


    def send_all(self, router_url, to_send):
        pks = []
        if len(to_send):
            backend_name = to_send[0].connection.backend.name
            for msg in to_send:
                if backend_name != msg.connection.backend.name:
                    # send all of the same backend
                    self.send_backend_chunk(router_url, pks, backend_name)
                    # reset the loop status variables to build the next chunk of messages with the same backend
                    backend_name = msg.connection.backend.name
                    pks = [msg.pk]
                else:
                    pks.append(msg.pk)
            self.send_backend_chunk(router_url, pks, backend_name)

    def send_individual(self, router_url):
        to_process = Message.objects.using(self.db).filter(direction='O',
                          status__in=['Q']).order_by('priority', 'status', 'connection__backend__name')
        if len(to_process):
            self.send_all(router_url, [to_process[0]])


    def handle(self, **options):
        DBS = settings.DATABASES.keys()
        DBS.remove('default') # skip the dummy
        CHUNK_SIZE = getattr(settings, 'MESSAGE_CHUNK_SIZE', '400')
        while (True):
            for db in DBS:
                router_url = settings.DATABASES[db]['ROUTER_URL']
                transaction.enter_transaction_management(using=db)
                self.db = db
                to_process = MessageBatch.objects.using(db).filter(status='Q')
                if to_process.count():
                    batch = to_process[0]
                    to_process = batch.messages.using(db).filter(direction='O',
                                  status__in=['Q']).order_by('priority', 'status', 'connection__backend__name')[:CHUNK_SIZE]
                    if to_process.count():
                        self.send_all(router_url, to_process)
                    elif batch.messages.using(db).filter(status__in=['Q', 'P']).count() == 0:
                        batch.status = 'S'
                        batch.save()
                    else:
                        self.send_individual(router_url)
                else:
                    self.send_individual(router_url)

                transaction.commit(using=db)
