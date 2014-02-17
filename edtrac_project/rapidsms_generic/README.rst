Buried in here we have a few goodies:

Generic Dashboard
=================
* a generic rapidsms 'dashboard' which can pull in any other django url-ized view into a chunk of the dashboard (a 'module') (ModuleForm)

Generic Tables
=================
Given any queryset, generic tables can:
* provide easy styling of rows
* cascade filters (FilterForm)
* register arbitrary actions (ActionForm)
* filtering by date
* sorting

TODO: clean up and break this out into sub-apps, upgrade to Django 1.3 class-based views

