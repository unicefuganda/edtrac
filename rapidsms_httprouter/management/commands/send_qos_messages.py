from django.conf import settings
from django.core.management import BaseCommand
from django.core.mail import send_mail
from rapidsms.models import Connection
from rapidsms_httprouter.models import Message
from rapidsms.log.mixin import LoggerMixin
from rapidsms_httprouter.qos_messages import get_backends_by_type,gen_qos_msg

class Command(BaseCommand, LoggerMixin):
    help = """Sends quality of Service messages
    """     
    def send_qos_messages(self):
        def send_qos_messages(self):
            shortcode_backends = get_backends_by_type(btype="shortcode")
            for si in shortcode_backends:
                for mi in settings.ALLOWED_MODEMS[si.name]:
                    Message.objects.create(text=gen_qos_msg(), direction='O',
                            connection = Connection.objects.get(identity=settings.MODEM_BACKENDS[mi.name], backend=si))
                    Message.objects.create(text=gen_qos_msg(), direction='I',
                            connection = Connection.objects.get(identity=settings.SHORTCODE_BACKENDS[si.name], backend=mi))
    
    def handler(self, *args, **options):
        self.send_qos_messages()
