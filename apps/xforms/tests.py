"""
Basic tests for XForms
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.test.client import Client
from .models import XForm, XFormField

class SimpleTest(TestCase): # pragma: no cover
    urls = 'xforms.urls'

    def setUp(self):
        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
        self.user.save()
        self.client = Client()
        self.client.login(username='fred', password='secret')

    def testAuthenticated(self):
        self.client.logout()
        response = self.client.get("/xforms/")
        self.failUnlessEqual(response.status_code, 302)

    def testList(self):
        x1 = XForm.objects.create(name="form1", slug="form1", description="nothing", owner=self.user)
        response = self.client.get("/xforms/")
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(len(response.context['xforms']), 1)

    def testNew(self):
        response = self.client.post("/xforms/new/",
                                    { 'name': 'form2',
                                      'slug': 'slug2',
                                      'description': 'desc2' }, follow=True)

        self.failUnlessEqual(response.status_code, 200)

        # make sure we have the newly created xform
        xform = response.context['xform']

        self.failUnlessEqual(xform.pk, 1)
        self.failUnlessEqual(xform.name, 'form2')
        self.failUnlessEqual(xform.slug, 'slug2')
        self.failUnlessEqual(xform.description, 'desc2')
        self.failUnlessEqual(xform.owner, self.user)


        # check that dupe doesn't work
        response = self.client.post("/xforms/new/",
                                    { 'name': 'form2',
                                      'slug': 'form2',
                                      'description': 'desc2' }, follow=True)
        self.failUnlessEqual(response.status_code, 200)

        # we shouldnt have an xform created
        self.failIf('xform' in response.context)




