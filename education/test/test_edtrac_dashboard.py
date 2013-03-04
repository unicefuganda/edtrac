# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from django.contrib.auth.models import User, Group
from education.models import School, EmisReporter
from education.views import capitation_grants
from poll.models import Poll, Response
from rapidsms.contrib.locations.models import Location, LocationType, Point
from rapidsms.models import Backend, Connection
from rapidsms_httprouter.router import get_router


class TestEdtracDashboard(TestCase):
    def setUp(self):
        htg = Group.objects.create(name='Head Teachers')
        user = User.objects.create(username="John", password="john")
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

        school = School.objects.create(name="Don Bosco School", location=self.root_node)
        self.emisreporter1 = EmisReporter.objects.create(name="Reporter1", reporting_location=self.kampala_district)
        self.emisreporter1.schools.add(school)
        self.emisreporter1.groups.add(htg)
        self.emisreporter1.save()
        self.emisreporter2 = EmisReporter.objects.create(name="Reporter1", reporting_location=self.kampala_district)
        self.emisreporter2.schools.add(school)
        self.emisreporter2.groups.add(htg)
        self.emisreporter2.save()
        self.emisreporter3 = EmisReporter.objects.create(name="Reporter1", reporting_location=self.gulu_district)
        self.emisreporter3.schools.add(school)
        self.emisreporter3.groups.add(htg)
        self.emisreporter3.save()
        self.backend = Backend.objects.create(name='fake_backed')
        self.connection1 = Connection.objects.create(identity="02022222220", backend=self.backend,
                                                     contact=self.emisreporter1)
        self.connection2 = Connection.objects.create(identity="02022222221", backend=self.backend,
                                                     contact=self.emisreporter2)
        self.connection3 = Connection.objects.create(identity="02022222222", backend=self.backend,
                                                     contact=self.emisreporter3)
        self.poll = Poll.objects.create(name='edtrac_upe_grant',
                                        question="Have you received your UPE grant this term? Answer  YES or NO or I don't know",
                                        type=Poll.TYPE_TEXT, user=user, response_type=Poll.RESPONSE_TYPE_ONE)
        self.poll.contacts.add(self.emisreporter1, self.emisreporter2, self.emisreporter3)
        self.poll.add_yesno_categories()
        self.poll.save()
        self.poll.start()


    def test_yes_percentage_at_uganda_level(self):
        self.fake_incoming("yes", self.connection1)
        self.fake_incoming("yes", self.connection1)
        self.fake_incoming("no", self.connection2)
        grants = capitation_grants(self.root_node.get_children())
        self.assertAlmostEqual(33.33 , grants['grant_percent'],delta=0.01)

    def test_yes_percentage_at_district_level(self):
        self.fake_incoming("yes", self.connection1)
        self.fake_incoming("yes", self.connection3)
        grants = capitation_grants([self.kampala_district])
        self.assertAlmostEqual(50.0 , grants['grant_percent'],delta=0.01)



    def fake_incoming(self, message, connection):
        router = get_router()
        handled = router.handle_incoming(connection.backend.name, connection.identity, message)
        return handled

    def tearDown(self):
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        School.objects.all().delete()
        EmisReporter.objects.all().delete()
        Connection.objects.all().delete()
        Backend.objects.all().delete()
        Poll.objects.all().delete()
        Response.objects.all().delete()
        User.objects.all().delete()
        Group.objects.all().delete()



