"""
Here you can implement your test cases. you also can add another modules into
this folder.
"""

import logging
from nose.tools import istest
from unittest import TestCase

import art.test_handler.exceptions as exceptions

LOGGER = logging.getLogger(__name__)

# Some helping function
def function_that_fails(vm_name):
    """
    This function raises exception, that VM doesn't exist
    """
    raise exceptions.VMException("VM %s doesn't exist" % vm_name)


class NegativeTestCase(TestCase):
    """
    Negative test case with one action
    """
    __test__ = True
    vm_name = 'foo'
    # note that this class doesn't have setup and teardown methods

    @istest
    def test_exception(self):
        """
        This function is negative test
        """
        self.assertRaises(exceptions.VMException, function_that_fails,
                          self.vm_name)

