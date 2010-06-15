rapidsms-xforms
===============

This module provides an interactive form builder for RapidSMS that also allows for XForm compliant submissions.

Documentation can be found at:
  http://nyaruka.github.com/rapidsms-xforms-builder

Getting started
---------------

Quick start from a clone.  We don't encourage using the source, instead use the package (forthcoming) but this will get you going in the meantime::

  % git submodule init
  % git submodule update
  % cd submodules/rapidsms
  % git submodule init
  % git submodule update
  % cd ../..
  % ./manage.py syncdb
  % ./manage.py runserver

Building Docs
-------------

rapidsms-xforms has pretty decent documentation.  Please add to it if you find a need.  You build it::

  % cd docs
  % make html


Updating GitHub Docs
--------------------

We use some modified paver scripts fromthe github-tools package to manage uploading our built docs to github::

  % easy_install github-tools[template]
  % paver gh_pages_build gh_pages_update -m "update github docs"
