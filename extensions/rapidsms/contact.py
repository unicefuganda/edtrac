from django.db import models

from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group

class AuthenticatedContact(models.Model):
    """
    This extension for Contacts allows developers to tie a Contact (and potentially
    a phone number) to an authenticated django User object.  In order for this to
    work correctly, it's important to add the following line to settings.py:
    
    AUTH_PROFILE_MODULE = 'rapidsms.Contact'
    
    When this is set up properly, django will automatically load the appropriate
    Contact object as the User's "profile" (accessible via get_profile()) 
    upon login.
    
    See http://docs.djangoproject.com/en/dev/topics/auth/ under the section 
    'Storing additional information about users' for more information.
    """
    user = models.ForeignKey(User, unique=True, blank=True, null=True, related_name="contact")
    user_permissions = models.ManyToManyField(Permission, blank=True)
    groups = models.ManyToManyField(Group, blank=True, null=True)
    
    class Meta:
        abstract = True
    

