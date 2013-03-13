# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

from mock import patch, Mock

from education.absenteeism_view_helper import get_responses_over_month, get_responses_by_location
from education.models import EnrolledDeployedQuestionsAnswered, create_record_enrolled_deployed_questions_answered, UserProfile, Role
from education.test.abstract_clases_for_tests import TestAbsenteeism
from education.test.utils import create_attribute, create_group


class TestAbsenteeismViewHelper(TestAbsenteeism):
    def test_should_return_sum_over_districts(self):
        create_attribute()
        locations = [self.kampala_district, self.gulu_district]
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        result = get_responses_over_month(self.p3_boys_enrolled_poll.name, locations,4)
        kampala_result = result[0][0]
        self.assertTrue(self.kampala_district.name in kampala_result.values())
        self.assertTrue(20.0 in kampala_result.values())

    def test_should_return_data_for_given_location_only(self):
        create_attribute()
        locations = [self.kampala_district]
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.fake_incoming('10', self.emis_reporter3) #gulu response
        result = get_responses_over_month(self.p3_boys_enrolled_poll.name, locations,4)
        location_result = result[0][0]
        self.assertFalse(self.gulu_district.name in location_result.values())

    def test_should_ignore_locations_if_no_response_found(self):
        with patch('education.absenteeism_view_helper.get_responses_over_month') as method_mock:
            get_responses_by_location(self.admin_user.get_profile(), self.p3_boys_enrolled_poll.name)
            method_mock.assert_called_with(self.p3_boys_enrolled_poll.name, [],4)

    def test_should_give_result_for_p3_boys_poll(self):
        self.p3_boys_enrolled_poll.start()
        self.fake_incoming('10', self.emis_reporter1)
        self.fake_incoming('10', self.emis_reporter2)
        self.p3_boys_enrolled_poll.end()
        create_record_enrolled_deployed_questions_answered(model=EnrolledDeployedQuestionsAnswered)
        with patch('education.absenteeism_view_helper.get_responses_over_month') as method_mock:
            get_responses_by_location(self.admin_user.get_profile(), self.p3_boys_enrolled_poll.name)
            method_mock.assert_called_with(self.p3_boys_enrolled_poll.name, [self.kampala_district],4)

    def test_should_give_result_for_p3_boys_poll_at_location(self):
        test_role = create_group('test')
        with patch('education.absenteeism_view_helper.get_responses_over_month') as method_mock:
            get_responses_by_location(UserProfile(location=self.gulu_district, role=test_role),
                                      self.p3_boys_enrolled_poll.name)
            method_mock.assert_called_with(self.p3_boys_enrolled_poll.name, [self.gulu_district],4)
