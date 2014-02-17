from django.test import TestCase
from education.forms import SchoolForm
from rapidsms.contrib.locations.models import Location
from education.models import School
from education.test.utils import create_location_type, create_location

class TestAddSchoolForm(TestCase):

    def setUp(self):
        district = create_location_type("district")
        kampala_fields = {
            "rght": 10901,
            "level": 1,
            "tree_id": 1,
            "lft": 10686,
        }
        kampala_point = {
            "latitude": "0.3162800000",
            "longitude": "32.5821900000"
        }
        self.kampala_district = create_location("Kampala", district, point=kampala_point, **kampala_fields)

    def test_empty_form_should_not_be_bound(self):
        school_form = SchoolForm()
        self.assertFalse(school_form.is_bound)

    def test_empty_should_not_be_valid(self):
        school_form = SchoolForm()
        self.assertFalse(school_form.is_valid())

    def test_should_have_errors_on_missing_field_given_empty_form(self):
        pass

    def test_form_should_have_all_districts(self):
        school_form = SchoolForm()
        School.objects.create(name="St.Mary's Fairway", location=self.kampala_district)
        districts = Location.objects.filter(type='district')
        self.assertEquals(districts.count(), school_form.fields['location'].queryset.all().count())

    def test_valid_form_should_save_successfully(self):
        data = {
            "name": "St.Mary's Fairway Primary school",
            "location" : self.kampala_district.id
        }
        school = SchoolForm(data)
        school.save()
        self.assertTrue("St.Mary's Fairway Primary school" in School.objects.all().values_list('name', flat=True))

    def test_invalid_form_should_not_save_successfully(self):
        data = {
            "name" : 1,
            "location" : self.kampala_district
        }
        school = SchoolForm(data)
        self.assertRaises(TypeError, lambda : school.save())


