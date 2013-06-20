#! /bin/bash

echo "Synchronizing database ............... "
#python manage.py syncdb --noinput --database=test

echo "Running migrations ................... "
#python manage.py migrate --database=test

echo "Running tests ........................ "
python manage.py test education.test
