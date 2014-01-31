# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import date, time, datetime, timedelta
from unittest import TestCase
import dateutils
from education.reports import is_holiday
from script.models import Script
from education.utils import get_week_count, get_months, _next_thursday
from education.models.utils import should_reschedule
from unregister.models import Blacklist
from rapidsms.models import Connection, Backend

class TestUtilFunctions(TestCase):

    def test_should_return_week_count_between_two_dates(self):
        now  = datetime(2012,1,1)
        four_weeks_before = dateutils.increment(now , weeks=-4)
        self.assertEqual(5, get_week_count(four_weeks_before, now ))

    def test_should_give_proper_month_data_starting_from_today(self):
        start_date = datetime(2012, 1, 1)
        end_date = dateutils.increment(start_date, weeks=10)

        months = get_months(start_date, end_date)
        self.assertEqual(months[0][0].date(), start_date.date())
        self.assertEqual(months[-1][1].date(), end_date.date())

    def test_should_return_true_if_given_date_is_holiday(self):
        holiday_date = datetime(2012, 1, 1)
        self.assertTrue(is_holiday(holiday_date, [(holiday_date, '1d')]))

    def test_should_return_true_if_given_date_is_in_holidays(self):
        holidays = [(datetime(2012, 1, 1), datetime(2012, 1, 3))]
        self.assertTrue(is_holiday(datetime(2012,1,2), holidays))

    def test_should_return_true_if_given_date_is_not_in_holidays(self):
        holidays = [(datetime(2012, 1, 1), datetime(2012, 1, 3))]
        self.assertFalse(is_holiday(datetime(2012,1,4), holidays))

    def test_should_return_false_if_given_date_is_not_holiday(self):
        holiday_date = datetime(2012, 1, 1)
        not_holiday_date = datetime(2012, 2, 1)
        self.assertFalse(is_holiday(not_holiday_date, [(holiday_date, '1d')]))

    def test_should_determine_next_thursday(self):
        monday = date(2013, 8, 19)
        thursday = monday + timedelta(3)
        self.assertEqual(thursday, _next_thursday(get_time = lambda : monday).date())

    def test_next_thursday_is_next_week_on_thursday(self):
        thursday = date(2013, 9, 15)
        next_thursday = date(2013, 9, 19)
        self.assertEqual(next_thursday, _next_thursday(get_time = lambda : thursday).date())

    def test_time_of_next_thursday_is_ten_in_the_morning(self):
        monday_night = datetime(2013, 8, 26, 23, 0, 0)
        ten_am = time(10, 0, 0)
        self.assertEqual(ten_am, _next_thursday(get_time = lambda : monday_night).time())

    def test_next_thursday_skips_holidays(self):
        thursday_holiday = (datetime(2013, 8, 29), '1d')
        thursday_after_holiday = date(2013, 9, 5)
        monday = date(2013, 8, 26)
        self.assertEqual(thursday_after_holiday, _next_thursday(get_time = lambda : monday, holidays = [thursday_holiday]).date())

    def test_week_count(self):
        start = datetime(2013, 2, 2)
        now = datetime(2013, 4, 4)
        self.assertEqual(9, get_week_count(start, now))

    def test_week_count_starts_from_one(self):
        start = datetime(2013, 2, 2)
        self.assertEqual(1, get_week_count(start, start))

    def test_doesnt_reschedule_autoreg(self):
        connection = None
        script = Script.objects.create(slug='edtrac_autoreg')
        self.assertFalse(should_reschedule(connection, script))

    def test_doesnt_reschedule_blacklisted(self):
        backend = Backend.objects.create(name='bar')
        connection = Connection.objects.create(backend=backend)
        script = Script.objects.create(slug='edtrac_water_points')
        Blacklist.objects.create(connection=connection)
        self.assertFalse(should_reschedule(connection, script))

    def test_schedules_other_polls(self):
        connection = None
        script = Script.objects.create(slug='edtrac_monthly_violence')
        self.assertTrue(should_reschedule(connection, script))
