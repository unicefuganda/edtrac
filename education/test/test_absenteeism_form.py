# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from education.views import AbsenteeismForm
from datetime import datetime

class TestAbsenteeismForm(TestCase):
    def test_should_invalidate_empty_form(self):
        absenteeism_from = AbsenteeismForm(data={})
        self.assertFalse(absenteeism_from.is_valid())

    def test_should_validate_if_to_date_is_greater_than_from_date(self):
        absenteeism_from = AbsenteeismForm(data={'to_date':'12/12/2013', 'from_date':'12/14/2013'})
        self.assertFalse(absenteeism_from.is_valid())

    def test_should_get_cleaned_data_after_validation(self):
        absenteeism_from = AbsenteeismForm(data={'to_date':'12/21/2013', 'from_date':'12/14/2013', 'indicator':'all'})
        self.assertTrue(absenteeism_from.is_valid())
        self.assertEqual(datetime(2013,12,21), absenteeism_from.cleaned_data['to_date'])
        self.assertEqual(datetime(2013,12,14), absenteeism_from.cleaned_data['from_date'])
        self.assertEqual('all', absenteeism_from.cleaned_data['indicator'])
