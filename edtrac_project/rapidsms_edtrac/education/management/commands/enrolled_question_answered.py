from django.core.management.base import BaseCommand
from education.models import EnrolledDeployedQuestionsAnswered, create_record_enrolled_deployed_questions_answered

class Command(BaseCommand):

    def handle(self, *args, **options):
        # currently this manage command works on just that one model
        # TODO >>> in case you want to make code that will use similar logic
        create_record_enrolled_deployed_questions_answered(model = EnrolledDeployedQuestionsAnswered)