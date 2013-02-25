# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from education.views import CapitationGrants


class TestCapitationGrant(TestCase):
    def setUp(self):
        self.capitation_grant_view = CapitationGrants()

    def test_should_calculate_percentage_for_given_values(self):
        self.assertEqual(30, self.capitation_grant_view.compute_percent(30, 100))

    def test_should_handle_percentage_calculation_if_total_is_zero(self):
        self.assertEqual(0, self.capitation_grant_view.compute_percent(30, 0))

    def test_should_return_propere_percentvalues(self):
        input_list = [{'category__name': 'yes',
                       'value': 30},
                      {'category__name': 'no',
                       'value': 20}]
        expected = {'yes': 60, 'no': 40}
        self.assertEqual(expected, self.capitation_grant_view.extract_info(input_list))