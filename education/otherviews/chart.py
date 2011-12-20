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
