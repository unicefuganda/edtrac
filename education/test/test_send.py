from unittest import TestCase
from education.send import broadcast 
from rapidsms_httprouter.models import Message
from rapidsms.models import Connection, Backend
from unregister.models import Blacklist

class TestScheduling(TestCase):

    def test_broadcasts_message_to_all(self):
        fake = Backend.objects.create(name='fake')
        connection1 = Connection.objects.create(identity="02022222220", backend=fake)
        connection2 = Connection.objects.create(identity="02022222221", backend=fake)
	text = "Happy New Year!"
        broadcast(text)	
	self.assertEquals(2, Message.objects.filter(text = text, direction = 'O').count())
