#!/bin/sh

../setup.py develop
python manage.py test rapidsms_xforms --noinput


