from .utils import flatten_list, set_default_dates


class Column(object):
    def add_to_report(self, report, key, dictionary):
        pass


class Report(object):
    """
    A report was found to be a useful callable for more complicated aggregate reports, in which each
    column of the report is a complicated query, but can be performed for every row of the
    table at once.  Subclasses of this object can define tabular reports declaratively,
    by creating Column attributes.

    The main report class builds a dictionary of dictionaries.  Each key is a unique identifier, and
    the dictionary value has the remaining column attributes.  Each column is called in the order it was
    declared, adding its column value to each subdictionary in the main dictionary.  The final product
    is then flattened.

    For instance, suppose we were aggregating stats by Locations.  I might declare three columns:

    class MyCityReport(Report):
        population = PopulationColumn()
        crime = CrimeColumn()
        pollution = PollutionColumn()

    each Column knows how to add itself to the report structure following the same convention.
    So MyCityReport would start with an empty report dictionary, {}.
    After the call to PopulationColumn's add_to_report() method, the report dictionary might look
    like this:

    {'nairobi':{'pop':3000000},
     'kampala':{'pop':1420200},
     'kigali':{'pop':965398}}

    After Crime's add_to_report(), it would be:

    {'nairobi':{'pop':3000000, 'crime':'nairobbery'},
     'kampala':{'pop':1420200, 'crime':'lots of carjacking'},
     'kigali':{'pop':965398, 'crime':'ok lately'}}

    And so on.  After all columns have been given a shot at adding their data, the report finally flattens
    this list into something that can be used by the generic view in the standard way (i.e., as an iterable
    that can be sorted, paginated, and selected): 
    
    [{'key':'nairobi','pop':3000000, 'crime':'nairobbery'},
     {'key':'kampala','pop':1420200, 'crime':'lots of carjacking'},
     {'key':'kigali','pop':965398, 'crime':'ok lately'}]
     
     Reports also sort date filtering and drill-down by default, just be sure to set 
     `needs_date` to True when passing a Report object to the generic view, and also set
     the base_template to be `generic/timeslider_base.html' rather than the standard 
     `generic/base.html`
    """
    def __init__(self, request=None, dates=None):
        datedict = {}
        set_default_dates(dates, request, datedict)

        self.drill_key = request.POST['drill_key'] if 'drill_key' in request.POST else None
        self.start_date = datedict['start_date']
        self.end_date = datedict['end_date']
        self.report = {} #SortedDict()
        self.columns = []
        column_classes = Column.__subclasses__()
        for attrname in dir(self):
            val = getattr(self, attrname)
            if type(val) in column_classes:
                self.columns.append(attrname)
                val.add_to_report(self, attrname, self.report)

        self.report = flatten_list(self.report)
        print self.report

    def __iter__(self):
        return self.report.__iter__()

    def __len__(self):
        return len(self.report)
