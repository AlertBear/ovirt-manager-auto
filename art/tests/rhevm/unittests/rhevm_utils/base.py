
"""
File contains base classes for this module.
"""

__test__ = False

import time
import logging
from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.low_level.vms import addSnapshot, restoreSnapshot
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

from utilities.rhevm_tools import errors
from utilities.rhevm_tools.base import Setup
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)

WAIT_TIMEOUT = 600

CONFIG_ELEMENTS = 'elements_conf'
CONFIG_SECTION = 'RHEVM Utilities'

VARS = opts[CONFIG_ELEMENTS][CONFIG_SECTION]

from . import ART_CONFIG

# TODO:
# create patterns for errors recognition
# also think about moving of message patterns to consts, because it can be
# changed in next versions


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
    cleanDataCenter(True, params.get('storage_name'),
                    vdc=params.get('host'),
                    vdc_password=params.get('vdc_password'))


class SetupManager(object):
    """
    Class which is able to work with setup and perform cleanning action
    NOTE: I guess this will be generalized and moved somewhere else, because
          it is usable for another tasks as well.
    """

    BASE_SNAPSHOT = 'working_snapshot'

    def __init__(self):
        """
        C'tor
        """
        self.maps = {}
        self.setups = {}

    def _waitForEvent(self, event, machine, timeout=None, interval=2):
        if timeout is None:
            timeout = config.get('wait_timeout', WAIT_TIMEOUT)
        start = time.time()
        while True:
            if event():
                break
            if time.time() - start > timeout:
                name = machine.get_name()
                raise errors.WaitForStatusTimeout(timeout, name)
            time.sleep(interval)

    def waitForMachineStatus(self, machine, status, timeout=None, interval=2):
        """
        Wait until machine get specific status
        Parameters:
         * machine - VM object
         * status - name of status or list of acceptable states
         * timeout - timeout in seconds
         * interval - sleep interval between each check in seconds
        """
        def event(machine=machine, status=status):
            machine = VM_API.find(machine.name)
            st = machine.status.get_state()
            return st == status
        self._waitForEvent(event, machine, timeout, interval)

    def waitForAgentIsUp(self, machine, timeout=None, interval=2):
        """
        Wait until agent respond
        Parameters:
         * machine - VM object
         * timeout - timeout in seconds
         * interval - sleep interval between each check in seconds
        """
        def event(machine=machine):
            machine = VM_API.find(machine.name)
            guest_info = machine.get_guest_info()
            return guest_info is not None
        self._waitForEvent(event, machine, timeout, interval)

    def ensureMachineIsDown(self, machine):
        """
        Stop machine and wait for down status
        Parameters:
         * machine - VM object
        """
        machine = self.refreshMachine(machine)
        st = machine.status.get_state()
        if st != 'down':
            machine.stop()
            self.waitForMachineStatus(machine, 'down')

    def popMachine(self, name):
        """
        Return machine for test
        """
        # now it only takes vm_name from config, but it will use pool feature
        # as soon as we will create it.
        vm_name = config[name]['vm_name']
        machine = VM_API.find(vm_name)
        if not machine:
            raise errors.SetupsManagerError("can't find testing machine: %s"
                                            % vm_name)
        self.maps[name] = machine
        return machine

    def releaseMachine(self, name):
        try:
            m = self.maps.pop(name)
            self.waitForMachineStatus(m, 'down')
        except KeyError:
            logger.error("machine wasn't alloceted for test: %s", name)

    def refreshMachine(self, machine):
        """
        Reload machine's data
        Parameters:
         * machine - VM object
        Return: fresh VM object
        """
        name = machine.get_name()
        machine = VM_API.find(name)
        if not machine:
            raise errors.SetupsManagerError("can't find testing machine: %s"
                                            % name)
        return machine

    def createSnapshotWrapper(self, vm_name, snapshot_desc):
        """
        Creates snapshot of machine
        Parameters:
         * vm_name - VM name
         * snapshot_desc - name of snapshot
        """
        rc = addSnapshot(True, vm_name, snapshot_desc, True)
        if not rc:
            raise errors.AddSnapshotFailure("Create snapshot %s from vm %s" %
                                            (snapshot_desc, vm_name))

    def restoreSnapshotWrapper(self, vm_name, snapshot_desc):
        """
        Restores to snapshot
        Parameters:
         * vm_name - VM name
         * snapshot_desc - name of snapshot
        """
        rc = restoreSnapshot(True, vm_name, snapshot_desc, ensure_vm_down=True)
        if not rc:
            raise errors.RestoreSnapshotFailure("Restore snapshot %s for vm %s"
                                                % (snapshot_desc, vm_name))

    def getIp(self, machine):
        """
        Retrieve ip address for machine (needs agent)
        Parameters:
         * machine - VM object
        Return: ip
        """
        machine = self.refreshMachine(machine)
        g = machine.get_guest_info()
        ips = g.get_ips()
        for ip in ips.get_ip():
            ip = ip.get_address()
            if ip:
                return ip
        raise errors.NoIpFoundError(machine.get_name())

    def prepareSetup(self, name):
        machine = self.popMachine(name)
        self.createSnapshotWrapper(machine.name, self.BASE_SNAPSHOT)

    def saveSetup(self, name, point):
        """
        Save machine snapshot
        Parameters:
         * name - machine name
         * point - snapshot description
        """
        machine = self.refreshMachine(self.maps[name])
        self.createSnapshotWrapper(machine.name, point)

    def restoreSetup(self, name, point):
        """
        Restores machine snapshot
        Parameters:
         * name - machine name
         * point - snapshot description
        """
        machine = self.refreshMachine(self.maps[name])
        self.restoreSnapshotWrapper(machine.name, point)

    def dispatchSetup(self, name, ip=None):
        """
        Run Setup class
        Parameters:
         * name - machine name
         * ip - machine IP address
        """
        if not ip:
            machine = self.refreshMachine(self.maps[name])
            if machine.status.get_state() != 'up':
                VM_API.syncAction(machine, 'start', 'true')
                self.waitForMachineStatus(machine, 'up')
            self.waitForAgentIsUp(machine)
            ip = self.getIp(machine)
        return Setup(ip, 'root', config['testing_env']['host_pass'],
                     dbpassw=PGPASS, conf=VARS)

    def releaseSetup(self, name):
        """
        Restore machine snapshot
        Parameters:
         * name - machine name
        """
        try:
            machine = self.refreshMachine(self.maps[name])
            if machine.status.get_state() == 'up':
                VM_API.syncAction(machine, 'stop', 'true')
                self.waitForMachineStatus(machine, 'down')
            self.restoreSnapshotWrapper(machine.name, self.BASE_SNAPSHOT)
        finally:
            self.releaseMachine(name)


_multiprocess_can_split_ = True


class RHEVMUtilsTestCase(TestCase):
    """
    Base class for test plan. It contains general setUp and tearDown class
    which are suitable for most of RHEVM utilities
    """
    __test__ = False
    utility = None
    utility_class = None
    manager = SetupManager()
    snapshot_setup_installed = "installed_setup"
    clear_snap = 'clear_machine'
    _multiprocess_can_split_ = True
    installation = None

    @classmethod
    def setUpClass(cls):
        """
        dispatch setup for cleanup and setup tests
        """
        cls.installation = ART_CONFIG['PARAMETERS'].get('installation')
        if cls.utility in ['setup', 'cleanup']:
            cls.c = config[cls.utility]
            logger.info("DEBUG: cls.c %s", cls.c)
            if cls.installation != 'true':
                if cls.utility == 'setup':
                    machine = cls.manager.dispatchSetup(cls.utility,
                                                        REST_API_HOST)
                    machine.clean(config)

    @classmethod
    def tearDownClass(cls):
        """
        Remove all snapshots, and release machine
        """
        if cls.installation == 'true':
            if cls.utility in ['setup', 'cleanup']:
                cls.manager.releaseSetup(cls.utility)

        if cls.installation != 'true':
            if cls.utility == 'setup':
                machine = cls.manager.dispatchSetup(cls.utility, REST_API_HOST)
                machine.clean(config)

    def setUp(self):
        """
        Fetch instance of utility for test-case
        """
        if self.installation == 'true':
            if self.utility in ['setup', 'cleanup']:
                snap = self.clear_snap if self.utility == 'setup' \
                    else self.snapshot_setup_installed
                self.manager.saveSetup(self.utility, snap)
        else:
            ip = REST_API_HOST
            self.ut = self.utility_class(self.manager.dispatchSetup(
                self.utility, ip))

    def tearDown(self):
        """
        Discard changes which was made by test-case
        """
        if self.installation == 'true':
            if self.utility in ['setup', 'cleanup']:
                snap = self.clear_snap if self.utility == 'setup' \
                    else self.snapshot_setup_installed
                self.manager.restoreSetup(self.utility, snap)
        else:
            if self.utility == 'cleanup':
                machine = self.manager.dispatchSetup(self.utility,
                                                     REST_API_HOST)
                machine.install(config)
