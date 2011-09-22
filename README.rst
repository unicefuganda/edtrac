RapidSMS Uganda Common
======================
This module contains some common utilities used across RapidSMS (applications).

Dependecies
===========
Uganda Common reuses code that can be found in. Include the following on your python/django PATH
- rapidsms (mostly needed for custom template tags, this lets you have on-the-fly features such as tabs)
- dango-eav
- rapidsms-generic (common UI elements in the RapidSMS framework e.g. time slider, map renderer, and lots of others)

Code Structure
==============

* templates (a directory)
* cache_manager.py
* context_processors.py
* forms.py
* reports.py
* utils.py


Features
========
Using Uganda common, the following functions can be re-used across your project. This is a piece by piece teardown
analysis of rapidsms-uganda-common and what you can do with it.

The *cache_manager.py*


The *forms.py* module currently has a class that creates a DateRange form.

The *reports.py* module has utilities that  

The *utils.py* python module has the following awesomeness:

* basic datetime computation with functions that will allow you to calendar related output from
python objects (such as model instances), they include:
* previous calendar week
* previous calendar month
* and a number of others (please use the help() function to learn more about the modules, some inline documentation has
been added)
