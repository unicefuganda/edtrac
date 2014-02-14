"""A set of request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.
"""
from django.conf import settings

def map_params(request):
    """
    a context processor that passes all the pertinent map parameters to all templates.
    """
    return {
        'colors':getattr(settings,'CATEGORY_COLORS',[]),
        'min_lat':getattr(settings,'MIN_LAT',0.0),
        'max_lat':getattr(settings,'MAX_LAT',0.0),
        'min_lon':getattr(settings,'MIN_LON',0.0),
        'max_lon':getattr(settings,'MAX_LON',0.0),        
    }
