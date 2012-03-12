import rapidsms
from rapidsms.apps.base import AppBase
from rapidsms_httprouter.models import Message
from django.conf import settings
class App (AppBase):
    def handle (self, message):
        if message.connection.identity in getattr(settings, 'MODEM_NUMBERS',
                                              ['256777773260', '256752145316',
                                               '256711957281', '256790403038',
                                               '256701205129']):
            res = Message.objects.filter(direction='O', text=message.text, status='S',
                    connection=message.connection).count()
            if res > 0:
                return True
            Message.objects.create(direction="O", text=message.text,
                                           status='Q', connection=message.connection)
            return True
        return False

