from django.db import models
from rapidsms.models import Contact

from .school import School


class EmisReporter(Contact):
    CLASS_CHOICES = (
        ('P3', 'P3'),
        ('P6', 'P6'))

    grade = models.CharField(max_length=2, choices=CLASS_CHOICES, null=True)
    schools = models.ManyToManyField(School, null=True)
    has_exact_matched_school = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        app_label = 'education'

    def __unicode__(self):
        return self.name

    def is_member_of(self, group):
        grps = self.groups.objects.values_list('name', flat=True)
        return group.lower() in [grp.lower for grp in grps]

    def schools_list(self):
        return self.schools.values_list('name', flat=True)
