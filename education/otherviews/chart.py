from django.shortcuts import get_object_or_404
from uganda_common.views import XFormChartView
from rapidsms.contrib.locations.models import Location
from poll.models import Poll
import datetime
#POPULATE DATA for charts

#slug names
ABUSE_CASES = "emis_headteachers_abuses"
SMC_MEETINGS = "emis_meetings"
DAILY_LUNCH = "emis_meals"
#also lunch
SMC_MEALS = "emis_smc_meals"
#lunch that headmaster thinks was eaten up!
LUNCH_HEADMASTER = "emis_headteachers_meals"


abuse_polls = Poll.objects.filter(name=ABUSE_CASES)

#SMC Meals
smc_meals_poll = Poll.objects.get(name=SMC_MEALS)

# basic drill down to just 30 days
#TODO: include just work days?? thoughts.
total_responses = smc_meals_poll.responses.filter(date__gte=datetime.datetime.now()-datetime.timedelta(days=30))

# get data location
all_locations = Location.objects.filter(type__name="district")
lunch_polls = Poll.objects.filter(name="emis_headteachers_meals")

smc_meeting_polls = Poll.objects.get(name="emis_smc_meals")
for location in all_locations:
    print location
    responses = smc_meeting_polls.responses.filter(contact__in=Contact.objects.filter(reporting_location=location))
    print responses

    #single statement
    #all_responses = .responses.filter(contact__in=location)

#TODO move to utils when done
def compute_avg_percentage(list_of_percentages):
    """Average percentage"""
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
    return sum(sanitize) / float(len(sanitize))