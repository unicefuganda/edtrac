import datetime, time
from generic.reporting.views import ChartView, ReportView
from django.shortcuts import get_object_or_404
from rapidsms.contrib.locations.models import Location
from uganda_common.utils import total_submissions as total_submissions_api, total_attribute_value as total_attribute_value_api
from uganda_common.reports import XFormDateGetter

class XFormReport(ReportView):
    date_getter = XFormDateGetter()

class XFormChartView(ChartView):
    location_id = None
    xform_keyword = None
    attribute_keyword = None
    extra_filters = None
    date_getter = XFormDateGetter()

    def as_url(self):
        return ''

    def reorganize_for_chart_api(self, timespan, report):
        to_ret = []
        if len(report):
            series = []
            cur_loc = report[0]['location_name']
            current_series_obj = {'name':str(cur_loc), 'data':series}
            to_ret.append(current_series_obj)
            for d in report:
                if d['location_name'] != cur_loc:
                    series = []
                    current_series_obj = {'name':str(d['location_name']), 'data':series}
                    to_ret.append(current_series_obj)
                    cur_loc = d['location_name']
                dt = d[timespan]
                if timespan == 'month':
                    dt = datetime.datetime(int(d['year']), int(dt), 1)
                elif timespan == 'week':
                    dt = datetime.datetime(int(d['year']), 1, 1) + datetime.timedelta(days=(int(dt) * 7))
                elif timespan == 'quarter':
                    dt = datetime.datetime(int(d['year']), int(dt) * 3, 1)
                ts = int(time.mktime(dt.timetuple()))
                series.append([ts, d['value']])

        return to_ret


    def get_data(self):
        location = get_object_or_404(Location, pk=self.location_id)
        group_by = self.get_group_by(self.start_date, self.end_date)

        if self.attribute_keyword:
            data = total_attribute_value_api(self.attribute_keyword, self.start_date, self.end_date, location, group_by_timespan=group_by['group_by'])
        else:
            data = total_submissions_api(self.xform_keyword, self.start_date, self.end_date, location, self.extra_filters, group_by_timespan=group_by['group_by'])

        chart_data = list(data)
        chart_data = self.reorganize_for_chart_api(group_by['group_by_name'], chart_data)

        json_response_data = {'series':list(chart_data), \
                              'timespan':group_by['group_by_name'], \
                              'title':self.get_chart_title(), \
                              'subtitle':self.get_chart_subtitle(), \
                              'yaxis':self.get_y_axis(), \
                              }
        return json_response_data

    def drill_on(self, key):
        try:
            self.location_id = key
        except Location.DoesNotExist:
            self.location_id = Location.tree.root_nodes()[0].pk


class ArithmeticChartView(XFormChartView):
    first_column = None
    second_column = None
    main_column = None
    date_getter = XFormDateGetter()
    second_must_exist = False
    first_must_exist = False
    missing_first_default_value = 0
    missing_second_default_value = 0

    def func(self, first, second):
        return self.main_column.func(first, second)

    def reorganize_for_chart_api(self, timespan, report):
        to_ret = []
        if len(report):
            series = []
            cur_loc = report[0]['location_name']
            current_series_obj = {'name':str(cur_loc), 'data':series}
            to_ret.append(current_series_obj)
            for d in report:
                if d['location_name'] != cur_loc:
                    series = []
                    current_series_obj = {'name':str(d['location_name']), 'data':series}
                    to_ret.append(current_series_obj)
                    cur_loc = d['location_name']
                dt = d[timespan]
                if timespan == 'month':
                    dt = datetime.datetime(int(d['year']), int(dt), 1)
                elif timespan == 'week':
                    dt = datetime.datetime(int(d['year']), 1, 1) + datetime.timedelta(days=(int(dt) * 7))
                elif timespan == 'quarter':
                    dt = datetime.datetime(int(d['year']), int(dt) * 3, 1)
                ts = int(time.mktime(dt.timetuple()))
                series.append([ts, d['value']])

        return to_ret


    def get_data(self):
        """
        This function is all about stitching two different columns of chart
        data together using an arithmetic function.  The chart data from the
        two subcharts will be in its view-returnable state, i.e., a list of 
        lists, the sublists each containing two elements: a timestamp and a value.
        
        In most cases, the absence of one data point in one of the two charts
        implies that its value should be zero when the arithmetic function to merge 
        the two.  However, the behavior is different when the first set of data is
        to be divided by the other: the first data point should be discarded if the 
        second is absent, as a default value of zero in the second would result in
        a Division by Zero error.  Hence the ability to branch on different parameters
        to determine the 'merge' behavior in this function (see the non-default parameters
        that QuotientColumn passes in. 
        """
        first_chart = self.first_column.get_chart().get_data()
        second_chart = self.second_column.get_chart().get_data()
        chart_data = []
        series_names = []
        for second_data_series in second_chart['series']:
            if not second_data_series['name'] in series_names:
                series_names.append(second_data_series['name'])

        for first_data_series in first_chart['series']:
            if not first_data_series['name'] in series_names:
                series_names.append(first_data_series['name'])

        for series_name in series_names:
            data_to_add = []
            series_to_add = {'name': series_name, 'data':data_to_add}

            right_data_series = {'data':[]}
            # find the corresponding series in the second data dictionary,
            # if it exists, otherwise we end up with an empty list
            for t in second_chart['series']:
                if t['name'] == series_name:
                    right_data_series = t
                    break
            right_data = right_data_series['data']

            left_data_series = {'data':[]}
            # find the corresponding series in the first data dictionary,
            # if it exists, otherwise we end up with an empty list
            for t in first_chart['series']:
                if t['name'] == series_name:
                    left_data_series = t
                    break
            left_data = left_data_series['data']

            right_counter = 0
            left_counter = 0

            # pair-wise iteration over left and right data, looking for
            # matching timestamps so we can divide the values out
            while left_counter < len(left_data) and right_counter < len(right_data):
                left_ts = left_data[left_counter][0]
                right_ts = right_data[right_counter][0]
                if left_ts == right_ts:
                    # perfect, timestamps match so we can apply the function
                    # cleanly to this pair add it to data_to_add

                    # first add the timestamp
                    datum = [left_data[left_counter][0]]
                    # calculate the value
                    value = self.func(left_data[left_counter][1], right_data[right_counter][1])

                    # append that shizzle
                    datum.append(value)
                    data_to_add.append(datum)

                    # both counters move forward
                    right_counter += 1
                    left_counter += 1
                elif left_ts < right_ts:
                    # we're missing a second value.  In the case of division arithmetic
                    # you MUST ensure that self.second_must_exist is True
                    # and that the missing_second_default value is 'skip', 
                    # as the appropriate behavior is to just omit this pairwise
                    # data point and move on
                    if self.second_must_exist:
                        if not self.missing_second_default_value == 'skip':
                            data_to_add.append([left_ts, self.missing_second_default_value])
                    else:
                        data_to_add.append([left_ts, self.func(left_data[left_counter][1], self.missing_second_default_value)])
                    # we're missing a right value for a corresponding left
                    # that'd be a divide by zero (in the case of QuotientColumns, 
                    # so we just skip it
                    left_counter += 1
                elif right_ts < left_ts:
                    # we're missing a first value for a corresponding right
                    if self.first_must_exist:
                        if not self.missing_first_default_value == 'skip':
                            data_to_add.append([right_ts, self.missing_first_default_value])
                    else:
                        data_to_add.append([right_ts, self.func(self.missing_first_default_value, right_data[right_counter][1])])

                    right_counter += 1


            # we've run out of first values
            while left_counter < len(left_data):
                left_ts = left_data[left_counter][0]
                if self.second_must_exist:
                    if not self.missing_second_default_value == 'skip':
                        data_to_add.append([left_ts, self.missing_second_default_value])
                else:
                    data_to_add.append([left_ts, self.func(left_data[left_counter][1], self.missing_second_default_value)])
                left_counter += 1

            # we've run out of second values            
            while right_counter < len(right_data):
                right_ts = right_data[right_counter][0]
                if self.first_must_exist:
                    if not self.missing_first_default_value == 'skip':
                        data_to_add.append([right_ts, self.missing_first_default_value])
                else:
                    data_to_add.append([right_ts, self.func(self.missing_first_default_value, right_data[right_counter][1])])
                right_counter += 1

            chart_data.append(series_to_add)

        group_by = self.get_group_by(self.start_date, self.end_date)

        json_response_data = {'series':list(chart_data), \
                              'timespan':group_by['group_by_name'], \
                              'title':self.get_chart_title(), \
                              'subtitle':self.get_chart_subtitle(), \
                              'yaxis':self.get_y_axis(), \
                              }
        return json_response_data


class PercentageChartView(ArithmeticChartView):

    def func(self, first, second):
        return round((float(first) / second) * 100, 1)


class DifferenceChartView(ArithmeticChartView):

    def func(self, first, second):
        return first - second


class SumChartView(ArithmeticChartView):

    def func(self, first, second):
        return first + second

