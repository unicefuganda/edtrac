from unittest import TestCase
from django.contrib.auth.models import Group
from education.models import School, EmisReporter
from education.test.utils import create_emis_reporters, create_group, create_location_type, create_location, create_school
from education.water_polls_views import get_valid_reporters
from rapidsms.contrib.locations.models import Location, LocationType


class TestValidReporters(TestCase):

    def setUp(self):
        smc_group = create_group('SMC')
        country = create_location_type("country")
        uganda_fields = {
            "rght": 15274,
            "level": 0,
            "tree_id": 1,
            "lft": 1,
            }
        self.uganda = create_location("uganda", country, **uganda_fields)
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
        self.head_teachers_group = create_group('Head Teachers')
        self.emis_reporter1 = create_emis_reporters("dummy1", self.kampala_district, self.kampala_school, 12345,
                                                    self.head_teachers_group)
        self.emis_reporter2 = create_emis_reporters("dummy2", self.kampala_district, None, 12346, self.head_teachers_group)
        self.emis_reporter3 = create_emis_reporters("dummy3", self.uganda, self.kampala_school, 12347, self.head_teachers_group)
        self.emis_reporter4 = create_emis_reporters("dummy4", self.kampala_district, self.kampala_school, 12348, smc_group)

    def test_should_give_only_valid_reporters(self):
        valid_reporters = get_valid_reporters(self.head_teachers_group)
        self.assertTrue(self.emis_reporter1 in valid_reporters)
        self.assertTrue(1, len(valid_reporters)
        )

    def tearDown(self):
        EmisReporter.objects.all().delete()
        School.objects.all().delete()
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        Group.objects.all().delete()
