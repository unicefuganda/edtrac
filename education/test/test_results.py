from unittest import TestCase
from education.results import NumericResponsesFor
from education.test.utils import create_attribute
from education.models import *
from rapidsms.models import *

class TestResults(TestCase):

    def setUp(self):
        create_attribute()

    def test_gathers_only_error_free_incoming_messages(self):
        user = User.objects.create(username="peter")
        contact = Contact.objects.create()
        poll = Poll.objects.create(name="foo", user=user, response_type=Poll.TYPE_NUMERIC)
        backend = Backend.objects.create()
        connection = Connection.objects.create(contact=contact, backend=backend)
        erroring_incoming_message = Message.objects.create(direction="I", text="Hello?", connection=connection)
        incoming_message = Message.objects.create(direction="I", text="8", connection=connection)
        outgoing_message = Message.objects.create(direction="O", text="9", connection=connection)
        Response.objects.create(contact=contact, poll=poll, message=incoming_message, has_errors=False)
        Response.objects.create(contact=contact, poll=poll, message=erroring_incoming_message, has_errors=True)
        Response.objects.create(contact=contact, poll=poll, message=outgoing_message)

        self.assertEqual(1, NumericResponsesFor(poll).query.count())

