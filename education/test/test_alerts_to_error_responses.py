# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
from unittest import TestCase
import dateutils
from django.conf import settings
from django.contrib.auth.models import User, Group
from mock import patch
import time
from education.models import schedule_script_now, EmisReporter, School
from education.test.utils import create_group, create_location_type, create_location, create_school, create_emis_reporters, create_poll_with_reporters, create_user_with_group, fake_incoming
from poll.models import Poll, Response
from rapidsms.contrib.locations.models import Location, LocationType
from rapidsms_httprouter.models import Message
from script.models import Script, ScriptStep, ScriptProgress, ScriptSession
from script.utils.outgoing import check_progress
from education.utils import _this_thursday


class TestAlertsToErrorResponses(TestCase):
    def setUp(self):
        self.smc_group = create_group("SMC")
        country = create_location_type("country")
        uganda_fields = {
            "rght": 15274,
            "level": 0,
            "tree_id": 1,
            "lft": 1,
            }
        self.uganda = create_location("uganda", country, **uganda_fields)
        admin_group = create_group("Admins")
        self.admin_user = create_user_with_group("John", admin_group, self.uganda)
        district = create_location_type("district")
        kampala_fields = {
            "rght": 10901,
            "tree_parent": None,
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
        self.head_teacher_group = create_group("Head Teachers")
        self.emis_reporter1 = create_emis_reporters("dummy1", self.kampala_district, self.kampala_school, 12345,
                                                    self.head_teacher_group)
        self.emis_reporter1.grade ='P3'
        self.emis_reporter1.save()
        self.p3_boys_absent_poll = create_poll_with_reporters("edtrac_boysp3_attendance", "How many P3 boys are at school today?",
                                                              Poll.TYPE_NUMERIC, self.admin_user,
                                                              [self.emis_reporter1])
        self.p3_girls_absent_poll = create_poll_with_reporters("edtrac_girlsp3_attendance", "How many P3 girls are at school today?",
                                                              Poll.TYPE_NUMERIC, self.admin_user,
                                                              [self.emis_reporter1])

        self.teachers_weekly_script = Script.objects.create(name='Revised P3 Teachers Weekly Script',
                                                            slug='edtrac_p3_teachers_weekly')
        self.p3_boys_attendance_step = ScriptStep.objects.create(script=self.teachers_weekly_script, poll=self.p3_boys_absent_poll,
                                                                 order=0, rule=ScriptStep.WAIT_MOVEON, start_offset=0,
                                                                 giveup_offset=2)
        self.teachers_weekly_script.steps.add(self.p3_boys_attendance_step)

        self.p3_girls_attendance_step = ScriptStep.objects.create(script=self.teachers_weekly_script, poll=self.p3_girls_absent_poll,
                                                   order=1, rule=ScriptStep.WAIT_MOVEON, start_offset=0,
                                                   giveup_offset=2)
        self.teachers_weekly_script.steps.add(self.p3_girls_attendance_step)

        self.p3_boys_enroll_poll = create_poll_with_reporters("edtrac_boysp3_enrollment", "How many boys are enrolled in P3 this term?",
                                                               Poll.TYPE_NUMERIC, self.admin_user,
                                                               [self.emis_reporter1])
        self.p3_girls_enroll_poll = create_poll_with_reporters("edtrac_girlsp3_enrollment", "How many girls are enrolled in P3 this term?",
                                                               Poll.TYPE_NUMERIC, self.admin_user,
                                                               [self.emis_reporter1])
        self.head_teachers_termly_script = Script.objects.create(name='P3 Enrollment Headteacher Termly Script',
                                                            slug='edtrac_p3_enrollment_headteacher_termly')

        self.head_teachers_termly_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_termly_script, poll=self.p3_boys_enroll_poll, order=0,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200))

        self.head_teachers_termly_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_termly_script, poll=self.p3_girls_enroll_poll, order=1,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200))
        settings.SCHOOL_TERM_START = dateutils.increment(datetime.now(),weeks=-4)
        settings.SCHOOL_TERM_END = dateutils.increment(datetime.now(),weeks=8)

    def test_messages_are_handled_in_education_app(self):
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        with patch('script.app.App.handle') as mock_method:
            fake_incoming("dummy response"
                ,self.emis_reporter1)
            assert not mock_method.called

    def test_should_send_message_if_invalid_response_received(self):
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("dummy response",self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        expected = 'The answer you have provided is not in the correct format. use figures like 3 to answer the question'
        self.assertTrue(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))

    def test_should_send_message_if_number_too_large(self):
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("10001 boys",self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        expected = 'The answer you have provided is not in the correct format. use figures like 3 to answer the question'
        self.assertTrue(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))

    def test_should_resend_poll_question_on_invalid_responses(self):
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("invalid response",self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        self.assertEqual(3,Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).count())
        outgoing_messages = list(Message.objects.filter(direction='O',
                                                  connection=self.emis_reporter1.connection_set.all()[0]).values_list(
            'text', flat=True))
        self.assertEqual(2,outgoing_messages.count(self.p3_boys_absent_poll.question))

    def test_should_send_alert_messages_on_invalid_and_partial_responses(self):
        # 5 outgoing messages (1st) step 0 poll, (2nd) error msg alert (3rd) resend error poll (4th) step 1 msg (5th) Script completion alert
        schedule_script_now(grp=self.head_teacher_group.name, slug=self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("Invalid", self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        expected = 'The answer you have provided is not in the correct format. use figures like 3 to answer the question'
        self.assertTrue(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))
        time.sleep(3)
        check_progress(self.teachers_weekly_script)
        fake_incoming("3",self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        # self.assertEqual(5, Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).count())
        self.assertEqual(4, Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).count())#pausing feedback
        expected = 'Thank you for participating. Remember to answer all your questions next Thursday.'
        # self.assertTrue(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))
        self.assertFalse(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))#pausing feedback


    def test_should_send_2_invalid_alerts_by_script_completion(self):
        schedule_script_now(grp = self.head_teacher_group.name, slug = self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10", self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10", self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("Invalid", self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        fake_incoming("4", self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        fake_incoming("Invalid", self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        fake_incoming("4", self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        alert = 'The answer you have provided is not in the correct format. use figures like 3 to answer the question'
        messages = Message.objects.filter(direction='O', text =alert, connection=self.emis_reporter1.connection_set.all()[0])
        self.assertEqual(2, messages.count())
        expected ='Thankyou p3 Teacher, Attendance for boys have been improved by 40percent Attendance for girls have been improved by 40percent'
        # self.assertTrue(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))
        self.assertFalse(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))#pausing feedback

    def test_previous_week_attendance_against_current_week_attendance(self):
        schedule_script_now(grp = self.head_teacher_group.name, slug = self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10boys", self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10", self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        # previous week absenteeism script schedule
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("5", self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        fake_incoming("5girls", self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        expected ='Thankyou p3 Teacher, Attendance for boys have been improved by 50percent Attendance for girls have been improved by 50percent'
        # self.assertTrue(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))
        self.assertFalse(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))#pausing feedback
        responses = Response.objects.filter(contact__connection=self.emis_reporter1.connection_set.all()[0],
                                           has_errors=False)
        poll_list = ['edtrac_boysp3_attendance','edtrac_girlsp3_attendance']
        this_thursday = _this_thursday().date()
        previous_week = dateutils.increment(this_thursday,days=-12)
        for resp in responses:
            if resp.poll.name in poll_list:
                resp.date = previous_week
                resp.save()
        # current week absenteeism script schedule
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("6boys", self.emis_reporter1)
        check_progress(self.teachers_weekly_script)
        fake_incoming("4", self.emis_reporter1)
        check_progress(self.teachers_weekly_script)

        expected ='Thankyou p3 Teacher, Attendance for boys have been improved by 10percent Attendance for girls have been dropped by 10percent'
        # self.assertTrue(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))
        self.assertFalse(expected in Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).values_list('text',flat=True))#pausing feedback



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
        Response.objects.all().delete()
