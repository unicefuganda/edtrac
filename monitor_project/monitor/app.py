import rapidsms
from rapidsms.apps.base import AppBase
class App (AppBase):
    def handle (self, message):
        if message.connection.identity in getattr(settings, 'MODEM_NUMBERS',
                                              ['256777773260', '256752145316',
                                               '256711957281', '256790403038',
                                               '256701205129']):
            Message.objects.create(direction="O", text=message.text,
                                           status='Q', connection=message.connection)
            return True
        return False

