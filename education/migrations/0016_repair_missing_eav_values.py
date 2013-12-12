# -*- coding: utf-8 -*-
from south.v2 import DataMigration
from education.models import Response
import re
from django.conf import settings
from django.db.transaction import commit_on_success

@commit_on_success
class Migration(DataMigration):

    def forwards(self, orm):

        # Find responses that don't have a stored numeric value.
        numeric_responses = Response.objects.filter(has_errors=False, message__direction='I', poll__type='n')
        numeric_responses.query.join(('poll_response', 'eav_value', 'id', 'entity_id'), promote=True)
        missing = numeric_responses.extra(where = ["value_float IS NULL"])

        # Recalculate the numeric values where we can.
        regex = re.compile(r"(-?\d+(\.\d+)?)")
        for response in missing:
            parts = regex.split(response.message.text)
            if len(parts) == 4 :
                response.eav.poll_number_value = float(parts[1])
            else:
                response.has_errors = True

            # Make sure we don't insert implausible values.
            invalid = getattr(settings, "INVALID_RESPONSE", lambda response: False)
            response.has_errors = response.has_errors or invalid(response)

            response.save(force_update=True)
