"""
Testing watchdog card on VMS and their actions
Prerequisites: 1 DC, 2 hosts, 1 SD (NFS)
Tests covers:
    Vm CRUD and template CRUD tests
    Installation of watchdog software
    Watchdog event in event tab of webadmin portal
    Watchdog card specification in VM subtab
    test on watchdog card with action poweroff that is highly available
    Watchdog action with migration of VM
    Triggering watchdog actions (dump, none, pause, poweroff, reset)
"""

from art.unittest_lib import SlaTest as TestCase

import logging
import re
import time

from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import templates

from art.rhevm_api.utils.test_utils import get_api, setPersistentNetwork

from art.core_api.apis_utils import TimeoutingSampler


import art.test_handler.exceptions as errors

from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.unittest_lib.common import is_bz_state

from utilities import machine
from nose.plugins.attrib import attr

from rhevmtests.sla.watchdog import config

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__name__)


MEMORY_SIZE = 2 * config.GB
WATCHDOG_TIMEOUT = 600
WATCHDOG_TIMER = 120  # default time of triggering watchdog * 2
WATCHDOG_SAMPLING = 10  # sampling time of watchdog
MIGRATION_TIME = 20  # time of migration
QEMU_CONF = '/etc/libvirt/qemu.conf'
DUMP_PATH = '/var/lib/libvirt/qemu/dump'
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'

########################################################################
#                        Base classes                                  #
########################################################################


@attr(tier=0)
class WatchdogVM(TestCase):
    """
    Base class for vm watchdog operations
    """
    def kill_watchdog(self, vm_name, sleep_time=WATCHDOG_TIMER):
        """
        Kill watchdog process
        Author: lsvaty
        Parameters:
            * vm_name - name of VM to grep lspci on
            * sleep_time - time to sleep after watchdog is killed
        """
        vm_machine = vms.get_vm_machine(vm_name,
                                        config.VMS_LINUX_USER,
                                        config.VMS_LINUX_PW)
        rc, out = vm_machine.runCmd(['killall', '-9', 'watchdog'])

        self.assertTrue(rc, "Error on `killall -9 watchdog` output: " + out)

        logger.info("Watchdog process killed, waiting for %ds", sleep_time)
        time.sleep(sleep_time)

    def lspci_watchdog(self, positive, vm_name):
        """
        Detect watchdog
        Author: lsvaty
        Parameters:
            * vm_name - name of VM to grep lspci on
            * positive - True if should succeed
        """
        vm_machine = vms.get_vm_machine(vm_name,
                                        config.VMS_LINUX_USER,
                                        config.VMS_LINUX_PW)
        rc, output = vm_machine.runCmd(['lspci', '|', 'grep', '-i',
                                        config.WATCHDOG_MODEL[1:]])
        if positive:
            self.assertTrue(rc and output,
                            "Can't read 'lspci | grep -i " +
                            config.WATCHDOG_MODEL[1:] + "', output: %s" %
                            output)
        else:
            self.assertFalse(rc and output, "Watchdog still detected")
        logger.info("Watchdog detected - %s", positive)


########################################################################
#                             Functions                                #
########################################################################

def change_watchdog_action(vm, action):
    """
    Change action of watchdog
    Author: lsvaty
    Parameters:
        * vm - vm name
        * action - action of watchdog card
    Return value: True on success otherwise False
    """
    if not vms.stopVm(positive=True, vm=vm, async='false'):
        logger.error(
            "Can't shutdown VM, VM is down after failure of previous test")

    if not vms.updateVm(
        vm=vm, positive=True,
        watchdog_model=config.WATCHDOG_MODEL,
        watchdog_action=action
    ):
        raise errors.VMException("Failed to update watchdog on vm")

    if not vms.startVm(
        positive=True,
        vm=vm,
        wait_for_status=config.ENUMS['vm_state_up']
    ):
        raise errors.VMException(
            "Failed to start VM after changing watchdog action")

    return True


def install_watchdog(vm_machine):
    """
    Install watchdog and enable service
    Author: lsvaty
    Parameters:
        * vm_machine - vm machine
    """
    rc, output = vm_machine.runCmd(['rhnreg_ks',
                                    '--activationkey=' +
                                    config.ACTIVATION_KEY,
                                    '--serverUrl=' + config.REGISTER_URL,
                                    '--force'], timeout=900)
    if not rc:
        logger.error("Cannot add Vm to RHN, output: %s", output)
        return False
    rc = vm_machine.yum('watchdog', 'install', timeout=600)
    if not rc:
        logger.error("Can't install watchdog")
        return False
    logger.info("Watchdog installed")

    rc, out = vm_machine.runCmd(['sed', '-i',
                                 '\'s/#watchdog-device/watchdog-device/\'',
                                 '/etc/watchdog.conf'])

    if not rc:
        logger.error("Can't edit file /etc/watchdog.conf, output: %s", out)
        return False

    rc, output = vm_machine.runCmd(['chkconfig', 'watchdog',
                                    'on'])

    if not rc:
        logger.error("Watchdog enabled - %s", output)
        return False
    logger.info("Watchdog enabled - %s", output)

    rc = vm_machine.startService('watchdog')
    if not rc:
        logger.error("Can't start service watchdog")
        return False
    logger.info("Watchdog started")

    output = vm_machine.getServiceStatus('watchdog')

    if output != "running":
        logger.error("Watchdog status - %s", output)
        return False
    logger.info("Watchdog status - %s", output)

    logger.info("Watchdog successfully installed")
    return True


def run_watchdog_service(vm):
    """
    Check if watchdog service is running if not install and run
    Author: lsvaty
    Parameters:
        *vm - name of vm
    """
    if vms.checkVmState(True, vm, config.ENUMS['vm_state_down']):
        logger.warning("Vm was not running, starting VM")
        if not vms.startVm(True, vm):
            raise errors.VMException("Failed to start vm %s" % vm)

    vm_machine = vms.get_vm_machine(vm, config.VMS_LINUX_USER,
                                    config.VMS_LINUX_PW)
    output = vm_machine.getServiceStatus('watchdog')

    if output not in ("running", "stopped"):
        if not install_watchdog(vm_machine):
            raise errors.VMException("Watchdog installation failed")
    elif output == "stopped":
        vm_machine.startService('watchdog')

    args = 'watchdog',
    for output in TimeoutingSampler(
        WATCHDOG_TIMEOUT,
        WATCHDOG_SAMPLING,
        vm_machine.getServiceStatus,
        *args
    ):
        if output == 'running':
            logger.info("Watchdog running")
            break
        else:
            logger.warning("Watchdog status: %s", output)

########################################################################
#                             Test Cases                               #
########################################################################


class WatchdogCRUD(WatchdogVM):
    """
    Create Vm with watchdog
    """
    __test__ = True

    @bz({'1107992': {'engine': ['java'], 'version': None}})
    @tcms('9846', '295149')
    def test_add_watchdog(self):
        """
        Add watchdog to clean VM
        """
        self.assertTrue(vms.updateVm(vm=config.VM_NAME[0],
                                     positive=True,
                                     watchdog_model='i6300esb',
                                     watchdog_action='reset'),
                        "Can't add watchdog model")

        self.assertTrue(vms.startVm(
            positive=True,
            wait_for_status=config.ENUMS['vm_state_up'],
            vm=config.VM_NAME[0]), "VM did not start")

        logger.info("Watchdog added to VM")

    @bz({'1107992': {'engine': ['java'], 'version': None}})
    @tcms('9846', '285329')
    def test_detect_watchdog(self):
        """
        Detect watchdog
        """
        self.assertTrue(
            vms.checkVmState(
                True, config.VM_NAME[0], config.ENUMS['vm_state_up']
            ),
            "VM is not running")
        self.lspci_watchdog(True, config.VM_NAME[0])

    @bz({'1107992': {'engine': ['java'], 'version': None}})
    @tcms('9846', '285331')
    def test_remove_watchdog(self):
        """
        Deleting watchdog model
        """

        self.assertTrue(vms.stopVm(positive=True,
                                   vm=config.VM_NAME[0]),
                        "Can't shutdown VM")

        self.assertTrue(vms.updateVm(vm=config.VM_NAME[0],
                                     positive=True,
                                     watchdog_model=''),
                        "Can't delete watchdog model")

        self.assertTrue(
            vms.startVm(
                positive=True,
                wait_for_status=config.ENUMS['vm_state_up'],
                vm=config.VM_NAME[0]
            ),
            "VM did not start")

        self.lspci_watchdog(False, config.VM_NAME[0])
        logger.info("Watchdog successfully deleted")

    @classmethod
    def teardown_class(cls):
        vms.stop_vms_safely([config.VM_NAME[0]])

#####################################################################


class WatchdogInstall(TestCase):
    """
    Install VM watchdog
    """

    __test__ = True

    @tcms('9846', '295157')
    def test_install_watchdog(self):
        """
        Install watchdog and enable service
        """
        run_watchdog_service(config.WATCHDOG_VM)
        logger.info("Watchdog install test successful")

#######################################################################


class WatchdogTestNone(WatchdogVM):
    """
    Test action none
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Change action to none
        """
        change_watchdog_action(config.WATCHDOG_VM, 'none')
        run_watchdog_service(config.WATCHDOG_VM)

    @tcms('9846', '285346')
    def test_action_none(self):
        """
        Test action none, wm should stay in kernel panic
        """
        self.assertTrue(vms.waitForVMState(config.WATCHDOG_VM),
                        "Vm not in up status")

        self.kill_watchdog(config.WATCHDOG_VM)

        self.assertTrue(vms.waitForVMState(config.WATCHDOG_VM),
                        "Watchdog action none did not succeed")

        self.lspci_watchdog(True, config.WATCHDOG_VM)

        logger.info("Watchdog action none succeeded")

    @classmethod
    def teardown_class(cls):
        """
        Set watchdog VM to starting state
        """
        logger.info("rebooting VM")
        if not vms.reboot_vms([config.WATCHDOG_VM]):
            raise errors.VMException(
                "Cannot reboot VM %s" % config.WATCHDOG_VM
            )

#######################################################################


class WatchdogTestReset(WatchdogVM):
    """
    Test action reset
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set action to reset
        """
        change_watchdog_action(config.WATCHDOG_VM, 'reset')
        run_watchdog_service(config.WATCHDOG_VM)

    @tcms('9846', '285336')
    def test_action_reset(self):
        """
        Test action reset
        """
        self.kill_watchdog(config.WATCHDOG_VM, 0)

        vm_machine = vms.get_vm_machine(config.WATCHDOG_VM,
                                        config.VMS_LINUX_USER,
                                        config.VMS_LINUX_PW)

        args = ['lspci', '|', 'grep', '-i', 'watchdog'],

        time.sleep(WATCHDOG_TIMER)

        rc = False
        for rc, output in TimeoutingSampler(
            WATCHDOG_TIMEOUT,
            WATCHDOG_SAMPLING,
            vm_machine.runCmd, *args
        ):
            if rc:
                logger.info('Vm successfully rebooted.')
                break

        self.assertTrue(rc, "Watchdog action reboot did not succeed")

    @classmethod
    def teardown_class(cls):
        """
        Set watchdog VM to starting state
        """
        logger.info("rebooting VM")
        if not vms.reboot_vms([config.WATCHDOG_VM]):
            raise errors.VMException(
                "Cannot reboot VM %s" % config.WATCHDOG_VM
            )

#######################################################################


class WatchdogTestPoweroff(WatchdogVM):
    """
    Test action poweroff
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Change action to poweroff
        """
        change_watchdog_action(config.WATCHDOG_VM, 'poweroff')
        run_watchdog_service(config.WATCHDOG_VM)

    @tcms('9846', '285335')
    def test_action_poweroff(self):
        """
        Test action poweroff
        """
        self.kill_watchdog(config.WATCHDOG_VM)

        self.assertTrue(
            vms.waitForVMState(config.WATCHDOG_VM,
                               state=config.ENUMS['vm_state_down']),
            "Watchdog action poweroff failed")

    @classmethod
    def teardown_class(cls):
        """
        Set watchdog VM to starting state
        """
        logger.info("rebooting VM")
        if not vms.reboot_vms([config.WATCHDOG_VM]):
            raise errors.VMException(
                "Cannot reboot VM %s" % config.WATCHDOG_VM
            )

#######################################################################


class WatchdogTestPause(WatchdogVM):
    """
    Test action pause
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Change action to pause
        """
        change_watchdog_action(config.WATCHDOG_VM, 'pause')
        run_watchdog_service(config.WATCHDOG_VM)

    @tcms('9846', '285339')
    def test_action_pause(self):
        """
        Test action pause
        """
        self.kill_watchdog(config.WATCHDOG_VM)

        self.assertTrue(vms.waitForVMState(config.WATCHDOG_VM,
                                           state='paused'),
                        "Watchdog action pause failed")

        logger.info("actian pause successfull")

    @classmethod
    def teardown_class(cls):
        """
        Set watchdog VM to starting state
        """
        logger.info("rebooting VM")
        if not vms.reboot_vms([config.WATCHDOG_VM]):
            raise errors.VMException(
                "Cannot reboot VM %s" % config.WATCHDOG_VM
            )

#######################################################################


class WatchdogTestDump(WatchdogVM):
    """
    Test action dump
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Change action to dump
        """
        change_watchdog_action(config.WATCHDOG_VM, 'dump')
        run_watchdog_service(config.WATCHDOG_VM)

    @tcms('9846', '285345')
    def test_action_dump(self):
        """
        Test action pause
        """
        dump_path = DUMP_PATH
        host_machine = hosts.get_linux_machine_obj(
            config.HOSTS[0], config.HOSTS_USER, config.HOSTS_PW
        )

        rc, output = host_machine.runCmd(
            ['grep', '^auto_dump_path', QEMU_CONF])
        logger.info(
            "grep ^auto_dump_path %s output: %s", QEMU_CONF, output
        )
        if rc:
            regex = r"auto_dump_path=\"(.+)\""
            dump_path = re.search(regex, output).group(1)
            logger.info("dump path set to %s", dump_path)

        rc, output = host_machine.runCmd(
            ['ls', '-l', dump_path,  '|', 'wc', '-l'])
        self.assertTrue(rc, "Cannot read %s" % dump_path)

        logger.info("files in dumpath: %s", output)
        logs_count = int(output)

        self.kill_watchdog(config.WATCHDOG_VM)

        self.lspci_watchdog(True, config.WATCHDOG_VM)

        logger.info("Watchdog action dump successful")

        rc, output = host_machine.runCmd(
            ['ls', '-l', dump_path,  '|', 'wc', '-l'])
        self.assertTrue(rc, "Cannot read %s" % dump_path)

        self.assertEqual(logs_count + 1, int(output),
                         "Dump file was not created")
        logger.info("dump file successfully created")

    @classmethod
    def teardown_class(cls):
        """
        Set watchdog VM to starting state
        """
        logger.info("rebooting VM")
        if not vms.reboot_vms([config.WATCHDOG_VM]):
            raise errors.VMException(
                "Cannot reboot VM %s" % config.WATCHDOG_VM
            )

######################################################################


@attr(tier=1)
class WatchdogGeneralVMSubtab(TestCase):
    """
    Watchdog info in generat subtab
    """

    __test__ = True

    @bz({'996521': {'engine': None, 'version': None}})
    @tcms('9846', '285333')
    def test_general_subtab(self):
        """
        Test if watchdog model and action are in general subtab of VM tab
        """
        self.assertTrue(is_bz_state('996521'), "BZ#996521 not closed.")

#######################################################################


@attr(tier=1)
class WatchdogMigration(TestCase):
    """
    Test watchdog with migration of vm
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Change watchdog action to poweroff
        """
        change_watchdog_action(config.WATCHDOG_VM, 'poweroff')
        run_watchdog_service(config.WATCHDOG_VM)

    @tcms('9846', '294620')
    def test_migration(self):
        """
        Test migration of VM.
        Timestamp of watchdog on fist host should move to other host or
        be deleted
        """
        if (len(config.HOSTS)) < 2:
            raise errors.SkipTest("Too few hosts.")

        logger.info("Migrating VM")
        self.assertTrue(
            vms.migrateVm(positive=True,
                          vm=config.WATCHDOG_VM,
                          host=config.HOSTS[1],
                          force=True),
            "Migration Failed")
        logger.info("Migrating successfull")
        time.sleep(WATCHDOG_TIMER)
        self.assertTrue(vms.waitForVMState(config.WATCHDOG_VM),
                        "Watchdog was triggered")
        logger.info("Migration of vm did not trigger watchdog")

    @classmethod
    def teardown_class(cls):
        """
        Set watchdog VM to starting state
        """
        logger.info("rebooting VM")
        if not vms.reboot_vms([config.WATCHDOG_VM]):
            raise errors.VMException(
                "Cannot reboot VM %s" % config.WATCHDOG_VM
            )

#######################################################################


@attr(tier=1)
class WatchdogHighAvailability(WatchdogVM):
    """
    Action poweroff with vm that is highly available
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Test high availability with action shutdown
        """
        if not vms.stopVm(positive=True, vm=config.WATCHDOG_VM):
            raise errors.VMException("Cannot stop VM %s" % config.WATCHDOG_VM)

        if not vms.updateVm(
            positive=True, vm=config.WATCHDOG_VM,
            placement_affinity=config.ENUMS['vm_affinity_migratable'],
            highly_available=True
        ):
            raise errors.VMException(
                "Vm %s not set to automatic migratable and highly available" %
                config.WATCHDOG_VM
            )

        if not vms.startVm(positive=True, vm=config.WATCHDOG_VM):
            raise errors.VMException("Cannot start VM %s" % config.WATCHDOG_VM)
        change_watchdog_action(config.WATCHDOG_VM, 'poweroff')
        run_watchdog_service(config.WATCHDOG_VM)

    @tcms('9846', '294619')
    def test_high_availability(self):
        """
        Test action poweroff with Vm set to highly available.
        """

        logger.info("Killing watchdog process")

        self.kill_watchdog(config.WATCHDOG_VM)

        self.assertTrue(vms.waitForVMState(config.WATCHDOG_VM),
                        "VM did not start as high available")

        logger.info("Vm started successfully")

    @classmethod
    def teardown_class(cls):
        """
        Run the VM to start state
        """
        logger.info("rebooting VM")
        if not vms.stopVm(positive=True, vm=config.WATCHDOG_VM):
            raise errors.VMException("Cannot stop VM %s" % config.WATCHDOG_VM)
        if not vms.updateVm(
            positive=True, vm=config.WATCHDOG_VM,
            placement_affinity=config.ENUMS['vm_affinity_user_migratable'],
            highly_available='false'
        ):
            raise errors.VMException("Cannot edit vm %s" % config.WATCHDOG_VM)

        if not vms.startVm(positive=True, vm=config.WATCHDOG_VM):
            raise errors.VMException("Cannot start VM %s" % config.WATCHDOG_VM)

#######################################################################


@attr(tier=1)
class WatchdogEvents(WatchdogVM):
    """
    Event in logs
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Change watchdog action to reset
        """
        change_watchdog_action(config.WATCHDOG_VM, 'reset')
        run_watchdog_service(config.WATCHDOG_VM)

    @tcms('9846', '294615')
    def test_event(self):
        """
        Test if event is displayed in log file
        """
        engine_machine = machine.Machine(
            config.VDC_HOST, config.VDC_ROOT_USER,
            config.VDC_ROOT_PASSWORD).util(machine.LINUX)
        logger.info("Saving backup of log")
        rc, out = engine_machine.runCmd(
            ['cp', ENGINE_LOG,
             'watchdog_test_event.log'])

        self.assertTrue(rc, "Cannot read watchdog_test_event.log")

        self.kill_watchdog(config.WATCHDOG_VM)

        rc, out = engine_machine.runCmd(
            ['diff', '/var/log/ovirt-engine/engine.log',
             'watchdog_test_event.log', '|', 'grep',
             'event', '|', 'grep', 'Watchdog'])
        self.assertTrue(rc, "Error: no event in engine.log, output: " + out)

        logger.info("Event successfully created")

    @classmethod
    def teardown_class(cls):
        """
        Remove used file
        """
        # reboot VM
        engine_machine = machine.Machine(
            config.VDC_HOST, config.VDC_ROOT_USER,
            config.VDC_ROOT_PASSWORD).util(machine.LINUX)
        _, _ = engine_machine.runCmd(['rm', 'watchdog_test_event.log'])
        logger.info("rebooting VM")
        if not vms.reboot_vms([config.WATCHDOG_VM]):
            raise errors.VMException(
                "Cannot reboot VM %s" % config.WATCHDOG_VM
            )

#######################################################################


class WatchdogCRUDTemplate(WatchdogVM):
    """
    CRUD test for template
    """
    __test__ = True
    vm_name1 = "watchdog_template_vm1"
    vm_name2 = "watchdog_template_vm2"
    template_name = "watchdog_template"

    @classmethod
    def setup_class(cls):
        """
        Create Template
        """
        if not vms.startVm(True, config.VM_NAME[0]):
            raise errors.VMException("Cannot stop VM")
        status, guest = vms.waitForIP(config.VM_NAME[0],
                                      timeout=600,
                                      sleep=10)

        if not setPersistentNetwork(guest['ip'], config.VMS_LINUX_PW):
            raise errors.VMException("Cannot set persistent network")

        if not (vms.stopVm(positive=True, vm=config.VM_NAME[0])):
            raise errors.VMException(
                "Cannot shutdown VM %s" % config.VM_NAME[0])
        if not templates.createTemplate(
                positive=True,
                wait=True,
                vm=config.VM_NAME[0],
                name=cls.template_name
        ):
            raise errors.VMException(
                "Cannot add template %s" % cls.template_name)

    @bz({'1107992': {'engine': ['java'], 'version': None}})
    @tcms('9846', '294476')
    def test_add_watchdog_template(self):
        """
        Add watchdog to clean template
        """
        self.assertTrue(templates.updateTemplate(template=self.template_name,
                                                 positive=True,
                                                 vmDescription="template vm",
                                                 watchdog_model='i6300esb',
                                                 watchdog_action='reset'),
                        "Can't add watchdog model to template")
        logger.info("Watchdog added to template")

    @bz({'1107992': {'engine': ['java'], 'version': None}})
    @tcms('9846', ' 285330')
    def test_detect_watchdog_template(self):
        """
        Detect watchdog
        """
        self.assertTrue(vms.createVm(positive=True, vmName=self.vm_name1,
                                     vmDescription="Watchdog VM",
                                     cluster=config.CLUSTER_NAME[0],
                                     template=self.template_name),
                        "Cannot create vm")

        self.assertTrue(
            vms.waitForVMState(self.vm_name1,
                               state=config.ENUMS['vm_state_down']),
            "Vm not in status down after creation from template")

        vms.startVm(positive=True, vm=self.vm_name1)
        self.lspci_watchdog(True, self.vm_name1)

    @bz({'1107992': {'engine': ['java'], 'version': None}})
    @tcms('9846', ' 294457')
    def test_remove_watchdog_template(self):
        """
        Deleting watchdog model
        """
        self.assertTrue(templates.updateTemplate(template=self.template_name,
                                                 positive=True,
                                                 watchdog_model=''),
                        "Can't remove watchdog model to template")

        self.assertTrue(vms.createVm(positive=True, vmName=self.vm_name2,
                                     vmDescription="tempalte vm",
                                     cluster=config.CLUSTER_NAME[0],
                                     template=self.template_name),
                        "Cannot create vm")

        self.assertTrue(
            vms.waitForVMState(self.vm_name2,
                               state=config.ENUMS['vm_state_down']),
            "Vm not in status down after creation from template")
        vms.startVm(positive=True, vm=self.vm_name2)

        self.lspci_watchdog(False, self.vm_name2)
        logger.info("Watchdog removed from template")

    @classmethod
    def teardown_class(cls):
        if not vms.safely_remove_vms([cls.vm_name1, cls.vm_name2]):
            raise errors.VMException("Failed to remove vms")
        if not templates.removeTemplate(
            positive=True, template=cls.template_name
        ):
            raise errors.VMException("Cannot remove template")
        logger.info("template removed")

######################################################################
