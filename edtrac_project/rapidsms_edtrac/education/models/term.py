from django.db import models
from datetime import date


class Term(models.Model):
    TERMS = (
        (1, "Term 1"),
        (2, "Term 2"),
        (3, "Term 3"),
    )
    year = models.IntegerField(default=date.today().year)
    term = models.IntegerField(default=1, choices=TERMS)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        app_label = 'education'
