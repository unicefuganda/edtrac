#!/bin/sh

pip install django-debug-toolbar

cd ..
python setup.py develop

cd test-runner
python manage.py test rapidsms_xforms --noinput


