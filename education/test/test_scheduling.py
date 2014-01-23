from unittest import TestCase
from education.scheduling import *
from datetime import date

class TestScheduling(TestCase):

    def test_finds_upcoming_date(self):
        today = date(2013, 12, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals(date(2014, 1, 2), upcoming(dates, get_day = lambda: today))

    def test_finds_when_no_upcoming_date(self):
        today = date(2014, 1, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals(None, upcoming(dates, get_day = lambda: today))

    def test_finds_current_period(self):
        today = date(2013, 12, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals((date(2013, 12, 26),date(2014, 1, 1)), current_period(dates, get_day = lambda: today))

    def test_finds_current_period_with_open_end(self):
        today = date(2014, 1, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals((date(2013, 12, 26),None), current_period(dates, get_day = lambda: today))

    def test_finds_current_period_with_open_start(self):
        today = date(2013, 11, 29)
        dates = [date(2013, 12, 26), date(2014, 1, 2), date(2014, 1, 9)]
        self.assertEquals((None,date(2013, 12, 25)), current_period(dates, get_day = lambda: today))
