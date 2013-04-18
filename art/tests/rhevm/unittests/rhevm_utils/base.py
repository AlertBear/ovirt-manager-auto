
"""
File contains base classes for this module.
"""

__test__ = False

import time
import logging
import unittest
from art.rhevm_api.tests_lib.low_level.vms import addSnapshot, restoreSnapshot
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter, \
    prepareVmWithRhevm
from art.rhevm_api.utils.test_utils import get_api
VM_API = get_api('vm', 'vms')

# Folowing 'try-except' blocks are here because this modules are needed only
# for nose testframework, but you can use this module also for another purposes.
try:
    # PGPASS, PREPARE_CONF should move to test conf file, once possible.
    from unittest_conf import config, PGPASS, REST_API_PASS, ISO_UP_CONF
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
            raise errors.SetupsManagerError("can't find testing machine: %s" % vm_name)
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
            raise errors.SetupsManagerError("can't find testing machine: %s" % name)
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
            raise errors.AddSnapshotFailure("Create snapshot %s from vm %s" % snapshot_desc, vm_name)

    def restoreSnapshotWrapper(self, vm_name, snapshot_desc):
	"""
	Restores to snapshot
	Parameters:
	* vm_name - VM name
	* snapshot_desc - name of snapshot
	"""
        rc = restoreSnapshot(True, vm_name, snapshot_desc, ensure_vm_down=True)
        if not rc:
            raise errors.RestoreSnapshotFailure("Restore snapshot %s for vm %s" % snapshot_desc, vm_name)

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
        #sn_list = [ x.description for x in machine.snapshots.list()]
        #if self.BASE_SNAPSHOT in sn_list:
        #    if self.BASE_SNAPSHOT == sn_list[-1]:
        #        return
        #    else:
        #        self.restoreSnapshot(machine, self.BASE_SNAPSHOT)
        self.createSnapshotWrapper(machine.name, self.BASE_SNAPSHOT)

    def startSetup(self, name):
        machine = self.maps[name]
        rc = VM_API.syncAction(machine, 'start', 'true')
        self.waitForMachineStatus(machine, 'up')

    def stopSetup(self, name):
        machine = self.maps[name]
        rc = VM_API.syncAction(machine, 'stop', 'true')
        self.waitForMachineStatus(machine, 'down')

    def saveSetup(self, name, point):
        machine = self.refreshMachine(self.maps[name])
        self.createSnapshotWrapper(machine.name, point)

    def restoreSetup(self, name, point):
        machine = self.refreshMachine(self.maps[name])
        self.restoreSnapshotWrapper(machine.name, point)

    def dispatchSetup(self, name):
        machine = self.refreshMachine(self.maps[name])
        if machine.status.get_state() != 'up':
            rc = VM_API.syncAction(machine, 'start', 'true')
            self.waitForMachineStatus(machine, 'up')
        self.waitForAgentIsUp(machine)
        ip = self.getIp(machine)
        return Setup(ip, 'root', config['testing_env']['host_pass'],
                     dbpassw=PGPASS, conf=VARS)

    def releaseSetup(self, name):
        try:
            machine = self.refreshMachine(self.maps[name])
            if machine.status.get_state() == 'up':
                rc = VM_API.syncAction(machine, 'stop', 'true')
                self.waitForMachineStatus(machine, 'down')
            self.restoreSnapshotWrapper(machine.name, self.BASE_SNAPSHOT)
        finally:
            self.releaseMachine(name)

    def installSetup(self, name):
        m = self.dispatchSetup(name)
        # TODO: install


_multiprocess_can_split_ = True

class RHEVMUtilsTestCase(unittest.TestCase):
    """
    Base class for test plan. It contains general setUp and tearDown class
    which are suiteable for most of RHEVM utilities
    """
    __test__ = False
    utility = None
    utility_class = None
    manager = SetupManager()
    snapshot_setup_installed = "installed_setup"
    clear_snap = 'clear_machine'
    _multiprocess_can_split_ = True

    @classmethod
    def setUpClass(cls):
        """
        Prepares setup machine, install RHEVM on it, and create snapshot
        """
        ENUMS = opts['elements_conf']['RHEVM Enums']
        logger.info("Preparation flow")
        params = ART_CONFIG['PARAMETERS']
        data_domain_address = None
        data_storage_domains = None
        lun_address = None
        lun_target = None
        luns = None

        hosts = params.get('vds')
        cpuName = params.get('cpu_name')
        username = 'root'
        password = params.get('vds_password')[0]
        data_center_type = params.get('data_center_type')
        datacenter ='%sToolsTest' % data_center_type
        storage_type = data_center_type
        cluster = '%sToolsTest' % data_center_type
        if data_center_type.lower() == ENUMS['storage_type_nfs']:
            data_domain_address = params.as_list('data_domain_address')[0]
            data_storage_domains = params.as_list('data_domain_path')[0]
        if data_center_type.lower() == ENUMS['storage_type_iscsi']:
            lun_address = params.as_list('lun_address')[0]
            lun_target = params.as_list('lun_target')[0]
            luns = params.as_list('lun')[0]

        version=params.get('compatibility_version')
        type = ENUMS['storage_dom_type_export']
        export_domain_address = params.get('export_domain_address')[0]
        export_storage_domain = params.get('export_domain_path')[0]
        export_domain_name = params.get('export_domain_name')
        data_domain_name = params.get('data_domain_name')
        template_name = params.get('template_name')
        vm_name = params.get('vm_name')
        vm_description = params.get('vm_description')
        tested_setup_mac_address = params.get('tested_setup_mac_address')
        memory_size = int(params.get('memory_size'))
        format_export_domain = params.get('format_export_domain')
        nic = params.get('host_nics')[0]
        nicType = ENUMS['nic_type_virtio']
        disk_size = int(params.get('disk_size'))
        disk_type = ENUMS['disk_type_system']
        volume_format = ENUMS['format_cow']
        disk_interface = ENUMS['interface_ide']
        bootable = params.get('bootable')
        wipe_after_delete = params.get('wipe_after_delete')
        start = params.get('start')
        vm_type = ENUMS['vm_type_server']
        os_type = params.get('vm_os')
        cpu_socket = params.get('cpu_socket')
        cpu_cores = params.get('cpu_cores')
        display_type = ENUMS['display_type_spice']
        installation = params.get('installation')
        vm_user = params.get('vm_linux_user')
        vm_password = params.get('vm_linux_password')
        cobblerAddress = params.get('cobbler_address')
        cobblerUser = params.get('cobbler_user')
        cobblerPasswd = params.get('cobbler_passwd')
        image = params.get('cobbler_profile')
        network = params.get('mgmt_bridge')
        useAgent = params.get('useAgent')


        if not prepareVmWithRhevm(True, hosts, cpuName, username, password, datacenter,
               storage_type, cluster, data_domain_address, data_storage_domains,
               version, type, export_domain_address, export_storage_domain,
               export_domain_name, data_domain_name, template_name, vm_name,
               vm_description, tested_setup_mac_address, memory_size,
               format_export_domain, nic, nicType, lun_address, lun_target,
               luns, disk_size, disk_type, volume_format, disk_interface,
               bootable, wipe_after_delete, start, vm_type, cpu_socket,
               cpu_cores, display_type, installation, os_type, vm_user,
               vm_password, cobblerAddress, cobblerUser, cobblerPasswd, image,
               network, useAgent):
            logger.info("prepareVmWithRhevm failed")
        logger.info("DEBUG: cls.utility = %s", cls.utility)
        cls.c = config[cls.utility]
        logger.info("DEBUG: cls.c %s", cls.c)
        cls.manager.prepareSetup(cls.utility)
        if cls.utility is not 'setup':
            machine = cls.manager.dispatchSetup(cls.utility)
            machine.install(config)
            #cls.manager.saveSetup(cls.utility, cls.snapshot_setup_installed)

    @classmethod
    def tearDownClass(cls):
        """
        Remove all snapshosts, and relase machine
        """
        cls.manager.releaseSetup(cls.utility)
        logger.info("Clean Data center")
        cleanDataCenter(True, 'nfsToolsTest')

    def setUp(self):
        """
        Fetch instance of utility for test-case
        """
        snap = self.clear_snap if self.utility is 'setup' else self.snapshot_setup_installed
        self.manager.saveSetup(self.utility, snap)
        self.ut = self.utility_class(self.manager.dispatchSetup(self.utility))

    def tearDown(self):
        """
        Discart changes which was made by test-case
        """
        snap = self.clear_snap if self.utility is 'setup' else self.snapshot_setup_installed
        self.manager.restoreSetup(self.utility, snap)



