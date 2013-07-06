# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from django.contrib.auth.models import User
from django.test import Client
from education.models import School, Role
from education.test.utils import create_location_type, create_location, create_group, create_user_with_group, create_school
from rapidsms.contrib.locations.models import Location, LocationType


class TestAdditionOfSchools(TestCase):
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
        self.kampala_school = create_school("St. Joseph's", self.kampala_district)
        self.admin_user = create_user_with_group("John", admin_group, self.uganda)

    def test_that_one_school_has_been_created_in_setup(self):
        self.assertEqual(1, School.objects.all().count())

    def test_school_name_exist_in_database(self):
        self.assertTrue("St. Joseph's" in School.objects.all().values_list('name', flat=True))

    def test_if_school_gets_added(self):
        client = Client()
        client.login(username='John', password='password')
        client.post('/edtrac/add_schools/', {'name': 'School2', 'location': self.kampala_district.id})
        self.assertEqual(2, School.objects.all().count())
        self.assertTrue("School1", School.objects.all().values_list('name', flat=True))

    def test_add_multiple_schools(self):
        self.assertTrue(2 == 1)

    def tearDown(self):
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        Role.objects.all().delete()
        School.objects.all().delete()
        User.objects.all().delete()


