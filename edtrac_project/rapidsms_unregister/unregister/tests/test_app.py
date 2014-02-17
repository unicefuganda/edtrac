# unregister/tests/test_app.py

import unittest

from rapidsms.tests.scripted import TestScript
from unregister.app import App as UnregisterApp


class TestUnregisterApp(TestScript):
    apps = (UnregisterApp,)

    testJoin = """
        256712123456 > quit
        256712123456 < You have just quit.
    """


if __name__ == "__main__":
    unittest.main()
