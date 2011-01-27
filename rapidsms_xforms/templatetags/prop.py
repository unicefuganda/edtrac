from django import template

def prop(input, property):
    return input.__dict__[property]
    #return input.fields[property]

register = template.Library()
register.filter('prop', prop)

