# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
from unittest import TestCase
from django.contrib.auth.models import User, Group
from education.models import EmisReporter, School
from education.test.utils import create_group, create_location_type, create_location, create_school, create_emis_reporters, create_user_with_group, create_poll
from education.water_polls_view_helper import get_all_responses
from education.water_polls_views import get_categories_and_data
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
        self.water_source_poll = create_poll('edtrac_water_source', "Does this school have a water source within 500 metres from the school? Answer yes or no",
                                               Poll.TYPE_TEXT, self.admin_user,
                                               [self.emis_reporter1, self.emis_reporter2, self.emis_reporter3,
                                                self.emis_reporter4])
        self.water_source_poll.add_yesno_categories()
        self.water_source_poll.save()

    def fake_incoming(self, message, reporter):
        router = get_router()
        connection = reporter.default_connection
        return router.handle_incoming(connection.backend.name, connection.identity, message)


    def set_date(self, responses):
        i = 1
        for r in responses:
            r.date = datetime(datetime.today().year, i, datetime.today().day)
            r.save()
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
        self.set_date(responses)
        location_result,monthly_result = get_all_responses(self.water_source_poll,[self.kampala_district])
        self.assertTrue(('January',{'yes':100}) in monthly_result)



    def tearDown(self):
        Poll.objects.all().delete()
        User.objects.all().delete()
        EmisReporter.objects.all().delete()
        School.objects.all().delete()
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        Group.objects.all().delete()