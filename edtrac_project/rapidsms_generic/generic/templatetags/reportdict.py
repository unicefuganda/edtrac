from django import template

register = template.Library()

@register.filter
def reportdict(input, property):
    if property in input:
        if input[property]:
            return input[property]

    return 0

