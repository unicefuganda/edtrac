from django.conf import settings
from django.core.management import BaseCommand
from django.core.mail import send_mail
from rapidsms.models import Connection, Backend
from rapidsms_httprouter.models import Message
from rapidsms.log.mixin import LoggerMixin
from rapidsms_httprouter.qos_messages import get_backends_by_type, gen_qos_msg

class Command(BaseCommand, LoggerMixin):
    help = """Sends quality of Service messages
    """
    def send_qos_messages(self):
        shortcode_backends = get_backends_by_type(btype=getattr(settings, 'QOS_BACKEND_TYPE', 'shortcode'))
        for si in shortcode_backends:
            for mi in settings.ALLOWED_MODEMS[si.name]:
                (mb, t) = Backend.objects.using('monitor').get_or_create(name=mi)
                Message.objects.using('monitor').create(text=gen_qos_msg(), direction='O', status='Q',
                        connection=Connection.objects.using('monitor').get_or_create(identity=settings.MODEM_BACKENDS[mb.name], backend=si)[0])
                Message.objects.using('monitor').create(text=gen_qos_msg(), direction='O', status='Q',
                        connection=Connection.objects.using('monitor').get_or_create(identity=settings.SHORTCODE_BACKENDS[si.name], backend=mb)[0])

    def handle(self, *args, **options):
        self.send_qos_messages()
