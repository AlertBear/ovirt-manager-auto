"""
Here you can implement your test cases. you also can add another modules into
this folder.
"""

from concurrent.futures import ThreadPoolExecutor
import logging
from nose.tools import istest
from unittest2 import TestCase, skipIf

from art.rhevm_api.utils.test_utils import get_api
import art.test_handler.exceptions as exceptions
import config

logger = logging.getLogger(__name__)
VM_API = get_api('vms', 'vm')

SKIP_THAT_TEST = True


def function_that_does_nothing():
    """
    This function does nothing
    """


def function_that_returns_a(a):
    """
    This function returns parameter a
    """
    return a


def setup_module():
    "setup module"


def teardown_module():
    "teardown module"


class PositiveTestCase(TestCase):
    """
    This is positive test case with several actions
    """
    __test__ = True  # nose.loader will collect it
    my_variable = 'var'

    @classmethod
    def setup_class(cls):
        "setup class"
        logger.info("Setting up class %s with class attribute %s",
                    cls.__name__, cls.my_variable)

    @classmethod
    def teardown_class(cls):
        "tear down class"

    @istest
    @skipIf(SKIP_THAT_TEST, "example reasons")
    def test_skip(self):
        """
        Tests only if SKIP_THAT_TEST is False
        """
        logger.info("This is statement is False: %s", SKIP_THAT_TEST)

    @istest
    def test_true(self):
        """
        This tests function that returns parameters a
        """
        self.assertTrue(function_that_returns_a, True)
        self.assertFalse(function_that_returns_a, False)

    @istest
    def test_that_fails(self):
        """
        This test will fail
        """
        first = function_that_returns_a(True)
        second = False
        self.assertEqual(first, second, "First %s is not second %s"
                                        % (first, second))

    @istest
    def test_nothing(self):
        """
        This tests nothing
        """
        function_that_does_nothing()

    @istest
    def test_vm_presence(self):
        """
        This function tests that vm from config file exists in rhevm system.
        If not, EntityNotFound is raised by find function.
        """
        VM_API.find(config.VM_NAME)


class ParallelTestCase(TestCase):
    """
    This is test case containing action that does loop in parallel manner
    """
    __test__ = True

    @istest
    def test_number_is_not_three(self):
        """
        This functions tests in a parallel loop that given number isn't 9
        It will fail at the end, cause it goes through numbers 0 to 9
        """

        def check_nine(num):
            """
            If num is nine, raises exception
            If num is five, returns False
            """
            # sleep 3 seconds so it's not that fast
            from time import sleep
            sleep(3)

            logger.info("Checking that %d isn't 9", num)
            if num == 9:
                raise exceptions.RHEVMEntityException("%d isn't 9" % num)
            if num == 5:
                return False
            logger.info("OK, %d isn't 9", num)

        results = list()

        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for num in range(10):
                results.append(executor.submit(check_nine, num))

        for res, index in enumerate(results):
            if res.exception():
                raise res.exception()
            if not res.result():
                logger.warn("Number %d seems like five", index)
