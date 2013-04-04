# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

#targets
from django.conf import settings
from education.utils import get_week_count

target = {
    1:1.1,
    2:1.2,
    3:1.3,
    4:2.1,
    5:2.2,
    6:2.3,
    7:3.1,
    8:3.2,
    9:3.3,
    10:4.1,
    11:4.2,
    12:4.3
}


def add_offset_according_to_term_number(target_value):
    term_start= getattr(settings,'SCHOOL_TERM_START')
    first_term_start= getattr(settings,'FIRST_TERM_BEGINS')
    second_term_start= getattr(settings,'SECOND_TERM_BEGINS')
    third_term_start= getattr(settings,'THIRD_TERM_BEGINS')

    if term_start == first_term_start:
        return target_value
    if term_start == second_term_start:
        return target_value+4
    if term_start ==third_term_start:
        return target_value+8

def get_target_value(given_date):
    term_start = getattr(settings,'SCHOOL_TERM_START')
    week_count = get_week_count(term_start,given_date)
    target_value = target[week_count]
    target_value = add_offset_according_to_term_number(target_value)
    return target_value