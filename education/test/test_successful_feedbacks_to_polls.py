# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
import time
from unittest import TestCase
import dateutils
from django.conf import settings
from django.contrib.auth.models import Group, User
from mock import patch,Mock
from education.attendance_diff import calculate_percent, get_enrolled_boys_and_girls, calculate_attendance_difference
from education.models import schedule_script_now, EmisReporter, School
from education.test.utils import create_poll_with_reporters, create_group, create_location_type, create_location, create_school, create_emis_reporters, create_user_with_group, fake_incoming
from poll.models import Poll
from rapidsms.contrib.locations.models import Location, LocationType
from rapidsms_httprouter.models import Message
from script.models import Script, ScriptStep, ScriptProgress, ScriptSession
from script.utils.outgoing import check_progress


class TestSuccessfulFeedbacksToPolls(TestCase):

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
        self.smc_group = create_group("SMC")
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
        self.emis_reporter1.grade ='P3'
        self.emis_reporter1.save()
        self.emis_reporter2 = create_emis_reporters("dummy2", self.kampala_district, self.kampala_school, 12346,
                                                    self.head_teacher_group)
        self.emis_reporter2.grade ='P3'
        self.emis_reporter2.save()

        self.emis_reporter3 = create_emis_reporters("dummy1", self.kampala_district, self.kampala_school, 12347,
                                                    self.smc_group)

        self.p3_boys_absent_poll = create_poll_with_reporters("edtrac_boysp3_attendance", "How many P3 boys are at school today?",
                                                              Poll.TYPE_NUMERIC, self.admin_user,
                                                              [self.emis_reporter1, self.emis_reporter2])
        self.p3_girls_absent_poll = create_poll_with_reporters("edtrac_girlsp3_attendance", "How many P3 girls are at school today?",
                                                              Poll.TYPE_NUMERIC, self.admin_user,
                                                              [self.emis_reporter1, self.emis_reporter2])

        self.teachers_weekly_script = Script.objects.create(name='Revised P3 Teachers Weekly Script',
                                            slug='edtrac_p3_teachers_weekly')
        self.p3_boys_attendance_step = ScriptStep.objects.create(script=self.teachers_weekly_script, poll=self.p3_boys_absent_poll,
                                                   order=0, rule=ScriptStep.WAIT_MOVEON, start_offset=0,
                                                   giveup_offset=2)
        self.teachers_weekly_script.steps.add(
            self.p3_boys_attendance_step)
        self.p3_girls_attendance_step = ScriptStep.objects.create(script=self.teachers_weekly_script, poll=self.p3_girls_absent_poll,
                                                   order=1, rule=ScriptStep.WAIT_MOVEON, start_offset=0,
                                                   giveup_offset=2)
        self.teachers_weekly_script.steps.add(
            self.p3_girls_attendance_step)

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
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200 ))

        self.head_teachers_termly_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_termly_script, poll=self.p3_girls_enroll_poll, order=1,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200 ))


        self.head_teacher_poll = create_poll_with_reporters("edtrac_head_teachers_attendance", "Has the head teacher been at school for at least 3 days? Answer YES or NO",
                                                               Poll.TYPE_TEXT, self.admin_user,
                                                               [self.emis_reporter3])
        self.head_teacher_poll.add_yesno_categories()
        self.head_teacher_poll.save()
        self.smc_weekly_script = Script.objects.create(name='Education monitoring smc weekly script',
                                                                 slug='edtrac_smc_weekly')
        self.smc_weekly_script.steps.add(
            ScriptStep.objects.create(script=self.smc_weekly_script, poll=self.head_teacher_poll, order=0,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200 ))

        self.head_teachers_weekly_script = Script.objects.create(name = "Teachers weekly attendance script",
                                                            slug = 'edtrac_weekly_teachers_attendance_script')
        self.male_teachers_attendance_poll = create_poll_with_reporters(
            "edtrac_male_teachers_attendance", "How many male teachers were in school this week?",
            Poll.TYPE_NUMERIC, self.admin_user, [self.emis_reporter1])

        self.female_teachers_attendance_poll = create_poll_with_reporters(
            "edtrac_female_teacher_attendance", "How many female teachers were in school this week?",
            Poll.TYPE_NUMERIC, self.admin_user, [self.emis_reporter1])

        self.male_teacher_deployment_poll = create_poll_with_reporters(
            "edtrac_male_teachers_deployment", "How many male teachers were deployed in school this term?",
            Poll.TYPE_NUMERIC, self.admin_user, [self.emis_reporter1])


        self.female_teacher_deployment_poll = create_poll_with_reporters(
            "edtrac_female_teachers_deployment", "How many female teachers were deployed in school this term?",
            Poll.TYPE_NUMERIC, self.admin_user, [self.emis_reporter1])

        self.head_teachers_weekly_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_weekly_script, poll=self.female_teacher_deployment_poll,
                order=0, rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=1)
        )

        self.head_teachers_weekly_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_weekly_script, poll=self.male_teacher_deployment_poll,
                order=1, rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=1)
        )

        self.head_teachers_weekly_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_weekly_script, poll=self.female_teachers_attendance_poll,
                order=2, rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=1)
        )

        self.head_teachers_weekly_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_weekly_script, poll=self.male_teachers_attendance_poll,
                order=3, rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=1)
        )

        self.male_teacher_step = ScriptStep.objects.create(script=self.head_teachers_weekly_script,
        poll=self.male_teachers_attendance_poll, order=3, rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=1)

        settings.SCHOOL_TERM_START = dateutils.increment(datetime.today(),weeks=-4)
        settings.SCHOOL_TERM_END = dateutils.increment(datetime.today(),weeks=8)

    def test_calculate_percent_should_return_50_when_given_1_and_2(self):
        self.assertEqual(50, calculate_percent(1, 2))

    def test_calculate_percent_should_return_0_when_given_denominator_0(self):
        self.assertEqual(0, calculate_percent(1, 0))

    def test_should_check_increment_in_outgoing_msg_count_on_all_responses_received(self):
        schedule_script_now(grp=self.head_teacher_group.name,slug = self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("4",self.emis_reporter1)#response to p3 boys poll
        check_progress(self.teachers_weekly_script)
        self.assertEqual(2,Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).count())
        fake_incoming("3",self.emis_reporter1)#response to p3 girls poll
        check_progress(self.teachers_weekly_script)
        self.assertEqual(3,Message.objects.filter(direction='O',connection=self.emis_reporter1.connection_set.all()[0]).count())

    def test_should_return_10_boys_and_15_girls_given_reporter_responds_10_and_15_to_enrollment_poll(self):
        schedule_script_now(grp = self.head_teacher_group.name, slug = self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10", self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("15", self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        boys, girls = get_enrolled_boys_and_girls(self.emis_reporter1.connection_set.all()[0],
            self.p3_boys_enroll_poll.name, self.p3_girls_enroll_poll.name)
        self.assertEqual(10, boys)
        self.assertEqual(15, girls)

    def test_should_return_0_boys_and_0_girls_given_no_reporter_responds_to_enrollment_poll(self):
        schedule_script_now(grp = self.head_teacher_group.name, slug = self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        time.sleep(2)
        check_progress(self.head_teachers_termly_script)
        time.sleep(2)
        check_progress(self.head_teachers_termly_script)
        boys, girls = get_enrolled_boys_and_girls(self.emis_reporter1.connection_set.all()[0],
            self.p3_boys_enroll_poll.name, self.p3_girls_enroll_poll.name)
        self.assertEqual(0, boys)
        self.assertEqual(0, girls)

    def test_should_return_10_boys_and_0_girls_given_reporter_responds_10boys_but_no_girls_to_enrollment_poll(self):
        schedule_script_now(grp = self.head_teacher_group.name, slug = self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10", self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        time.sleep(2)
        check_progress(self.head_teachers_termly_script)
        boys, girls = get_enrolled_boys_and_girls(self.emis_reporter1.connection_set.all()[0],
            self.p3_boys_enroll_poll.name, self.p3_girls_enroll_poll.name)
        self.assertEqual(10, boys)
        self.assertEqual(0, girls)


    def test_should_calculate_difference_in_attendance_for_this_and_past_week(self):
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10",self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10",self.emis_reporter1)
        schedule_script_now(grp=self.head_teacher_group.name,slug = self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("4",self.emis_reporter1)#response to p3 boys poll
        progress = ScriptProgress.objects.create(script=self.teachers_weekly_script,
            connection=self.emis_reporter1.connection_set.all()[0],step=self.p3_boys_attendance_step)
        attendance_difference = calculate_attendance_difference(self.emis_reporter1.connection_set.all()[0],progress)
        self.assertEqual(40,attendance_difference[self.p3_boys_absent_poll.name][0])
        self.assertEqual("improved",attendance_difference[self.p3_boys_absent_poll.name][1])

    def test_should_give_attendance_difference_as_0_if_error_message_received(self):
        schedule_script_now(grp=self.head_teacher_group.name,slug=self.head_teachers_termly_script.slug)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10",self.emis_reporter1)
        check_progress(self.head_teachers_termly_script)
        fake_incoming("10",self.emis_reporter1)
        schedule_script_now(grp=self.head_teacher_group.name,slug = self.teachers_weekly_script.slug)
        check_progress(self.teachers_weekly_script)
        fake_incoming("I am not in school today",self.emis_reporter1)#response to p3 boys poll
        progress = ScriptProgress.objects.create(script=self.teachers_weekly_script,
            connection=self.emis_reporter1.connection_set.all()[0],step=self.p3_boys_attendance_step)
        attendance_difference = calculate_attendance_difference(self.emis_reporter1.connection_set.all()[0],progress)
        self.assertEqual(0,attendance_difference[self.p3_boys_absent_poll.name][0])
        self.assertEqual("improved",attendance_difference[self.p3_boys_absent_poll.name][1])

    def test_should_report_attendance_difference_for_teachers(self):
        schedule_script_now(grp= self.head_teacher_group.name, slug=self.head_teachers_weekly_script.slug)
        check_progress(self.head_teachers_weekly_script)
        fake_incoming("10", self.emis_reporter1)
        check_progress(self.head_teachers_weekly_script)
        fake_incoming("10", self.emis_reporter1)
        check_progress(self.head_teachers_weekly_script)
        fake_incoming("9", self.emis_reporter1)
        check_progress(self.head_teachers_weekly_script)
        fake_incoming("4", self.emis_reporter1)
        progress = ScriptProgress.objects.create(script=self.head_teachers_weekly_script,
            connection=self.emis_reporter1.connection_set.all()[0], step=self.male_teacher_step)
        teachers_attendance_difference = calculate_attendance_difference(self.emis_reporter1.connection_set.all()[0],
        progress)
#        self.assertEqual()
        print "---"*10
        print teachers_attendance_difference
        print "---"*10

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
