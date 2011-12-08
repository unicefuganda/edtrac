from django.conf import settings
from django.core.management import BaseCommand
from rapidsms.models import Connection
from rapidsms_httprouter.models import Message
from rapidsms_httprouter.qos_messages import get_backends_by_type, get_recipients, get_qos_time_offset
from rapidsms.log.mixin import LoggerMixin
from django.core.mail import send_mail

class Command(BaseCommand, LoggerMixin):
    help = """Monitor QOS Messages"""
    def check_qos_messages(self):
        #check that we got an incoming message for each message set from the modems to shorcodes
        #get_current_datetime
        modem_backends = get_backends_by_type(btype='modem')
        shortcode_backends = get_backends_by_type(btype='shortcode')

        #modem_numbers = getattr(settings, 'MODEM_NUMBERS',[])

        time_offset = get_qos_time_offset()

        for si in shortcode_backends:
            for mi in modem_backends:
                # receiving from shortcode backend to modem number
                modem = settings.MODEMS[mi.name]
                try:
                    #Message.objects.filter(connection__backend__name=si.name,connection__identity=modem)
                    b = Message.objects.filter(connection=Connection.objects.get(identity=modem, backend=si))\
                    .filter(date__gt=time_offset)
                    if b.count():
                        #we have received message from shortcode backend to modem
                        for shortcode in settings.SHORTCODES[si.name]:
                            got_match = False
                            for i in b:
                                c = Message.objects.filter(date__gt=time_offset)\
                                .filter(text=i.text)\
                                .filter(connection = Connection.objects.get(backend=mi, identity=shortcode))
                                if c.count():
                                    got_match = True
                            #raise an alarm for
                            if not got_match:
                                msg = "No response from %s for %s"%(shortcode,mi.name)
                                #send email alert
                                send_mail("QOS Alarm", msg,'root@uganda.rapidsms.org',get_recipients(),fail_silently=True)
                    else:
                        # raise alarm for si.name backend responding to modem
                        msg = "%s Backend could not respond to %s"%(si.name,modem)
                        send_mail("QOS Alarm", msg,'root@uganda.rapidsms.org',get_recipients(),fail_silently=True)
                except Connection.DoesNotExist:
                    msg = "%s Backend could not respond to %s"%(si.name,modem)
                    send_mail("QOS Alarm", msg,'root@uganda.rapidsms.org',get_recipients(),fail_silently=True)

            # receiving from modem backend to shortcode
                for shortcode in  settings.SHORTCODES[si.name]:
                    msg=""
                    try:
                        d = Message.objects.filter(connection=Connection.objects.get(identity=shortcode, backend=mi))\
                        .filter(date__gt=time_offset)
                        if d.count():
                            # consider using only the modem-number that matches mi backend
                            got_match = False
                            for x in d:
                                e = Message.objects.filter(date__gt=time_offset)\
                                .filter(text=x.text)\
                                .filter(connection = Connection(backend=si, identity=modem)) # modem should only be the number for mi backend
                                if e.count(): got_match = True
                            if not got_match:
                                msg = "No response from %s to %s"%(mi.name,shortcode)

                        else:
                            msg = "No response from %s Backend to %s"%(mi.name,shortcode)
                    except Connection.DoesNotExist:
                        msg = "%s Backend could not respond to %s"%(mi.name,shortcode)
                    if msg:
                        send_mail("QOS Alarm", msg,'root@uganda.rapidsms.org',get_recipients(),fail_silently=True)

    def handle(self, *args, **options):
        self.check_qos_messages()

