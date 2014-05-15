
"""
File contains base classes for this module.
"""

__test__ = False

import logging
from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
import art.rhevm_api.tests_lib.low_level.vms as llvms
from art.rhevm_api.utils.test_utils import get_api
VM_API = get_api('vm', 'vms')


# Folowing 'try-except' blocks are here because this modules are needed only
# for nose test framework, but you can use this module
# also for another purposes.
try:
    # PGPASS, PREPARE_CONF should move to test conf file, once possible.
    from unittest_conf import (config, PGPASS, REST_API_HOST)

    if not config:
        raise ImportError()
except ImportError:
    #from unittest_conf import config
    config = {}
try:
    from nose.tools import istest
except ImportError:
    def istest(f):
        return f

from utilities.rhevm_tools.base import Setup
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

CONFIG_ELEMENTS = 'elements_conf'
CONFIG_SECTION = 'RHEVM Utilities'
BASE_SNAPSHOT = 'working_snapshot'

VARS = opts[CONFIG_ELEMENTS][CONFIG_SECTION]

from . import ART_CONFIG


def setup_module():
    """
    Build datacenter
    """
    params = ART_CONFIG['PARAMETERS']
    build_setup(config=params, storage=params,
                storage_type=params.get('data_center_type'),
                basename=params.get('basename'))


def teardown_module():
    """
    Clean datacenter
    """
    params = ART_CONFIG['PARAMETERS']
    dc_name = params.get('dc_name', 'datacenter_%s' % params.get('basename'))
    cleanDataCenter(True, dc_name, vdc=params.get('host'),
                    vdc_password=params.get('vdc_password'))

_multiprocess_can_split_ = True


class RHEVMUtilsTestCase(TestCase):
    """
    Base class for test plan. It contains general setUp and tearDown class
    which are suitable for most of the RHEVM utilities
    """
    __test__ = False
    utility = None
    utility_class = None
    snapshot_setup_installed = "installed_setup"
    clear_snap = 'clear_machine'
    _multiprocess_can_split_ = True
    installation = None

    @classmethod
    def setUpClass(cls):
        """
        dispatch setup for the cleanup and setup tests
        """
        cls.installation = ART_CONFIG['PARAMETERS'].get('installation')
        cls.machine = Setup(REST_API_HOST,
                            'root',
                            config['testing_env']['host_pass'],
                            dbpassw=PGPASS,
                            conf=VARS)
        if cls.utility in ['setup', 'cleanup']:
            cls.c = config[cls.utility]
            logger.info("DEBUG: cls.c %s", cls.c)
            if cls.installation != 'true' and cls.utility == 'setup':
                cls.machine.clean(config)

    @classmethod
    def tearDownClass(cls):
        """
        Remove all snapshots and release the machine
        """
        if cls.installation == 'true' and cls.utility in ['setup', 'cleanup']:
            try:
                if llvms.checkVmState(True, cls.utility, 'up'):
                    llvms.stopVm(True, cls.utility)
                llvms.restoreSnapshot(True, cls.utility, BASE_SNAPSHOT,
                                      ensure_vm_down=True)
            finally:
                llvms.waitForVMState(cls.utility, state='down')

    def setUp(self):
        """
        Fetch utility instance for the test-case
        """
        if self.installation == 'true':
            if self.utility in ['setup', 'cleanup']:
                if self.utility == 'setup':
                    self.snap = self.clear_snap
                else:
                    self.snap = self.snapshot_setup_installed
                llvms.addSnapshot(True, self.utility, self.snap, True)
        else:
            self.ut = self.utility_class(self.machine)

    def tearDown(self):
        """
        Discard changes which were made by a test-case
        """
        if self.installation == 'true':
            if self.utility in ['setup', 'cleanup']:
                llvms.restoreSnapshot(True, self.utility, self.snap,
                                      ensure_vm_down=True)
        else:
            if self.utility == 'cleanup':
                self.machine.install(config)
