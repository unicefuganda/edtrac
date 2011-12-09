from django.conf import settings
from django.core.management import BaseCommand
from rapidsms.models import Connection
from rapidsms_httprouter.models import Message
from rapidsms_httprouter.qos_messages import get_backends_by_type, get_recipients, get_qos_time_offset,gen_qos_msg
from rapidsms.log.mixin import LoggerMixin
from django.core.mail import send_mail

class Command(BaseCommand, LoggerMixin):
    help = """Monitor QOS Messages"""
    def check_qos_messages(self):
        recipients = get_recipients()
        shortcode_backends = get_backends_by_type(btype="shortcode")
        time_offset = get_qos_time_offset()
        for si in shortcode_backends:
            for mi in settings.ALLOWED_MODEMS[si.name]:
                try:
                    b = Message.objects.filter(date__gt=time_offset, direction='I',
                            connection=Connection(identity=settings.SHORTCODE_BACKENDS[si.name], backend=mi, text=gen_qos_msg()))
                    if not b.count():
                        msg = "Could not get response from %s when sender %s Backend"%(settings.SHORTCODE_BACKENDS[si.name],mi.name)
                        send_mail("QOS Alarm",msg,"root@uganda.rapidsms.org",recipients,fail_silently=True)
                except Connection.DoesNotExist:
                    msg = "Could not get response from %s when sender %s Backend"%(settings.SHORTCODE_BACKENDS[si.name],mi.name)
                    send_mail("QOS Alarm",msg,"root@uganda.rapidsms.org",recipients,fail_silently=True)

                try:
                    b = Message.objects.filter(date__gt=time_offset, direction='I',
                            connection=Connection(identity=settings.MODEM_BACKENDS[mi.name], backend=si, text=gen_qos_msg()))
                    if not b.count():
                        msg = "Could not get response from %s when sender %s Backend"%(settings.MODEM_BACKENDS[mi.name],si.name)
                        send_mail("QOS Alarm",msg,"root@uganda.rapidsms.org",recipients,fail_silently=True)

                except Connection.DoesNotExist:
                    msg = "Could not get response from %s when sender %s Backend"%(settings.MODEM_BACKENDS[mi.name],si.name)
                    send_mail("QOS Alarm",msg,"root@uganda.rapidsms.org",recipients,fail_silently=True)

    def handle(self, *args, **options):
        self.check_qos_messages()

