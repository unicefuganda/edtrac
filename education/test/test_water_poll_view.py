# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
from unittest import TestCase
import dateutils
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.test import Client
from education.models import EmisReporter, School
from education.test.utils import create_group, create_location_type, create_location, create_school, create_emis_reporters, create_user_with_group, create_poll_with_reporters
from education.water_polls_view_helper import get_all_responses
from education.water_polls_views import get_categories_and_data, DistrictWaterForm
from poll.models import Poll
from rapidsms.contrib.locations.models import Location, LocationType
from rapidsms_httprouter.router import get_router


class TestWaterPollView(TestCase):
    def setUp(self):
        smc_group = create_group('SMC')
        admin_group = create_group('Admins')
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
        self.emis_reporter2 = create_emis_reporters("dummy2", self.kampala_district, self.kampala_school, 12346, self.head_teachers_group)
        self.emis_reporter3 = create_emis_reporters("dummy3", self.kampala_district, self.kampala_school, 12347, self.head_teachers_group)
        self.emis_reporter4 = create_emis_reporters("dummy4", self.kampala_district, self.kampala_school, 12348, smc_group)
        self.admin_user = create_user_with_group("John", admin_group, self.uganda)
        self.water_source_poll = create_poll_with_reporters('edtrac_water_source', "Does this school have a water source within 500 metres from the school? Answer yes or no",
                                               Poll.TYPE_TEXT, self.admin_user,
                                               [self.emis_reporter1, self.emis_reporter2, self.emis_reporter3,
                                                self.emis_reporter4])
        self.water_source_poll.add_yesno_categories()
        self.water_source_poll.save()
        today = datetime(datetime.now().year,datetime.now().month,datetime.now().day)
        settings.SCHOOL_TERM_START = dateutils.increment(today, weeks=-5)
        settings.SCHOOL_TERM_END = dateutils.increment(today,weeks=7)
        self.term_range = [settings.SCHOOL_TERM_START,settings.SCHOOL_TERM_END]

    def fake_incoming(self, message, reporter):
        router = get_router()
        connection = reporter.default_connection
        return router.handle_incoming(connection.backend.name, connection.identity, message)


    def set_date(self, date, r):
        r.date = date
        r.save()

    def set_monthly_date(self, responses):
        start_term = self.term_range[0]
        i = start_term.month
        for response in responses:
            print "setting month as %s " % i
            self.set_date(datetime(datetime.today().year, i, start_term.day), response)
            i += 1

    def test_should_reorganize_data_for_bar_chart(self):
        responses= [('January',{'yes':50,'no':50}),('February',{'yes':100}),('March',{'no':100})]
        categories,data = get_categories_and_data(responses)
        self.assertEqual(['March', 'February', 'January'],categories)
        self.assertEqual([0,100,50], data)

    def test_should_get_monthly_data(self):
        self.water_source_poll.start()
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('yes',self.emis_reporter2)
        self.fake_incoming('no',self.emis_reporter3)
        responses = self.water_source_poll.responses.all()
        self.set_monthly_date(responses)
        location_result,monthly_result,percent = get_all_responses(self.water_source_poll, [self.kampala_district], self.term_range)
        self.assertTrue((self.term_range[0].strftime("%B"),{'yes':100}) in monthly_result)
        self.assertTrue((dateutils.increment(self.term_range[0],months=2).strftime("%B"),{'no':100}) in monthly_result)


    def test_should_get_location_termly_data(self):
        self.water_source_poll.start()
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('yes',self.emis_reporter2)
        self.fake_incoming('no',self.emis_reporter3)
        location_result , monthly_result,percent = get_all_responses(self.water_source_poll, [self.kampala_district], self.term_range)
        self.assertTrue(('yes', 66) in location_result)

    def test_should_responses_for_current_term_only(self):
        settings.SCHOOL_TERM_START = dateutils.increment(datetime.now(),weeks=-16)
        settings.SCHOOL_TERM_END = dateutils.increment(datetime.now(),weeks=-4)
        term_range = [settings.SCHOOL_TERM_START,settings.SCHOOL_TERM_END]
        self.water_source_poll.start()
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('yes',self.emis_reporter2)
        self.fake_incoming('no',self.emis_reporter3)
        location_result , monthly_result,percent = get_all_responses(self.water_source_poll, [self.kampala_district], term_range)
        self.assertEqual([],location_result)

    def test_should_exclude_unknown_responses_for_pie(self):
        self.water_source_poll.start()
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('no',self.emis_reporter2)
        self.fake_incoming('unknown',self.emis_reporter3)
        location_result , monthly_result,percent = get_all_responses(self.water_source_poll, [self.kampala_district], self.term_range)
        self.assertTrue(('yes', 50) in location_result)
        self.assertTrue(('no', 50) in location_result)

    def test_should_exclude_unknown_responses_for_bar(self):
        day_count=0
        self.water_source_poll.start()
        self.fake_incoming('yes',self.emis_reporter1)
        self.fake_incoming('no',self.emis_reporter2)
        self.fake_incoming('i dont know',self.emis_reporter3)
        responses = self.water_source_poll.responses.all()
        for response in responses:
            self.set_date(dateutils.increment(datetime(datetime.today().year, datetime.today().month, datetime.today().day),days=day_count), response)
            day_count += 1
        location_result,monthly_result,percent = get_all_responses(self.water_source_poll, [self.kampala_district], self.term_range)
        self.assertTrue((datetime.today().strftime("%B"),{'yes':50,'no':50}) in monthly_result)

    def test_should_redirect_to_detail_view_when_form_is_valid(self):
        client = Client()
        client.login(username=self.admin_user.username,password='password')
        response = client.post('/edtrac/district-water-source/', {'district_choices':self.kampala_district.id})
        self.assertEqual(response.status_code,302)

    def tearDown(self):
        Poll.objects.all().delete()
        User.objects.all().delete()
        EmisReporter.objects.all().delete()
        School.objects.all().delete()
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        Group.objects.all().delete()