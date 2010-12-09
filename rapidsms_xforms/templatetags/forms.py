from django.conf import settings
from django.template import Context, Template
from django.template.loader import get_template
from django import template
from django.template.defaultfilters import slugify

register = template.Library()

###################################################
# Renders the layout in a form helper, but without the surrounding
# form tags.
###################################################
@register.filter
def render_layout(form):
    form_html = form.helper.render_layout(form)
    return form_html

