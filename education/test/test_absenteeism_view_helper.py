# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import datetime
import dateutils
from django.conf import settings
from django.contrib.auth.models import Group
from django.test import Client

from mock import patch

from education.absenteeism_view_helper import get_responses_over_depth, get_responses_by_location, get_head_teachers_absent_over_time, get_date_range, get_polls_for_keyword
from education.models import EnrolledDeployedQuestionsAnswered, create_record_enrolled_deployed_questions_answered, schedule_script_now, reschedule_weekly_script
from education.reports import get_week_date
from education.test.abstract_clases_for_tests import TestAbsenteeism
from education.test.utils import create_attribute, create_group, create_poll_with_reporters, create_emis_reporters, create_school
from poll.models import Poll, Response
from script.models import Script, ScriptStep, ScriptProgress, ScriptSession
from script.utils.outgoing import check_progress
from rapidsms_httprouter.models import Message


class TestAbsenteeismViewHelper(TestAbsenteeism):
    def setUp(self):
        super(TestAbsenteeismViewHelper, self).setUp()
        self.kampala_school1 = create_school("St. Joseph's", self.kampala_district)
        self.smc_group = create_group("SMC")
        self.emis_reporter5 = create_emis_reporters('Derek', self.kampala_district, self.kampala_school, 1234557,
                                                    self.smc_group)
        self.emis_reporter6 = create_emis_reporters('Peter', self.kampala_district, self.kampala_school1, 1234558,
                                                    self.smc_group)
        self.head_teachers_group = create_group("Head Teachers")
        self.emis_reporter7 = create_emis_reporters('John', self.kampala_district, self.kampala_school, 1234559,
                                                    self.head_teachers_group)
        self.emis_reporter7.gender = 'M'
        self.emis_reporter7.save()
        self.emis_reporter8 = create_emis_reporters('James', self.kampala_district, self.kampala_school1, 1234550,
                                                    self.head_teachers_group)
        self.emis_reporter8.gender = 'm'
        self.emis_reporter8.save()
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

        self.teachers_weekly_script = Script.objects.create(name='Revised P3 Teachers Weekly Script',slug='edtrac_p3_teachers_weekly')
        self.p3_boys_absent_poll.contacts.add(self.emis_reporter7)
        self.p3_boys_absent_poll.contacts.add(self.emis_reporter8)
        self.p3_boys_absent_poll.save()
        self.teachers_weekly_script.steps.add(
            ScriptStep.objects.create(script=self.teachers_weekly_script, poll=self.p3_boys_absent_poll, order=0,
                                      rule=ScriptStep.WAIT_MOVEON, start_offset=0, giveup_offset=7200 ))

        settings.SCHOOL_TERM_START = dateutils.increment(datetime.datetime.now(),weeks=-8)
        settings.SCHOOL_TERM_END = dateutils.increment(datetime.datetime.now(),weeks=1)
        self.date_week = get_week_date(4)

    def test_should_return_sum_over_districts(self):
        create_attribute()
        locations = [self.kampala_district, self.gulu_district]
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.p3_boys_enrolled_poll.end()
        result_absent, result_enrolled,school_percent = get_responses_over_depth(self.p3_boys_absent_poll.name,
                                                                  self.p3_boys_enrolled_poll.name, locations, self.date_week)
        kampala_result = result_enrolled[0]
        self.assertTrue(self.kampala_district.name in kampala_result.values())
        self.assertIn(20.0, kampala_result.values())
        self.assertEqual(0,school_percent)

    def test_should_return_data_for_given_location_only(self):
        create_attribute()
        locations = [self.kampala_district]
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.fake_incoming('10', self.emis_reporter3) #gulu response
        result_absent, result_enrolled,school_percent = get_responses_over_depth(self.p3_boys_absent_poll.name,
                                                                  self.p3_boys_enrolled_poll.name, locations, self.date_week)
        location_result = result_enrolled[0]
        self.assertFalse(self.gulu_district.name in location_result.values())

    def test_should_ignore_locations_if_no_response_found(self):
        with patch('education.absenteeism_view_helper.get_responses_over_depth') as method_mock:
            method_mock.return_value = [], [] , 0
            config_data = get_polls_for_keyword('P3Boys')
            config=config_data[0]
            get_responses_by_location(list(self.uganda.get_children()),config,
                                      self.date_week)
            method_mock.assert_called_with(config['attendance_poll'][0],config['enrollment_poll'][0], list(self.uganda.get_children()), self.date_week)

    def test_should_give_result_for_p3_boys_poll(self):
        locations = [self.kampala_district]
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.p3_boys_enrolled_poll.end()
        create_record_enrolled_deployed_questions_answered(model=EnrolledDeployedQuestionsAnswered)
        with patch('education.absenteeism_view_helper.get_responses_over_depth') as method_mock:
            method_mock.return_value = [], [],0
            config_data = get_polls_for_keyword('P3Boys')
            config=config_data[0]
            get_responses_by_location(locations, config ,self.date_week)
            method_mock.assert_called_with(config['attendance_poll'][0],config['enrollment_poll'][0],
                                           locations, self.date_week)

    def test_should_give_result_for_p3_boys_poll_at_location(self):
        locations = [self.gulu_district]
        with patch('education.absenteeism_view_helper.get_responses_over_depth') as method_mock:
            method_mock.return_value = [], [],0
            config_data = get_polls_for_keyword('P3Boys')
            config=config_data[0]
            get_responses_by_location(locations, config ,self.date_week)
            method_mock.assert_called_with(config['attendance_poll'][0],config['enrollment_poll'][0],
                                           locations, self.date_week)

    def test_should_give_head_teachers_absenteeism_percent(self):
        schedule_script_now(grp=self.smc_group.name,slug='edtrac_smc_weekly')
        check_progress(self.head_teachers_script)
        locations = [self.kampala_district]
        # self.head_teachers_poll.start()
        self.fake_incoming('no', self.emis_reporter5)
        self.fake_incoming('yes', self.emis_reporter6)
        config = get_polls_for_keyword('MaleHeadTeachers')
        result_by_location, result_by_time,school_percent = get_head_teachers_absent_over_time(locations,config[0], self.date_week)
        self.assertEqual(50, result_by_location.get('Kampala'))
        self.assertIn(50, result_by_time)
        self.assertEqual(25,school_percent) #n four weeks only once replies were sent

    def test_should_return_proper_result_on_POST_request(self):
        client = Client()
        client.login(username='John',password='password')
        create_attribute()
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.p3_boys_enrolled_poll.end()
        self.p3_boys_absent_poll.start()
        self.fake_incoming('5', self.emis_reporter1)
        self.fake_incoming('5', self.emis_reporter2)
        self.p3_boys_absent_poll.end()
        create_record_enrolled_deployed_questions_answered(model = EnrolledDeployedQuestionsAnswered)
        response = client.post('/edtrac/detail-attd/', {'from_date': getattr(settings, 'SCHOOL_TERM_START').strftime('%m/%d/%Y') , 'to_date': getattr(settings, 'SCHOOL_TERM_END').strftime('%m/%d/%Y') , 'indicator':'P3Boys'})
        kampala_result =  response.context['collective_result']['Kampala']
        self.assertEqual(94.0 , round(kampala_result['P3 Boys']))

    def test_should_calculate_date_by_weeks_for_today(self):
        today = datetime.datetime.today()
        fortnight_before = today - datetime.timedelta(days=15)
        date_range = get_date_range(fortnight_before, today)
        self.assertIn((fortnight_before, fortnight_before+datetime.timedelta(days=7)), date_range)

    def test_should_return_proper_config_data_if_indicator_passed(self):
        expected = [dict(attendance_poll=['edtrac_boysp3_attendance'], collective_dict_key='P3 Boys',
                         enrollment_poll=['edtrac_boysp3_enrollment'], time_data_name='P3 Boys', func= get_responses_by_location)]
        config_data = get_polls_for_keyword("P3Boys")
        self.assertEqual(expected,config_data)

    def test_should_give_proper_school_percent_for_location_and_time(self):
        self.p3_boys_absent_poll.start()
        locations = [self.kampala_district]
        self.fake_incoming('3', self.emis_reporter7)
        self.fake_incoming('4', self.emis_reporter8)
        config_data = get_polls_for_keyword('P3Boys')
        config=config_data[0]
        absent_by_loc, absent_by_time, school_percent = get_responses_by_location(locations,config,self.date_week)
        self.assertEqual(25,school_percent)

    def test_should_ignore_attd_if_no_enrollment_found(self):
        client = Client()
        client.login(username='John',password='password')
        create_attribute()
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.fake_incoming('10', self.emis_reporter3)
        self.fake_incoming('10', self.emis_reporter4)
        self.p3_boys_enrolled_poll.end()

        self.p3_boys_absent_poll.start()
        self.fake_incoming('12', self.emis_reporter1)
        self.fake_incoming('6', self.emis_reporter2)
        self.fake_incoming('8', self.emis_reporter3)
        self.fake_incoming('4', self.emis_reporter4)
        self.p3_boys_absent_poll.end()
        self.p3_girls_absent_poll.start()
        self.fake_incoming('3', self.emis_reporter1)
        self.fake_incoming('2', self.emis_reporter2)
        self.fake_incoming('6', self.emis_reporter3)
        self.fake_incoming('4', self.emis_reporter4)
        self.p3_girls_absent_poll.end()
        create_record_enrolled_deployed_questions_answered(model = EnrolledDeployedQuestionsAnswered)
        response = client.post('/edtrac/detail-attd/', {'from_date': getattr(settings, 'SCHOOL_TERM_START').strftime('%m/%d/%Y') , 'to_date': getattr(settings, 'SCHOOL_TERM_END').strftime('%m/%d/%Y') , 'indicator':'P3Pupils'})
        import ast
        time_data = ast.literal_eval(response.context['time_data'])
        self.assertIn(25.0, time_data[0]['data'])

    def test_should_calculate_attd_for_past_five_weeks(self):
        client = Client()
        client.login(username='John',password='password')
        create_attribute()
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.p3_boys_enrolled_poll.end()

        self.p3_boys_absent_poll.start()
        self.fake_incoming('6', self.emis_reporter1)
        self.fake_incoming('5', self.emis_reporter1)
        self.fake_incoming('7', self.emis_reporter1)
        self.fake_incoming('0', self.emis_reporter1)
        self.fake_incoming('4', self.emis_reporter1)
        self.p3_boys_absent_poll.end()
        responses = self.p3_boys_absent_poll.responses.all()
        self.set_weekly_date(responses)
        self.p3_girls_absent_poll.start()
        self.fake_incoming('5', self.emis_reporter1)
        self.fake_incoming('6', self.emis_reporter1)
        self.fake_incoming('4', self.emis_reporter1)
        self.fake_incoming('6', self.emis_reporter1)
        self.fake_incoming('4', self.emis_reporter1)
        self.p3_girls_absent_poll.end()
        responses = self.p3_boys_absent_poll.responses.all()
        self.set_weekly_date(responses)

        create_record_enrolled_deployed_questions_answered(model = EnrolledDeployedQuestionsAnswered)
        response = client.post('/edtrac/detail-attd/', {'from_date': getattr(settings, 'SCHOOL_TERM_START').strftime('%m/%d/%Y') , 'to_date': getattr(settings, 'SCHOOL_TERM_END').strftime('%m/%d/%Y') , 'indicator':'P3Pupils'})
        import ast
        time_data = ast.literal_eval(response.context['time_data'])
        self.assertTrue(set([60.0, 100.0, 30.0, 50.0, 40.0]) < set(time_data[0]['data']))
        self.assertEqual(76.0 , round(response.context['collective_result']['Kampala']['P3 Pupils']))

    def set_weekly_date(self, responses):
        today = datetime.datetime.now()
        i=-1
        for response in responses:
            self.set_date(dateutils.increment(today,weeks=i), response)
            i -= 1

    def set_date(self, date, r):
        r.date = date
        r.save()

    def tearDown(self):
        super(TestAbsenteeismViewHelper, self).tearDown()
        ScriptStep.objects.all().delete()
        Script.objects.all().delete()
        ScriptProgress.objects.all().delete()
        ScriptSession.objects.all().delete()
        Group.objects.all().delete()
        Message.objects.all().delete()
        Response.objects.all().delete()
