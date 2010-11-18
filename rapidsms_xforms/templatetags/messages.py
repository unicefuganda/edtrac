from django import template

# 
# Contains simple filters that may be useful within messages processing.
#

def multiply(input, property):
    return "%.2f" % (float(input) * float(property))

register = template.Library()
register.filter('multiply', multiply)
