from django.test import TestCase

from rapidsms_httprouter_src.rapidsms_httprouter.management.commands.send_messages import Command
from rapidsms_httprouter_src.rapidsms_httprouter.models import MessageBatch, Message
from rapidsms.models import Backend, Connection


class SendMessagesCommandTestCase(TestCase):
    def setUp(self):
	self.batch1 = MessageBatch(status="Q", name="batch1")
	self.batch1.save()
	self.command = Command()
	self.router_url = "text=%(text)s&to=%(recipient)s&smsc=%(backend)s&%(priority)s"
	self.command.fetch_url = self.fake_get_url

    def fake_get_url(self, url):
	if "400" in url:
	    return 403
	return 200

    def create_message(self, id, backend):
	fake_connection = Connection(identity=str(id))
	fake_connection.backend, created = Backend.objects.get_or_create(name=backend)
	fake_connection.save()
	message = Message(status='Q', direction="O")
	message.connection = fake_connection

	message.batch = self.batch1;
	message.save()
	return message


    def test_send_all_updates_status_to_sent_if_fetch_returns_200(self):
	self.command.db_key = "default"
	self.message = self.create_message(129, "fake")
	self.command.send_all(self.router_url, [self.message], 1)
	self.assertEquals((Message.objects.get(pk=self.message.pk)).status, 'S')


    def test_process_messages_for_db_processes_all_first_chunk_of_the_messages(self):
	msg1 = self.create_message(3, "fake")
	msg2 = self.create_message(2, "fake")
	self.command.process_messages_for_db(3, "default", self.router_url)
	self.assertEquals((Message.objects.get(pk=msg1.pk)).status, 'S')
	self.assertEquals((Message.objects.get(pk=msg2.pk)).status, 'S')

    def test_process_messages_can_handle_a_non_routable_backend(self):
	msg1 = self.create_message(1, "fake")
	msg2 = self.create_message(2, "fake")
	msg3 = self.create_message(400, "warid")
	msg4 = self.create_message(4, "fake")
	self.command.process_messages_for_db(5, "default", self.router_url)
	self.assertEquals((Message.objects.get(pk=msg1.pk)).status, 'S')
	self.assertEquals((Message.objects.get(pk=msg2.pk)).status, 'S')
	self.assertEquals((Message.objects.get(pk=msg3.pk)).status, 'Q')
	self.assertEquals((Message.objects.get(pk=msg4.pk)).status, 'S')
