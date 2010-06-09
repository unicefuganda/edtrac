from django.db import models
from django.contrib.auth.models import User

class XForm(models.Model):
    slug = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=255)

    owner = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return self.name

TYPE_CHOICES = (
    ('INT', 'Integer'),
    ('DEC', 'Decimal'),
    ('STR', 'String'),
	('GPS', 'GPS Coordinates')
)

class XFormField(models.Model):
    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    name = models.CharField(max_length=16)
    description = models.CharField(max_length=32)
    required = models.BooleanField(default=True)
    
    xform = models.ForeignKey(XForm)

    def __unicode__(self):
        return self.name
