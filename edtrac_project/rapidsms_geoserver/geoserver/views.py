from django.shortcuts import render_to_response
import random
def home(request):


    return render_to_response('geoserver/index.html')
