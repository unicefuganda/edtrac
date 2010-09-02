"""
Test cases for 
"""

from django.test import TestCase

class BasicPatternTemplateTest(TestCase):
    def test_basic_pattern_template(self):
        from .models import BASIC_PATTERN_TEMPLATE

        testregex = (BASIC_PATTERN_TEMPLATE % '|'.join(['my','three','keywords']))
        
        import re
        rx = re.compile(testregex)
        self.failIf(not rx.search('my'))
        self.failIf(not rx.search(' my'))
        self.failIf(not rx.search('my '))
        self.failIf(not rx.search('three'))
        self.failIf(not rx.search('keywords'))
        self.failIf(not rx.search('my1'))
        self.failIf(not rx.search('my1. some more text'))
        self.failIf(rx.search('some text and then i say my'))
        self.failIf(rx.search('some text and then i say my '))
        self.failIf(rx.search('myopic'))
        
        
        
    
    