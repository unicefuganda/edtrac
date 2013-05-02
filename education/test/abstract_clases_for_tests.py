# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from django.contrib.auth.models import Group
from education.test.utils import *
from poll.models import Response
from rapidsms.models import Connection
from rapidsms_httprouter.router import get_router
from script.models import Script, ScriptProgress, ScriptStep, ScriptSession


class TestAbsenteeism(TestCase):
    def setUp(self):
        country = create_location_type("country")
        uganda_fields = {
            "rght": 15274,
            "level": 0,
            "tree_id": 1,
            "lft": 1,
            }
        self.uganda = create_location("uganda", country, **uganda_fields)
        admin_group = create_group("Admins")
        district = create_location_type("district")
        kampala_fields = {
            "rght": 10901,
            "tree_parent": self.uganda,
            "level": 1,
            "tree_id": 1,
            "lft": 10686,
            }
        kampala_point = {
            "latitude": "0.3162800000",
            "longitude": "32.5821900000"
        }
        self.kampala_district = create_location("Kampala", district, point=kampala_point, **kampala_fields)
        gulu_point = {
            "latitude": "2.7666700000",
            "longitude": "32.3055600000"
        }
        gulu_fields = {
            "rght": 9063,
            "tree_parent": self.uganda,
            "level": 1,
            "tree_id": 1,
            "lft": 8888,
            }
        self.gulu_district = create_location("Gulu", district, point=gulu_point, **gulu_fields)
        gulu_school = create_school("St. Joseph's", self.gulu_district)
        self.kampala_school = create_school("St. Joseph's", self.kampala_district)
        self.emis_reporter1 = create_emis_reporters("dummy1", self.kampala_district, self.kampala_school, 12345, admin_group)
        self.emis_reporter2 = create_emis_reporters("dummy2", self.kampala_district, self.kampala_school, 12346, admin_group)
        self.emis_reporter3 = create_emis_reporters("dummy3", self.gulu_district, gulu_school, 12347, admin_group)
        self.emis_reporter4 = create_emis_reporters("dummy4", self.gulu_district, gulu_school, 12348, admin_group)
        self.admin_user = create_user_with_group("John", admin_group, self.uganda)
        self.p3_boys_absent_poll = create_poll_with_reporters("edtrac_boysp3_attendance", "How many P3 boys are at school today?",
                                               Poll.TYPE_NUMERIC, self.admin_user,
                                               [self.emis_reporter1, self.emis_reporter2, self.emis_reporter3,
                                                self.emis_reporter4])
        self.p3_boys_enrolled_poll = create_poll_with_reporters("edtrac_boysp3_enrollment",
                                                 "How many boys are enrolled in P3 this term?",
                                                 Poll.TYPE_NUMERIC, self.admin_user,
                                                 [self.emis_reporter1, self.emis_reporter2, self.emis_reporter3,
                                                  self.emis_reporter4])

    def fake_incoming(self, message, reporter):
        router = get_router()
        connection = reporter.default_connection
        return router.handle_incoming(connection.backend.name, connection.identity, message)

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
        Attribute.objects.all().delete()

class TestSetup(TestCase):
    def setUp(self):
        country = LocationType.objects.create(name='country', slug='country')
        district = LocationType.objects.create(name='district', slug='district')
        uganda_fields = dict(rght=15274, name="Uganda", level=0, tree_id=1, lft=1, type=country)

        self.root_node = Location.objects.create(**uganda_fields)
        self.admin_user = create_user_with_group("John", Role.objects.create(name="Admins"), self.root_node)

        kampala_point_fields = dict(latitude="0.3162800000", longitude="32.5821900000")
        kampala_point = Point.objects.create(**kampala_point_fields)
        kampala_fields = dict(rght=10901, tree_parent=self.root_node, name="Kampala", point=kampala_point, level=1,
                              tree_id=1, lft=10686, type=district)
        self.kampala_district = Location.objects.create(**kampala_fields)

        gulu_point_fields = dict(latitude="2.7666700000", longitude="32.3055600000")
        gulu_point = Point.objects.create(**gulu_point_fields)
        gulu_fields = dict(rght=9063, tree_parent=self.root_node, name="Gulu", point=gulu_point, level=1, tree_id=1,
                           lft=8888, type=district)
        self.gulu_district = Location.objects.create(**gulu_fields)

        self.school = School.objects.create(name="Don Bosco School", location=self.root_node)
        self.school1 = School.objects.create(name="St. Mary School", location=self.root_node)

        self.emisreporter1 = EmisReporter.objects.create(name="Reporter1", reporting_location=self.kampala_district)
        self.emisreporter1.schools.add(self.school)
        self.emisreporter1.save()

        self.emisreporter2 = EmisReporter.objects.create(name="Reporter2", reporting_location=self.kampala_district)
        self.emisreporter2.schools.add(self.school1)
        self.emisreporter2.save()

        self.emisreporter3 = EmisReporter.objects.create(name="Reporter3", reporting_location=self.gulu_district)
        self.emisreporter3.schools.add(self.school)
        self.emisreporter3.save()

        self.backend = Backend.objects.create(name='fake_backed')
        self.connection1 = Connection.objects.create(identity="02022222230", backend=self.backend,
                                                     contact=self.emisreporter1)
        self.connection2 = Connection.objects.create(identity="02022222231", backend=self.backend,
                                                     contact=self.emisreporter2)
        self.connection3 = Connection.objects.create(identity="02022222232", backend=self.backend,
                                                     contact=self.emisreporter3)

    def fake_incoming(self, message, connection):
        router = get_router()
        handled=router.handle_incoming(connection.backend.name, connection.identity, message)
        return handled

    def fake_incoming_with_date(self, message, connection, date):
        router = get_router()
        handled = router.handle_incoming(connection.backend.name, connection.identity, message)
        for response in handled.poll_responses.all():
            response.date = date
            response.save()

        return handled

    def add_group(self, reporters, group):
        for reporter in reporters:
            reporter.groups.add(group)
            reporter.save()

    def create_poll(self, poll_name, poll_user, poll_type, poll_question, poll_default_response):
        self.violence_poll, self.violence_poll_created = Poll.objects.get_or_create(name=poll_name,
                                                                                    user=poll_user,
                                                                                    type=poll_type,
                                                                                    question=poll_question,
                                                                                    default_response=poll_default_response)

    def tearDown(self):
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        School.objects.all().delete()
        EmisReporter.objects.all().delete()
        Connection.objects.all().delete()
        Backend.objects.all().delete()
        Poll.objects.all().delete()
        User.objects.all().delete()
        Group.objects.all().delete()
        Attribute.objects.all().delete()
        Script.objects.all().delete()
        ScriptProgress.objects.all().delete()
        ScriptStep.objects.all().delete()
        ScriptSession.objects.all().delete()
