#! /bin/bash

echo "Synchronizing database ............... "
python manage.py syncdb --noinput

echo "Running migrations ................... "
python manage.py migrate --database=test_edtrac

echo "Running tests ........................ "
python manage.py test education.test
