import dateutils
import re
import calendar
import datetime
import time

from difflib import get_close_matches
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms import ValidationError
from eav.models import Attribute
from education.utils import _schedule_script_now, _this_thursday
from rapidsms_httprouter.models import Message
from rapidsms.contrib.locations.models import Location
from poll.models import Poll
from script.signals import script_progress_was_completed, script_progress
from script.models import *
from script.utils.handling import find_best_response, find_closest_match
from poll.models import ResponseCategory, Category
from education.attendance_diff import calculate_attendance_difference,\
    append_time_to_week_date
import logging

from .emis_reporter import EmisReporter
from .school import School

from education.scheduling import schedule, schedule_all, schedule_script_at
from unregister.models import Blacklist

logger = logging.getLogger(__name__)


def parse_date(command, value):
    return parse_date_value(value)


def parse_gender(gender):
    gender = get_close_matches(gender, ['M', 'Male', 'F', 'Female'], 1, 0.6)
    try:
        return list(gender[0])[0]
    except:
        return None


def parse_grade(grade):
    grade = get_close_matches(
        grade,
        ['P 3', 'P3', 'p3', 'P 6', 'P6', 'p6', 'primary three', 'primary six'],
        1,
        0.6
    )
    grade_chart = {
        'primary three': 'P3',
        'primary six': 'P6'
    }

    try:
        if grade[0] in grade_chart.keys():
            grade = grade_chart[grade[0]]
            return grade
        else:
            cls = None
            if list(grade([0][1].strip())):
                cls = list(grade[0][1])
            else:
                cls = list(grade[0][2])

            return (list(grade[0])[0]).upper() + cls
    except:
        return None


def parse_date_value(value):
    try:
        date_expr = re.compile(
            r"\d{1,2} (?:%s) \d{2,4}" % '|'.join(calendar.month_abbr[1:])
        )
        date_expr1 = re.compile(r"\d{1,2}-\d{1,2}-\d{2,4}")
        date_expr2 = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")
        date_expr3 = re.compile(r"\d{1,2}\.\d{1,2}\.\d{2,4}")
        date_expr4 = re.compile(r"\d{2,4}\.\d{1,2}\.\d{1,2}")

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
                              "(\"dd mmm YYYY\", \"dd/mm/yyyy\", "
                              "\"dd-mm-yyyy\", \"dd.mm.yyyy\", "
                              "\"yyyy.mm.dd\" or \"yyyy-mm-dd\"), "
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


def match_group_response(session, response, poll):
    logger.info(
        'match_group_response() called to match : session->%s response->%s '
        'poll->%s' % (session.pk, response, poll.question))
    grp_dict = {'teacher': 'Teachers',
                'hteacher': 'Head Teachers',
                'smc': 'SMC',
                'gem': 'GEM',
                'deo': 'DEO',
                'meo': 'MEO',
                'unknown': 'Other Reporters',
                }
    resp_cats = {'1': 'teacher',
                 '2': 'hteacher',
                 '3': 'smc',
                 '4': 'gem',
                 '5': 'deo',
                 '6': 'meo',
                 }
    try:
        category = Category.objects.get(
            name=resp_cats.get(response.strip(), 'unknown'),
            poll=poll
        )
        logger.info(
            'Found category: %s corresponding to response: %s '
            % (category, response)
        )
    except:
        category = Category.objects.get(name='unknown', poll=poll)
        logger.info(
            'Category not found, so defaulting to: %s corresponding to '
            'response: %s ' % (category, response)
        )
    try:
        #some times an answer for role might be missing
        resp = session.responses.filter(
            response__poll=poll,
            response__has_errors=False
        ).order_by('-response__date')[0]
        logger.info(
            'Response stored in this session: %s '
            % resp.response.message
        )
        try:
            rc = ResponseCategory.objects.get(
                response=resp.response,
                category=category
            )
            grp = Group.objects.get(name=grp_dict[rc.category.name])
            logger.info(
                'Response categorized as: %s so, user belongs to group: %s '
                % (rc.category.name, grp.name)
            )
        except ResponseCategory.DoesNotExist:
            # if answer was not categorized, put member in "Other Reporters"
            grp = Group.objects.get(name='Other Reporters')
            logger.info(
                'Group corresponding to response category not found, '
                'defaulting to group: %s ' % grp.name
            )
    except IndexError:
        # if no response is given, still put member in Other Reporters
        grp = Group.objects.get(name='Other Reporters')
        logger.info(
            'No group response found in session, defaulting to group: %s '
            % grp.name
        )
    return grp


def edtrac_autoreg(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
    if not progress.script.slug == 'edtrac_autoreg':
        return
    session = ScriptSession.objects.filter(
        script=progress.script,
        connection=connection
    ).order_by('-end_time')[0]
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
    subcounty = find_best_response(session, subcounty_poll)
    district = find_best_response(session, district_poll)

    if name:
        name = ' '.join([n.capitalize() for n in name.lower().split()])[:100]
    if district:
        district = find_closest_match(
            district,
            Location.objects.filter(type='district')
        )

    if subcounty:
        if district:
            subcounty = find_closest_match(
                subcounty,
                district.get_descendants().filter(type='sub_county')
            )
        else:
            subcounty = find_closest_match(
                subcounty,
                Location.objects.filter(type='sub_county')
            )

    grp = match_group_response(session, role, role_poll)

    if subcounty:
        rep_location = subcounty
    elif district:
        rep_location = district
    else:
        rep_location = Location.tree.root_nodes()[0]
    try:
        contact = connection.contact or EmisReporter.objects.get(
            name=name,
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
            reporting_school = School.objects.filter(name__iexact=school)
            if reporting_school.exists():
                reporting_school = reporting_school[0]
            else:
                reporting_school = find_closest_match(
                    school,
                    School.objects.filter(
                        location__name__in=[district],
                        location__type__name='district'
                    ),
                    True
                )
                contact.has_exact_matched_school = False
                contact.save()
        elif subcounty:
            reporting_school = find_closest_match(
                school,
                School.objects.filter(
                    location__name__in=[subcounty],
                    location__type__name='sub_county'
                ),
                True
            )

    schedule_all(connection)


def edtrac_reschedule_script(**kwargs):
    connection = kwargs['connection']
    script = kwargs['sender'].script
    if should_reschedule(connection, script):
        schedule(connection, script)

def should_reschedule(connection, script):
    return script.slug != 'edtrac_autoreg' and not Blacklist.objects.filter(connection=connection).exists()

def edtrac_autoreg_transition(**kwargs):

    connection = kwargs['connection']
    progress = kwargs['sender']
    if not progress.script.slug == 'edtrac_autoreg':
        return
    script = progress.script
    try:
        session = ScriptSession.objects.filter(
            script=progress.script,
            connection=connection,
            end_time=None
        ).latest('start_time')
    except ScriptSession.DoesNotExist:
        return
    role_poll = script.steps.get(poll__name="edtrac_role").poll
    role = None
    best_response = find_best_response(session, role_poll)
    if best_response:
        role = best_response
    group = None
    if role:
        logger.info('Role: %s' % role)

    if role:
        group = match_group_response(session, role, role_poll)

        logger.info('Identified group: %s' % group.name)

        skipsteps = {
            'edtrac_class': ['Teachers'],
            'edtrac_gender': ['Head Teachers'],
            'edtrac_subcounty': ['Teachers', 'Head Teachers', 'SMC', 'GEM'],
            'edtrac_school': ['Teachers', 'Head Teachers', 'SMC']
        }
        skipped = True
        while group and skipped:
            skipped = False
            for step_name, roles in skipsteps.items():
                if (
                    progress.step.poll
                    and progress.step.poll.name == step_name
                    and group.name not in roles
                ):

                    logger.info(
                        'SKIPPED! %s -> %s:' % (
                            step_name,
                            progress.step.poll.question
                        )
                    )

                    skipped = True
                    progress.step = progress.script.steps.get(
                        order=progress.step.order + 1
                    )
                    progress.save()
                    break


def edtrac_attendance_script_transition(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
    if not progress.script.slug in [
        'edtrac_p3_teachers_weekly',
        'edtrac_p6_teachers_weekly'
    ]:
        return
    script = progress.script
    try:
        ScriptSession.objects.filter(
            script=script,
            connection=connection,
            end_time=None
        ).latest('start_time')
    except ScriptSession.DoesNotExist:
        return
    grade = connection.contact.emisreporter.grade
    if not grade:
        if progress.last_step():
            progress.giveup()
            return
        progress.step = progress.script.steps.get(
            order=progress.step.order + 1
        )
        progress.save()

    skipsteps = {
        'edtrac_boysp3_attendance': ['P3'],
        'edtrac_boysp6_attendance': ['P6'],
        'edtrac_girlsp3_attendance': ['P3'],
        'edtrac_girlsp6_attendance': ['P6'],
        'edtrac_p3curriculum_progress': ['P3'],
    }
    skipped = True
    while grade and skipped:
        skipped = False
        for step_name, grades in skipsteps.items():
            if (
                progress.step.poll
                and progress.step.poll.name == step_name
                and not grade in grades
            ):
                skipped = True
                if progress.last_step():
                    progress.giveup()
                    return
                progress.step = progress.script.steps.get(
                    order=progress.step.order + 1
                )
                progress.save()
                break


def edtrac_scriptrun_schedule(**kwargs):
    progress = kwargs['sender']
    step = kwargs['step']
    if progress.script.slug == 'edtrac_autoreg':
        return
    script = progress.script
    date = datetime.datetime.now().date()
    if step == 0:
        s, c = ScriptSchedule.objects.get_or_create(
            script=script,
            date__contains=date
        )


def send_alert_for_expired_script(script, connection):
    if not all_steps_answered(script):
        if script.slug in [
            'edtrac_p3_teachers_weekly',
            'edtrac_p6_teachers_weekly',
            'edtrac_smc_weekly'
        ]:
            message_string = 'Thank you for participating. Remember to '
            'answer all your questions next Thursday.'
            Message.mass_text(message_string, [connection])


def all_steps_answered(script):
    this_thursday = _this_thursday().date()
    week_start = dateutils.increment(this_thursday, days=-6)
    current_week = append_time_to_week_date(this_thursday, week_start)
    for step in script.steps.all():
        if not Response.objects.filter(
            poll=step.poll,
            date__range=current_week,
            has_errors=False
        ).exists():
            return False
    return True


def get_message_string(atttd_diff, emisreporter_grade, keys, progress):
    if (None, '') in atttd_diff.values():
        return None
    return None

    if progress.script.slug == 'edtrac_head_teachers_weekly':
        return "Thank you, attendance for male teacher have been %s by %s "
        "percent Attendance for female teachers have been %s by %s "
        "percent" % (
            atttd_diff['edtrac_m_teachers_attendance'][1],
            atttd_diff['edtrac_m_teachers_attendance'][0],
            atttd_diff['edtrac_f_teachers_attendance'][1],
            atttd_diff['edtrac_m_teachers_attendance'][0]
        )

    return "Thank you %s Teacher, Attendance for boys have been %s by %s "
    "percent. Attendance for girls have been %s by %spercent" % (
        emisreporter_grade,
        atttd_diff[keys[emisreporter_grade][0]][1],
        atttd_diff[keys[emisreporter_grade][0]][0],
        atttd_diff[keys[emisreporter_grade][1]][1],
        atttd_diff[keys[emisreporter_grade][1]][0]
    )


def send_feedback_on_complete(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
    message_string = None
    if (
        progress.script.slug not in [
            'edtrac_head_teachers_weekly',
            'edtrac_smc_weekly',
            'edtrac_p3_teachers_weekly',
            'edtrac_p6_teachers_weekly'
        ]
    ):
        return
    if not all_steps_answered(progress.script):
        send_alert_for_expired_script(progress.script, connection)
        return
    keys = {'p3': ['edtrac_boysp3_attendance', 'edtrac_girlsp3_attendance'],
            'p6': ['edtrac_boysp6_attendance', 'edtrac_girlsp6_attendance']}
    if progress.script.slug in [
        'edtrac_p3_teachers_weekly',
        'edtrac_p6_teachers_weekly',
        'edtrac_head_teachers_weekly'
    ]:
        atttd_diff = calculate_attendance_difference(connection, progress)
        if not connection.contact.emisreporter.grade is None:
            emisreporter_grade = connection.contact.emisreporter.grade.lower()
            message_string = get_message_string(
                atttd_diff,
                emisreporter_grade,
                keys,
                progress
            )
    if progress.script.slug == 'edtrac_smc_weekly':
        message_string = "Thank you for your report. Please continue to visit"
        "your school and report on what is happening."
    if message_string is not None:
        Message.mass_text(message_string, [connection])


def schedule_script_now(grp='all', slug=''):
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

    logger.info("Scheduling the %s script at %s \n " % (now_script.slug, datetime.datetime.now()))
    for reporter in reporters:
        if reporter.default_connection and reporter.groups.count() > 0:
            _schedule_script_now(reporter.groups.all()[0], reporter.default_connection, slug, ['Teachers', 'Head Teachers', 'SMC', 'GEM'])

    #script = Script.objects.get(slug=slug)
    #logger.info("Scheduling the %s script at %s \n " % (script.slug, datetime.datetime.now()))
    #schedule_script_at(script, datetime.datetime.now())

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

script_progress_was_completed.connect(edtrac_autoreg, weak=False)
script_progress_was_completed.connect(edtrac_reschedule_script, weak=False)
script_progress.connect(edtrac_autoreg_transition, weak=False)
script_progress.connect(edtrac_attendance_script_transition, weak=False)
