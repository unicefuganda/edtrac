# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from django.contrib.auth.models import Group
from education.models import schedule_script_now
from education.test.abstract_clases_for_tests import TestAbsenteeism
from education.test.test_absenteeism_view_helper import TestAbsenteeismViewHelper
from education.test.utils import create_group, create_emis_reporters
from poll.models import Poll
from rapidsms.models import Backend, Connection
from script.models import Script, ScriptStep, ScriptProgress, ScriptSession
from script.utils.outgoing import check_progress


class TestFilterForms(TestAbsenteeism):

    def setUp(self):
        super(TestFilterForms, self).setUp()
        self.test_group= create_group("test")
        self.smc_group= create_group("SMC")
        self.emis_reporter5 = create_emis_reporters('Derek', self.kampala_district, self.kampala_school, 1234557,
                                                    self.test_group)
        self.emis_reporter6 = create_emis_reporters('Derek', self.kampala_district, self.kampala_school, 1234558,
                                                    self.smc_group)
        self.head_teachers_script = Script.objects.create(name='Education monitoring smc weekly script',
                                                          slug='edtrac_smc_weekly')
        self.head_teachers_poll, self.head_teachers_poll_created = Poll.objects.get_or_create(
            name='edtrac_head_teachers_attendance',
            user=self.admin_user,
            type=Poll.TYPE_TEXT,
            question='Has the head teacher been at school for at least 3 days? Answer YES or NO',
            default_response='')
        self.head_teachers_poll.add_yesno_categories()
        self.head_teachers_poll.save()
        self.head_teachers_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_script, poll=self.head_teachers_poll, order=0,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=86400 ))

    def test_should_check_wrong_mgs_path(self):
        schedule_script_now(grp=self.smc_group.name,slug='edtrac_smc_weekly')
        check_progress(self.head_teachers_script)
        self.fake_incoming('no', self.emis_reporter5)

    def test_should_check_proper_mgs_path(self):
        schedule_script_now(grp=self.smc_group.name,slug='edtrac_smc_weekly')
        check_progress(self.head_teachers_script)
        self.fake_incoming('no', self.emis_reporter6)

    def tearDown(self):
        super(TestFilterForms, self).tearDown()
        ScriptStep.objects.all().delete()
        Script.objects.all().delete()
        ScriptProgress.objects.all().delete()
        ScriptSession.objects.all().delete()
        Group.objects.all().delete()
        Backend.objects.all().delete()
        Connection.objects.all().delete()