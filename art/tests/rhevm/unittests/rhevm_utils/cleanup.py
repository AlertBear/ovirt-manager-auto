"""
    rhevm cleanup module
"""

from rhevm_utils.base import RHEVMUtilsTestCase, istest
from utilities.rhevm_tools.cleanup import CleanUpUtility
import os
import logging
from unittest_conf import config, REST_API_HOST
logger = logging.getLogger(__name__)

NAME = 'cleanup'
host = REST_API_HOST

_multiprocess_can_split_ = True


class CleanUpTestCase(RHEVMUtilsTestCase):
    """
        rhevm cleanup test cases
    """

    __test__ = True
    utility = NAME
    utility_class = CleanUpUtility
    _multiprocess_can_split_ = True

    def create_answer_file(self):
        ans = os.path.join('/tmp', 'cleanup_answer_file')
        params = self.ut.setup.getInstallParams('__default__',
                                                config['CLEANUP_ANSWERS'])
        self.ut.setup.fillAnswerFile(ans, **params)
        logger.info("%s: clean engine with %s", host, params)

    @istest
    def cleanUp(self):
        """ clean_Up """
        self.create_answer_file()
        self.ut(config_append=self.c['cleanup_answer_file'])
        self.ut.autoTest()

    @istest
    def generatingAnswerFile(self):
        """ generating_Answer_File """
        self.create_answer_file()
        self.ut(config_append=self.c['cleanup_answer_file'],
                generate_answer=self.c['new_cleanup_ans_file'])
        self.ut.testGenerateAnswerFile()
