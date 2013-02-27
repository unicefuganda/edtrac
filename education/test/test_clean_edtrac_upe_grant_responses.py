# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase

from django.contrib.auth.models import User, Group
from django.http import HttpRequest
from django.core import management

from education.models import School, EmisReporter, Role
from education.views import CapitationGrants
from rapidsms.models import Backend, Connection
from rapidsms.contrib.locations.models import LocationType, Location
from poll.models import Poll, Response
from rapidsms_httprouter.router import get_router


class TestCleanEdtracUpeGrantResponses(TestCase):
    def setUp(self):
        head_teachers_group, smc_group = self._create_users_and_roles()
        self._create_schools()
        self._create_poll(head_teachers_group, smc_group)

    def test_should_clean_responses(self):
        self.fake_incoming('yes', self.connection1)
        self.fake_incoming('no', self.connection2)
        self.fake_incoming('i dont know', self.connection3)

        self.assertEqual(3, Response.objects.filter(poll=self.poll).count())
        management.call_command('clean_edtrac_upe_grant_responses')
        self.assertEqual(1, Response.objects.filter(poll=self.poll).count())

    def tearDown(self):
        School.objects.all().delete()
        EmisReporter.objects.all().delete()
        Connection.objects.all().delete()
        Backend.objects.all().delete()
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        Response.objects.all().delete()
        Poll.objects.all().delete()
        User.objects.all().delete()
        Group.objects.all().delete()

    def fake_incoming(self, message, connection):
        router = get_router()
        handled = router.handle_incoming(connection.backend.name, connection.identity, message)
        return handled

    def _create_users_and_roles(self):
        smc_group = Role.objects.create(name="Smc")
        head_teachers_group = Role.objects.create(name="Head Teachers")
        self.user = User.objects.create(username='fred', email='welma@daffny.com')
        self.user.set_password('scoobydoo')
        self.user.save()
        return head_teachers_group, smc_group

    def _create_schools(self):
        country = LocationType.objects.create(name='country', slug='country')
        uganda_fields = {
            "rght": 15274,
            "name": "Uganda",
            "level": 0,
            "tree_id": 1,
            "lft": 1,
            "type": country
        }
        self.root_node = Location.objects.create(**uganda_fields)

        self.uganda_school = School.objects.create(name="St. Mary's", location=self.root_node)

    def _create_emis_reporters(self, head_teachers_group, smc_group):
        emis_reporter1 = EmisReporter.objects.create(name='kampala_contact', reporting_location=self.root_node)
        emis_reporter1.schools.add(self.uganda_school)
        emis_reporter1.groups.add(head_teachers_group)
        emis_reporter1.save()

        emis_reporter2 = EmisReporter.objects.create(name='kampala_contact2', reporting_location=self.root_node)
        emis_reporter2.schools.add(self.uganda_school)
        emis_reporter2.groups.add(smc_group)
        emis_reporter2.save()

        emis_reporter3 = EmisReporter.objects.create(name='gulu_contact', reporting_location=self.root_node)
        emis_reporter3.groups.add(head_teachers_group)
        emis_reporter3.save()

        self.backend = Backend.objects.create(name='test')
        self.connection1 = Connection.objects.create(identity='8675301', backend=self.backend, contact=emis_reporter1)
        self.connection2 = Connection.objects.create(identity='8675302', backend=self.backend, contact=emis_reporter2)
        self.connection3 = Connection.objects.create(identity='8675303', backend=self.backend, contact=emis_reporter3)
        return emis_reporter1, emis_reporter2, emis_reporter3

    def _create_poll(self, head_teachers_group, smc_group):
        emis_reporter1, emis_reporter2, emis_reporter3 = self._create_emis_reporters(head_teachers_group, smc_group)
        params = {
            "default_response": "",
            "name": "edtrac_upe_grant",
            "question": "Have you received your UPE grant this term? Answer  YES or NO or I don't know",
            "user": self.user,
            "type": Poll.TYPE_TEXT,
            "response_type": Poll.RESPONSE_TYPE_ALL
        }
        self.poll = Poll.objects.create(**params)
        self.poll.add_yesno_categories()
        self.poll.contacts.add(emis_reporter1)
        self.poll.contacts.add(emis_reporter2)
        self.poll.contacts.add(emis_reporter3)
        self.poll.save()
        self.poll.start()

    def _create_capitation_grant_view(self):
        self.capitation_grant_view = CapitationGrants()
        request = HttpRequest()
        request.user = self.user
        self.capitation_grant_view.request = request
