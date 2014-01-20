# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from education.test.utils import create_location_type, create_location, create_group, create_user_with_group,\
    create_school, create_emis_reporters, create_poll_with_reporters, fake_incoming
from poll.models import Poll
from script.models import Script, ScriptStep, ScriptProgress, ScriptSession
import dateutils
import datetime
from django.conf import settings
from rapidsms_httprouter.models import Message
from education.models import EmisReporter, School, schedule_script_now
from rapidsms.contrib.locations.models import Location, LocationType
from django.contrib.auth.models import User, Group
from script.utils.outgoing import check_progress
from edtrac_project.rapidsms_edtrac.education.attendance_diff import get_enrolled_pupils, calculate_attendance_difference


class TestScheduling(TestCase):


    def setUp(self):

        admin_group = create_group("Admins")
        self.admin_user = create_user_with_group("John", admin_group)

        district = create_location_type("district")
        self.kampala_district = create_location("Kampala", district)
        self.kampala_school = create_school("St. Joseph's", self.kampala_district)
        self.teacher_group = create_group("Head Teachers")
        self.reporter = create_emis_reporters("dummy1", self.kampala_district, self.kampala_school, 12345, self.teacher_group)
        self.reporter.grade = 'P6'
        self.reporter.save()

        self.p6_boys_absent_poll = create_poll_with_reporters("edtrac_boysp6_attendance",
                                                              "How many P6 boys are at school today?",
                                                              Poll.TYPE_NUMERIC, self.admin_user,
                                                              [self.reporter])
        self.teachers_weekly_script = Script.objects.create(name='Revised P6 Teachers Weekly Script',
                                                            slug='edtrac_p6_teachers_weekly')
        self.p6_boys_attendance_step = ScriptStep.objects.create(script=self.teachers_weekly_script,
                                                                 poll=self.p6_boys_absent_poll,
                                                                 order=0, rule=ScriptStep.WAIT_MOVEON, start_offset=0,
                                                                 giveup_offset=7200)
        self.teachers_weekly_script.steps.add(self.p6_boys_attendance_step)

        settings.SCHOOL_TERM_START = dateutils.increment(datetime.datetime.today(), weeks=-4)
        settings.SCHOOL_TERM_END = dateutils.increment(datetime.datetime.today(), weeks=8)


    def test_weekly_poll_is_rescheduled_to_next_thursday(self):
        schedule_script_now(grp=self.teacher_group.name, slug = self.teachers_weekly_script.slug)
        self.assertEqual(1, ScriptProgress.objects.filter(time__gte = datetime.datetime.now().date()).count())
        check_progress(self.teachers_weekly_script)
        fake_incoming("4", self.reporter)
        self.assertEqual(1, ScriptProgress.objects.count())


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
