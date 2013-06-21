#! /bin/bash



psql -c 'create database test_edtrac;' -U postgres

echo "Setting up test database ................... "
python manage.py syncdb --noinput --database=test
python manage.py migrate --database=test

echo "Running tests ........................ "
python manage.py test education.test REUSE_DB=1
