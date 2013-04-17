# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.management import BaseCommand
from poll.models import Poll
from script.models import ScriptStep, Script


class Command(BaseCommand):
    help = "Create new water polls"

    def handle(self, **options):
        """
            Command to create new water polls
        """
        try:
            edtrac_water_source = Poll.objects.create(
                name="edtrac_water_source",
                type="t",
                question="Does this school have a water source within 500 metres from the school? Answer yes or no",
                default_response='',
                user=User.objects.get(username='admin'),
                )
            edtrac_water_source.sites.add(Site.objects.get_current())
            edtrac_water_source.add_yesno_categories()
            edtrac_water_source.save()
            print "Created Poll: %s with question %s" % (edtrac_water_source.name, edtrac_water_source.question)

            edtrac_functional_water_source = Poll.objects.create(
                name="edtrac_functional_water_source",
                type="t",
                question="Is the water source functional (working)? Answer Yes or No",
                default_response='',
                user = User.objects.get(username='admin'),
                )
            edtrac_functional_water_source.sites.add(Site.objects.get_current())
            edtrac_functional_water_source.add_yesno_categories()
            edtrac_functional_water_source.save()
            print "Created Poll: %s with question %s" % (edtrac_functional_water_source.name, edtrac_functional_water_source.question)

            script_water_source = Script.objects.create(
                slug="edtrac_script_water_source",
                name="Water Source Script",
                )
            script_water_source.sites.add(Site.objects.get_current())

            script_water_source.steps.add(ScriptStep.objects.create(
                script=script_water_source,
                poll=edtrac_water_source,
                order=0,
                rule = ScriptStep.WAIT_MOVEON,
                start_offset=0,
                giveup_offset=10800, # we'll give them two hours to respond
            ))
            print "Created Script: %s" % script_water_source.slug

            script_functional_water_source = Script.objects.create(
                slug="edtrac_script_functional_water_source",
                name="Functional Water Source Script",
                )
            script_functional_water_source.sites.add(Site.objects.get_current())
            script_functional_water_source.steps.add(ScriptStep.objects.create(
                script=script_functional_water_source,
                poll=edtrac_functional_water_source,
                order=0,
                rule=ScriptStep.WAIT_MOVEON,
                start_offset=0,
                giveup_offset=10800, # we'll give them two hours to respond
            ))
            print "Created Script: %s" % script_functional_water_source.slug
        except Exception as e:
            print "Job failed because: %s" % e.message
