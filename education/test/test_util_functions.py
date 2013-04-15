# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
from unittest import TestCase
import dateutils
from education.utils import get_week_count


class TestUtilFunctions(TestCase):
    def test_should_return_week_count_between_two_dates(self):
        today = datetime.today()
        four_weeks_before = dateutils.increment(today,weeks=-4)
        self.assertEqual(4,get_week_count(four_weeks_before,today))

    def test_should_return_week_count_between_two_dates_passed_in_any_order(self):
        today = datetime.today()
        four_weeks_before = dateutils.increment(today,weeks=-4)
        self.assertEqual(4,get_week_count(today,four_weeks_before))