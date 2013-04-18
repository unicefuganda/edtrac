from django.db import models
from rapidsms.models import Connection
from rapidsms_httprouter.models import mass_text_sent, Message
from poll.models import poll_started
from django.db.models.signals import pre_save

import logging
log = logging.getLogger(__name__)

class Blacklist(models.Model):
    connection = models.ForeignKey(Connection)

def bulk_process(sender, **kwargs):
    messages = kwargs['messages']
    status = kwargs['status']
    if status == 'P':
        bad_conns = Blacklist.objects.values_list('connection__pk', flat=True).distinct()
        bad_conns = Connection.objects.filter(pk__in=bad_conns)
        messages.filter(status='P').exclude(connection__in=bad_conns).update(status='Q')
        messages.filter(status='P').filter(connection__in=bad_conns).update(status='C')

def log_bulk_process_info(poll, message):
    log.info("[bulk-process-poll-" + str(poll.pk) + "]" + message)

def bulk_process_poll(sender, **kwargs):
    log.info("[bulk_process_poll] sender=" + str(type(sender)) + " - toString " + str(sender))
    poll = sender
    log_bulk_process_info(poll, " finding bad connections...")
    bad_conns = Blacklist.objects.values_list('connection__pk', flat=True).distinct()
    log_bulk_process_info(poll, " setting status to Q for anything thats not blacklisted and has status P...")
    poll.messages.filter(status='P').exclude(connection__in=bad_conns).update(status='Q')
    log_bulk_process_info(poll, " ok. setting status to C for all the blacklisted connections...")
    poll.messages.filter(status='P').filter(connection__in=bad_conns).update(status='C')
    log_bulk_process_info(poll, "ok.")

def blacklist(sender, **kwargs):
    m = kwargs['instance']
    raw = kwargs['raw']
    if not raw and m.direction == 'O' and m.status == 'P':
        bad_conns = Blacklist.objects.values_list('connection__pk', flat=True).distinct()
        bad_conns = Connection.objects.filter(pk__in=bad_conns)
        if m.connection in bad_conns:
            m.status = 'C'
        else:
            m.status = 'Q'

mass_text_sent.connect(bulk_process, weak=False)
poll_started.connect(bulk_process_poll, weak=False)
#pre_save.connect(blacklist, sender=Message, weak=False)
