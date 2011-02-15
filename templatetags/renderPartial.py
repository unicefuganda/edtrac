from django import template
from django.template.loader import get_template
from django.template.context import Context

def renders(values, partial):
    partial = get_template('contact/partials/'+partial+'.html')
    data = Context({"contacts": values})
    return partial.render(data)

register = template.Library()
register.filter('renders', renders)