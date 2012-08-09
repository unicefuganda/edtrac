from celery.task import Task, PeriodicTask
from celery.registry import tasks
from .models import School, EnrolledDeployedQuestionsAnswered
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
        if EnrolledDeployedQuestionsAnswered.objects.exists():
            # this runs on existing EnrolledDeployedQuestionsAnswered records
            erqa = EnrolledDeployedQuestionsAnswered.objects.latest('sent_at')

            # query against the poll model
            poll = Poll.objects.select_related().filter(name__incontains__in=["enrolled", "deployed"])

            # get responses that came in after the time of latest `erqa` recorded created
            all_responses = poll.responses.filter(date__gte = erqa.sent_at).select_related().values_list(
                'poll__name', 'contact__emisreporter__schools__pk', 'date'
            )

            resp_dict = {}
            for poll_name, school_pk, sent_at in all_responses:
                if resp_dict.has_key(poll_name):
                    resp_dict.update([school_pk, sent_at])
                else:
                    resp_dict[poll_name] = [school_pk, sent_at]

            for poll_name in resp_dict.keys():
                try:
                    poll = Poll.objects.select_related().get(name = poll_name)
                    other_responses = resp_dict[poll_name]
                    for school_pk, sent_at in other_responses:
                        EnrolledDeployedQuestionsAnswered.objects.get_or_create(
                            poll = poll,
                            school = School.objects.select_related().get(pk = school_pk),
                            sent_at = sent_at)
                except DoesNotExist:
                    pass
            return
            #optimize this with a view
        else:
            print "This record doesn't exist"
tasks.register(CreateRecordEnrolledDeployedQuestionsAnswered)

class ProcessRecordCreation(PeriodicTask):
    run_every = timedelta(minutes = 5)
    def run(self, **kwargs):
        CreateRecordEnrolledDeployedQuestionsAnswered.delay()
        logger = self.get_logger(**kwargs)
        logger.info("Running  CreateRecordEnrolledDeployedQuestionsAnswered")
        return
tasks.register(ProcessRecordCreation)