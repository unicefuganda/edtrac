import datetime
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.management import BaseCommand
from django.db import IntegrityError
from education.models import Role, UserProfile
from rapidsms.contrib.locations.models import Location, LocationType
from poll.models import Poll, Category


class Command(BaseCommand):

    def handle(self, *args, **options):
        Role.objects.get_or_create(name='Admins')
        admin = User.objects.get_or_create(username='admin')[0]
        admin.set_password('admin')
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        UserProfile.objects.get_or_create(
            name='Admins',
            location=Location.objects.get(
                name='Kampala',
                type=LocationType.objects.get(slug='district')),
            role=Role.objects.get(name='Admins'),
            user=User.objects.get(username='admin'))
        try:
            Site.objects.get_or_create(
                id=2,
                domain="edtrac.unicefuganda.org",
                name="edtrac")
        except IntegrityError:
            pass

        poll_names = [
            'edtrac_violence_boys',
            'edtrac_violence_girls',
            'edtrac_violence_reported',
            'edtrac_upe_grant',
            'edtrac_smc_meetings',
            'edtrac_smc_meals',
            'edtrac_head_teachers_attendance',
            'edtrac_f_teachers_deployment',
            'edtrac_m_teachers_deployment',
            'edtrac_f_teachers_attendance',
            'edtrac_m_teachers_attendance',
            'edtrac_boysp3_attendance',
            'edtrac_boysp6_attendance',
            'edtrac_girlsp3_attendance',
            'edtrac_girlsp6_attendance',
            'edtrac_boysp3_enrollment',
            'edtrac_boysp6_enrollment',
            'edtrac_girlsp3_enrollment',
            'edtrac_girlsp6_enrollment',
            'edtrac_headteachers_meals',
            'edtrac_gem_abuse',
            'edtrac_girls_violence',
            'edtrac_p3curriculum_progress',
        ]

        Poll.objects.all().delete()
        for poll_name in poll_names:
            Poll.objects.get_or_create(
                name=poll_name,
                start_date=datetime.datetime.now(),
                type='n',
                default_response='',
                user=User.objects.get(username='admin'))
            Category.objects.get_or_create(
                name='yes',
                poll=Poll.objects.get(name=poll_name))
