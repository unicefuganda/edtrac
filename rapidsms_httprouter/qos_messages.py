from django.conf import settings
from django.core.mail import send_mail
from rapidsms.models import Backend, Connection
from rapidsms_httprouter.models import Message
import traceback
from rapidsms.log.mixin import LoggerMixin
from datetime import datetime, timedelta

def get_backends_by_type(btype='shortcode'):
        backends = []
        for db in settings.DATABASES.keys():
            if db == 'default':
                continue
            bs = list(Backend.objects.using(db).exclude(name='console').order_by('name').values_list('name', flat=True))
            for b in bs:
                if b not in backends:
                    backends.append(b)

        if btype == 'shortcode':
            # messenger's DB has all backends from all other deployments
            return Backend.objects.using('default').filter(name__in=backends).order_by('name')
        elif btype == 'modem':
            backends.append('console')
            return Backend.objects.using('default').exclude(name__in=backends).order_by('name')
        else:
            return []

        
def gen_qos_msg():
    return datetime.now().strftime('%Y-%m-%d %H')

def get_recipients():
    recipients = getattr(settings, 'ADMINS', None)
    if recipients:
        recipients = [email for name, email in recipients]
    else:
        recipients = []
    mgr = getattr(settings, 'MANAGERS', None)
    if mgr:
        for email in mgr:
            recipients.append(email)
    return recipients
    
def get_qos_time_offset():
    qos_interval = getattr(settings,'QOS_INTERVAL', {'hours':1,'minutes':0,'offset':5})
    time_offset = datetime.now() - timedelta(hours=qos_interval['hours'],minutes=(qos_interval['minutes']+qos_interval['offset']))
    return time_offset

def get_alarms():
    msgs = []
    shortcode_backends = get_backends_by_type(btype="shortcode")
    time_offset = get_qos_time_offset()
    for si in shortcode_backends:
        for mi in settings.ALLOWED_MODEMS[si.name]:
            try:
                b = Message.objects.filter(date__gt=time_offset, direction='I',
                        connection=Connection(identity=settings.SHORTCODE_BACKENDS[si.name], backend=mi, text=gen_qos_msg()))
                if not b.count():
                    msg = "Could not get response from %s when sender is %s Backend"%(settings.SHORTCODE_BACKENDS[si.name],mi.name)
                    msgs.append(msg)
                    
            except Connection.DoesNotExist:
                msg = "Could not get response from %s when sender is %s Backend"%(settings.SHORTCODE_BACKENDS[si.name],mi.name)
                msgs.append(msg)
            try:
                b = Message.objects.filter(date__gt=time_offset, direction='I',
                        connection=Connection(identity=settings.MODEM_BACKENDS[mi.name], backend=si, text=gen_qos_msg()))
                if not b.count():
                    msg = "Could not get response from %s when sender is %s Backend"%(settings.MODEM_BACKENDS[mi.name],si.name)
                    msgs.append(msg)
            except Connection.DoesNotExist:
                msg = "Could not get response from %s when sender is %s Backend"%(settings.MODEM_BACKENDS[mi.name],si.name)
    return msgs
