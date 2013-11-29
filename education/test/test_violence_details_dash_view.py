from unittest import TestCase
from rapidsms.contrib.locations.models import Location
from rapidsms.contrib.locations.models import LocationType
from django.contrib.auth.models import Group
from education.models import schedule_script_now
from education.test.utils import *
from education.views import total_number_of_schools_that_responded_to_all_violence_questions
from poll.models import Poll
from rapidsms_httprouter.models import Message
from script.models import Script, ScriptStep, ScriptProgress
from script.utils.outgoing import check_progress
from education.reports import get_month_day_range

class TestViolenceDetailsDashView(TestCase):
    def setUp(self):
        self.country = create_location_type("country")
        uganda_fields = {
            "rght": 15274,
            "level": 0,
            "tree_id": 1,
            "lft": 1,
        }
        self.uganda = create_location("uganda", self.country, **uganda_fields)
        kampala_fields = {
            "rght": 10901,
            "tree_parent": self.uganda,
            "level": 1,
            "tree_id": 1,
            "lft": 10686,
        }

        masaka_fields = {
            "rght": 10996,
            "tree_parent": self.uganda,
            "level": 1,
            "tree_id": 1,
            "lft": 10008,
        }

        moroto_fields = {
            "rght": 1716,
            "tree_parent": self.uganda,
            "level": 1,
            "tree_id": 1,
            "lft": 14944,
        }

        kampala_point = {
            "latitude": "0.3162800000",
            "longitude": "32.5821900000"
        }
        moroto_point = {
            "latitude": "0.4162800000",
            "longitude": "32.5821900000"
        }
        masaka_point = {
            "latitude": "0.5162800000",
            "longitude": "32.5821900000"
        }
        self.admin_group = create_group("Admins")
        self.smc_group = create_group("SMC")
        self.admin_user = create_user_with_group("John", self.admin_group, self.uganda)

        district = create_location_type("district")

        masaka_district = create_location("Masaka", district, point=masaka_point, **masaka_fields)
        moroto_district = create_location("Moroto", district, point=moroto_point, **moroto_fields)
        kampala_district = create_location("Kampala", district, point=kampala_point, **kampala_fields)

        kampala_school = create_school("St. Joseph's", kampala_district)
        masaka_school = create_school("St. Mary's", masaka_district)
        moroto_school = create_school("St. xyzs Nursery School", moroto_district)

        self.head_teacher_group = create_group("Head Teachers")
        self.emis_reporter1 = create_emis_reporters("dummy1", kampala_district, kampala_school, 12904,
                                               self.head_teacher_group)
        self.emis_reporter1.grade = 'P3'
        self.emis_reporter1.save()

        self.emis_reporter2 = create_emis_reporters("dummy2", masaka_district, masaka_school, 16646,
                                               self.head_teacher_group)
        self.emis_reporter2.grade = 'P3'
        self.emis_reporter2.save()

        self.emis_reporter3 = create_emis_reporters("dummy3", moroto_district, moroto_school, 13247,
                                               self.head_teacher_group)
        self.emis_reporter3.grade = 'P3'
        self.emis_reporter3.save()

        self.p3_boys_violence_poll = create_poll_with_reporters("edtrac_violence_boys",
                                                           "How many cases of violence against boys were recorded this month? Answer in figures e.g. 5",
                                                           Poll.TYPE_NUMERIC, self.admin_user,
                                                           [self.emis_reporter1, self.emis_reporter2, self.emis_reporter3])

        self.p3_girls_violence_poll = create_poll_with_reporters("edtrac_violence_girls",
                                                            "How many cases of violence against girls were recorded this month? Answer in figures e.g. 5",
                                                            Poll.TYPE_NUMERIC, self.admin_user,
                                                            [self.emis_reporter1, self.emis_reporter2, self.emis_reporter3])

        self.refererred_violence_poll = create_poll_with_reporters("edtrac_violence_reported",
                                                              "How many cases of violence were referred to the Police this month? Answer in figures e.g. 6",
                                                              Poll.TYPE_NUMERIC, self.admin_user,
                                                              [self.emis_reporter1, self.emis_reporter2, self.emis_reporter3])

        self.p3_violence_script = Script.objects.create(name="Headteacher Violence Monthly Script",
                                                   slug="edtrac_headteacher_violence_monthly")
        self.p3_violence_script.steps.add(
            ScriptStep.objects.create(script=self.p3_violence_script, poll=self.p3_boys_violence_poll, order=0,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=2)
        )
        self.p3_violence_script.steps.add(
            ScriptStep.objects.create(script=self.p3_violence_script, poll=self.p3_girls_violence_poll, order=1,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=2)
        )
        self.p3_violence_script.steps.add(
            ScriptStep.objects.create(script=self.p3_violence_script, poll=self.refererred_violence_poll, order=2,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=2)
        )

    def test_returns_3_as_number_of_schools_that_responded_to_all_violence_questions_if_3_schools_respond(self):
        month_day_range = get_month_day_range(datetime.datetime.now(), depth=1)[0]
        schedule_script_now(self.head_teacher_group.name, slug=self.p3_violence_script.slug)
        check_progress(self.p3_violence_script)
        fake_incoming('6', self.emis_reporter1)
        fake_incoming('3', self.emis_reporter2)
        check_progress(self.p3_violence_script)
        fake_incoming('0', self.emis_reporter1)
        fake_incoming('1', self.emis_reporter2)
        check_progress(self.p3_violence_script)
        fake_incoming('0', self.emis_reporter1)
        fake_incoming('1', self.emis_reporter2)
        self.assertEquals(2, total_number_of_schools_that_responded_to_all_violence_questions([self.emis_reporter1.reporting_location,\
                                                                                               self.emis_reporter2.reporting_location],\
                                                                                              month_day_range))


    def test_returns_the_number_of_schools_that_responded_to_all_the_three_questions(self):
        month_day_range = get_month_day_range(datetime.datetime.now(), depth=1)[0]
        schedule_script_now(self.head_teacher_group.name, slug=self.p3_violence_script.slug)
        check_progress(self.p3_violence_script)
        fake_incoming('6', self.emis_reporter1)
        fake_incoming('3', self.emis_reporter2)
        fake_incoming('0', self.emis_reporter3)
        check_progress(self.p3_violence_script)
        fake_incoming('0', self.emis_reporter1)
        fake_incoming('1', self.emis_reporter2)
        fake_incoming('2', self.emis_reporter3)
        check_progress(self.p3_violence_script)
        fake_incoming('0', self.emis_reporter1)
        fake_incoming('1', self.emis_reporter2)
        fake_incoming('2', self.emis_reporter3)
        self.assertEquals(3, total_number_of_schools_that_responded_to_all_violence_questions([self.emis_reporter1.reporting_location,\
                                                                                               self.emis_reporter2.reporting_location,\
                                                                                              self.emis_reporter3.reporting_location],\
                                                                                              month_day_range))

    def test_that_2_reporters_responded_to_all_the_three_questions_given_one_responds_to_only_two_questions(self):
        month_day_range = get_month_day_range(datetime.datetime.now(), depth=1)[0]
        schedule_script_now(self.head_teacher_group.name, slug=self.p3_violence_script.slug)
        check_progress(self.p3_violence_script)
        fake_incoming('6', self.emis_reporter1)
        fake_incoming('3', self.emis_reporter2)
        fake_incoming('0', self.emis_reporter3)
        check_progress(self.p3_violence_script)
        fake_incoming('0', self.emis_reporter1)
        fake_incoming('1', self.emis_reporter2)
        fake_incoming('2', self.emis_reporter3)
        check_progress(self.p3_violence_script)
        fake_incoming('0', self.emis_reporter1)
        fake_incoming('1', self.emis_reporter2)
        self.assertEquals(2, total_number_of_schools_that_responded_to_all_violence_questions([self.emis_reporter1.reporting_location,\
                                                                                               self.emis_reporter2.reporting_location,\
                                                                                              self.emis_reporter3.reporting_location],\
                                                                                              month_day_range))


    def test_that_0_reporters_responded_to_all_the_three_questions_given_all_respond_to_only_two_questions(self):
        month_day_range = get_month_day_range(datetime.datetime.now(), depth=1)[0]
        schedule_script_now(self.head_teacher_group.name, slug=self.p3_violence_script.slug)
        check_progress(self.p3_violence_script)
        fake_incoming('6', self.emis_reporter1)
        fake_incoming('3', self.emis_reporter2)
        fake_incoming('0', self.emis_reporter3)
        check_progress(self.p3_violence_script)
        fake_incoming('1', self.emis_reporter2)
        fake_incoming('2', self.emis_reporter3)
        check_progress(self.p3_violence_script)
        fake_incoming('9', self.emis_reporter1)
        self.assertEquals(0, total_number_of_schools_that_responded_to_all_violence_questions([self.emis_reporter1.reporting_location,\
                                                                                               self.emis_reporter2.reporting_location,\
                                                                                              self.emis_reporter3.reporting_location],\
                                                                                              month_day_range))

    def tearDown(self):
        Message.objects.all().delete()
        ScriptProgress.objects.all().delete()
        ScriptStep.objects.all().delete()
        ScriptSession.objects.all().delete()
        Script.objects.all().delete()
        Poll.objects.all().delete()
        EmisReporter.objects.all().delete()
        Location.objects.all().delete()
        LocationType.objects.all().delete()
        School.objects.all().delete()
        User.objects.all().delete()
        Group.objects.all().delete()