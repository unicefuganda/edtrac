from django.conf import settings
from django.core.management import BaseCommand
from rapidsms_httprouter.qos_messages import get_recipients, get_alarms
from rapidsms.log.mixin import LoggerMixin
from django.core.mail import send_mail

class Command(BaseCommand, LoggerMixin):
    help = """Monitor QOS Messages"""
    def check_qos_messages(self):
        allow = getattr(settings, 'QOS_INCLUDE_MANAGERS_AS_RECIPIENTS', False)
        recipients = get_recipients(include_managers=allow)
        for msg in get_alarms(mode=getattr(settings, 'QOS_BACKEND_TYPE', 'shortcode')):
            send_mail("QOS Alarm", msg, "root@uganda.rapidsms.org", recipients, fail_silently=True)

    def handle(self, *args, **options):
        self.check_qos_messages()

