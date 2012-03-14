#from django.test.client import Client
#from django.contrib.auth.models import User, Group
#from django.test import TestCase
#from django.core.urlresolvers import reverse
#
#class ViewTest(TestCase):
#    def setUp(self):
#        self.client = Client()
#        self.user = User.objects.create_user("admin", email="fake@email.com", password="myfakepassword")
#
#    def test_login(self):
#        self.client.login(username="admin", password="myfakepassword")
#        response = self.client.get(reverse('login'))
#        self.assertEqual(response.status_code, 200)