from django.db import models
from django.contrib.auth.models import User
from rapidsms.contrib.locations.nested.models import Location

from .role import Role


class UserProfile(models.Model):
    name = models.CharField(max_length=160)
    location = models.ForeignKey(Location)
    role = models.ForeignKey(Role)
    user = models.ForeignKey(User, related_name="profile")

    class Meta:
        app_label = 'education'

    def is_member_of(self, group):
        return group.lower() == self.role.name.lower()

    def __unicode__(self):
        return self.name
