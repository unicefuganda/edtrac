from django.db import models
from rapidsms.models import Connection

class Blacklist(models.Model):
    connection = models.ForeignKey(Connection)