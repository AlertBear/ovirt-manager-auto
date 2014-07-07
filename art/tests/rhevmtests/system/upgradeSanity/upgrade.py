'''
Sanity testing of upgrade.
'''

import logging
from pprint import pformat

from art.unittest_lib import CoreSystemTest as TestCase
from utilities.rhevm_tools.base import Setup
from utilities.rhevm_tools.setup import SetupUtility

from art.unittest_lib import attr

from rhevmtests.system.upgradeSanity import config

LOGGER = logging.getLogger(__name__)


@attr(tier=1)
class UpgradeSanityUpgrade(TestCase):
    """ Perform the upgrade """
    __test__ = True

    @classmethod
    def setUpClass(cls):
        cls.machine = Setup(config.VDC,
                            config.HOSTS_USER,
                            config.VDC_PASSWORD,
                            dbpassw=config.PGPASS,
                            conf=config.VARS)
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
                                                config.ANSWERS)
        self.ut.setup.fillAnswerFile(self.answerfile, **params)
        LOGGER.info("%s: install setup with %s", config.VDC, pformat(params))

    def test_upgrade(self):
        """ Perform the upgrade of the setup """
        self.machine.yum(config.SETUP_PACKAGE, 'update')
        self.create_answer_file()
        self.ut(config_append=self.answerfile)
        self.ut.testInstallation()
