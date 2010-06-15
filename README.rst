This module provides an interactive form builder for RapidSMS.

Documentation can be found at:
  http://nyaruka.github.com/rapidsms-xforms-builder

Getting started
================

  % git submodule init
  % git submodule update
  % cd submodules/rapidsms
  % git submodule init
  % git submodule update
  % cd ../..
  % ./manage.py syncdb
  % ./manage.py runserver


Building Docs
=============

  % cd docs
  % make html


Updating GitHub Docs
====================

We use some modified paver scripts fromthe github-tools package to manage uploading our built docs to github.

  % easy_install github-tools[template]
  % rm -rf docs/_build
  % paver gh_pages_build gh_pages_update -m "update github docs"
