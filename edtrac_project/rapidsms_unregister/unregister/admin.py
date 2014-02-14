# unregister/admin.py

from django.contrib import admin
from .models import Blacklist


admin.site.register(Blacklist)
