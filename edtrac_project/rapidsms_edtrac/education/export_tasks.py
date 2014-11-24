from celery.task import Task
from datetime import timedelta
from celery.task import task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from poll.models import Poll

__author__ = 'kenneth'

def get_district_parent(reporting_location):
    parent_locations = reporting_location.get_ancestors()
    district_parent = [parent for parent in parent_locations if parent.type.name == 'district']
    return district_parent[0].name


@task
def export_responses(form, user):
    def _format_responses(responses):
        a = []
        for response in responses:
            if response.contact:
                contact = response.contact
                sender = contact
                location_type = contact.reporting_location.type
                reporting_location = contact.reporting_location.name
                if not location_type.name == 'district' and not location_type.name == 'country':
                    reporting_location = get_district_parent(contact.reporting_location)
                    location_type = 'district'
                school = ", ".join(contact.emisreporter.schools.values_list('name', flat=True))
            else:
                sender = response.message.connection.identity
                location_type = "--"
                reporting_location = "--"
                school = "--"
            date = response.message.date
            if response.poll.type == "t":
                value = response.eav.poll_text_value
            elif response.poll.type == "n":
                if hasattr(response.eav, 'poll_number_value'):
                    value = response.eav.poll_number_value
                else:
                    value = 0
            elif response.poll.type == 'l':
                value = response.eav.poll_location_value.name
            category = response.categories.values_list('category__name', flat=True)
            if len(category) == 0:
                category = "--"
            else:
                category = ", ".join(category)
            a.append((sender, location_type, reporting_location, school, date, value, category))
        return a
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