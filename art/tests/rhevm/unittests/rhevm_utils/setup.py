"""
    rhevm setup module
"""
import os
import logging
from pprint import pformat

from rhevm_utils import base
from utilities.rhevm_tools.setup import SetupUtility
from unittest_conf import config, REST_API_HOST

logger = logging.getLogger(__name__)

NAME = 'setup'
_multiprocess_can_split_ = True

host = REST_API_HOST


class SetupTestCase(base.RHEVMUtilsTestCase):
    """
        rhevm setup test cases
    """
    __test__ = True
    utility = NAME
    utility_class = SetupUtility
    clear_snap = 'clear_machine'
    _multiprocess_can_split_ = True

    def create_answer_file(self):
        ans = os.path.join('/tmp', 'answer_file')
        params = self.ut.setup.getInstallParams('__default__',
                                                config['ANSWERS'])
        self.ut.setup.fillAnswerFile(ans, **params)
        logger.info("%s: install setup with %s", host, pformat(params))

    def test_generating_answer_file(self):
        """ generating_Answer_File """
        self.create_answer_file()
        self.ut(config_append=self.c['answer_file'],
                generate_answer=self.c['new_ans_file'])
        self.ut.testGenerateAnswerFile()
        self.ut.setup.clean(config)

    def test_install_setup(self):
        """ install_Setup """
        self.create_answer_file()
        self.ut(config_append=self.c['answer_file'])
        self.ut.testInstallation()
