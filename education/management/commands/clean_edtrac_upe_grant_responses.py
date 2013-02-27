from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from poll.models import Poll


class Command(BaseCommand):
    def handle(self, **options):
        edtrac_upe_grant_poll = Poll.objects.get(name='edtrac_upe_grant')
        head_teachers_group = Group.objects.get(name='Head Teachers')

        other_groups_responses = edtrac_upe_grant_poll.responses.exclude(contact__groups=head_teachers_group)
        print "Found %s responses from reporters belonging to group other than Head Teachers..." % (
            other_groups_responses.count(), )
        print 'Deleting responses from reporters belonging to group other than Head Teachers...'
        other_groups_responses.delete()

        responses_whose_school_is_none = edtrac_upe_grant_poll.responses.filter(contact__emisreporter__schools=None)
        print 'Found %s responses from reporters whose school is None...' % (responses_whose_school_is_none.count(), )
        print 'Deleting responses from reporters whose school is None...'
        responses_whose_school_is_none.delete()
