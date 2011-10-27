from django.forms import ValidationError
from script.utils.handling import find_best_response, find_closest_match
from rapidsms.contrib.locations.models import Location
import re
from poll.models import Poll, LocationResponseForm, STARTSWITH_PATTERN_TEMPLATE
from eav.models import Attribute

def parse_district_value(value):
    location_template = STARTSWITH_PATTERN_TEMPLATE % '[a-zA-Z]*'
    regex = re.compile(location_template)
    toret = find_closest_match(value, Location.objects.filter(type__name='district'))
    if not toret:
        raise ValidationError("We didn't recognize your district.  Please carefully type the name of your district and re-send.")
    else:
        return toret

Poll.register_poll_type('district', 'District Response', parse_district_value, db_type=Attribute.TYPE_OBJECT, \
                        view_template='polls/response_location_view.html',
                        edit_template='polls/response_location_edit.html',
                        report_columns=(('Text', 'text'), ('Location', 'location'), ('Categories', 'categories')),
                        edit_form=LocationResponseForm)
