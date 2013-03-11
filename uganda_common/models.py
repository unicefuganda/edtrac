import urlparse
from django.contrib.auth.models import User, Group
from django.forms import ValidationError
from django.db import models
from django.db.models.query import QuerySet
from script.utils.handling import find_best_response, find_closest_match
from rapidsms.contrib.locations.models import Location
from generic.sorters import SimpleSorter
import re
from poll.models import Poll, LocationResponseForm, STARTSWITH_PATTERN_TEMPLATE
from eav.models import Attribute
from .urls import urlpatterns


def parse_district_value(value):
    location_template = STARTSWITH_PATTERN_TEMPLATE % '[a-zA-Z]*'
    regex = re.compile(location_template)
    toret = find_closest_match(value, Location.objects.filter(type__name='district'))
    if not toret:
        raise ValidationError(
            "We didn't recognize your district.  Please carefully type the name of your district and re-send.")
    else:
        return toret


Poll.register_poll_type('district', 'District Response', parse_district_value, db_type=Attribute.TYPE_OBJECT, \
                        view_template='polls/response_location_view.html',
                        edit_template='polls/response_location_edit.html',
                        report_columns=((('Text', 'text', True, 'message__text', SimpleSorter()), (
                            'Location', 'location', True, 'eav_values__generic_value_id', SimpleSorter()), (
                                             'Categories', 'categories', True, 'categories__category__name',
                                             SimpleSorter()))),
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


class Access(models.Model):
    """"
    This models stores a bunch of users and the urls that they can access they can't access anything else that requires login
    Users that aren't in this models follow the normal django auth and permission stuff
    """
    user = models.ForeignKey(User, null=True)
    group = models.ForeignKey(Group, null=True)
    url_allowed = models.CharField(max_length=200,
                                   choices=[(p[0].regex.pattern, p[0].regex.pattern) for p in urlpatterns])

    def __unicode__(self):
        return "%s %s" % (self.user.username, self.url_allowed)

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.user and not self.group:
            raise ValidationError("Access Requires at least a user or a group of users")

    @classmethod
    def all_restricted_users(cls):
        all_groups = Access.objects.values_list('group', flat=True).distinct()
        all_users = Access.objects.values_list('user', flat=True).distinct()
        all_users = all_users | User.objects.filter(groups__in=all_groups)
        return all_users

    @classmethod
    def denied(cls, request):
        path = request.build_absolute_uri()
        path = urlparse.urlparse(path)[2]
        if path.startswith('/'): path = path[1:]
        user = request.user if request.user.is_authenticated() else None
        if not user in Access.all_restricted_users():
            return False
        paths = list(Access.objects.filter(user=user).values_list('url_allowed', flat=True).distinct())
        for p in paths:
            if re.match(r'' + p, path):
                return False
        return True