#!/bin/sh

pip install django-debug-toolbar

cd ..
python setup.py develop

cd proj
python manage.py test rapidsms_xforms --noinput


