
from django.core.management.base import BaseCommand
from script.models import Script

class Command(BaseCommand):

    def edtrac_special_script(self):
        if Script.objects.filter(name='Special Script', scriptprogress = None).exists(): # classical?
            # delete script only if there are no scriptprogresses that are still present
            Script.objects.filter(name = "Special Script", scriptprogress = None).delete()

    def handle(self, **options):
        self.edtrac_special_script()
