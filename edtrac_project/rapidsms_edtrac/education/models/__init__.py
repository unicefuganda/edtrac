from emis_reporter import EmisReporter, update_last_reporting_date
from enrolled_deployed_questions_answered import EnrolledDeployedQuestionsAnswered
from report_comment import ReportComment
from role import Role
from school import School
from script_schedule import ScriptSchedule,ScriptScheduleTime
from user_profile import UserProfile
from indicator import Indicator
from term import Term
from utils import *
from django.db.models.signals import post_save

post_save.connect(update_last_reporting_date, sender=Message)
