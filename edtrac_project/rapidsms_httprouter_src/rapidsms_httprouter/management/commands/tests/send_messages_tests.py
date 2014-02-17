from django.test import TestCase
from rapidsms_httprouter.management.commands.send_messages import Command
from rapidsms_httprouter.models import Message, MessageBatch
from rapidsms.models import Backend, Connection
from django.conf import settings


class StubSendMessagesCommand(Command):

    def __init__(self, **kwargs):
        self.reset_invocations()

    def reset_invocations(self):
        self.invocations = []

    def fetch_url(self, url):
        self.invocations.append(url)
        return 200

class SendMessagesTest(TestCase):

    def setUp(self):
        Message.objects.all().delete()
        MessageBatch.objects.all().delete()


        self.backend = Backend.objects.create(name='send_messages_test')

        self.connection_1 = Connection.objects.create(backend=self.backend, identity='990000')

        self.connection_2 = Connection.objects.create(backend=self.backend, identity='990001')

        self.send_messages_command = StubSendMessagesCommand()

        self.db_key = "default"


    def test_should_send_messages_if_batch_status_is_Q(self):
        self.create_batch_of_messages("Q")

        self.send_messages_command.process_messages_for_db(10, self.db_key, "http://whocares.com?text=%(text)s&to=%(recipient)s")

        self.assertEqual(len(self.send_messages_command.invocations), 1)
        self.assertEqual(self.send_messages_command.invocations[0], "http://whocares.com?text=Hello+from+the+SendMessagesTest&to=990000+990001")


    def test_should_not_send_messages_if_batch_status_is_P(self):
        self.create_batch_of_messages("P")

        self.send_messages_command.process_messages_for_db(10, self.db_key, "http://whocares.com?text=%(text)s&to=%(recipient)s")

        self.assertEqual(len(self.send_messages_command.invocations), 0)

    def test_should_send_messages_one_at_a_time_if_there_is_no_batch(self):
        self.create_queued_outgoing_message(None, self.connection_1)
        self.create_queued_outgoing_message(None, self.connection_2)

        self.send_messages_command.process_messages_for_db(10, self.db_key, "http://whocares.com?text=%(text)s&to=%(recipient)s")

        self.assertEqual(len(self.send_messages_command.invocations), 1)
        self.assertEqual(self.send_messages_command.invocations[0], "http://whocares.com?text=Hello+from+the+SendMessagesTest&to=990000")

        self.send_messages_command.reset_invocations()
        self.send_messages_command.process_messages_for_db(10, self.db_key, "http://whocares.com?text=%(text)s&to=%(recipient)s")

        self.assertEqual(len(self.send_messages_command.invocations), 1)
        self.assertEqual(self.send_messages_command.invocations[0], "http://whocares.com?text=Hello+from+the+SendMessagesTest&to=990001")


    def create_queued_outgoing_message(self, message_batch, connection, text="Hello from the SendMessagesTest"):
        return Message.objects.create(status="Q", batch=message_batch, text=text, connection=connection, direction="O")

    def create_batch_of_messages(self, status):
        message_batch = MessageBatch.objects.create(status=status, name="SMT_%s" % status)
        self.create_queued_outgoing_message(message_batch, self.connection_1)
        self.create_queued_outgoing_message(message_batch, self.connection_2)
