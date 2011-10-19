from django.db import models
from poll.models import Poll

class PollData(models.Model):
    district = models.CharField(max_length=100, blank=True, null=True)
    yes = models.FloatField(blank=True, null=True, default=0)
    no = models.FloatField(blank=True, null=True, default=0)
    uncategorized = models.FloatField(blank=True, null=True, default=0)
    unknown = models.FloatField(max_length=5, blank=True, null=True, default=0)
    poll = models.ForeignKey(Poll, null=True)

