# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from education.views import AbsenteeismForm
from datetime import datetime

class TestAbsenteeismForm(TestCase):
    def test_should_invalidate_empty_form(self):
        absenteeism_form = AbsenteeismForm(data={})
        self.assertFalse(absenteeism_form.is_valid())

    def test_should_validate_if_to_date_is_greater_than_from_date(self):
        absenteeism_form = AbsenteeismForm(data={'to_date':'12/12/2012', 'from_date':'12/14/2012'})
        self.assertFalse(absenteeism_form.is_valid())

    def test_should_invalidate_if_from_date_is_greater_than_to_date(self):
        absenteeism_form = AbsenteeismForm(data={'from_date':'12/12/2012', 'to_date':'12/14/2012'})
        self.assertTrue(absenteeism_form.is_valid())

    def test_should_get_cleaned_data_after_validation(self):
        absenteeism_form = AbsenteeismForm(data={'to_date':'12/21/2012', 'from_date':'12/14/2012', 'indicator':'all'})
        self.assertTrue(absenteeism_form.is_valid())
        self.assertEqual(datetime(2012,12,21), absenteeism_form.cleaned_data['to_date'])
        self.assertEqual(datetime(2012,12,14), absenteeism_form.cleaned_data['from_date'])
        self.assertEqual('all', absenteeism_form.cleaned_data['indicator'])
