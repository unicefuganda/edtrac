from django.db import models

from poll.models import Poll

from .school import School


class EnrolledDeployedQuestionsAnswered(models.Model):
    poll = models.ForeignKey(Poll)
    school = models.ForeignKey(School)
    sent_at = models.DateTimeField()

    class Meta:
        app_label = 'education'

    def __unicode__(self):
        return self.school.name
