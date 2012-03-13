from django.conf import settings
from django.core.mail import send_mail
from rapidsms.models import Backend, Connection
from rapidsms_httprouter.models import Message
import traceback
from rapidsms.log.mixin import LoggerMixin
from datetime import datetime, timedelta

def get_backends_by_type(backend_type='shortcode'):
        if backend_type == 'shortcode':
            # messenger's DB has all backends from all other deployments
            return Backend.objects.using('monitor').exclude(name__endswith='modem').order_by('name')
        elif backend_type == 'modem':
            return Backend.objects.using('monitor').filter(name__endswith='modem').order_by('name')
        else:
            return [Backend.objects.using('monitor').get_or_create(name="test_backend")[0]]

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
    qos_interval = getattr(settings, 'QOS_INTERVAL', {'hours':1, 'minutes':0, 'offset':5})
    time_offset = datetime.now() - timedelta(hours=qos_interval['hours'], minutes=(qos_interval['minutes'] + qos_interval['offset']))
    return time_offset

def get_alarms(mode="shortcode"):
    backend_type = mode
    msgs = []
    shortcode_backends = get_backends_by_type(backend_type=backend_type)
    time_offset = get_qos_time_offset()
    for shortcode in shortcode_backends:
        for modem in settings.ALLOWED_MODEMS[shortcode.name]:
            (modem_backend, t) = Backend.objects.get_or_create(name=modem)

            ret = Message.objects.filter(date__gt=time_offset, direction='I', text=gen_qos_msg(),
                    connection=Connection.objects.get_or_create(identity=settings.SHORTCODE_BACKENDS[shortcode.name], backend=modem_backend)[0])
            if not ret.count():
                msg = "No response  from %s when using  %s(%s)" % (settings.SHORTCODE_BACKENDS[shortcode.name], modem_backend.name, settings.MODEM_BACKENDS[modem_backend.name])
                msgs.append(msg)

#            ret = Message.objects.using('monitor').filter(date__gt=time_offset, direction='I', text=gen_qos_msg(),
#                    connection=Connection.objects.using('monitor').get_or_create(identity=settings.MODEM_BACKENDS[modem], backend=shortcode)[0])
#            if not ret.count():
#                msg = "Could not get response from %s when sender is %s Backend. Sent Msg=>(%s)" % (settings.MODEM_BACKENDS[modem], shortcode.name, gen_qos_msg())
#                msgs.append(msg)
    return msgs
