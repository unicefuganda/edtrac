from unittest import TestCase
from education.results import NumericResponsesFor
from education.test.utils import create_attribute
from education.models import *
from rapidsms.models import *
from eav.models import *

class TestResults(TestCase):

    def test_gathers_only_error_free_incoming_messages(self):
        attribute = create_attribute()
        user = User.objects.create(username="peter")
        contact = Contact.objects.create()
        poll = Poll.objects.create(name="foo", user=user, response_type=Poll.TYPE_NUMERIC)
        backend = Backend.objects.create()
        connection = Connection.objects.create(contact=contact, backend=backend)

        erroring_incoming_message = Message.objects.create(direction="I", text="10", connection=connection)
        incoming_message = Message.objects.create(direction="I", text="8", connection=connection)
        outgoing_message = Message.objects.create(direction="O", text="9", connection=connection)
        content_type = ContentType.objects.create()

        valued_response = Response.objects.create(contact=contact, poll=poll, message=incoming_message, has_errors=False)
        value = Value.objects.create(entity_ct=content_type, attribute=attribute, entity=valued_response, value_float=8.0)
        Response.objects.create(contact=contact, poll=poll, message=erroring_incoming_message, has_errors=True)
        Response.objects.create(contact=contact, poll=poll, message=outgoing_message)

        self.assertEqual(8, NumericResponsesFor(poll).total())
