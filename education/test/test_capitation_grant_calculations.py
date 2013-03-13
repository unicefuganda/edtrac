# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

from unittest import TestCase
from django.contrib.auth.models import User, Group
from education.models import School, EmisReporter
from education.views import CapitationGrants
from rapidsms.models import Backend, Connection
from rapidsms.contrib.locations.models import LocationType, Location
from poll.models import Poll, Response
from education.test.utils import *
from rapidsms_httprouter.router import get_router


class TestCapitationGrantView(TestCase):
    def setUp(self):

        country = create_location_type("country")
        uganda_fields = {
            "rght": 15274,
            "level": 0,
            "tree_id": 1,
            "lft": 1,
        }
        self.uganda = create_location("Uganda", country, **uganda_fields)


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

        smc_group = create_group('SMC')
        admin_group = create_group('Admins')
        admin_user = create_user_with_group('fred', admin_group, self.uganda)
        district_user = create_user_with_group('John', smc_group, self.kampala_district)

        self.kampala_school = create_school("St. Mary's", self.kampala_district)
        self.emis_reporter1 = create_emis_reporters("dummy1", self.kampala_district, self.kampala_school, 1233456, smc_group)
        self.kampala_school2 = create_school("St. Joseph's", self.kampala_district)
        self.emis_reporter2 = create_emis_reporters("dummy2", self.kampala_district, self.kampala_school2, 1233457, smc_group)
        self.emis_reporter4 = create_emis_reporters("dummy4", self.kampala_district, self.kampala_school, 1233459, smc_group)
        self.emis_reporter3 = create_emis_reporters("dummy3", self.gulu_district, gulu_school, 1233458, smc_group)

        self.smc_poll = create_poll("edtrac_smc_upe_grant",
                               "Have you received your UPE grant this term? Answer  YES or NO or I don't know",
                               Poll.TYPE_TEXT,
                               admin_user, [self.emis_reporter1, self.emis_reporter2, self.emis_reporter3,self.emis_reporter4])

        self.smc_poll.add_yesno_categories()
        self.smc_poll.start()
        self.smc_capitation_grant_view = create_view(CapitationGrants, admin_user, self.smc_poll, smc_group)
        self.smc_capitation_grant_view_district = create_view(CapitationGrants, district_user, self.smc_poll, smc_group)


    def test_should_check_calculation_of_response_percentages(self):
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('no',self.emis_reporter2)
        self.fake_incoming('no',self.emis_reporter3)
        result = self.smc_capitation_grant_view.get_context_data()
        self.assertTrue(result.get('authorized_user'))
        result_dict = dict(result.get('responses'))
        self.assertAlmostEqual(33.33 , result_dict['yes'],places=1)
        self.assertAlmostEqual(66.66 , result_dict['no'],places=1)

    def test_should_consider_only_i_dont_know_responses_as_unknown(self):
        self.fake_incoming('i Dont know',self.emis_reporter1)
        self.fake_incoming('blah',self.emis_reporter2)
        self.fake_incoming('yes',self.emis_reporter3)
        result = self.smc_capitation_grant_view.get_context_data()
        result_dict = dict(result.get('responses'))
        self.assertEqual(50.00 , result_dict['yes'])
        self.assertEqual(50.00 , result_dict['unknown'])

    def test_should_check_calculation_of_smc_count(self):
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('blah',self.emis_reporter2)
        result = self.smc_capitation_grant_view.get_context_data()
        self.assertEqual(25.00,result.get('reporter_count'))

    def test_should_check_location_of_user(self):
        result = self.smc_capitation_grant_view.get_context_data()
        self.assertEqual(self.uganda,result.get('location'))

    def test_should_check_sub_location_data(self):
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('no',self.emis_reporter2)
        self.fake_incoming('yes',self.emis_reporter3)
        result = self.smc_capitation_grant_view.get_context_data()
        self.assertTrue((self.kampala_district,[('yes',50.00),('no',50.00)]) in result.get('sub_locations'))
        self.assertTrue((self.gulu_district,[('yes',100.00)]) in result.get('sub_locations'))

    def test_should_check_sub_location_type(self):
        result = self.smc_capitation_grant_view.get_context_data()
        self.assertEqual(self.kampala_district.type.name , result.get('sub_location_type'))

    def test_should_check_responses_at_district_level(self):
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('no',self.emis_reporter2)
        result = self.smc_capitation_grant_view_district.get_context_data()
        self.assertFalse(result.get('authorized_user'))
        result_dict= dict(result.get('responses'))
        self.assertEqual(50.00,result_dict['yes'])
        self.assertEqual(50.00,result_dict['no'])

    def test_should_consider_only_i_dont_know_at_district_level(self):
        self.fake_incoming('blah',self.emis_reporter1)
        self.fake_incoming('i dont know',self.emis_reporter2)
        self.fake_incoming('yes',self.emis_reporter4)
        result = self.smc_capitation_grant_view_district.get_context_data()
        self.assertTrue(('yes', 50.00) in result.get('responses'))
        self.assertTrue(('unknown', 50.00) in  result.get('responses'))

    def test_should_check_smc_count_at_district_level(self):
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('blah',self.emis_reporter2)
        result = self.smc_capitation_grant_view_district.get_context_data()
        self.assertAlmostEqual(33.33,result.get('reporter_count'),places=1)

    def test_should_check_location_of_user_at_district_level(self):
        result = self.smc_capitation_grant_view_district.get_context_data()
        self.assertEqual(self.kampala_district,result.get('location'))

    def test_should_check_sub_location_data_at_district_level(self):
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('no',self.emis_reporter2)
        self.fake_incoming('no',self.emis_reporter4)
        result = self.smc_capitation_grant_view_district.get_context_data()
        self.assertTrue((self.kampala_school,[('yes',50.0),('no',50.0)])in result['sub_locations'])
        self.assertTrue((self.kampala_school2,[('no',100.0)]) in result['sub_locations'])

    def test_should_check_type_of_sub_locations_at_distrcit_level(self):
        result = self.smc_capitation_grant_view_district.get_context_data()
        self.assertEqual("school",result['sub_location_type'])

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


    def fake_incoming(self, message, reporter):
        router = get_router()
        connection = reporter.default_connection
        return router.handle_incoming(connection.backend.name, connection.identity, message)