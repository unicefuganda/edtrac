from dateutil.relativedelta import relativedelta
from script.models import Script, ScriptProgress
from rapidsms.models import Connection
import datetime
from rapidsms.models import Contact
from rapidsms.contrib.locations.models import Location
from poll.models import Poll
from script.models import ScriptStep
from django.db.models import Count
from django.conf import settings
from education.scheduling import schedule_at, at


def is_holiday(date1, holidays = getattr(settings, 'SCHOOL_HOLIDAYS', [])):
    for date_start, date_end in holidays:
        if isinstance(date_end, str):
            if date1.date() == date_start.date():
                return True
        elif date1.date() >= date_start.date() and date1.date() <= date_end.date():
            return True
    return False

def is_empty(arg):
    """
    Generalizes 'empty' checks on Strings, sequences, and dicts.

    Returns 'True' for None, empty strings, strings with just white-space,
    and sequences with len == 0
    """

    if arg is None:
        return True

    if isinstance(arg, basestring):
        arg = arg.strip()

    try:
        if not len(arg):
            return True
    except TypeError:
        # wasn't a sequence
        pass

    return False

def previous_calendar_week(t=None):
    """
    To education monitoring, a week runs between Thursdays,
    Thursday marks the beginning of a new week of data submission
    Data for a new week is accepted until Wednesday evening of the following week
    """
    d = t or datetime.datetime.now()
    if not d.weekday() == 3:
        # last Thursday == next Thursday minus 7 days.
        last_thursday = d + (datetime.timedelta((3-d.weekday())%7) - (datetime.timedelta(days=7)))
    else:
        last_thursday = d
    end_date = last_thursday + datetime.timedelta(days=6)
    return (last_thursday.date(), end_date)

def _this_thursday(sp=None, get_time=datetime.datetime.now, time_set=None, holidays=getattr(settings, 'SCHOOL_HOLIDAYS', [])):
    """
    This Thursday of the week which is not a school holiday.
    """
    schedule = time_set or get_time()
    d = sp.time if sp else schedule
    d = d + datetime.timedelta((3 - d.weekday()) % 7)

    while(is_holiday(d, holidays)):
        d = d + datetime.timedelta(1) # try next day

    return at(d.date(), 10)


def get_polls(**kwargs):
    script_polls = ScriptStep.objects.values_list('poll', flat=True).exclude(poll=None)
    return Poll.objects.exclude(pk__in=script_polls).annotate(Count('responses'))

def compute_average_percentage(list_of_percentages):
    """
    Average percentage
    -> this is also a handly tool to compute averages generally while sanitizing
    """
    sanitize = []
    try:
        for i in list_of_percentages:
            if isinstance(float(i), float):
                sanitize.append(float(i))
            else:
                pass
    except ValueError:
        print "non-numeric characters used"
        pass
    if len(sanitize) <= 0:
        return 0
    return sum(sanitize) / float(len(sanitize))


def list_poll_responses(poll, **kwargs):
    """
    pass a poll queryset and you get yourself a dict with locations vs responses (quite handy for the charts)
    dependecies: Contact and Location must be in your module; this lists all Poll responses by district
    """
    #forceful import
    from poll.models import Poll
    to_ret = {}

    """
    narrowed down to 3 districts (and up to 14 districts)
    """
    DISTRICT = ['Kaabong', 'Kabarole', 'Kyegegwa', 'Kotido']
    if not kwargs:
        # if no other arguments are provided
        for location in Location.objects.filter(name__in=DISTRICT):
            to_ret[location.__unicode__()] = compute_average_percentage([msg.message.text for msg in poll.responses.filter(contact__in=Contact.objects.filter(reporting_location=location))])
        return to_ret
    else:
        # filter by number of weeks
        #TODO more elegant solution to coincide with actual school term weeks
        date_filter = kwargs['weeks'] #give the date in weeks
        date_now = datetime.datetime.now()
        date_diff = date_now - datetime.timedelta(weeks=date_filter)
        all_emis_reports = EmisReporter.objects.filter(reporting_location__in=[loc for loc in Locations.objects.filter(name__in=DISTRICT)])
        for location in Location.objects.filter(name__in=DISTRICT):
            to_ret[location.__unicode__()] = compute_average_percentage([msg.message.text for msg in poll.responses.filter(date__gte=date_diff, contact__in=Contact.objects.filter(reporting_location=location))])
        return to_ret

themes = {
    1.1 : "Name and location of our Sub-county/Division",
    1.2 : 'Physical features of our Sub-County/Division',
    1.3 : 'People in our Sub-county/Division',
    2.1 : 'Occupations of people in our Sub-county/Division and their importance',
    2.2 : 'Social Services and their importance',
    2.3 : 'Challenges in social services and their possible solutions',
    3.1 : 'Soil',
    3.2 : 'Natural causes of changes in the environment',
    3.3 : 'Changes in the environment through human activities',
    4.1 : 'Air and the Sun',
    4.2 : 'Water',
    4.3 : 'Managing Water',
    5.1 : 'Living things',
    5.2 : 'Birds and Insects',
    5.3 : 'Care for insects, birds and animals',
    6.1 : 'Plants and their habitat',
    6.2 : 'Parts of a flowering plant and their uses',
    6.3 : 'Crop-growing practices',
    7.1 : 'Saving resources',
    7.2 : 'Spending resources',
    7.3 : 'Projects',
    8.1 : 'Living in peace with others',
    8.2 : 'Child rights, needs and their importance',
    8.3 : 'Child responsibility',
    9.1 : 'Customs in our sub-county/division',
    9.2 : 'Gender',
    9.3 : 'Ways of promoting and preserving culture',
    10.1: 'Disease vectors',
    10.2: 'Diseases spread by vectors',
    10.3: 'HIV/AIDS',
    11.1: 'Concept of technology',
    11.2: 'Processing and making things from natural materials',
    11.3: 'Making things from artificial materials',
    12.1: 'Sources of energy',
    12.2: 'Ways of saving energy',
    12.3: 'Dangers of energy and ways of avoiding them'
}





## {{{ http://code.activestate.com/recipes/409413/ (r2)
"""
Descriptive statistical analysis tool.
"""

class StatisticsException(Exception):
    """Statistics Exception class."""
    pass

class Statistics(object):
    """Class for descriptive statistical analysis.

    Behavior:
       Computes numerical statistics for a given data set.

    Available public methods:

       None

    Available instance attributes:

           N: total number of elements in the data set
         sum: sum of all values (n) in the data set
         min: smallest value of the data set
         max: largest value of the data set
        mode: value(s) that appear(s) most often in the data set
        mean: arithmetic average of the data set
       range: difference between the largest and smallest value in the data set
      median: value which is in the exact middle of the data set
    variance: measure of the spread of the data set about the mean
      stddev: standard deviation - measure of the dispersion of the data set
              based on variance

    identification: Instance ID

    Raised Exceptions:

       StatisticsException

    Bases Classes:

       object (builtin)

    Example Usage:

       x = [ -1, 0, 1 ]

       try:
          stats = Statistics(x)
       except StatisticsException, mesg:
          <handle exception>

       print "N: %s" % stats.N
       print "SUM: %s" % stats.sum
       print "MIN: %s" % stats.min
       print "MAX: %s" % stats.max
       print "MODE: %s" % stats.mode
       print "MEAN: %0.2f" % stats.mean
       print "RANGE: %s" % stats.range
       print "MEDIAN: %0.2f" % stats.median
       print "VARIANCE: %0.5f" % stats.variance
       print "STDDEV: %0.5f" % stats.stddev
       print "DATA LIST: %s" % stats.sample

    """
    def __init__(self, sample=[], population=False):
        """Statistics class initializer method."""

        # Raise an exception if the data set is empty.
        if (not sample):
            raise StatisticsException, "Empty data set!: %s" % sample

        # The data set (a list).
        self.sample = sample

        # Sample/Population variance determination flag.
        self.population = population

        self.N = len(self.sample)

        self.sum = float(sum(self.sample))

        self.min = min(self.sample)

        self.max = max(self.sample)

        self.range = self.max - self.min

        self.mean = self.sum/self.N

        # Inplace sort (list is now in ascending order).
        self.sample.sort()

        self.__getMode()

        # Instance identification attribute.
        self.identification = id(self)

    def __getMode(self):
        """Determine the most repeated value(s) in the data set."""

        # Initialize a dictionary to store frequency data.
        frequency = {}

        # Build dictionary: key - data set values; item - data frequency.
        for x in self.sample:
            if (x in frequency):
                frequency[x] += 1
            else:
                frequency[x] = 1

        # Create a new list containing the values of the frequency dict.  Convert
        # the list, which may have duplicate elements, into a set.  This will
        # remove duplicate elements.  Convert the set back into a sorted list
        # (in descending order).  The first element of the new list now contains
        # the frequency of the most repeated values(s) in the data set.
        # mode = sorted(list(set(frequency.values())), reverse=True)[0]
        # Or use the builtin - max(), which returns the largest item of a
        # non-empty sequence.
        mode = max(frequency.values())

        # If the value of mode is 1, there is no mode for the given data set.
        if (mode == 1):
            self.mode = []
            return

        # Step through the frequency dictionary, looking for values equaling
        # the current value of mode.  If found, append the value and its
        # associated key to the self.mode list.
        self.mode = [(x, mode) for x in frequency if (mode == frequency[x])]

    def __getVariance(self):
        """Determine the measure of the spread of the data set about the mean.
        Sample variance is determined by default; population variance can be
        determined by setting population attribute to True.
        """

        x = 0	# Summation variable.

        # Subtract the mean from each data item and square the difference.
        # Sum all the squared deviations.
        for item in self.sample:
            x += (item - self.mean)**2.0

        try:
            if (not self.population):
                # Divide sum of squares by N-1 (sample variance).
                self.variance = x/(self.N-1)
            else:
                # Divide sum of squares by N (population variance).
                self.variance = x/self.N
        except:
            self.variance = 0

    def __getStandardDeviation(self):
        """Determine the measure of the dispersion of the data set based on the
        variance.
        """

        from math import sqrt     # Mathematical functions.

        # Take the square root of the variance.
        self.stddev = sqrt(self.variance)


def extract_key_count(list, key=None):
    """
    A utility function written to count the number of times a `key` would appear in, for example, a categorized poll.
    Examples:
        >>> extract_key_count('yes',
    """

    if list and key:

        # go through a list of dictionaries
        for dict in list:
            if dict.get('category__name') == key:
                return dict.get('value')
    else:
        return 0


def get_week_count(reference_date, d):

    week_count = 0
    while(reference_date.date() <= d.date()):
        d = d - datetime.timedelta(days=7)
        week_count = week_count + 1

    return week_count


def get_months(start_date,end_date):
    to_ret = []
    first_day = start_date
    while start_date < end_date:
        last_day = start_date + relativedelta(day=1, months=+1, days=-1,hour=23,minute=59)
        start_date += relativedelta(months=1)
        to_ret.append([
            datetime.datetime(first_day.year, first_day.month, first_day.day,first_day.hour,first_day.minute),
            datetime.datetime(last_day.year, last_day.month, last_day.day,last_day.hour,last_day.minute)])
        first_day = start_date + relativedelta(day=1,hour=00,minute=00)
    to_ret.append([
        datetime.datetime(first_day.year, first_day.month, first_day.day,first_day.hour,first_day.minute),
        datetime.datetime(end_date.year, end_date.month, end_date.day,end_date.hour,end_date.minute)])
    return to_ret


