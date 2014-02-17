# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from unittest import TestCase
from django.test.client import Client


class TestNationalStats(TestCase):

    def setUp(self):
        self.client = Client()

    def test_should_throw_error_if_not_logged_in(self):
        response = self.client.get('/edtrac/national-stats/')
        self.assertEqual(302,response.status_code)

    def tearDown(self):
        pass