'''
Created on May 12, 2014

@author: ncredi
'''

import logging

from nose.tools import istest
from automation_unittests.verify_results import VerifyUnittestResults


logger = logging.getLogger(__name__)


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    @istest
    def verify(self):
        self.assert_expected_results(1, 0, 8, 0)
