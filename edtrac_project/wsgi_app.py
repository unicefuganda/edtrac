# wsgi_app.py
import sys, os

filedir = os.path.dirname(__file__)
sys.path.append(os.path.join(filedir))

from django.core.handlers.wsgi import WSGIHandler

application = WSGIHandler()
import djcelery
djcelery.setup_loader()
