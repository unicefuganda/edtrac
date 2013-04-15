# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from datetime import datetime
from unittest import TestCase
import dateutils
from django.conf import settings
from education.curriculum_progress_helper import get_target_value


class TestCurriculumProgressHelper(TestCase):
    def setUp(self):
        self.today = datetime.today()
        settings.FIRST_TERM_BEGINS = dateutils.increment(self.today,weeks=-16)
        settings.SECOND_TERM_BEGINS = dateutils.increment(self.today,weeks=-4)


    def test_should_return_target_value_for_given_date_in_first_term(self):
        settings.SCHOOL_TERM_START = dateutils.increment(self.today,weeks=-16)
        target_value = get_target_value(dateutils.increment(self.today,weeks=-12))
        self.assertEqual(2.1,target_value[0])

    def test_should_return_target_value_for_given_date_in_second_term(self):
        settings.SCHOOL_TERM_START = dateutils.increment(self.today,weeks=-4)
        target_value = get_target_value(self.today)
        self.assertEqual(6.1,target_value[0])

