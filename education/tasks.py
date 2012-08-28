from celery.task import Task, PeriodicTask
from celery.registry import tasks
from .models import EnrolledDeployedQuestionsAnswered, create_record_enrolled_deployed_questions_answered
from poll.models import Poll
from datetime import timedelta

class CreateSystemReport(Task):
    def run(self, **kwargs):
        if kwargs.has_key('role'):
            role = kwargs.get('role')
            if role in ['DFO', 'DEO']:
                pass
            else:
                pass
tasks.register(CreateSystemReport)

class CreateRecordEnrolledDeployedQuestionsAnswered(Task):
    def run(self, **kwargs):
        create_record_enrolled_deployed_questions_answered(model = EnrolledDeployedQuestionsAnswered)

tasks.register(CreateRecordEnrolledDeployedQuestionsAnswered)

class ProcessRecordCreation(PeriodicTask):
    run_every = timedelta(minutes = 5)
    def run(self, **kwargs):
        CreateRecordEnrolledDeployedQuestionsAnswered.delay()
        logger = self.get_logger(**kwargs)
        logger.info("Running  CreateRecordEnrolledDeployedQuestionsAnswered")
        return
tasks.register(ProcessRecordCreation)