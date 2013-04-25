# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
from unittest import TestCase
from dateutil.relativedelta import relativedelta
import dateutils
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
