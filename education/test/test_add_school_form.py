from django.test import TestCase
from education.forms import SchoolForm
from rapidsms.contrib.locations.models import Location


class TestAddSchoolForm(TestCase):

    def test_empty_form_should_not_be_bound(self):
        school_form = SchoolForm()
        self.assertFalse(school_form.is_bound)

    def test_empty_should_not_be_valid(self):
        school_form = SchoolForm()
        self.assertFalse(school_form.is_valid())

    def test_have_errors_on_missing_field_given_empty_form(self):
        pass

    def test_form_should_have_all_districts(self):
        school_form = SchoolForm()
        districts = Location.objects.filter(type='district')
        self.assertEquals(districts.count(), school_form.fields['location'].queryset.all().count())

