from datetime import datetime
from unittest import TestCase
from poll.models import Poll, Response
from django.contrib.auth.models import User
from rapidsms.models import Contact, Backend, Connection
from rapidsms_httprouter.router import get_router
from dateutil.relativedelta import relativedelta

class TestPolls(TestCase):

    def setUp(self):
        self.male_user = User.objects.create(username='fred', email='shaggy@scooby.com')
        self.female_user = User.objects.create(username='scrapy', email='shaggy@scooby.com')
        self.poll = Poll.objects.create(name='test poll', question='are you happy', user=self.male_user, type=Poll.TYPE_TEXT)

        self.male_contact = Contact.objects.create(name='shaggy', user=self.male_user, gender='M',birthdate=datetime.now() - relativedelta(years=20))
        self.female_contact = Contact.objects.create(name='dafny', user=self.female_user, gender='F',birthdate=datetime.now() - relativedelta(years=25))

        self.backend = Backend.objects.create(name='scoobydoo')

        self.connection_for_male = Connection.objects.create(identity='0794339344', backend=self.backend)
        self.connection_for_male.contact = self.male_contact
        self.connection_for_male.save()

        self.connection_for_female = Connection.objects.create(identity='0794339345', backend=self.backend)
        self.connection_for_female.contact = self.female_contact
        self.connection_for_female.save()

        self.poll.contacts.add(self.female_contact)
        self.poll.contacts.add(self.male_contact)
        self.poll.add_yesno_categories()
        self.poll.save()
        self.poll.start()

    def send_message(self, connection, message):
        router = get_router()
        router.handle_incoming(connection.backend.name, connection.identity, message)

    def test_responses_by_gender_only_for_male(self):
        self.send_message(self.connection_for_male, 'yes')

        yes_aggregation = {"category__name": u"yes", "category__color": u"", "value": 1}

        filtered_responses = self.poll.responses_by_gender(gender='m')
        self.assertIn(yes_aggregation, filtered_responses)

    def test_responses_by_gender(self):
        self.send_message(self.connection_for_male, 'yes')
        self.send_message(self.connection_for_female, 'No')

        no_aggregation = {"category__name": u"no", "category__color": u"", "value": 1}
        filtered_responses = self.poll.responses_by_gender(gender='F')

        self.assertIn(no_aggregation, filtered_responses)

    def test_responses_by_gender_should_check_if_poll_is_yes_no(self):
        poll = Poll.objects.create(name='test poll2', question='are you happy??', user=self.male_user, type=Poll.TYPE_TEXT)
        with(self.assertRaises(AssertionError)):
            poll.responses_by_gender(gender='F')

    def test_responses_by_age(self):
        self.send_message(self.connection_for_male,'yes')
        self.send_message(self.connection_for_female,'no')
        self.send_message(self.connection_for_male,'foobar')

        yes_responses = {'category__name': 'yes', 'value': 1}
        no_responses = {'category__name': 'no', 'value': 1}
        unknown_responses = {'category__name': 'unknown', 'value': 1}

        results = self.poll.responses_by_age(20, 26)

        self.assertIn(yes_responses,results)
        self.assertIn(no_responses,results)
        self.assertIn(unknown_responses,results)

    def tearDown(self):
        Backend.objects.all().delete()
        Connection.objects.all().delete()
        Response.objects.all().delete()
        Poll.objects.all().delete()
        Contact.objects.all().delete()
        User.objects.all().delete()

