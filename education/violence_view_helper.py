'''
Created on Apr 08, 2013

@author: raybesiga
'''

from collections import defaultdict
from datetime import timedelta
from django.conf import settings

from django.db.models import Sum, Count

from education.models import EmisReporter, School, EnrolledDeployedQuestionsAnswered
from education.reports import get_week_date
from education.utils import is_empty
from poll.models import Poll, ResponseCategory, Response
from rapidsms.contrib.locations.models import Location
from unregister.models import Blacklist