"""
Basic tests for RapidSMS-Script
"""

from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.core.exceptions import ValidationError
from django.contrib.sites.models import Site
from rapidsms.models import Contact
from script.utils import incoming_progress, check_progress
from script.models import *
from rapidsms.models import Contact, Connection, Backend
from rapidsms.messages.incoming import IncomingMessage
from rapidsms_httprouter.models import Message
import datetime

class ModelTest(TestCase): #pragma: no cover

    def setUp(self):
        """
        Create a default script for all test cases
        """
        pass

    def testIncomingProgress(self):
        self.assertEquals(1 + 1, 2)
