import datetime
from datetime import date

#All term schedulled polls are computed based on these dates
#these dates are necessary for the system to work properly and
#should be entered every beginning of year. See _next_term_question_date()
FIRST_TERM_BEGINS =  datetime.datetime(2014, 2, 3)
SECOND_TERM_BEGINS =  datetime.datetime(2014, 5, 19)
THIRD_TERM_BEGINS =  datetime.datetime(2014, 9, 8)

# Current term start and end dates
SCHOOL_TERM_START = FIRST_TERM_BEGINS
SCHOOL_TERM_END   = datetime.datetime(2014, 4, 25)

SCHOOL_HOLIDAYS=[
    # (start_of_holiday_datetime, end_of_holidate_datetime),
    # (start_of_holiday2_datetime...),
    # (,),
    # ...
    #start of year holiday season
    (datetime.datetime(2014, 1, 1), datetime.datetime(2014, 2, 2)),

    #public holidays
    (datetime.datetime(2014, 1, 26), '1d'), #Liberation day
    (datetime.datetime(2014, 3, 8), '1d'), #Women's day
    (datetime.datetime(2014, 4, 18), datetime.datetime(2014, 4, 21)), #Easter holiday
    (datetime.datetime(2014, 5, 1), '1d'), #Labour day
    (datetime.datetime(2014, 6, 3), '1d'), #Uganda Martyrs' Day
    (datetime.datetime(2014, 6, 9), '1d'), #Heroes' day
    (datetime.datetime(2014, 10, 9), '1d'), #Independence Day
    (datetime.datetime(2014, 12, 6), datetime.datetime(2014, 12, 31)), #Xmas holiday

    #TBD
    (datetime.datetime(2014, 8, 8), '1d'), #Idd El Fitri
    (datetime.datetime(2014, 10, 15), '1d'), #Idd Adhua
]

WEEKLY = [
    # Term one
    date(2014, 2, 14), # First poll delayed by a day.
    date(2014, 2, 20),
    date(2014, 2, 27),
    date(2014, 3, 6),
    date(2014, 3, 13),
    date(2014, 3, 20),
    date(2014, 3, 27),
    date(2014, 4, 3),
    date(2014, 4, 10),
    date(2014, 4, 17),
    date(2014, 4, 24),

    # Term two
    date(2014, 5, 22),
    date(2014, 5, 29),
    date(2014, 6, 5),
    date(2014, 6, 12),
    date(2014, 6, 19),
    date(2014, 6, 26),
    date(2014, 7, 3),
    date(2014, 7, 10),
    date(2014, 7, 17),
    date(2014, 7, 24),
    date(2014, 7, 31),
    date(2014, 8, 7),

    # Term three
    date(2014, 9, 11),
    date(2014, 9, 18),
    date(2014, 9, 25),
    date(2014, 10, 2),
    #date(2014, 10, 9), Independence Day
    date(2014, 10, 10),
    date(2014, 10, 16),
    date(2014, 10, 23),
    date(2014, 10, 30),
    date(2014, 11, 6),
    date(2014, 11, 13),
    date(2014, 11, 20),
    date(2014, 11, 27),
    date(2014, 12, 4),
]

VIOLENCE = [
    # Term one
    date(2014, 2, 24),
    date(2014, 3, 24),
    date(2014, 4, 22),

    # Term two
    date(2014, 5, 26),
    date(2014, 6, 23),
    date(2014, 7, 28),

    # Term three
    date(2014, 9, 29),
    date(2014, 10, 27),
    date(2014, 11, 24),
]

HEAD_MEALS = [
    # Term one
    date(2014, 2, 21),
    date(2014, 3, 28),
    date(2014, 4, 25),

    # Term two
    date(2014, 5, 23),
    date(2014, 6, 27),
    date(2014, 7, 25),

    # Term three
    date(2014, 9, 26),
    date(2014, 10, 24),
    date(2014, 11, 28),
]

SMC_MEALS = [
    # Term one
    date(2014, 2, 24),
    date(2014, 3, 24),
    date(2014, 4, 22),

    # Term two
    date(2014, 5, 26),
    date(2014, 6, 23),
    date(2014, 7, 28),

    # Term three
    date(2014, 9, 29),
    date(2014, 10, 27),
    date(2014, 11, 24),
]

GEM = [
    # Term one
    date(2014, 2, 21),
    date(2014, 3, 28),
    date(2014, 4, 25),

    # Term two
    date(2014, 5, 23),
    date(2014, 6, 27),
    date(2014, 7, 25),

    # Term three
    date(2014, 9, 26),
    date(2014, 10, 24),
    date(2014, 11, 28),
]

TEACHER_DEPLOYMENT = [
    date(2014, 2, 21),
    date(2014, 6, 6),
    date(2014, 10, 3),
]

P6_ENROLLMENT = [
    date(2014, 2, 26),
    date(2014, 5, 28),
    date(2014, 9, 17),
]

P3_ENROLLMENT = [
    date(2014, 2, 28),
    date(2014, 5, 30),
    date(2014, 9, 19),
]

ENROLLMENT = [
    date(2014, 3, 4),
    date(2014, 6, 11),
    date(2014, 10, 7),
]

UPE_GRANT = [
    date(2014, 3, 5),
    date(2014, 6, 25),
    date(2014, 10, 8),
]

SMC_MONITORING = [
    date(2014, 4, 23),
    date(2014, 8, 1),
    date(2014, 11, 26),
]

MONITORING = [
    date(2014, 4, 23),
    date(2014, 8, 1),
    date(2014, 11, 26),
]

WATER_SOURCE = [
    date(2014, 3, 19),
    date(2014, 6, 17),
    date(2014, 10, 13),
]

FUNCTIONAL_WATER_SOURCE = [
    date(2014, 3, 21),
    date(2014, 6, 18),
    date(2014, 10, 14),
]

POLL_DATES = {
    'edtrac_head_teachers_weekly':                  WEEKLY,
    'edtrac_upe_grant_headteacher_termly':          UPE_GRANT,
    'edtrac_teacher_deployment_headteacher_termly': TEACHER_DEPLOYMENT,
    'edtrac_script_water_source':                   WATER_SOURCE,
    'edtrac_script_functional_water_source':        FUNCTIONAL_WATER_SOURCE,
    'edtrac_p6_enrollment_headteacher_termly':      P6_ENROLLMENT,
    'edtrac_headteacher_violence_monthly':          VIOLENCE,
    'edtrac_head_teachers_monthly':                 TEACHER_DEPLOYMENT,
    'edtrac_p3_enrollment_headteacher_termly':      P3_ENROLLMENT,
    'edtrac_headteacher_meals_monthly':             HEAD_MEALS,
    'edtrac_head_teachers_midterm':                 MONITORING,
    'edtrac_school_enrollment_termly':              ENROLLMENT,

    'edtrac_smc_weekly':                            WEEKLY,
    'edtrac_smc_termly':                            SMC_MONITORING,
    'edtrac_smc_monthly':                           SMC_MEALS,

    'edtrac_p3_teachers_weekly':                    WEEKLY,

    'edtrac_p6_teachers_weekly':                    WEEKLY,

    'edtrac_gem_monthly':                           GEM,
}

GROUPS = {'Teachers' :  [],
          'Head Teachers' : ['edtrac_head_teachers_weekly',
                             'edtrac_upe_grant_headteacher_termly',
                             'edtrac_teacher_deployment_headteacher_termly',
                             'edtrac_script_water_source',
                             'edtrac_script_functional_water_source',
                             'edtrac_p6_enrollment_headteacher_termly',
                             'edtrac_headteacher_violence_monthly',
                             'edtrac_head_teachers_monthly',
                             'edtrac_p3_enrollment_headteacher_termly',
                             'edtrac_school_enrollment_termly',
                             'edtrac_head_teachers_midterm',
                             'edtrac_headteacher_meals_monthly'],
          'SMC' :           ['edtrac_smc_weekly',
                             'edtrac_smc_termly',
                             'edtrac_smc_monthly'],
          'GEM':            ['edtrac_gem_monthly'],
          'p3' :            ['edtrac_p3_teachers_weekly'],
          'p6' :            ['edtrac_p6_teachers_weekly']}
