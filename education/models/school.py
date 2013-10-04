from django.db import models
from rapidsms.contrib.locations.nested.models import Location


class School(models.Model):
    name = models.CharField(max_length=160)
    emis_id = models.CharField(max_length=10)
    location = models.ForeignKey(Location, related_name='schools')

    class Meta:
        app_label = 'education'

    def __unicode__(self):
        return '%s - %s' % (self.name, self.location.name)

    def no_of_reporters(self):
        return len(self.reporters_set.values_list())
