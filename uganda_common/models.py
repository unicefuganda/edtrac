from django.forms import ValidationError
from django.db import models
from django.db.models.query import QuerySet
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

class PolymorphicManager(models.Manager):
    def get_query_set(self):
        attrs = []
        cls = self.model.__class__
        if not hasattr(cls, '_meta'):
            return QuerySet(self.model, using=self._db)

        for r in cls._meta.get_all_related_objects():
            if not issubclass(r.model, cls) or \
                not isinstance(r.field, models.OneToOneField):
                continue
            attrs.append(r.get_accessor_name())
        return QuerySet(self.model, using=self._db).select_related(*attrs)

class PolymorphicMixin():

    def downcast(self):
        cls = self.__class__ #inst is an instance of the base model
        for r in cls._meta.get_all_related_objects():
            if not issubclass(r.model, cls) or \
                not isinstance(r.field, models.OneToOneField) or \
                r.model == cls:
                continue
            try:
                toret = getattr(self, r.get_accessor_name())
                # If the queryset has used 'select_related', the
                # above call won't throw an exception, but will
                # return None
                if toret:
                    # check if we can downcast further
                    recurse = toret.downcast()

                    # return the lowest possible downcast
                    return recurse or toret

            except models.ObjectDoesNotExist:
                continue

        # this is the lowest class, no further downcasting possible
        return self
