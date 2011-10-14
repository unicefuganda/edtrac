from django.db import models
class PollData(models.Model):
    district = models.CharField(max_length=50, blank=True,null=True)
    yes=models.IntegerField(max_length=9, blank=True,null=True,default=0)
    no=models.IntegerField(max_length=9, blank=True,null=True,default=0)
    uncategorized=models.IntegerField(max_length=9, blank=True,null=True,default=0)
    poll=models.IntegerField(max_length=5, blank=True,null=True)
    unknown=models.IntegerField(max_length=5, blank=True,null=True,default=0)
    dominant_category=models.CharField(max_length=10, blank=True)


    
