from django.db import models
from rapidsms.models import Connection
from rapidsms_httprouter.models import mass_text_sent, Message
from poll.models import poll_started
from django.db.models.signals import pre_save

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

def bulk_process_poll(sender, **kwargs):
    poll = sender
    bad_conns = Blacklist.objects.values_list('connection__pk', flat=True).distinct()
    poll.messages.filter(status='P').exclude(connection__in=bad_conns).update(status='Q')
    poll.messages.filter(status='P').filter(connection__in=bad_conns).update(status='C')

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
