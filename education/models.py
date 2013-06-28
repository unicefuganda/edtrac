from difflib import get_close_matches
import dateutils
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.db.models import Q
from django.forms import ValidationError
from eav.models import Attribute
from education.utils import _schedule_weekly_scripts, _schedule_weekly_scripts_now, _schedule_monthly_script, _schedule_termly_script,\
    _schedule_weekly_report, _schedule_monthly_report, _schedule_midterm_script, _schedule_weekly_script, _schedule_teacher_weekly_scripts,\
    _schedule_new_monthly_script, _schedule_script_now, _this_thursday
from rapidsms_httprouter.models import mass_text_sent, Message
from rapidsms.models import Contact, ContactBase
from rapidsms.contrib.locations.models import Location
from poll.models import Poll
from script.signals import script_progress_was_completed, script_progress
from script.models import *
from script.utils.handling import find_best_response, find_closest_match
import re, calendar, datetime, time
from poll.models import ResponseCategory, Category
from education.attendance_diff import calculate_attendance_difference, append_time_to_week_date
import logging

logger = logging.getLogger(__name__)

class School(models.Model):
    name = models.CharField(max_length=160)
    emis_id = models.CharField(max_length=10)
    location = models.ForeignKey(Location, related_name='schools')

    def __unicode__(self):
        return '%s - %s' % (self.name, self.location.name)


class EmisReporter(Contact):
    CLASS_CHOICES = (
        ('P3', 'P3'),
        ('P6', 'P6'),
        )

    grade = models.CharField(max_length=2, choices=CLASS_CHOICES, null=True)
    schools = models.ManyToManyField(School, null=True)

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name

    def is_member_of(self, group):
        return group.lower() in [grp.lower for grp in self.groups.objects.values_list('name', flat=True)]

    def schools_list(self):
        return self.schools.values_list('name', flat=True)


class Role(Group):
    class Meta:
        proxy = True
        permissions = (
            ("can_report", "can  send data and receive data via text messages"),
            ("can_view_one_school", "Access to View his/her school specific info"),
            ("can_view_all_schools", "Access to View information from all schools"),
            ("can_message_all", "Can send out mass text,polls etc "),
            ("can_message_one_district", "Can send mass text,polls etc to district schools"),
            ("can_view_one_district_verified", "Access to view verified district data "),
            ("can_view_one_district_unverified", "Access to view district unverified  data  "),
            ("can_edit_one_district", "Access to edit his/her district specific info"),
            ("can_verify_one_district", "Access to edit his/her district specific info"),
            ("can_export_one_district", "Access to export his/her district specific info"),
            ("can_export_all", "Access to export all data"),
            ("can_schedule_special_script", "can send schedule special scripts")

            )

class UserProfile(models.Model):
    name = models.CharField(max_length=160)
    location = models.ForeignKey(Location)
    role = models.ForeignKey(Role)
    user = models.ForeignKey(User,related_name="profile")

    def is_member_of(self, group):
        return group.lower() == self.role.name.lower()

    def __unicode__(self):
        return self.name

class ScriptSchedule(models.Model):
    script = models.ForeignKey(Script)
    date = models.DateTimeField(auto_now=True)

def parse_date(command, value):
    return parse_date_value(value)

def parse_gender(gender):
    gender = get_close_matches(gender, ['M', 'Male', 'F', 'Female'], 1, 0.6)
    try:
        return list(gender[0])[0]
    except:
        return None



class ReportComment(models.Model):
    user = models.ForeignKey(User)

    commentable_choices = (
        ('abs', 'Absenteeism'),
        ('viol', 'Violence'),
        ('cp', 'Curriculum Progress'),
        ('mm', 'Missed Meals'),
        ('smc', 'School Management Committee Meetings'),
        ('upge', 'UPE Capitation Grants')
        )

    comment = models.TextField(null=False)

    commentable = models.CharField(max_length=10, choices=commentable_choices, blank=False)

    reporting_period_choices = (
        ('wk', 'Weekly'),
        ('mo', 'Monthly'),
        ('t', 'Termly')
        )

    reporting_period = models.CharField(max_length=2, choices=reporting_period_choices, blank=False)

    """
    `report_date` is populated when user saves this comment; it will be based on
    the last reporting date. You should be able to sort comments by their ``commentable_choices`` and define that the
    date is based on weekly, monthly, or termly basis.
    """
    report_date = models.DateTimeField(blank=False)

    def __unicode__(self):
        return self.comment

    def set_report_date(self, reporting_date):
        self.report_date = reporting_date

class EnrolledDeployedQuestionsAnswered(models.Model):
    poll = models.ForeignKey(Poll)
    school = models.ForeignKey(School)
    sent_at = models.DateTimeField()

    def __unicode__(self):
        return self.school.name


def parse_grade(grade):
    grade = get_close_matches(grade, ['P 3', 'P3','p3', 'P 6', 'P6', 'p6', 'primary three', 'primary six'], 1, 0.6)
    grade_chart = {
        'primary three': 'P3',
        'primary six' : 'P6'
    }

    try:
        if grade[0] in grade_chart.keys():
            grade = grade_chart[grade[0]]
            return grade
        else:
            cls = list(grade[0])[1] if list(grade[0])[1].strip() else list(grade[0])[2]
            return (list(grade[0])[0]).upper() + cls
    except:
        return None


def parse_date_value(value):
    try:
        date_expr = re.compile(r"\d{1,2} (?:%s) \d{2,4}" % '|'.join(calendar.month_abbr[1:]))
        date_expr1 = re.compile(r"\d{1,2}-\d{1,2}-\d{2,4}")
        date_expr2 = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")
        date_expr3 = re.compile(r"\d{1,2}\.\d{1,2}\.\d{2,4}")
        date_expr4 = re.compile(r"\d{2,4}\.\d{1,2}\.\d{1,2}")
        date_expr5 = re.compile(r"\d{2,4}-\d{1,2}-\d{1,2}")

        if date_expr.match(value):
            dt_obj = datetime.datetime.strptime(value, "%d %b %Y")
        elif date_expr1.match(value):
            dt_obj = datetime.datetime.strptime(value, "%d-%m-%Y")
        elif date_expr2.match(value):
            dt_obj = datetime.datetime.strptime(value, "%d/%m/%Y")
        elif date_expr3.match(value):
            dt_obj = datetime.datetime.strptime(value, "%d.%m.%Y")
        elif date_expr4.match(value):
            dt_obj = datetime.datetime.strptime(value, "%Y.%m.%d")
        else:
            dt_obj = datetime.datetime.strptime(value, "%Y-%m-%d")

    except ValueError:
        raise ValidationError("Expected date format "
                              "(\"dd mmm YYYY\", \"dd/mm/yyyy\", \"dd-mm-yyyy\", \"dd.mm.yyyy\", \"yyyy.mm.dd\" or \"yyyy-mm-dd\"), "
                              "but instead received: %s." % value)

    time_tuple = dt_obj.timetuple()
    timestamp = time.mktime(time_tuple)
    return int(timestamp)


def parse_yesno(command, value):
    lvalue = value.lower().strip()
    if dl_distance(lvalue, 'yes') <= 1 or lvalue == 'y':
        return 1
    else:
        return 0

def parse_fuzzy_number(command, value):
    fuzzy_number = re.compile('([0-9oOI]+)|(None)', re.IGNORECASE)
    m = fuzzy_number.match(value)
    if m:
        num = value[m.start():m.end()]
        try:
            index_l = num.lower().index('None'.lower())
            num[:index_l] + '0' + num[index_l + len('None'):]
        except ValueError:
            num = num.replace('o', '0')
            num = num.replace('O', '0')
            num = num.replace('I', '1')

        remaining = value[m.end():].strip()
        if remaining:
            if len(remaining) > 50:
                remaining = "%s..." % remaining[:47]
            raise ValidationError('You need to send a number for %s, you sent %s.Please resend' % (command, remaining))
        else:
            return int(num)

# rewrite of parse_fuzzy_number
def parse_fuzzy_number_2(value):
    fuzzy_number = re.compile('([0-9oOI]+)|(None)', re.IGNORECASE)
    m = fuzzy_number.match(value)
    if m:
        num = value[m.start():m.end()]
        try:
            inder_lower = num.lower().index('None'.lower())
            num[:inder_lower] + '0' + num[inder_lower + len('None'):]
        except ValueError:
            num = num.replace('o', 'O')
            num = num.replace('O', '0')
            num = num.replace('I', '1')
        remaining = value[m.end():].strip()
        if remaining:
            if len(remaining) > 50:
                remaining= "%s..." % remaining[:47]
            raise ValidationError('You need to send a number. You sent %s. Please resend' % (remaining))
        else:
            return int(num)

def match_group_response(session, response, poll):
    logger.info('match_group_response() called to match : session->%s response->%s poll->%s' % (session.pk, response, poll.question))
    grp_dict = {'teacher': 'Teachers',\
                    'hteacher': 'Head Teachers',\
                    'smc': 'SMC',\
                    'gem': 'GEM',\
                    'deo': 'DEO',\
                    'meo': 'MEO',\
                    'unknown': 'Other Reporters',\
                    }
    resp_cats = {'1': 'teacher',\
                '2': 'hteacher',\
                '3': 'smc',\
                '4': 'gem',\
                '5': 'deo',\
                '6': 'meo',\
                    }
    try:
        category = Category.objects.get(name=resp_cats.get(response.strip(), 'unknown'), poll=poll)
        logger.info('Found category: %s corresponding to response: %s ' % (category, response))
    except:
        category = Category.objects.get(name='unknown', poll=poll)
        logger.info('Category not found, so defaulting to: %s corresponding to response: %s ' % (category, response))
    try:
        #some times an answer for role might be missing    
        resp = session.responses.filter(response__poll=poll, response__has_errors=False).order_by('-response__date')[0]
        logger.info('Response stored in this session: %s ' % resp.response.message)
        try:
            rc = ResponseCategory.objects.get(response=resp.response, category=category)
            grp = Group.objects.get(name=grp_dict[rc.category.name])
            logger.info('Response categorized as: %s so, user belongs to group: %s ' % (rc.category.name, grp.name))
        except ResponseCategory.DoesNotExist:
            # if answer was not categorized, put member in "Other Reporters"
            grp = Group.objects.get(name='Other Reporters')
            logger.info('Group corresponding to response category not found, defaulting to group: %s ' % grp.name)
    except IndexError:
        # if no response is given, still put member in Other Reporters
        grp = Group.objects.get(name='Other Reporters')
        logger.info('No group response found in session, defaulting to group: %s ' % grp.name)
    return grp

def edtrac_autoreg(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
    if not progress.script.slug == 'edtrac_autoreg':
        return
    session = ScriptSession.objects.filter(script=progress.script, connection=connection).order_by('-end_time')[0]
    script = progress.script
    role_poll = script.steps.get(poll__name='edtrac_role').poll
    gender_poll = script.steps.get(poll__name='edtrac_gender').poll
    class_poll = script.steps.get(poll__name='edtrac_class').poll
    district_poll = script.steps.get(poll__name='edtrac_district').poll
    subcounty_poll = script.steps.get(poll__name='edtrac_subcounty').poll
    school_poll = script.steps.get(poll__name='edtrac_school').poll
    name_poll = script.steps.get(poll__name='edtrac_name').poll

    name = find_best_response(session, name_poll)
    role = find_best_response(session, role_poll)
    gender = find_best_response(session, gender_poll)
    grade = find_best_response(session, class_poll)
    default_group = Group.objects.get(name='Other Reporters')
    subcounty = find_best_response(session, subcounty_poll)
    district = find_best_response(session, district_poll)

    if name:
        name = ' '.join([n.capitalize() for n in name.lower().split()])[:100]
    if district:
        district =  find_closest_match(district.name, Location.objects.filter(type='district'))

    if subcounty:
        if district:
            subcounty = find_closest_match(subcounty, district.get_descendants().filter(type='sub_county'))
        else:
            subcounty = find_closest_match(subcounty, Location.objects.filter(type='sub_county'))

    grp = match_group_response(session, role, role_poll)
#    grp = find_closest_match(role, Group.objects)
#    grp = grp if grp else default_group

    if subcounty:
        rep_location = subcounty
    elif district:
        rep_location = district
    else:
        rep_location = Location.tree.root_nodes()[0]
    try:
        contact = connection.contact or EmisReporter.objects.get(name=name,\
            reporting_location=rep_location,
            groups=grp,
            connection=connection
        )
        if connection.contact:
            contact = EmisReporter.objects.get(pk=connection.contact.pk)
    except EmisReporter.DoesNotExist, EmisReporter.MultipleObectsReturned:
        contact = EmisReporter.objects.create()

    connection.contact = contact
    connection.save()
    
    group = grp
    if contact.groups.count() > 0: 
        for g in contact.groups.all():
            contact.groups.remove(g)
    contact.groups.add(group)

#    group = Group.objects.get(name='Other Reporters')
#    default_group = group
#    if role:
#        group = find_closest_match(role, Group.objects) or find_closest_match(role, Group.objects, True)
#        if not group:
#            group = default_group
#    contact.groups.add(group)

    if subcounty:
        contact.reporting_location = subcounty
    elif district:
        contact.reporting_location = district
    else:
        contact.reporting_location = Location.tree.root_nodes()[0]

    if gender:
        gender = parse_gender(gender)
        if gender:
            contact.gender = gender

    if grade:
        grade = parse_grade(grade)
        if grade:
            contact.grade = grade

    if name:
        contact.name = name

    if not contact.name:
        contact.name = 'Anonymous User'
    # activate reporter by default (deactivate when quit)
    contact.active = True
    contact.save()

    reporting_school = None
    school = find_best_response(session, school_poll)
    if school:
        if district:
            reporting_school = find_closest_match(school, School.objects.filter(location__name__in=[district],\
                location__type__name='district'), True)
        elif subcounty:
            reporting_school = find_closest_match(school, School.objects.filter(location__name__in=[subcounty],\
                location__type__name='sub_county'), True)
#        elif district:
#            reporting_school = find_closest_match(school, School.objects.filter(location__name__in=[district.name],\
#                location__type__name='district'), True)
        else:
            reporting_school = find_closest_match(school, School.objects.filter(location__name=Location.tree.root_nodes()[0].name))
        if reporting_school:
            contact.schools.add(reporting_school)
            contact.save()
            
        

    if not getattr(settings, 'TRAINING_MODE', False):
        # Now that you have their roll, they should be signed up for the periodic polling
#        _schedule_weekly_scripts(group, connection, ['Teachers', 'Head Teachers', 'SMC'])
#        _schedule_weekly_script(group, connection, 'edtrac_p3_teachers_weekly', ['Teachers'])
        _schedule_weekly_script(group, connection, 'edtrac_p3_teachers_weekly', ['Teachers'])
        _schedule_weekly_scripts(group, connection, ['Head Teachers', 'SMC'])
        #_schedule_monthly_script(group, connection, 'edtrac_teachers_monthly', 'last', ['Teachers'])
#        _schedule_monthly_script(group, connection, 'edtrac_head_teachers_monthly', 'last', ['Head Teachers'])
        _schedule_new_monthly_script(group, connection, 'edtrac_headteacher_violence_monthly', ['Head Teachers'])
        _schedule_new_monthly_script(group, connection, 'edtrac_headteacher_meals_monthly', ['Head Teachers'])
        _schedule_monthly_script(group, connection, 'edtrac_smc_monthly', 5, ['SMC'])
        _schedule_monthly_script(group, connection, 'edtrac_gem_monthly', 20, ['GEM'])
        #termly messages go out mid April, July or November by default, this can be overwridden by manual process
#        _schedule_termly_script(group, connection, 'edtrac_upe_grant', ['Head Teachers'])
        _schedule_termly_script(group, connection, 'edtrac_smc_termly', ['SMC'])

def edtrac_reschedule_script(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
    
    slug = progress.script.slug
    if not progress.script.slug.startswith('edtrac_') or progress.script.slug == 'edtrac_autoreg':
        return
    if not connection.contact:
        return
    if not connection.contact.groups.count():
        return
    group = connection.contact.groups.all()[0]
    if slug in ["edtrac_%s" % g.lower().replace(' ', '_') + '_weekly' for g in ['Teachers', 'Head Teachers', 'SMC']]:
#        import ipdb;ipdb.set_trace()
        _schedule_weekly_scripts(group, connection, ['Teachers', 'Head Teachers', 'SMC'])
    elif slug == 'edtrac_head_teachers_monthly':
        _schedule_monthly_script(group, connection, 'edtrac_head_teachers_monthly', 'last', ['Head Teachers'])
    elif slug == 'edtrac_smc_monthly':
        _schedule_monthly_script(group, connection, 'edtrac_smc_monthly', 5, ['SMC'])
    elif slug == 'edtrac_gem_monthly':
        _schedule_monthly_script(group, connection, 'edtrac_gem_monthly', 20, ['GEM'])
    elif slug == 'edtrac_head_teachers_termly':
        _schedule_termly_script(group, connection, 'edtrac_head_teachers_termly', ['Head Teachers'])
    elif slug == 'edtrac_smc_termly':
        _schedule_termly_script(group, connection, 'edtrac_smc_termly', ['SMC'])
    else:
        pass


def edtrac_autoreg_transition(**kwargs):
    
    # logger.info('Keyword arguments: %s' % kwargs)
    
    connection = kwargs['connection']
    progress = kwargs['sender']
    if not progress.script.slug == 'edtrac_autoreg':
        return
    script = progress.script
    try:
        session = ScriptSession.objects.filter(script=progress.script, connection=connection, end_time=None).latest('start_time')
    except ScriptSession.DoesNotExist:
        return
    role_poll = script.steps.get(poll__name="edtrac_role").poll
    role = find_best_response(session, role_poll) if find_best_response(session, role_poll) else None
    group = None
    if role:
        logger.info('Role: %s' % role)

#    if role:
#        group = find_closest_match(role, Group.objects) or find_closest_match(role, Group.objects, True)
    if role:
        group = match_group_response(session, role, role_poll)
        
        logger.info('Identified group: %s'% group.name)
        
        skipsteps = {
            'edtrac_class' : ['Teachers'],
            'edtrac_gender' : ['Head Teachers'],
            'edtrac_subcounty' : ['Teachers', 'Head Teachers', 'SMC', 'GEM'],
            'edtrac_school' : ['Teachers', 'Head Teachers', 'SMC']
        }
        skipped = True
        while group and skipped:
            skipped = False
            for step_name, roles in skipsteps.items():
                if  progress.step.poll and\
                    progress.step.poll.name == step_name and group.name not in roles:
                    
                    logger.info('SKIPPED! %s -> %s:' % (step_name, progress.step.poll.question))
                    
                    skipped = True
                    progress.step = progress.script.steps.get(order=progress.step.order + 1)
                    progress.save()
                    break

def edtrac_attendance_script_transition(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
#    if not progress.script.slug == 'edtrac_teachers_weekly':
    if not progress.script.slug in ['edtrac_p3_teachers_weekly', 'edtrac_p6_teachers_weekly']:    
        return
    script = progress.script
    try:
        session = ScriptSession.objects.filter(script=script, connection=connection, end_time=None).latest('start_time')
    except ScriptSession.DoesNotExist:
        return
    grade = connection.contact.emisreporter.grade
    if not grade:
        if progress.last_step():
            progress.giveup()
            return
        progress.step = progress.script.steps.get(order=progress.step.order + 1)
        progress.save()
        return

    skipsteps = {
        'edtrac_boysp3_attendance':['P3'],
        'edtrac_boysp6_attendance':['P6'],
        'edtrac_girlsp3_attendance':['P3'],
        'edtrac_girlsp6_attendance':['P6'],
        'edtrac_p3curriculum_progress':['P3'],
        }
    skipped = True
    while grade and skipped:
        skipped = False
        for step_name, grades in skipsteps.items():
            if  progress.step.poll and progress.step.poll.name == step_name and not grade in grades:
                skipped = True
                if progress.last_step():
                    progress.giveup()
                    return
                progress.step = progress.script.steps.get(order=progress.step.order + 1)
                progress.save()
                break

def edtrac_scriptrun_schedule(**kwargs):

    connection = kwargs['connection']
    progress = kwargs['sender']
    step = kwargs['step']
    if progress.script.slug == 'edtrac_autoreg':
        return
    script = progress.script
    connections = ScriptProgress.objects.filter(script=script)
    date = datetime.datetime.now().date()
    if step == 0:
        s, c = ScriptSchedule.objects.get_or_create(script=script, date__contains=date)


def send_message_for_partial_response(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
    is_last_step = progress.script.steps.order_by("-order").all()[0]

    if progress.step.order == is_last_step.order:
       if not all_steps_answered(progress.script):
           send_alert_for_expired_script(progress.script, connection)

def send_alert_for_expired_script(script,connection):
    if not all_steps_answered(script):
        if script.slug in ['edtrac_p3_teachers_weekly','edtrac_p6_teachers_weekly','edtrac_smc_weekly']:
            message_string = 'Thank you for participating. Remember to answer all your questions next Thursday.'
            Message.mass_text(message_string,[connection])


def all_steps_answered(script):
    this_thursday = _this_thursday().date()
    week_start = dateutils.increment(this_thursday, days=-6)
    current_week = append_time_to_week_date(this_thursday, week_start)
    for step in script.steps.all():
        if not Response.objects.filter(poll = step.poll,date__range=current_week,has_errors=False).exists():
            return False
    return True


def get_message_string(atttd_diff, emisreporter_grade, keys, progress):
    if (None,'') in atttd_diff.values():
        return None
    if progress.script.slug == 'edtrac_head_teachers_weekly':

       return "Thankyou, Attendance for male teacher have been %s by %spercent Attendance for female teachers have been %s by %spercent" % (
            atttd_diff['edtrac_m_teachers_attendance'][1], atttd_diff['edtrac_m_teachers_attendance'][0],
            atttd_diff['edtrac_f_teachers_attendance'][1], atttd_diff['edtrac_m_teachers_attendance'][0])

    return "Thankyou %s Teacher, Attendance for boys have been %s by %spercent" \
                         " Attendance for girls have been %s by %spercent" % (
                             emisreporter_grade, atttd_diff[keys[emisreporter_grade][0]][1],
                             atttd_diff[keys[emisreporter_grade][0]][0], atttd_diff[keys[emisreporter_grade][1]][1],
                             atttd_diff[keys[emisreporter_grade][1]][0])


def send_feedback_on_complete(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
    message_string = None
    if not all_steps_answered(progress.script):
        send_alert_for_expired_script(progress.script, connection)
        return
    keys = {'p3':['edtrac_boysp3_attendance','edtrac_girlsp3_attendance'],
            'p6':['edtrac_boysp6_attendance','edtrac_girlsp6_attendance']}
    if progress.script.slug in ['edtrac_p3_teachers_weekly','edtrac_p6_teachers_weekly','edtrac_head_teachers_weekly']:
        atttd_diff = calculate_attendance_difference(connection, progress)
        if not connection.contact.emisreporter.grade is None:
            emisreporter_grade = connection.contact.emisreporter.grade.lower()
            message_string = get_message_string(atttd_diff, emisreporter_grade, keys, progress)
    if progress.script.slug == 'edtrac_smc_weekly':
        message_string = "Thank you for your report. Please continue to visit your school and report on what is happening."
    if message_string is not None:
        Message.mass_text(message_string, [connection])

def reschedule_weekly_polls(grp=None):
    """
    manually reschedule all weekly polls or for a specified group
    """
    weekly_scripts = Script.objects.filter(slug__endswith='_weekly')
    if grp:
        slg_start = 'edtrac_%s'%grp.replace(' ','_').lower()
        weekly_scripts = weekly_scripts.filter(slug__startswith=slg_start)
        ScriptProgress.objects.filter(script__in=weekly_scripts).filter(connection__contact__emisreporter__groups__name__iexact=grp).delete()
    else:
        ScriptProgress.objects.filter(script__in=weekly_scripts).delete()
    Script.objects.filter(slug__in=weekly_scripts.values_list('slug', flat=True)).update(enabled=True)
    grps = Group.objects.filter(name__iexact=grp) if grp else Group.objects.filter(name__in=['Teachers', 'Head Teachers', 'SMC'])
    # get active reporters
    print grps
    reps = EmisReporter.objects.filter(groups__in=grps)
    for rep in reps:
        if rep.default_connection and len(rep.groups.all()) > 0:
            _schedule_weekly_scripts(rep.groups.all()[0], rep.default_connection, ['Teachers', 'Head Teachers', 'SMC'])

def reschedule_teacher_weekly_polls(grp=None):
    """
    manually reschedule all weekly polls or for a specified group
    """
    weekly_scripts = Script.objects.filter(slug__in=['edtrac_p3_teachers_weekly', 'edtrac_p6_teachers_weekly'])
    if grp:
        ScriptProgress.objects.filter(script__in=weekly_scripts).filter(connection__contact__emisreporter__groups__name__iexact=grp).delete()
    else:
        ScriptProgress.objects.filter(script__in=weekly_scripts).delete()
    Script.objects.filter(slug__in=weekly_scripts.values_list('slug', flat=True)).update(enabled=True)
    grps = Group.objects.filter(name__iexact=grp) if grp else Group.objects.filter(name__in=['Teachers', 'Head Teachers', 'SMC'])
    # get active reporters
    print grps
    reps = EmisReporter.objects.filter(groups__in=grps)
    for rep in reps:
        if rep.default_connection and len(rep.groups.all()) > 0:
            _schedule_teacher_weekly_scripts(rep.groups.all()[0], rep.default_connection, ['Teachers', 'Head Teachers', 'SMC'])
            print rep.name
    print "Poll sent out to " + str(reps.count()) + " reporters"


def reschedule_monthly_polls(grp=None):
    """
    manually reschedule all monthly polls or for a specified group
    """
    monthly_scripts = Script.objects.filter(slug__endswith='_monthly')
    if grp:
        slg_start = 'edtrac_%s'%grp.replace(' ','_').lower()
#        monthly_scripts = monthly_scripts.filter(slug__startswith=slg_start)
        monthly_scripts = monthly_scripts.filter(slug__in=['edtrac_smc_monthly', 'edtrac_gem_monthly'])
        ScriptProgress.objects.filter(script__in=monthly_scripts)\
        .filter(connection__contact__emisreporter__groups__name__iexact=grp).delete()
    else:
        ScriptProgress.objects.filter(script__in=monthly_scripts).delete()
    Script.objects.filter(slug__in=monthly_scripts.values_list('slug', flat=True)).update(enabled=True)
    for slug in monthly_scripts.values_list('slug', flat=True):
        grps = Group.objects.filter(name__iexact=grp) if grp else Group.objects.filter(name__in=['SMC', 'GEM'])
        # get list of active reporters
        reps = EmisReporter.objects.filter(groups__in=grps)
        for rep in reps:
            print 'processing %s' % rep.name
            if rep.default_connection and rep.groups.count() > 0:
                if slug == 'edtrac_smc_monthly':
                    _schedule_monthly_script(rep.groups.all()[0], rep.default_connection, 'edtrac_smc_monthly', 5, ['SMC'])
                elif slug == 'edtrac_gem_monthly':
                    _schedule_monthly_script(rep.groups.all()[0], rep.default_connection, 'edtrac_gem_monthly', 20, ['GEM'])

def reschedule_midterm_polls(grp = 'all', date=None):

    """
    manually reschedule all mid-term polls or for a specified group
    """

    midterm_scripts = Script.objects.filter(slug__endswith='_midterm')
    if not grp == 'all':
        slg_start = 'edtrac_%s'%grp.replace(' ','_').lower()
        midterm_scripts = midterm_scripts.filter(slug__startswith=slg_start)
        ScriptProgress.objects.filter(script__in=midterm_scripts)\
            .filter(connection__contact__emisreporter__groups__name__iexact=grp).delete()
    else:
        ScriptProgress.objects.filter(script__in=midterm_scripts).delete()

    Script.objects.filter(slug__in=midterm_scripts.values_list('slug', flat=True)).update(enabled=True)
    for slug in midterm_scripts.values_list('slug', flat=True):
        grps = Group.objects.filter(name__iexact=grp) if not grp == 'all' else Group.objects.filter(name__in=['Head Teachers'])
        # send poll questions to active reporters
        reps = EmisReporter.objects.filter(groups__in=grps)
        for rep in reps:
            if rep.default_connection and rep.groups.count() > 0:
                _schedule_midterm_script(rep.groups.all()[0], rep.default_connection, slug, ['Head Teachers'], date)
                
def reschedule_termly_polls(grp = 'all', date=None):

    """
    manually reschedule all termly polls or for a specified group
    """

    termly_scripts = Script.objects.filter(slug__endswith='_termly')
    if not grp == 'all':
        slg_start = 'edtrac_%s'%grp.replace(' ','_').lower()
        termly_scripts = termly_scripts.filter(slug__startswith=slg_start)
        ScriptProgress.objects.filter(script__in=termly_scripts)\
            .filter(connection__contact__emisreporter__groups__name__iexact=grp).delete()
    else:
        ScriptProgress.objects.filter(script__in=termly_scripts).delete()

    Script.objects.filter(slug__in=termly_scripts.values_list('slug', flat=True)).update(enabled=True)
    for slug in termly_scripts.values_list('slug', flat=True):
        grps = Group.objects.filter(name__iexact=grp) if not grp == 'all' else Group.objects.filter(name__in=['Head Teachers', 'SMC'])
        # send poll questions to active reporters
        reps = EmisReporter.objects.filter(groups__in=grps)
        for rep in reps:
            if rep.default_connection and rep.groups.count() > 0:
                _schedule_termly_script(rep.groups.all()[0], rep.default_connection, slug, ['Head Teachers', 'SMC'], date)
                
def reschedule_termly_script(grp = 'all', date=None, slug=''):
    
    """
    manually reschedule each of the termly scripts for headteachers
    """
    
    tscript = Script.objects.get(slug=slug)
    if not grp == 'all':
        ScriptProgress.objects.filter(script=tscript).filter(connection__contact__emisreporter__groups__name__iexact=grp).delete()
    else:
        ScriptProgress.objects.filter(script=tscript).delete()
        
    tscript.enabled=True
    grps = Group.objects.filter(name__iexact=grp) if not grp == 'all' else Group.objects.filter(name__in=['Head Teachers', 'SMC', 'GEM'])
    reps = EmisReporter.objects.filter(groups__in=grps)
    for rep in reps:
        if rep.default_connection and rep.groups.count() > 0:
            _schedule_termly_script(rep.groups.all()[0], rep.default_connection, slug, ['Head Teachers', 'SMC', 'GEM'], date)
            
def reschedule_monthly_script(grp = 'all', date=None, slug=''):
    
    """
    manually reschedule each of the monthly scripts for headteachers
    """
    
    tscript = Script.objects.get(slug=slug)
    if not grp == 'all':
        ScriptProgress.objects.filter(script=tscript).filter(connection__contact__emisreporter__groups__name__iexact=grp).delete()
    else:
        ScriptProgress.objects.filter(script=tscript).delete()
        
    tscript.enabled=True
    grps = Group.objects.filter(name__iexact=grp) if not grp == 'all' else Group.objects.filter(name__in=['Head Teachers', 'SMC', 'GEM'])
    reps = EmisReporter.objects.filter(groups__in=grps)
    for rep in reps:
        if rep.default_connection and rep.groups.count() > 0:
            _schedule_new_monthly_script(rep.groups.all()[0], rep.default_connection, slug, ['Head Teachers', 'SMC', 'GEM'], date)
    
def reschedule_weekly_script(grp = 'all', date=None, slug=''):
    
    """
    manually reschedule each of the termly scripts for headteachers
    """
    
    tscript = Script.objects.get(slug=slug)
    if not grp == 'all':
        ScriptProgress.objects.filter(script=tscript).filter(connection__contact__emisreporter__groups__name__iexact=grp).delete()
    else:
        ScriptProgress.objects.filter(script=tscript).delete()
        
    tscript.enabled=True
    grps = Group.objects.filter(name__iexact=grp) if not grp == 'all' else Group.objects.filter(name__in=['Teachers', 'Head Teachers'])
    reps = EmisReporter.objects.filter(groups__in=grps)
    for rep in reps:
        if rep.default_connection and rep.groups.count() > 0:
            _schedule_weekly_script(rep.groups.all()[0], rep.default_connection, slug, ['Teachers', 'Head Teachers'])
            print rep.name
    print "Script sent out to " + str(reps.count()) + " reporters"
    
def schedule_script_now(grp = 'all', slug=''):
    
    """
    manually reschedule script immediately
    """
    now_script = Script.objects.get(slug=slug)
    if not grp == 'all':
        ScriptProgress.objects.filter(script=now_script).filter(connection__contact__emisreporter__groups__name__iexact=grp).delete()
    else:
        ScriptProgress.objects.filter(script=now_script).delete()    
    
    now_script.enabled = True
    grps = Group.objects.filter(name__iexact=grp)
    reporters = EmisReporter.objects.filter(groups__in=grps)
    for reporter in reporters:
        if reporter.default_connection and reporter.groups.count() > 0:
            _schedule_script_now(reporter.groups.all()[0], reporter.default_connection, slug, ['Teachers', 'Head Teachers', 'SMC', 'GEM'])
    print "Script sent out to " + str(reporters.count()) + " reporters"


def schedule_weekly_report(grp='DEO'):
    from .utils import _schedule_report_sending
    _schedule_report_sending()

#more scheduled stuff
def create_record_enrolled_deployed_questions_answered(model=None):
    """
    This function is run in a periodic task to create instances of the EnrolledDeployedQuestionsAnswered class that
    represents schools that have the enrollment and deployment questions answered.

    PERKS: Currently this function is called in a celery task and is optionally called as a management command.
    """
    if model:
        # query against the poll model
        polls = Poll.objects.filter(Q(name__icontains="enrollment")|Q(name__icontains="deployment"))
        all_responses = []
        resp_dict = {}

        if model.objects.exists():
            # this runs on existing EnrolledDeployedQuestionsAnswered records
            erqa = model.objects.latest('sent_at')
            # get responses that came in after the time of latest `erqa` recorded created

            for poll in polls:
                resp_dict[poll.name] = []
                all_responses.extend(poll.responses.exclude(contact__emisreporter__schools=None).\
                    filter(date__gte = erqa.sent_at).select_related().\
                    values_list( 'poll__name', 'contact__emisreporter__schools__pk', 'date'))
        else:
            # This is run only once; no chance of it happening unless the `erqa` model is flushed out.
            now = datetime.datetime.now()
            # get responses that came in before now!!!
            for poll in polls:
                resp_dict[poll.name] = []
                all_responses.extend(
                    poll.responses.exclude(contact__emisreporter__schools=None).filter(date__lte = now).\
                        select_related().values_list('poll__name', 'contact__emisreporter__schools__pk', 'date'))

        # populate the res_dict with school_pk and sent_at values as a list of lists
        for poll_name, school_pk, sent_at in all_responses:
            resp_dict[poll_name].append([school_pk, sent_at])

        for poll_name in resp_dict.keys():
            try:
                poll = Poll.objects.get(name = poll_name)
                other_responses = resp_dict[poll_name]
                for school_pk, sent_at in other_responses:
                    school = School.objects.select_related().get(pk = school_pk)
                    model.objects.create(
                        poll = poll,
                        school = school,
                        sent_at = sent_at)
            except ObjectDoesNotExist:
                pass
            return

Poll.register_poll_type('date', 'Date Response', parse_date_value, db_type=Attribute.TYPE_OBJECT)

#reversion.register(School)
#reversion.register(UserProfile)#, follow = ['location', 'role', 'user'])
#reversion.register(EmisReporter, follow=['schools'])#, follow = ['contact_ptr'])
#reversion.register(ReportComment)

script_progress_was_completed.connect(edtrac_autoreg, weak=False)
script_progress_was_completed.connect(edtrac_reschedule_script, weak=False)
script_progress.connect(edtrac_autoreg_transition, weak=False)
script_progress.connect(edtrac_attendance_script_transition, weak=False)
script_progress_was_completed.connect(send_feedback_on_complete,weak=True)
#script_progress.connect(edtrac_scriptrun_schedule, weak=False)

class ScriptScheduleTime(models.Model):
    script = models.ForeignKey(Script)
    scheduled_on = models.DateField(auto_now=True)