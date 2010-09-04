from django.test import TestCase
from django.contrib.auth.models import User
from rapidsms.models import Contact

class TestAuthenticatedContact(TestCase):
    def test_get_profile(self):
        """
        Test that the get_profile() method works properly and links to
        Contact
        """
        web_user = User.objects.create_user('test', 'test@test.com', 'passw0rd')
        contact = Contact.objects.create(name='Testy McTesterton', user=web_user)
        self.failUnlessEqual(web_user.get_profile(), contact)
