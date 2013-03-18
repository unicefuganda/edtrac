# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
import datetime
import dateutils
from django.conf import settings

from mock import patch

from education.absenteeism_view_helper import get_responses_over_depth, get_responses_by_location, get_head_teachers_absent_over_time
from education.models import EnrolledDeployedQuestionsAnswered, create_record_enrolled_deployed_questions_answered, UserProfile
from education.test.abstract_clases_for_tests import TestAbsenteeism
from education.test.utils import create_attribute, create_group, create_poll, create_emis_reporters, create_school
from poll.models import Poll


class TestAbsenteeismViewHelper(TestAbsenteeism):
    def setUp(self):
        super(TestAbsenteeismViewHelper, self).setUp()
        smc_group = create_group("SMC")
        head_teacher_group = create_group("Head Teachers")
        self.kampala_school1 = create_school("St. Joseph's", self.kampala_district)
        self.emis_reporter5 = create_emis_reporters('Derek', self.kampala_district, self.kampala_school, 1234557,
                                                    smc_group)
        self.emis_reporter6 = create_emis_reporters('Peter', self.kampala_district, self.kampala_school1, 1234558,
                                                    smc_group)
        self.emis_reporter7 = create_emis_reporters('John', self.kampala_district, self.kampala_school, 1234559,
                                                    head_teacher_group)
        self.emis_reporter7.gender = 'M'
        self.emis_reporter7.save()
        self.emis_reporter8 = create_emis_reporters('James', self.kampala_district, self.kampala_school1, 1234550,
                                                    head_teacher_group)
        self.emis_reporter8.gender = 'm'
        self.emis_reporter8.save()
        self.head_teachers_poll = create_poll('edtrac_head_teachers_attendance',
                                              'Has the head teacher been at school for at least 3 days? Answer YES or NO',
                                              Poll.TYPE_TEXT,
                                              self.admin_user, [self.emis_reporter5, self.emis_reporter6])
        self.head_teachers_poll.add_yesno_categories()
        self.head_teachers_poll.save()
        settings.SCHOOL_TERM_START = dateutils.increment(datetime.datetime.now(), weeks=-2)
        settings.SCHOOL_TERM_END = dateutils.increment(datetime.datetime.now(), weeks=2)

    def test_should_return_sum_over_districts(self):
        create_attribute()
        locations = [self.kampala_district, self.gulu_district]
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.p3_boys_enrolled_poll.end()
        result_absent, result_enrolled = get_responses_over_depth(self.p3_boys_absent_poll.name,
                                                                  self.p3_boys_enrolled_poll.name, locations, 4)
        kampala_result = result_enrolled[0]
        self.assertTrue(self.kampala_district.name in kampala_result.values())
        self.assertTrue(20.0 in kampala_result.values())

    def test_should_return_data_for_given_location_only(self):
        create_attribute()
        locations = [self.kampala_district]
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.fake_incoming('10', self.emis_reporter3) #gulu response
        result_absent, result_enrolled = get_responses_over_depth(self.p3_boys_absent_poll.name,
                                                                  self.p3_boys_enrolled_poll.name, locations, 4)
        location_result = result_enrolled[0]
        self.assertFalse(self.gulu_district.name in location_result.values())

    def test_should_ignore_locations_if_no_response_found(self):
        with patch('education.absenteeism_view_helper.get_responses_over_depth') as method_mock:
            method_mock.return_value = [], []
            get_responses_by_location(list(self.uganda.get_children()), [self.p3_boys_absent_poll.name],
                                      [self.p3_boys_enrolled_poll.name])
            method_mock.assert_called_with(self.p3_boys_absent_poll.name, self.p3_boys_enrolled_poll.name, list(self.uganda.get_children()), 4)

    def test_should_give_result_for_p3_boys_poll(self):
        locations = [self.kampala_district]
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.p3_boys_enrolled_poll.end()
        create_record_enrolled_deployed_questions_answered(model=EnrolledDeployedQuestionsAnswered)
        with patch('education.absenteeism_view_helper.get_responses_over_depth') as method_mock:
            method_mock.return_value = [], []
            get_responses_by_location(locations, [self.p3_boys_absent_poll.name],
                                      [self.p3_boys_enrolled_poll.name])
            method_mock.assert_called_with(self.p3_boys_absent_poll.name, self.p3_boys_enrolled_poll.name,
                                           locations, 4)

    def test_should_give_result_for_p3_boys_poll_at_location(self):
        locations = [self.gulu_district]
        test_role = create_group('test')
        with patch('education.absenteeism_view_helper.get_responses_over_depth') as method_mock:
            method_mock.return_value = [], []
            get_responses_by_location(locations,[self.p3_boys_absent_poll.name], [self.p3_boys_enrolled_poll.name])
            method_mock.assert_called_with(self.p3_boys_absent_poll.name, self.p3_boys_enrolled_poll.name,
                                           locations, 4)

    def test_sholud_give_head_teachers_absenteeism_percent(self):
        locations = [self.kampala_district]
        self.head_teachers_poll.start()
        self.fake_incoming('no', self.emis_reporter5)
        self.fake_incoming('yes', self.emis_reporter6)
        result_by_location, result_by_time = get_head_teachers_absent_over_time(locations, 'M', 2)
        self.assertEqual(50, result_by_location.get('Kampala'))
        self.assertTrue(50 in result_by_time)