from django.db import models
from django.contrib.auth.models import User
import re

class XForm(models.Model):
    slug = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=255)

    owner = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    def __unicode__(self): # pragma: no cover
        return self.name

TYPE_CHOICES = (
    ('INT', 'Integer'),
    ('DEC', 'Decimal'),
    ('STR', 'String'),
    ('GPS', 'GPS Coordinates')
)

class XFormField(models.Model):
    xform = models.ForeignKey(XForm, related_name='fields')

    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    name = models.CharField(max_length=16)
    description = models.CharField(max_length=32)
    order = models.IntegerField(default=0)

    def check_value(self, value):
        # TODO: We should be checking that the value is of the appropriate type if present

        for constraint in self.constraints.order_by('order'):
            error = constraint.check_value(value)
            if error:
                return error
        
        return None

    def __unicode__(self): # pragma: no cover
        return self.name

CONSTRAINT_CHOICES = (
    ('min_val', 'Minimum Value'),
    ('max_val', 'Maximum Value'),
    ('min_len', 'Minimum Length'),
    ('max_len', 'Maximum Length'),
    ('req_val', 'Required'),
    ('regex', 'Regular Expression')
)

class XFormFieldConstraint(models.Model):
    field = models.ForeignKey(XFormField, related_name='constraints')
    
    type = models.CharField(max_length=10, choices=CONSTRAINT_CHOICES)
    test = models.CharField(max_length=255, null=True)
    message = models.CharField(max_length=100)
    order = models.IntegerField(default=1000)

    def check_value(self, value):
        if self.type == 'req_val':
            if not value:
                return self.message

        # if our value is None, none of these other constraints apply
        if value is None:
            return None

        # otherwise, check the appropriate constraint
        if self.type == 'min_val':
            if float(value) < float(self.test):
                return self.message

        elif self.type == 'max_val':
            if float(value) > float(self.test):
                return self.message

        elif self.type == 'min_len':
            if len(value) < int(self.test):
                return self.message

        elif self.type == 'max_len':
            if len(value) > int(self.test):
                return self.message

        elif self.type == 'regex':
            if not re.match(self.test, value, re.IGNORECASE):
                return self.message

        return None

    def __unicode__(self): # pragma: no cover
        return "%s (%s)" % (self.type, self.value)


