from celery.task import Task, PeriodicTask, task
from celery.registry import tasks
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from poll.models import Poll
from education.utils import _format_responses
from .models import EnrolledDeployedQuestionsAnswered, create_record_enrolled_deployed_questions_answered
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
        create_record_enrolled_deployed_questions_answered(model=EnrolledDeployedQuestionsAnswered)


tasks.register(CreateRecordEnrolledDeployedQuestionsAnswered)


class ProcessRecordCreation(PeriodicTask):
    run_every = timedelta(minutes=5)

    def run(self, **kwargs):
        CreateRecordEnrolledDeployedQuestionsAnswered.delay()
        logger = self.get_logger(**kwargs)
        logger.info("Running  CreateRecordEnrolledDeployedQuestionsAnswered")
        return
tasks.register(ProcessRecordCreation)


@task
def export_responses(form, user):
    poll = Poll.objects.get(pk=form.cleaned_data['poll_name'])
    responses = poll.responses.all().order_by('-pk')
    to_date = form.cleaned_data['to_date']
    from_date = form.cleaned_data['from_date']
    if from_date and to_date:
        to_date = to_date + timedelta(days=1)
        responses = responses.filter(date__range=[from_date, to_date])

    resp = render_to_string(
        'education/admin/export_poll_responses.csv', {
            'responses': _format_responses(responses)
        }
    )
    root_dir = getattr(settings, 'ROOT_SPREADSHEETS_DIR',
                       '/var/www/prod_edtrac/edtrac/edtrac_project/rapidsms_edtrac/education/static/spreadsheets/')
    with open('%s%s.csv' % (root_dir, poll.name), 'w') as spreadsheet:
        spreadsheet.write(resp)
    message = 'Spreadsheet has finished exporting. Please download it here http://edutrac.unicefuganda.org/static/' \
              'education/spreadsheets/%s.csv' % poll.name
    send_mail('Spreadsheet Exported', message, "", [user.email], fail_silently=False)