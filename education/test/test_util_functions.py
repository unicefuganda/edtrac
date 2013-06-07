# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
from unittest import TestCase
import dateutils
from django.conf import settings
from education.reports import is_holiday
from education.utils import get_week_count, get_months


class TestUtilFunctions(TestCase):
    def test_should_return_week_count_between_two_dates(self):
        today = datetime.today()
        four_weeks_before = dateutils.increment(today,weeks=-4)
        self.assertEqual(5,get_week_count(four_weeks_before,today))

    def test_should_return_week_count_between_two_dates_passed_in_any_order(self):
        today = datetime.today()
        four_weeks_before = dateutils.increment(today,weeks=-4)
        self.assertEqual(5,get_week_count(today,four_weeks_before))

    def test_should_give_proper_month_data_starting_from_today(self):
        today_date=datetime.today()
        end_date = dateutils.increment(today_date,weeks=10)

        months = get_months(today_date,end_date)
        self.assertEqual(months[0][0].date(),today_date.date())
        self.assertEqual(months[-1][1].date(),end_date.date())

    def test_should_return_true_if_given_date_is_holiday(self):
        today = datetime.today()
        two_weeks_later = dateutils.increment(today,weeks=2)
        three_weeks_later = dateutils.increment(today, weeks=3)
        settings.SCHOOL_HOLIDAYS = [(today,two_weeks_later),(three_weeks_later,'1d')]
        self.assertTrue(is_holiday(three_weeks_later,getattr(settings,'SCHOOL_HOLIDAYS')))


    def test_should_return_false_if_given_date_is_not_holiday(self):
        today = datetime.today()
        two_weeks_later = dateutils.increment(today,weeks=2)
        three_weeks_later = dateutils.increment(today, weeks=3)
        four_weeks_later = dateutils.increment(today, weeks=4)
        settings.SCHOOL_HOLIDAYS = [(today,two_weeks_later),(three_weeks_later,'1d')]
        self.assertFalse(is_holiday(four_weeks_later,getattr(settings,'SCHOOL_HOLIDAYS')))