from django.db import models
from rapidsms.models import Connection
from rapidsms_httprouter.models import mass_text_sent

class Blacklist(models.Model):
    connection = models.ForeignKey(Connection)

def bulk_process(sender, **kwargs):
    messages = kwargs['messages']
    bad_conns = Blacklist.objects.values_list('connection__pk', flat=True).distinct()
    bad_conns = Connection.objects.filter(pk__in=bad_conns)
    messages.filter(status='P').exclude(connection__in=bad_conns).update(status='Q')
    messages.filter(status='P').filter(connection__in=bad_conns).update(status='C')

mass_text_sent.connect(bulk_process, weak=False)

