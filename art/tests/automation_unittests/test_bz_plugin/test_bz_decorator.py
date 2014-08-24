'''
Created on Aug 20, 2014

@author: ncredi
'''

import logging
from bugzilla.bug import _Bug

from nose.tools import istest
from art.test_handler.plmanagement.plugins.bz_plugin import (
    BugNotFound,
    INFO_TAGS
)
from art.test_handler.settings import initPlmanager
from art.test_handler.tools import bz as bzd  # pylint: disable=E0611

from art.unittest_lib import BaseTestCase as TestCase
from automation_unittests.verify_results import VerifyUnittestResults


logger = logging.getLogger(__name__)


class TestCaseBzPlugin(TestCase):

    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info('************** setup class **************')

    @classmethod
    def teardown_class(cls):
        logger.info('************** teardown class **************')

    def setUp(self):
        logger.info('************** setup test **************')

    def tearDown(self):
        logger.info('************** teardown test **************')

    @istest  # should run
    @bzd({'1': {'engine': ['java'], 'version': ['3.5']}})
    def t01(self):
        logger.info('************** NEW BUG not current engine **************')

    @istest  # should skip
    @bzd({'2': {'engine': ['rest'], 'version': ['3.5']}})
    def t02(self):
        logger.info('************** ON QA BUG current engine **************')

    @istest  # should run
    @bzd({'3': {'engine': ['java', 'sdk'], 'version': ['3.4', '3.5']}})
    def t03(self):
        logger.info('*********** ON_QA BUG not current version ***********')

    @istest  # should run
    @bzd({'4': {'engine': ['rest'], 'version': ['3.5']}})
    def t04(self):
        logger.info('************* VERIFIED BUG current engine *************')

    @istest  # should skip
    @bzd({'5': {'engine': None, 'version': ['3.5']}})
    def t05(self):
        logger.info('************* CLOSED BUG in newer version *************')

    @istest  # should run
    @bzd({'5': {'engine': None, 'version': ['3.6.1']}})
    def t06(self):
        logger.info('************** CLOSED BUG **************')

    @istest  # should skip
    @bzd({'6': {'engine': ['rest'], 'version': ['3.5.1']}})
    def t07(self):
        logger.info('************* DUPLICATE BUG points to NEW *************')

    @istest  # should run
    @bzd('7')
    def t08(self):
        logger.info('************** Verify backward compatible **************')

    @istest  # should run
    @bzd({'7': {'engine': None, 'version': None},
          '8': {'engine': None, 'version': None}})
    def t09(self):
        logger.info('**************** Verify multiple bugs ****************')


class VerifyResults(VerifyUnittestResults):

    __test__ = True

    @istest
    def verify(self):
        self.assert_expected_results(6, 0, 3, 0)


class FakeBugs(object):

    def __init__(self):
        self.cache = {}
        import bugzilla
        self.bugzilla = bugzilla.Bugzilla44(url='faceBzUrl')

    def bz(self, bz_id):
        """
        Set all BZs as solved if BZ plugin is not available
        """
        if bz_id == '1':
            bug_dict = {
                "bug_id": 1,
                "product": 'dont care at this point',
                "version": ['3.5'],
                "resolution": '',
                "bug_status": 'NEW',
            }
        elif bz_id == '2':
            bug_dict = {
                "bug_id": 2,
                "product": 'dont care at this point',
                "version": ['3.4', '3.5'],
                "resolution": '',
                "bug_status": 'ON_QA',
                "target_release": None,
            }
        elif bz_id == '3':
            bug_dict = {
                "bug_id": 3,
                "product": 'dont care at this point',
                "version": ['3.4', '3.5'],
                "bug_status": 'ON_QA',
                "resolution": '',
                "target_release": ['3.6'],
            }
        elif bz_id == '4':
            bug_dict = {
                "bug_id": 4,
                "product": 'dont care at this point',
                "version": ['3.5'],
                "bug_status": 'VERIFIED',
                "resolution": 'CURRENTRELEASE',
                "target_release": ['3.5'],
            }
        elif bz_id == '5':
            bug_dict = {
                "bug_id": 5,
                "product": 'dont care at this point',
                "version": ['3.5'],
                "bug_status": 'CLOSED',
                "resolution": '',
                "target_release": ['3.6'],
            }
        elif bz_id == '6':
            bug_dict = {
                "bug_id": 6,
                "product": 'dont care at this point',
                "version": ['3.5.1'],
                "bug_status": 'CLOSED',
                "resolution": 'DUPLICATE',
                "dupe_of": '1',
                "target_release": None,
            }
        elif bz_id == '7' or bz_id == '8':
            bug_dict = {
                "bug_id": 7,
                "product": 'dont care at this point',
                "version": ['1.0'],
                "bug_status": 'CLOSED',
                "resolution": '',
                "target_release": ['1.0'],
            }
        else:
            raise BugNotFound(bz_id)

        bug_dict["assigned_to"] = 'dontcare@redhat.com'
        bug_dict["summary"] = 'no summary'

        bug = _Bug(dict=bug_dict, autorefresh=False, bugzilla=self.bugzilla)

        msg = "BUG<%s> info: %s" % (bz_id, dict((x, getattr(bug, x)) for x in
                                    INFO_TAGS if hasattr(bug, x)))
        logger.info(msg)
        return bug


plmanager = initPlmanager()
BZ_PLUGIN = [pl for pl in plmanager.application_liteners
             if pl.name == "Bugzilla"][0]
BZ_PLUGIN.bz = FakeBugs().bz
