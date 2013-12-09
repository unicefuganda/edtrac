from django.db import models
from script.models import Script

class ScriptSchedule(models.Model):
    script = models.ForeignKey(Script)
    date = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'education'


class ScriptScheduleTime(models.Model):
    script = models.ForeignKey(Script)
    scheduled_on = models.DateField(auto_now=True)

    class Meta:
        app_label = 'education'
