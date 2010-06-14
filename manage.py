#!/usr/bin/env python

import sys, os
from django.core.management import execute_manager

# use a default settings module if none was specified on the command line
DEFAULT_SETTINGS = 'settings'
settings_specified = any([arg.startswith('--settings=') for arg in sys.argv])
if not settings_specified and len(sys.argv) >= 2:
    print "NOTICE: using default settings module '%s'" % DEFAULT_SETTINGS
    sys.argv.append('--settings=%s' % DEFAULT_SETTINGS)

"""
This is basically a clone of the rapidsms runner, but it lives here because 
we will do some automatic editing of the python path in order to avoid 
sym-linking all the various dependencies that come in as submodules through
this project.
"""

if __name__ == "__main__":
    project_root = os.path.abspath(
        os.path.dirname(__file__))

    for dir in ["lib", "apps"]:
        path = os.path.join(project_root, dir)
        sys.path.insert(0, path)

    sys.path.insert(0, project_root)

    import settings
    execute_manager(settings)
