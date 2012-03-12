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
        shortcode_backends = get_backends_by_type(backend_type=getattr(settings, 'QOS_BACKEND_TYPE', 'shortcode'))
        for shortcode in shortcode_backends:
            for modem in settings.ALLOWED_MODEMS[shortcode.name]:
                (modem_backend, t) = Backend.objects.using('monitor').get_or_create(name=modem)
                Message.objects.using('monitor').create(text=gen_qos_msg(), direction='O', status='Q',
                        connection=Connection.objects.using('monitor').get_or_create(identity=settings.MODEM_BACKENDS[modem_backend.name], backend=shortcode)[0])
                Message.objects.using('monitor').create(text=gen_qos_msg(), direction='O', status='Q',
                        connection=Connection.objects.using('monitor').get_or_create(identity=settings.SHORTCODE_BACKENDS[shortcode.name], backend=modem_backend)[0])

    def handle(self, *args, **options):
        self.send_qos_messages()
