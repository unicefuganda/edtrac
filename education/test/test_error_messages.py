# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from django.contrib.auth.models import Group
from django.test import Client, RequestFactory
from education.models import schedule_script_now
from education.reports import messages
from education.test.abstract_clases_for_tests import TestAbsenteeism
from education.test.utils import create_group, create_emis_reporters
from poll.models import Poll
from rapidsms.models import Backend, Connection
from script.models import Script, ScriptStep, ScriptProgress, ScriptSession
from script.utils.outgoing import check_progress


class TestErrorMessages(TestAbsenteeism):

    def setUp(self):
        super(TestErrorMessages, self).setUp()
        self.test_group= create_group("test")
        self.smc_group= create_group("SMC")
        self.emis_reporter5 = create_emis_reporters('Derek', self.kampala_district, self.kampala_school, 1234557,
                                                    self.test_group)
        self.emis_reporter6 = create_emis_reporters('Derek', self.kampala_district, self.kampala_school, 1234558,
                                                    self.smc_group)
        self.emis_reporter7 = create_emis_reporters('Derek', self.kampala_district, self.kampala_school, 1234559,
                                                    self.smc_group)
        self.emis_reporter8 = create_emis_reporters('Derek', self.kampala_district, self.kampala_school, 1234550,
                                                    self.smc_group)
        self.head_teachers_script = Script.objects.create(name='Education monitoring head teachers weekly script',
                                                          slug='edtrac_head_teachers_weekly')
        self.head_teachers_poll, self.head_teachers_poll_created = Poll.objects.get_or_create(
            name='edtrac_f_teachers_attendance',
            user=self.admin_user,
            type=Poll.TYPE_NUMERIC,
            question='How many female teachers are at school today?',
            default_response='')
        # self.head_teachers_poll.add_yesno_categories()
        self.head_teachers_poll.save()
        self.head_teachers_script.steps.add(
            ScriptStep.objects.create(script=self.head_teachers_script, poll=self.head_teachers_poll, order=0,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=86400 ))

        self.factory = RequestFactory()


    def test_should_check_count_of_error_messages(self):
        schedule_script_now(grp=self.smc_group.name,slug='edtrac_head_teachers_weekly')
        check_progress(self.head_teachers_script)
        self.fake_incoming(3, self.emis_reporter5) #error msg
        self.fake_incoming(2, self.emis_reporter6)
        request = self.factory.get('/customer/messages/?error_msgs=True')
        request.user = self.admin_user
        resp = messages(request)
        self.assertEqual(1 , resp.count())

    def test_should_check_message_of_error_messages(self):
        schedule_script_now(grp=self.smc_group.name,slug='edtrac_head_teachers_weekly')
        check_progress(self.head_teachers_script)
        self.fake_incoming(2, self.emis_reporter6)
        self.fake_incoming("NO one in school today", self.emis_reporter7) #error msg
        request = self.factory.get('/customer/messages/?error_msgs=True')
        request.user = self.admin_user
        resp = messages(request)
        self.assertEqual(1 ,resp.count())

    def test_should_return_none_if_all_messages_are_valid(self):
        schedule_script_now(grp=self.smc_group.name,slug='edtrac_head_teachers_weekly')
        check_progress(self.head_teachers_script)
        self.fake_incoming(2, self.emis_reporter6)
        self.fake_incoming(3, self.emis_reporter7)
        self.fake_incoming(2, self.emis_reporter8)
        request = self.factory.get('/customer/messages/?error_msgs=True')
        request.user = self.admin_user
        resp = messages(request)
        self.assertEqual(0,resp.count())

    def tearDown(self):
        super(TestErrorMessages, self).tearDown()
        ScriptStep.objects.all().delete()
        Script.objects.all().delete()
        ScriptProgress.objects.all().delete()
        ScriptSession.objects.all().delete()
        Group.objects.all().delete()
        Backend.objects.all().delete()
        Connection.objects.all().delete()