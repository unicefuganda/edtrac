from unittest import TestCase
from education.results import NumericResponsesFor
from education.test.utils import create_attribute
from education.models import *
from rapidsms.models import *
from eav.models import *

class TestResults(TestCase):

    def setUp(self):
        self.attribute = create_attribute()
        user = User.objects.create(username="peter")
        backend = Backend.objects.create()
        self.contact = Contact.objects.create()
        self.poll = Poll.objects.create(name="foo", user=user, response_type=Poll.TYPE_NUMERIC)
        self.connection = Connection.objects.create(contact=self.contact, backend=backend)
        self.content_type = ContentType.objects.create()

    def record_response(self, text, value_float, direction='I', has_errors=False):
        message = Message.objects.create(direction=direction, text=text, connection=self.connection)
        response = Response.objects.create(contact=self.contact, poll=self.poll, message=message, has_errors=has_errors)
        value = Value.objects.create(entity_ct=self.content_type, attribute=self.attribute, entity=response, value_float=value_float)
        return response

    def test_gathers_only_error_free_incoming_messages(self):
        self.record_response("Hello world!", None, direction='I', has_errors=True)
        self.record_response("8 boys", 8, direction='I', has_errors=False)
        self.record_response("Do you have more than 1 latrine?", None, direction='O', has_errors=True)
        self.assertEqual(8, NumericResponsesFor(self.poll).total())
