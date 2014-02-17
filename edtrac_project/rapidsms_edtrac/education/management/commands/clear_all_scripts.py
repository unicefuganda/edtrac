from django.core.management.base import BaseCommand
from script.models import ScriptProgress

class Command(BaseCommand):

    def handle(self, **options):
        ScriptProgress.objects.all().delete()
        print("Done")
