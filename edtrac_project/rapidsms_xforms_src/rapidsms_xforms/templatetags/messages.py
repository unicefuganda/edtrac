from django import template
from django.utils.safestring import mark_safe

# 
# Contains simple filters that may be useful within messages processing.
#

def multiply(input, property):
    """
    Just multiplies two values together.  Surprisingly this isn't possible in normal templates.
    """
    return "%.2f" % (float(input) * float(property))

register = template.Library()
register.filter('multiply', multiply)

def in_base_36(number):
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')
    if number < 0:
        raise ValueError('number must be positive')

    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    base36 = ''
    while number:
        number, i = divmod(number, 36)
        base36 = alphabet[i] + base36

    return base36 or alphabet[0]

def codify(input, property=None):
    """
    Turns a numerical id into something slightly more impressive.  Specifically a 4 letter
    base 36 item with an optional prefix, zero padded.  This will work up to about 1.5M
    entries, at which point it will start skipping to six letters instead up to ~2B, then
    just echo the raw value in base 36.

    IE, if you pass in 3688, this will return 00A8.  If you pass in a prefix of S, then
    the value will be S00A8.
    """
    val = int(input)

    # values that can be represented in 4 letters
    if val <= 1679615:
        based = in_base_36(val)
        based = "0" * (4-len(based)) + based
    # things that are six letters
    elif val <= 2176782335:
        based = in_base_36(val)
        based = "0" * (6-len(based)) + based
    # huge!
    else:
        based = in_base_36(val)

    if property:
        return property + based
    else:
        return based

register.filter('codify', codify)
codify.is_safe = True
