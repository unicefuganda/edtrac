from celery.task import task
from celery.task import Task
from celery.registry import tasks
#import twitter
#from twitter import TwitterError, Twitter

@task
def add(x,y):
    return x + y