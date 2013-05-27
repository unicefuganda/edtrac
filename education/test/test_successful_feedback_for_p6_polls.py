# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
import datetime
import dateutils
from django.contrib.auth.models import User, Group
from education.attendance_diff import calculate_attendance_diff, get_enrolled_boys_and_girls, calculate_attendance_difference_for_p6
from rapidsms_httprouter.models import Message
from edtrac_project import settings
from education.models import EmisReporter, School, schedule_script_now
from education.test.utils import create_location_type, create_location, create_group, create_user_with_group, create_school, create_emis_reporters, create_poll_with_reporters, fake_incoming
from poll.models import Poll
from rapidsms.contrib.locations.models import Location, LocationType
from script.models import Script, ScriptStep, ScriptProgress, ScriptSession
from script.utils.outgoing import check_progress
from edtrac_project.rapidsms_edtrac.education.attendance_diff import get_enrolled_p6_boys

class TestSuccessFulFeedbackToP6Polls(TestCase):

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
        self.admin_user = create_user_with_group("John", admin_group, self.uganda)

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
        self.head_teacher_group = create_group("Head Teachers")
        self.emis_reporter1 = create_emis_reporters("dummy1", self.kampala_district, self.kampala_school, 12345,
                                                    self.head_teacher_group)
        self.emis_reporter1.grade = 'P6'
        self.emis_reporter1.save()
        self.emis_reporter2 = create_emis_reporters("dummy2", self.kampala_district, self.kampala_school, 12346,
                                                    self.head_teacher_group)
        self.emis_reporter2.grade = 'P6'
        self.emis_reporter2.save()

        self.p6_boys_absent_poll = create_poll_with_reporters("edtrac_boysp6_attendance",
                                                              "How many P6 boys are at school today?",
                                                              Poll.TYPE_NUMERIC, self.admin_user,
                                                              [self.emis_reporter1, self.emis_reporter2])
        self.p6_girls_absent_poll = create_poll_with_reporters("edtrac_girlsp6_attendance",
                                                               "How many P6 girls are at school today?",
                                                               Poll.TYPE_NUMERIC, self.admin_user,
                                                               [self.emis_reporter1, self.emis_reporter2])

        self.teachers_weekly_script = Script.objects.create(name='Revised P6 Teachers Weekly Script',
                                                            slug='edtrac_p6_teachers_weekly')
        self.p6_boys_attendance_step = ScriptStep.objects.create(script=self.teachers_weekly_script,
                                                                 poll=self.p6_boys_absent_poll,
                                                                 order=0, rule=ScriptStep.WAIT_MOVEON, start_offset=0,
                                                                 giveup_offset=7200)
        self.teachers_weekly_script.steps.add(
            self.p6_boys_attendance_step)
        self.p6_girls_attendance_step = ScriptStep.objects.create(script=self.teachers_weekly_script,
                                                                  poll=self.p6_girls_absent_poll,
                                                                  order=1, rule=ScriptStep.WAIT_MOVEON, start_offset=0,
                                                                  giveup_offset=7200)
        self.teachers_weekly_script.steps.add(
            self.p6_girls_attendance_step)
        self.p6_boys_enroll_poll = create_poll_with_reporters("edtrac_boysp6_enrollment",
                                                              "How many boys are enrolled in P6 this term?",
                                                              Poll.TYPE_NUMERIC, self.admin_user,
                                                              [self.emis_reporter1])
        self.p6_girls_enroll_poll = create_poll_with_reporters("edtrac_girlsp6_enrollment",
                                                               "How many girls are enrolled in P6 this term?",
                                                               Poll.TYPE_NUMERIC, self.admin_user,
                                                               [self.emis_reporter1])

        self.head_teachers_termly_script = Script.objects.create(name='P6 Enrollment Headteacher Termly Script',
                                                                 slug='edtrac_p6_enrollment_headteacher_termly')
        self.head_teachers_termly_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_termly_script, poll=self.p6_boys_enroll_poll, order=0,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200))

        self.head_teachers_termly_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_termly_script, poll=self.p6_girls_enroll_poll, order=1,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200))
        settings.SCHOOL_TERM_START = dateutils.increment(datetime.datetime.today(), weeks=-4)
        settings.SCHOOL_TERM_END = dateutils.increment(datetime.datetime.today(), weeks=8)

    def test_should_return_10_given_reporter_responds_10_to_boys_enrollment_poll(self):
        schedule_script_now(grp=self.head_teacher_group.name, slug = self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10", self.emis_reporter1)
        enrolled_boys = get_enrolled_p6_boys(self.emis_reporter1.connection_set.all()[0],
            settings.SCHOOL_TERM_START, settings.SCHOOL_TERM_END)
        self.assertEqual(10, enrolled_boys)

    def test_should_return_0_given_no_reporter_responds_to_boys_enrollment_poll(self):
        schedule_script_now(grp=self.head_teacher_group.name, slug = self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        enrolled_boys = get_enrolled_p6_boys(self.emis_reporter1.connection_set.all()[0],
            settings.SCHOOL_TERM_START, settings.SCHOOL_TERM_END)
        self.assertEqual(0, enrolled_boys)

    def test_should_calculate_difference_in_attendance_for_this_and_past_week(self):
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10",self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10",self.emis_reporter1)
        schedule_script_now(grp=self.head_teacher_group.name,slug = self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("4",self.emis_reporter1)
        progress = ScriptProgress.objects.create(script=self.teachers_weekly_script,
                                                 connection=self.emis_reporter1.connection_set.all()[0],
                                                 step=self.p6_boys_attendance_step)
        attendance_difference = calculate_attendance_difference_for_p6(self.emis_reporter1.connection_set.all()[0], progress)

        self.assertEqual(40,attendance_difference['boysp6'][0])
        self.assertEqual("improved",attendance_difference['boysp6'][1])

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


