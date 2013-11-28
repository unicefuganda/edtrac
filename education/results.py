from education.models import *
from django.db.models import *

class NumericResponsesFor():
    def __init__(self, poll):
        self.query = Response.objects.filter(poll = poll,
                                             has_errors = False,
                                             message__direction = 'I')

    def forDateRange(self, range):
        self.query = self.query.filter(date__range = range)
        return self

    def forLocations(self, locations):
        self.query = self.query.filter(contact__reporting_location__in = locations)
        return self

    def forValues(self, values):
        self.query = self.query.filter(eav_values__value_float__in = values)
        return self

    def forSchools(self, schools):
        self.query = self.query.filter(contact__emisreporter__schools__in = schools)
        return self

    def excludeZeros(self):
        self.query = self.query.filter(eav_values__value_float__gt = 0)
        return self

    def excludeGreaterThan(self, number):
        self.query = self.query.filter(eav_values__value_float__lte = number)
        return self

    def groupByLocation(self):
        results = self.query.values('contact__reporting_location') \
                            .annotate(total = Sum('eav_values__value_float'))
        location_totals = [(result['contact__reporting_location'], result['total'] or 0) for result in results]
        return collapse(location_totals)

    def groupBySchools(self):
        results = self.query.values('contact__emisreporter__schools') \
                            .annotate(total = Sum('eav_values__value_float'))
        school_totals = [(result['contact__emisreporter__schools'], result['total'] or 0) for result in results]
        return collapse(school_totals)

    def total(self):
        result = self.query.aggregate(total=Sum('eav_values__value_float'))
        return result['total'] or 0

    def mean(self):
        result = self.query.aggregate(total=Avg('eav_values__value_float'))
        return result['total'] or 0

    def mode(self):
        results = self.query.values('eav_values__value_float') \
                            .annotate(frequency = Count('eav_values__value_float'))
        totals = [(result['eav_values__value_float'], result['frequency'] or 0) for result in results]

        if totals:
            stage,frequency = max(totals, key=lambda x: x[1])
            return stage
        else:
            return 0

def collapse(key_vals):
    result = {}
    for (key, value) in key_vals:
        result[key] = value
    return result
