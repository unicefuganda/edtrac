from django.shortcuts import get_object_or_404
from uganda_common.views import XFormChartView
from rapidsms.contrib.locations.models import Location

#POPULATE DATA for charts

#slug names
ABUSE_CASES = "emis_headteachers_abuses"
SMC_MEETINGS = "emis_meetings"
DAILY_LUNCH = "emis_meals"
#also lunch
SMC_MEALS = "emis_smc_meals"
#lunch that headmaster thinks was eaten up!
LUNCH_HEADMASTER = "emis_headteachers_meals"
