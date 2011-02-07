from django.template import Library
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = Library()



def paginator_number(contacts,i):
    if i == '.':
        return u'... '
    elif i == contacts.page_num:
        return mark_safe(u'<span class="this-page">%d</span> ' % (i+1))
    else:
        return mark_safe(u'<a href="%s"%s>%d</a> ' % ('', (i == contacts.paginator.num_pages-1 and ' class="end"' or ''), i+1))
paginator_number = register.simple_tag(paginator_number)

def pagination(contacts):
    paginator, page_num = contacts.paginator, contacts.page_num
    ON_EACH_SIDE = 3
    ON_ENDS = 2
    if paginator.num_pages <= 10:

        page_range = range(paginator.num_pages)
    else:
        # Insert "smart" pagination links, so that there are always ON_ENDS
        # links at either end of the list of pages, and there are always
        # ON_EACH_SIDE links at either end of the "current page" link.
        page_range = []
        if page_num > (ON_EACH_SIDE + ON_ENDS):
            page_range.extend(range(0, ON_EACH_SIDE - 1))
            page_range.append('.')
            page_range.extend(range(page_num - ON_EACH_SIDE, page_num + 1))
        else:
            page_range.extend(range(0, page_num + 1))
        if page_num < (paginator.num_pages - ON_EACH_SIDE - ON_ENDS - 1):
            page_range.extend(range(page_num + 1, page_num + ON_EACH_SIDE + 1))
            page_range.append('.')
            page_range.extend(range(paginator.num_pages - ON_ENDS, paginator.num_pages))
        else:
            page_range.extend(range(page_num + 1, paginator.num_pages))
    return {
        'contacts':contacts,
        'page_range':page_range,
    }
pagination = register.inclusion_tag('contact/partials/pagination.html')(pagination)


