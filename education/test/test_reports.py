# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from education.reports import get_numeric_report_data


class TestReports(TestCase):

    def test_should_return_zero_for_non_existent_poll_name(self):
        poll_name = 'fake'
        self.assertEqual(get_numeric_report_data(poll_name), 0)
