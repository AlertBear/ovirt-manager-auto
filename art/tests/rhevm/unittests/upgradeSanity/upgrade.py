'''
Sanity testing of upgrade.
'''

import logging
from pprint import pformat

from art.unittest_lib import BaseTestCase as TestCase
from utilities.rhevm_tools.base import Setup
from utilities.rhevm_tools.setup import SetupUtility

import config as cfg

LOGGER = logging.getLogger(__name__)


class UpgradeSanityUpgrade(TestCase):
    """ Perform the upgrade """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        cls.machine = Setup(cfg.VDC,
                            cfg.HOSTS_USER,
                            cfg.VDC_PASSWORD,
                            dbpassw=cfg.PGPASS,
                            conf=cfg.VARS)
        cls.ut = SetupUtility(cls.machine)
        with cls.ut.setup.ssh as ssh:
            _, tempfile, _ = ssh.runCmd(['mktemp'])
            cls.answerfile = tempfile.rstrip('\n')
        LOGGER.debug("setUpClass: verify engine running")

    @classmethod
    def tearDownClass(cls):
        LOGGER.debug("tearDownClass: verify engine running")
        with cls.ut.setup.ssh as ssh:
            ssh.runCmd(['rm', '-f', cls.answerfile])

    def create_answer_file(self):
        params = self.ut.setup.getInstallParams('__default__',
                                                cfg.ANSWERS)
        self.ut.setup.fillAnswerFile(self.answerfile, **params)
        LOGGER.info("%s: install setup with %s", cfg.VDC, pformat(params))

    def test_upgrade(self):
        """ Perform the upgrade of the setup """
        self.machine.yum(cfg.SETUP_PACKAGE, 'update')
        self.create_answer_file()
        self.ut(config_append=self.answerfile)
        self.ut.testInstallation()
