from django.conf import settings
from django.core.management import BaseCommand
from django.core.mail import send_mail
from rapidsms.models import Backend, Connection
from rapidsms_httprouter.models import Message
import traceback
from rapidsms.log.mixin import LoggerMixin
from datetime import datetime
from rapidsms_httprouter.qos_messages import get_backends_by_type, get_recipients, get_qos_time_offset

class Command(BaseCommand, LoggerMixin):
    help = """Sends quality of Service messages
    """     
    def send_qos_messages(self):
        #bs = getattr(settings,'MODEMS',{'dmark':['8500','6767'],'y8200':['8200'],
        #                               'yo6200':['6200'], 'utl':[],'zain':[]})
        #scodes = [item for sublist in bs for item in sublist][0]
        
        modem_backends = get_backends_by_type(btype='modem')
        shortcode_backends = get_backends_by_type(btype='shortcode')
        
        for mi in modem_backends:
            for si in shortcode_backends:
                # sending from modem backend to shortcode
                for shortcode in settings.SHORTCODES[si.name]:
                    Message.objects.create(text=self.gen_qos_msg(),
                                           connection=Connection.objects.get(identity=shortcode,backend=mi))
                for modem in settings.MODEM_NUMBERS:
                    Message.objects.create(text=self.gen_qos_msg(),
                                           connection = Connection.objects.get(identity=modem,backend=si))

    
    def handler(self, *args, **options):
        self.send_qos_messages()
