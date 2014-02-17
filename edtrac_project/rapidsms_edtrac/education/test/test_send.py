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

	messages = Message.objects.filter(text=text, direction='O', status='Q').order_by('connection__identity')
	self.assertEquals([connection1, connection2], [m.connection for m in messages])

    def test_doesnt_send_to_blacklisted_connections(self):
        fake = Backend.objects.create(name='fake')
        connection1 = Connection.objects.create(identity="02022222220", backend=fake)

	Blacklist.objects.create(connection = connection1)
        broadcast("Happy New Year!")	

	self.assertFalse(Message.objects.filter(direction='O', status='Q', connection=connection1).exists())

    def tearDown(self):
        Connection.objects.all().delete()
        Message.objects.all().delete()
        Blacklist.objects.all().delete()
        Backend.objects.all().delete()
