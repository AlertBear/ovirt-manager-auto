"""
This module is responsible to produce logs which our automation engineers
are used to see (:

NOTE: this module will be removed once we ensure proper logging our tests
independently on test runner.
"""
import re
import logging
import pytest


__all__ = [
    "pytest_artconf_ready",
]


DELIMITER = "=" * 80
logger = logging.getLogger('art.logging')


def align_description(doc):
    if doc:
        return re.sub('\s+', ' ', doc).strip()


class ARTLogging(object):
    """
    Collection of pytest item related hooks.
    According these we can generate logs similar to ART logs.
    """

    def __init__(self):
        super(ARTLogging, self).__init__()
        self.itnum = 0
        self.last_test_class = None

    @staticmethod
    def get_test_name(item):
        # Get name of test
        name = item.name
        # Add class name in case test is method
        if item.cls:
            name = "%s.%s" % (item.cls.__name__, name)
        # Add module name
        name = "%s.%s" % (item.module.__name__, name)
        return name

    @staticmethod
    def get_desctription(item):
        """
        Get description of test, doc string
        """
        return align_description(item.function.__doc__)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        """
        :param item: test item to perform setup for
        :type item: instance of pytest.Item
        """
        logger.info(DELIMITER)
        # Print the test class description only once and at beginning.
        if item.cls:
            # Is it new class ?
            if self.last_test_class != item.cls.__name__:
                self.last_test_class = item.cls.__name__
                logger.info(
                    "Test class description: %s",
                    align_description(item.cls.__doc__),
                )
        logger.info("SETUP %s", item)
        yield
        logger.info(DELIMITER)

    def pytest_runtest_call(self, item):
        """
        :param item: test item to perform call for
        :type item: instance of pytest.Item
        """
        self.itnum += 1
        logger.info("Test Name: %s", self.get_test_name(item))
        logger.info("Test Description: %s", self.get_desctription(item))
        logger.info("Iteration number: %s", self.itnum)

    def pytest_report_teststatus(self, report):
        if report.when == "call":
            logger.info("Status: %s", report.outcome)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item, nextitem):
        """
        :param item: test item to perform teardown for
        :type item: instance of pytest.Item
        """
        logger.info(DELIMITER)
        logger.info("TEARDOWN %s", item)
        yield

    def pytest_package_setup(self, entry):
        logger.info("PACKAGE SETUP: %s", entry)

    def pytest_package_teardown(self, entry):
        logger.info("PACKAGE TEARDOWN: %s", entry)


def pytest_artconf_ready(config):
    """
    Load the logging plugin into pytest
    """
    config.pluginmanager.register(ARTLogging())
