from django.db import models
from django.contrib.auth.models import User


class ReportComment(models.Model):
    user = models.ForeignKey(User)

    commentable_choices = (
        ('abs', 'Absenteeism'),
        ('viol', 'Violence'),
        ('cp', 'Curriculum Progress'),
        ('mm', 'Missed Meals'),
        ('smc', 'School Management Committee Meetings'),
        ('upge', 'UPE Capitation Grants')
    )

    comment = models.TextField(null=False)

    commentable = models.CharField(
        max_length=10,
        choices=commentable_choices,
        blank=False
    )

    reporting_period_choices = (
        ('wk', 'Weekly'),
        ('mo', 'Monthly'),
        ('t', 'Termly')
    )

    reporting_period = models.CharField(
        max_length=2,
        choices=reporting_period_choices,
        blank=False
    )

    """
    `report_date` is populated when user saves this comment; it will be
    based on the last reporting date. You should be able to sort comments
    by their ``commentable_choices`` and define that the date is based
    on weekly, monthly, or termly basis.
    """
    report_date = models.DateTimeField(blank=False)

    class Meta:
        app_label = 'education'

    def __unicode__(self):
        return self.comment

    def set_report_date(self, reporting_date):
        self.report_date = reporting_date
