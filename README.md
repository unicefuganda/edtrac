RapidSMS Education Monitoring Information System (RapidSMS-EMIS)
================================================================
The school monitoring system is a mobile-phone based data collection
system using RapidSMS that collects data about schools from school
administrators and people who work closely with schools. Head teachers and
other administrators who work closely with the schools send data into the
system using their mobile phones based on a proposed schedule for data
collection. Data is sent into the system on a regular basis like weekly
for pupil attendance, monthly for reports on child abuse and termly for
capitation grants made to the schools. Other data that can be collected
by the education monitoring system include data on teacher attendance,
presense of amenities such as hygienic facilities at schools.

Technically speaking, RapidSMS-EMIS leverages the work of rapidsms-script
(github.com/daveycrockett/rapidsms-script/) to provide an easy system
for automated conversation-like communication between the rapidsms-emis
application, teachers and other education specialists and administrators.

Reports that are gathered include:
 - Teacher and student attendance
 - Classroom and latrine use
 - Cases of abuse

Requirements
------------
 - Python 2.7 (www.python.org/download/) : On linux machines, you can usually use your system's package manager to perform the installation
 - PostgreSQL
 - All other python libraries will be installed as part of the setup and configuration process
 - Some sort of SMS Connectivity, via an HTTP gateway.  By default,
   Rapidsms-EMIS comes configured to work with a two-way clickatell number
   (see http://www.clickatell.com/downloads/http/Clickatell_HTTP.pdf and
   http://www.clickatell.com/downloads/Clickatell_two-way_technical_guide.pdf).
   Ideally, you want to obtain a local short code in your country
   of operation, or configure Rapidsms-EMIS to use a GSM modem (see
   http://docs.rapidsms.org for more information on how to do this).


Installation
------------

##Git

        git clone https://github.com/unicefuganda/edtrac

        cd edtrac

        git submodule init

        git submodule sync

        git submodule update

        mkvirtualenv edtrac

        pip install -r requirements.pip

        cd edtrac_project

        python manage.py syncdb --noinput

        python manage.py migrate

        python manage.py initialize_database

        python manage.py runserver

##Settings

Set the environment variable `$DJANGO_SETTINGS_FILE` to e.g. `settings.local`.


Continuous Integration
----------------------

[![build status][build-status]](https://travis-ci.org/unicefuganda/edtrac)
