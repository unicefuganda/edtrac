from django.db import models
from poll.models import Poll

class PollGeoData(models.Model):
    district = models.CharField(max_length=100, blank=True, null=True)
    poll_id = models.IntegerField()
    deployment_id = models.IntegerField(max_length=3)

    class Meta:
        abstract = True
        unique_together = (('deployment_id', 'poll_id', 'district'),)


class PollData(PollGeoData):
    yes = models.FloatField(blank=True, null=True, default=0)
    no = models.FloatField(blank=True, null=True, default=0)
    uncategorized = models.FloatField(blank=True, null=True, default=0)
    unknown = models.FloatField(max_length=5, blank=True, null=True, default=0)


class PollCategoryData(PollGeoData):
    top_category = models.IntegerField(blank=True, null=True, default=0)
    description = models.TextField()


class PollResponseData(PollGeoData):
    percentage = models.FloatField(blank=True, null=True, default=0)

class BasicClassLayer(models.Model):
    district = models.CharField(max_length=100, blank=True, null=True)
    style_class = models.CharField(max_length=100, blank=True, null=True)
    deployment_id = models.IntegerField(max_length=3)
    layer_id = models.IntegerField(max_length=3)

    class Meta:
        unique_together = (('deployment_id', 'layer_id', 'district'),)
