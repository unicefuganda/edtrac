# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from django.contrib.auth.models import User, Group
from django.http import HttpRequest
from education.models import School, EmisReporter, Role, UserProfile
from education.views import CapitationGrants
from rapidsms.models import Backend, Connection
from rapidsms.contrib.locations.models import LocationType, Location, Point
from poll.models import Poll, Response
from rapidsms_httprouter.router import get_router


class TestCapitationGrantView(TestCase):
    def setUp(self):
        admin_group, head_teachers_group = self._create_users_and_roles()
        self._create_locations()
        self._create_schools()
        self._create_poll(head_teachers_group)
        UserProfile.objects.create(user=self.user, name='shaggy', location=self.root_node, role=admin_group)
        self._create_capitation_grant_view()

    def test_calculation_of_national_responses(self):
        self.fake_incoming('yes', self.connection1)
        self.fake_incoming('no', self.connection2)
        results = self.capitation_grant_view.get_context_data()
        national_responses = results['responses']
        self.assertIn(('yes', 50.00), national_responses)
        self.assertIn(('no', 50.00), national_responses)

    def test_calculation_of_head_teacher_count(self):
        self.fake_incoming('yes', self.connection1)
        self.fake_incoming('no', self.connection1)
        self.fake_incoming('yes', self.connection2)
        results = self.capitation_grant_view.get_context_data()
        self.assertAlmostEqual(66.66, results['head_teacher_count'], delta=0.01)
        self.assertEqual(self.root_node, results['location'])

    def test_calculation_of_district_categorization(self):
        self.fake_incoming('yes', self.connection1)
        self.fake_incoming('no', self.connection2)
        self.fake_incoming('no', self.connection3)
        results = self.capitation_grant_view.get_context_data()
        self.assertEqual(self.root_node.get_children()[0].type.name, results['sub_location_type'])
        districts = results['sub_locations']
        self.assertIn((self.kampala_district, [(u'yes', 50.00), (u'no', 50.00)]), districts)
        self.assertIn((self.gulu_district, [(u'no', 100.0)]), districts)

    def test_calculation_if_user_at_district_logged_in(self):
        user = User.objects.create(username='scrapy', email='scooby@shaggy.com')
        user.set_password('scrapydooo')
        user.save()
        UserProfile.objects.create(user=user, name='scrapy', location=self.kampala_district,
                                   role=Role.objects.get(name='Head Teachers'))
        request = HttpRequest()
        request.user = user
        self.capitation_grant_view.request = request

        self.fake_incoming('yes', self.connection1)
        self.fake_incoming('no', self.connection1)
        results = self.capitation_grant_view.get_context_data()
        self.assertAlmostEqual(50.00, results['head_teacher_count'], delta=0.01)
        self.assertEqual(self.kampala_district, results['location'])
        responses = results['responses']
        self.assertIn((u'yes', 50.00), responses)
        self.assertIn((u'no', 50.00), responses)

        self.assertEqual('school', results['sub_location_type'])
        sub_locations = results['sub_locations']
        self.assertIn((self.kampala_school, [(u'yes', 50.00), (u'no', 50.00)]), sub_locations)
        self.assertIn((self.kampala_school2, []), sub_locations)

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
        admin_group = Role.objects.create(name="Admins")
        head_teachers_group = Role.objects.create(name="Head Teachers")
        self.user = User.objects.create(username='fred', email='welma@daffny.com')
        self.user.set_password('scoobydoo')
        self.user.groups.add(admin_group)
        self.user.save()
        return admin_group, head_teachers_group

    def _create_locations(self):
        country = LocationType.objects.create(name='country', slug='country')
        district = LocationType.objects.create(name='district', slug='district')
        uganda_fields = {
            "rght": 15274,
            "name": "Uganda",
            "level": 0,
            "tree_id": 1,
            "lft": 1,
            "type": country
        }
        self.root_node = Location.objects.create(**uganda_fields)
        kampala_point_fields = {
            "latitude": "0.3162800000",
            "longitude": "32.5821900000"
        }
        kampala_point = Point.objects.create(**kampala_point_fields)
        kampala_fields = {
            "rght": 10901,
            "tree_parent": self.root_node,
            "name": "Kampala",
            "point": kampala_point,
            "level": 1,
            "tree_id": 1,
            "lft": 10686,
            "type": district
        }
        self.kampala_district = Location.objects.create(**kampala_fields)
        gulu_point_fields = {
            "latitude": "2.7666700000",
            "longitude": "32.3055600000"
        }
        gulu_point = Point.objects.create(**gulu_point_fields)
        gulu_fields = {
            "rght": 9063,
            "tree_parent": self.root_node,
            "name": "Gulu",
            "point": gulu_point,
            "level": 1,
            "tree_id": 1,
            "lft": 8888,
            "type": district
        }
        self.gulu_district = Location.objects.create(**gulu_fields)

    def _create_schools(self):
        self.gulu_school = School.objects.create(name="St. Mary's", location=self.gulu_district)
        self.kampala_school = School.objects.create(name="St. Mary's", location=self.kampala_district)
        self.kampala_school2 = School.objects.create(name="St. Peters", location=self.kampala_district)

    def _create_emis_reporters(self, head_teachers_group):
        emis_reporter1 = EmisReporter.objects.create(name='kampala_contact', reporting_location=self.kampala_district)
        emis_reporter1.schools.add(self.kampala_school)
        emis_reporter1.groups.add(head_teachers_group)
        emis_reporter1.save()
        emis_reporter2 = EmisReporter.objects.create(name='kampala_contact2', reporting_location=self.kampala_district)
        emis_reporter2.schools.add(self.kampala_school2)
        emis_reporter2.groups.add(head_teachers_group)
        emis_reporter2.save()
        emis_reporter3 = EmisReporter.objects.create(name='gulu_contact', reporting_location=self.gulu_district)
        emis_reporter3.schools.add(self.gulu_school)
        emis_reporter3.groups.add(head_teachers_group)
        emis_reporter3.save()
        self.backend = Backend.objects.create(name='test')
        self.connection1 = Connection.objects.create(identity='8675301', backend=self.backend, contact=emis_reporter1)
        self.connection2 = Connection.objects.create(identity='8675302', backend=self.backend, contact=emis_reporter2)
        self.connection3 = Connection.objects.create(identity='8675303', backend=self.backend, contact=emis_reporter3)
        return emis_reporter1, emis_reporter2, emis_reporter3

    def _create_poll(self, head_teachers_group):
        emis_reporter1, emis_reporter2, emis_reporter3 = self._create_emis_reporters(head_teachers_group)
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
