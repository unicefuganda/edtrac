from django.db import models


class Indicator(models.Model):
    name = models.CharField(max_length=34, blank=False)
    frequency = models.CharField(max_length=16, blank=False)
    description = models.CharField(max_length=1024)

    class Meta:
        app_label = 'education'
