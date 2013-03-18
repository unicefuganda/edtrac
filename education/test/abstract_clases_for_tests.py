# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from django.contrib.auth.models import Group
from education.test.utils import *
from poll.models import Response
from rapidsms.models import Connection
from rapidsms_httprouter.router import get_router


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
        self.p3_boys_absent_poll = create_poll("edtrac_boysp3_attendance", "How many P3 boys are at school today?",
                                               Poll.TYPE_NUMERIC, self.admin_user,
                                               [self.emis_reporter1, self.emis_reporter2, self.emis_reporter3,
                                                self.emis_reporter4])
        self.p3_boys_enrolled_poll = create_poll("edtrac_boysp3_enrollment",
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
