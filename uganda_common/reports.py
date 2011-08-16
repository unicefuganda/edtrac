from generic.reports import Column, Report
from .utils import total_submissions, reorganize_location, total_attribute_value
from rapidsms.contrib.locations.models import Location


class XFormSubmissionColumn(Column):
    def __init__(self, keyword, extra_filters=None):
        self.keyword = keyword
        self.extra_filters = extra_filters

    def add_to_report(self, report, key, dictionary):
        val = total_submissions(self.keyword, report.start_date, report.end_date, report.location, self.extra_filters)
        reorganize_location(key, val, dictionary)


class XFormAttributeColumn(Column):
    def __init__(self, keyword, extra_filters=None):
        self.keyword = keyword
        self.extra_filters = extra_filters

    def add_to_report(self, report, key, dictionary):
        val = total_attribute_value(self.keyword, report.start_date, report.end_date, report.location, self.extra_filters)
        reorganize_location(key, val, dictionary)


class PollNumericResultsColumn(Column):

    AVERAGE = 1
    MAX = 2
    MIN = 4
    COUNT = 8
    STDDEV = 16
    SUM = 32

    VALUE_FLAGS = [(AVERAGE, 'avg'),
                   (MAX, 'max'),
                   (MIN, 'min'),
                   (COUNT, 'count'),
                   (STDDEV, 'stddev'),
                   (SUM, 'sum')]

    def __init__(self, poll_name, attrs=SUM):
        self.poll = Poll.objects.get(name=poll_name)
        self.attrs = attrs

    def add_to_report(self, report, key, dictionary):
        var = poll.get_numeric_report_data(location=report.location)
        for dict in var:
            loc_id = dict['location_id']
            dictionary.setdefault(loc_id, {'location_name':dict['location_name'], 'diff':(dict['rght'] - dict['lft'])})
            report.columns = report.columns[0:len(report._columns) - 1]
            for flag, attrkey in VALUE_FLAGS:
                if self.attrs & flag:
                    dictionary[loc_name]["%s_%s" % (key, attrkey)] = dict["value_float__%s" % attrkey]
                    report.columns.append("%s_%s" % (key, attrkey))


class PollCategoryResultsColumn(Column):

    def __init__(self, poll, category):
        self.poll = Poll.obects.get(name=poll_name)
        self.category = Category.objects.get(poll=self.poll, name=category)

    def add_to_report(self, report, key, dictionary):
        var = poll.responses_by_category(location=report.location)
        if len(var):
            location_id = var[0]['location_id']
            total = 0
            category_dict = {}
            for dict in var:
                if dict['location_id'] == location_id:
                    dictionary.setdefault(location_id, {'location_name':dict['location_name'], 'diff':(dict['rght'] - dict['lft'])})
                    category_dict[dict['category__name']] = dict['value']
                    total = total + dict['value']
                else:
                    dictionary[location_id][key] = (category_dict[self.category] if self.category.name in category_dict else 0) / total
                    location_id = dict['location_id']
                    dictionary.setdefault(location_id, {'location_name':dict['location_name'], 'diff':(dict['rght'] - dict['lft'])})
                    category_dict = {}
                    category_dict[dict['category__name']] = dict['value']
                    total = dict['value']
            dictionary[location_id][key] = (category_dict[self.category] if self.category.name in category_dict else 0) / total


class LocationReport(Report):
    def __init__(self, request, dates):
        try:
            self.location = Location.objects.get(pk=int(request.POST['drill_key']))
        except:
            self.location = Location.tree.root_nodes()[0]
        print "LOCATION IS %s" % self.location
        Report.__init__(self, request, dates)
