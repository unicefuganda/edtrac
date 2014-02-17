# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from education.reports import get_numeric_report_data, get_month_day_range
import datetime


class TestReports(TestCase):

    def test_should_return_zero_for_non_existent_poll_name(self):
        poll_name = 'fake'
        self.assertEqual(get_numeric_report_data(poll_name), 0)

    def test_get_month_day_range(self):
        month_date_range = get_month_day_range(datetime.date(2012, 02, 01))
        self.assertEqual(month_date_range[0], datetime.datetime(2012, 02, 01, 8, 0))
        self.assertEqual(month_date_range[1], datetime.datetime(2012, 02, 29, 19, 0))
