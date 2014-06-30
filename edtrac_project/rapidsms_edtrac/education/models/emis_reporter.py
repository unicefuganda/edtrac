from django.db import models
from rapidsms.models import Contact
from unregister.models import Blacklist

import logging
logger = logging.getLogger(__name__)

from .school import School


class EmisReporterManager(models.Manager):
    def get_query_set(self):
        return super(EmisReporterManager, self).get_query_set().exclude(
            connection__in=Blacklist.objects.values_list('connection', flat=True))


class EmisReporter(Contact):
    CLASS_CHOICES = (
        ('P3', 'P3'),
        ('P6', 'P6'))

    grade = models.CharField(max_length=2, choices=CLASS_CHOICES, null=True)
    schools = models.ManyToManyField(School, null=True)
    has_exact_matched_school = models.BooleanField(default=True)
    objects = EmisReporterManager()
    last_reporting_date = models.DateTimeField(null=True)

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

def update_last_reporting_date(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if created:
        if instance.direction == 'I':
            logger.info('Updating last reporting date for reporter - New Message')
            reporter = instance.connection.contact.emisreporter
            reporter.last_reporting_date = instance.date
            reporter.save()
    else:
        logger.info("This is not a new message - Don't update last reporting date")