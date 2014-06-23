from generic.sorters import Sorter
from rapidsms.models import Connection
from rapidsms_xforms.models import XFormSubmission, XFormSubmissionValue
from eav.models import Attribute
from education.models import EmisReporter


class LatestSubmissionSorter(Sorter):
    def sort(self, column, object_list, ascending=True):
        order = '-last_reporting_date' if ascending else 'last_reporting_date'
        submissions = EmisReporter.objects.exclude(last_reporting_date=None).order_by(order)
        return submissions


class SubmissionValueSorter(Sorter):
    def sort(self, column, object_list, ascending=True):
        if len(object_list):
            submissions = list(object_list)
            xform = submissions[0].xform
            a = Attribute.objects.get(slug=column)
            if a.datatype == Attribute.TYPE_TEXT:
                order_by = 'value_text'
            elif a.datatype == Attribute.TYPE_INT:
                order_by = 'value_int'
            elif a.datatype == Attribute.TYPE_DATE:
                order_by = 'value_date'
            elif a.datatype == Attribute.TYPE_BOOLEAN:
                order_by = 'value_bool'
            elif a.datatype == Attribute.TYPE_OBJECT:
                order_by = 'generic_value_id'
            if order_by:
                values = list(XFormSubmissionValue.objects.filter(attribute__slug=column).order_by(order_by))
                toret = []
                for v in values:
                    if not v.submission in toret:
                        toret.append(v.submission)
                for s in submissions:
                    if not s in toret:
                        toret.append(s)
                if not ascending:
                    toret.reverse()
                return toret
        return object_list