"""
Testing watchdog card on VMS and their actions
Prerequisites: 1 DC, 2 hosts, 1 SD (NFS)
Tests covers:
    Vm CRUD and template CRUD tests
    Installation of watchdog software
    Watchdog event in event tab of webadmin portal
    test on watchdog card with action poweroff that is highly available
    Watchdog action with migration of VM
    Triggering watchdog actions (dump, none, pause, poweroff, reset)
"""
import logging
import re
import time

from unittest2 import SkipTest

import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
import rhevmtests.helpers as helpers
import rhevmtests.sla as sla
from art.test_handler.tools import polarion, bz
from art.unittest_lib import SlaTest as TestCase, attr
from rhevmtests.sla.watchdog import config

logger = logging.getLogger(__name__)

########################################################################
#                        Base classes                                  #
########################################################################


def setup_module():
    """
    Prepare environment for Watchdog test
    """
    config.GENERAL_VM_PARAMS['placement_host'] = config.HOSTS[0]
    params = dict(config.GENERAL_VM_PARAMS)
    for vm in config.VM_NAME[:2]:
        logger.info("Update vm %s with parameters: %s", vm, params)
        if not ll_vms.updateVm(True, vm, **params):
            raise errors.VMException("Failed to update vm %s" % vm)


def teardown_module():
    """
    SLA teardown
    """
    sla.sla_cleanup()
    for vm_name in config.VM_NAME[:2]:
        if ll_vms.get_watchdog_collection(vm_name=vm_name):
            ll_vms.delete_watchdog(vm_name=vm_name)


class WatchdogMixin(object):
    """
    Base class for vm watchdog operations
    """

    @classmethod
    def kill_watchdog(cls, vm_name, sleep_time=config.WATCHDOG_TIMER):
        """
        Kill watchdog process on given vm

        :param vm_name: vm name
        :type vm_name: str
        :param sleep_time: sleep time
        :type sleep_time: int
        """

        vm_resource = helpers.get_vm_resource(vm=vm_name)
        if not vm_resource.package_manager.install(config.KILLALL_PACKAGE):
            return False
        cmd = ['killall', '-9', 'watchdog']
        logger.info("Kill watchdog service on vm %s", vm_name)
        if vm_resource.run_command(command=cmd)[0]:
            raise errors.VMException(
                "Failed to kill watchdog process on vm %s", vm_name
            )
        logger.info("Watchdog process killed, waiting %d seconds", sleep_time)
        time.sleep(sleep_time)

    @staticmethod
    def detect_watchdog(positive, vm_name):
        """
        Detect watchdog device on given vm

        :param positive: positive or negative test
        :type positive: bool
        :param vm_name: vm name
        :type vm_name: str
        """
        vm_resource = helpers.get_vm_resource(vm=vm_name, start_vm=False)
        get_dev_package = (
            config.LSHW_PACKAGE if config.PPC_ARCH else config.LSPCI_PACKAGE
        )
        if config.PPC_ARCH:
            if not vm_resource.package_manager.install(get_dev_package):
                return False

        logger.info(
            "Check if vm %s have watchdog device %s",
            vm_name, config.WATCHDOG_MODEL[1:]
        )
        cmd = [get_dev_package, '|', 'grep', '-i', config.WATCHDOG_MODEL[1:]]
        status = vm_resource.run_command(command=cmd)[0]
        if positive:
            assert not status
        else:
            assert status
        logger.info("Watchdog detected - %s", positive)

    @classmethod
    def change_action(cls, vm_name, action):
        """
        Change watchdog action and start given vm

        :param vm_name: vm name
        :type vm_name: str
        :param action: watchdog action
        :type action: str
        :return: True, if success to change watchdog action, otherwise False
        """
        watchdog_col = ll_vms.get_watchdog_collection(vm_name=vm_name)
        if watchdog_col:
            # Add watchdog model as W/A for bz #1338502
            assert ll_vms.update_watchdog(
                vm_name=vm_name, model=config.WATCHDOG_MODEL, action=action
            )
        else:
            assert ll_vms.add_watchdog(
                vm_name=vm_name, model=config.WATCHDOG_MODEL, action=action
            )
        assert ll_vms.startVm(
            positive=True, vm=vm_name, wait_for_status=config.VM_UP
        )

    @classmethod
    def install_watchdog(cls, vm_resource):
        """
        Install watchdog and enable watchdog service

        :param vm_resource: vm resource
        :type vm_resource: Host
        """
        if not vm_resource.package_manager.install(config.WATCHDOG_PACKAGE):
            return False

        logger.info(
            "Enable watchdog in configuration file %s on resource %s",
            config.WATCHDOG_CONFIG_FILE, vm_resource
        )
        cmd = [
            'sed',
            '-i',
            '\'s/#watchdog-device/watchdog-device/\'',
            config.WATCHDOG_CONFIG_FILE
        ]
        if vm_resource.run_command(command=cmd)[0]:
            return False

        watchdog_service = vm_resource.service('watchdog')
        if not watchdog_service.is_enabled():
            logger.info("Enable watchdog service on resource %s", vm_resource)
            if not watchdog_service.enable():
                logger.error(
                    "Failed to enable watchdog service on resource %s",
                    vm_resource
                )
                return False

        logger.info("Start watchdog service on resource %s", vm_resource)
        if not watchdog_service.start():
            logger.error("Can't start service watchdog")
            return False

        logger.info("Watchdog successfully installed")
        return True

    @classmethod
    def run_watchdog_service(cls, vm_name):
        """
        Start vm, if vm down and install and start watchdog service on it

        :param vm_name: vm name
        :type vm_name: str
        :raises: VMException
        """
        if ll_vms.checkVmState(True, vm_name, config.VM_DOWN):
            logger.warning("Vm %s was not running, starting VM", vm_name)
            if not ll_vms.startVm(
                positive=True, vm=vm_name, wait_for_status=config.VM_UP
            ):
                raise errors.VMException("Failed to start vm %s" % vm_name)

        vm_resource = helpers.get_vm_resource(vm=vm_name, start_vm=False)
        try:
            watchdog_service = vm_resource.service('watchdog')
        except Exception as ex:
            logger.warning("Failed to create watchdog service %s", ex)
            if not cls.install_watchdog(vm_resource):
                raise errors.VMException(
                    "Watchdog installation failed on vm %s" % vm_resource
                )
        else:
            if not watchdog_service.status() and not watchdog_service.start():
                raise errors.VMException(
                    "Failed to run watchdog service on vm %s" % vm_resource
                )


@attr(tier=2)
class WatchdogVM(TestCase, WatchdogMixin):
    __test__ = False


########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class TestWatchdogCRUD(TestCase, WatchdogMixin):
    """
    Create Vm with watchdog
    """
    __test__ = True

    @polarion("RHEVM3-4953")
    def test_add_watchdog(self):
        """
        Add watchdog to clean VM
        """
        assert ll_vms.add_watchdog(
            vm_name=config.VM_NAME[0],
            model='i6300esb',
            action='reset'
        )
        assert ll_vms.startVm(
            positive=True, wait_for_status=config.VM_UP, vm=config.VM_NAME[0]
        )

    @polarion("RHEVM3-4952")
    def test_detect_watchdog(self):
        """
        Detect watchdog
        """
        logger.info("Check if vm %s run", config.VM_NAME[0])
        self.assertTrue(
            ll_vms.checkVmState(
                True, config.VM_NAME[0], config.VM_UP
            ),
            "VM %s is not running" % config.VM_NAME[0]
        )
        self.detect_watchdog(True, config.VM_NAME[0])

    @polarion("RHEVM3-4965")
    def test_remove_watchdog(self):
        """
        Deleting watchdog model
        """
        assert ll_vms.stopVm(positive=True, vm=config.VM_NAME[0])
        assert ll_vms.delete_watchdog(vm_name=config.VM_NAME[0])
        assert ll_vms.startVm(
            positive=True, wait_for_status=config.VM_UP, vm=config.VM_NAME[0]
        )
        self.detect_watchdog(False, config.VM_NAME[0])

    @classmethod
    def teardown_class(cls):
        ll_vms.stop_vms_safely([config.VM_NAME[0]])

#####################################################################


class WatchdogInstall(WatchdogVM):
    """
    Install VM watchdog
    """
    __test__ = True

    @polarion("RHEVM3-4967")
    def test_install_watchdog(self):
        """
        Install watchdog and enable service
        """
        self.run_watchdog_service(config.VM_NAME[1])
        logger.info("Watchdog install test successful")

    @classmethod
    def teardown_class(cls):
        """
        Stop vm
        """
        ll_vms.stop_vms_safely([config.VM_NAME[1]])

#######################################################################


class WatchdogActionTest(WatchdogVM):
    """
    Base class to test different watchdog action functionality
    """
    __test__ = False
    action = None

    @classmethod
    def setup_class(cls):
        """
        Change watchdog action and run watchdog service on vm
        """
        cls.change_action(
            config.VM_NAME[1], cls.action
        )
        cls.run_watchdog_service(config.VM_NAME[1])

    @classmethod
    def teardown_class(cls):
        """
        Reboot watchdog vm
        """
        ll_vms.stop_vms_safely([config.VM_NAME[1]])


class WatchdogTestNone(WatchdogActionTest):
    """
    Test watchdog action none
    """
    __test__ = True
    action = 'none'

    @polarion("RHEVM3-4959")
    def test_action_none(self):
        """
        Test watchdog action none, vm should stay in kernel panic
        """
        logger.info("Kill watchdog service on vm %s", config.VM_NAME[1])
        self.kill_watchdog(config.VM_NAME[1])
        self.assertTrue(
            ll_vms.waitForVMState(config.VM_NAME[1]),
            "Watchdog action none did not succeed"
        )
        self.detect_watchdog(True, config.VM_NAME[1])
        logger.info("Watchdog action none succeeded")

#######################################################################


class WatchdogTestReset(WatchdogActionTest):
    """
    Test watchdog action reset
    """
    __test__ = True
    action = 'reset'

    @polarion("RHEVM3-4962")
    def test_action_reset(self):
        """
        Test watchdog action reset
        """
        logger.info("Kill watchdog service on vm %s", config.VM_NAME[1])
        self.kill_watchdog(config.VM_NAME[1], sleep_time=0)

        logger.info(
            "Wait until vm %s will have state %s",
            config.VM_NAME[1], config.ENUMS['vm_state_reboot_in_progress']
        )
        self.assertTrue(
            ll_vms.waitForVMState(
                config.VM_NAME[1], config.ENUMS['vm_state_reboot_in_progress']
            ),
            "Vm still not have state %s" %
            config.ENUMS['vm_state_reboot_in_progress']
        )
        logger.info(
            "Wait until vm %s will have state %s",
            config.VM_NAME[1], config.VM_UP
        )
        self.assertTrue(
            ll_vms.waitForVMState(config.VM_NAME[1], config.VM_UP),
            "Vm still not have state %s" % config.VM_UP
        )

#######################################################################


class WatchdogTestPoweroff(WatchdogActionTest):
    """
    Test watchdog action poweroff
    """
    __test__ = True
    action = 'poweroff'

    @polarion("RHEVM3-4963")
    def test_action_poweroff(self):
        """
        Test watchdog action poweroff
        """
        logger.info("Kill watchdog service on vm %s", config.VM_NAME[1])
        self.kill_watchdog(config.VM_NAME[1])
        logger.info(
            "Wait until watchdog device will poweroff vm %s", config.VM_NAME[0]
        )
        self.assertTrue(
            ll_vms.waitForVMState(config.VM_NAME[1], state=config.VM_DOWN),
            "Watchdog action poweroff failed"
        )

#######################################################################


class WatchdogTestPause(WatchdogActionTest):
    """
    Test watchdog action pause
    """
    __test__ = True
    action = 'pause'

    @polarion("RHEVM3-4961")
    def test_action_pause(self):
        """
        Test watchdog action pause
        """
        logger.info("Kill watchdog service on vm %s", config.VM_NAME[1])
        self.kill_watchdog(config.VM_NAME[1])
        logger.info(
            "Wait until vm %s will have state paused", config.VM_NAME[1]
        )
        self.assertTrue(
            ll_vms.waitForVMState(config.VM_NAME[1], state='paused'),
            "Vm %s still not have state paused"
        )

#######################################################################


class WatchdogTestDump(WatchdogActionTest):
    """
    Test watchdog action dump
    """
    __test__ = True
    action = 'dump'

    @classmethod
    def get_host_dump_path(cls, host_resource):
        """

        """
        host_resource_executor = host_resource.executor()
        cmd = ['grep', '^auto_dump_path', config.QEMU_CONF]
        logger.info(
            "Run command '%s' on resource %s", " ".join(cmd), host_resource
        )
        rc, out, err = host_resource_executor.run_cmd(cmd)
        if rc:
            logger.error(
                "Failed to run command '%s' on resource %s; out: %s; err: %s" %
                (" ".join(cmd), host_resource, out, err)
            )
            return config.DUMP_PATH
        else:
            regex = r"auto_dump_path=\"(.+)\""
            dump_path = re.search(regex, out).group(1)
            return dump_path

    @polarion("RHEVM3-4960")
    def test_action_dump(self):
        """
        Test watchdog action dump
        """
        host_index = config.HOSTS.index(
            ll_vms.get_vm_host(config.VM_NAME[1])
        )
        host_executor = config.VDS_HOSTS[host_index].executor()
        dump_path = self.get_host_dump_path(config.VDS_HOSTS[host_index])
        cmd = ['ls', '-l', dump_path, '|', 'wc', '-l']
        rc, out, err = host_executor.run_cmd(cmd)
        self.assertTrue(
            not rc,
            "Failed to run command '%s' on resource %s; out: %s; err: %s" %
            (" ".join(cmd), config.VDS_HOSTS[host_index], out, err)
        )
        logger.info("Number of files in dumpath: %s", out)
        logs_count = int(out)

        logger.info("Kill watchdog service on vm %s", config.VM_NAME[1])
        self.kill_watchdog(config.VM_NAME[1])
        self.detect_watchdog(True, config.VM_NAME[1])

        logger.info("Watchdog action dump successful")

        rc, out, err = host_executor.run_cmd(cmd)
        self.assertTrue(
            not rc,
            "Failed to run command '%s' on resource %s; out: %s; err: %s" %
            (" ".join(cmd), config.VDS_HOSTS[host_index], out, err)
        )
        logger.info(
            "Number of files in dumpath after watchdog dump action: %s", out
        )
        self.assertEqual(
            logs_count + 1,
            int(out),
            "Dump file was not created on resource %s under directory %s" %
            (config.VDS_HOSTS[host_index], dump_path)
        )

#######################################################################


class WatchdogMigration(WatchdogActionTest):
    """
    Test watchdog with migration of vm
    """
    __test__ = True
    action = 'poweroff'

    @polarion("RHEVM3-4954")
    def test_migration(self):
        """
        Test, that migration not trigger watchdog action
        """
        if (len(config.HOSTS)) < 2:
            raise SkipTest("Too few hosts")

        logger.info("Migrate VM %s", config.VM_NAME[1])
        self.assertTrue(
            ll_vms.migrateVm(
                positive=True,
                vm=config.VM_NAME[1],
                force=True
            ),
            "Migration of vm %s Failed" % config.VM_NAME[1]
        )
        time.sleep(config.WATCHDOG_TIMER)
        logger.info("Check, that vm %s still up", config.VM_NAME[1])
        self.assertTrue(
            ll_vms.waitForVMState(config.VM_NAME[1]), "Watchdog was triggered"
        )

#######################################################################


class WatchdogHighAvailability(WatchdogActionTest):
    """
    Action poweroff with vm that is highly available
    """
    __test__ = True
    action = 'poweroff'

    @classmethod
    def setup_class(cls):
        """
        Test high availability with action shutdown
        """
        logger.info(
            "Update vm %s high available and placement affinity parameters",
            config.VM_NAME[1]
        )
        if not ll_vms.updateVm(
            positive=True,
            vm=config.VM_NAME[1],
            placement_affinity=config.VM_MIGRATABLE,
            highly_available=True
        ):
            raise errors.VMException(
                "Vm %s not set to automatic migratable and highly available" %
                config.VM_NAME[1]
            )
        super(WatchdogHighAvailability, cls).setup_class()

    @polarion("RHEVM3-4955")
    def test_high_availability(self):
        """
        Test action poweroff with Vm set to highly available.
        """
        logger.info("Kill watchdog service on vm %s", config.VM_NAME[1])
        self.kill_watchdog(config.VM_NAME[1])
        logger.info(
            "Check, that vm %s started because high available flag",
            config.VM_NAME[0]
        )
        self.assertTrue(
            ll_vms.waitForVMState(config.VM_NAME[1]),
            "VM %s did not start as high available" % config.VM_NAME[1]
        )

    @classmethod
    def teardown_class(cls):
        """
        Run the VM to start state
        """
        super(WatchdogHighAvailability, cls).teardown_class()
        logger.info(
            "Update vm %s high available and placement affinity parameters",
            config.VM_NAME[1]
        )
        if not ll_vms.updateVm(
            positive=True,
            vm=config.VM_NAME[1],
            placement_affinity=config.VM_USER_MIGRATABLE,
            highly_available=False
        ):
            logger.error(
                "Failed to update vm %s" % config.VM_NAME[1]
            )

#######################################################################


class WatchdogEvents(WatchdogActionTest):
    """
    Event in logs
    """
    __test__ = True
    action = 'reset'
    engine_backup_log = 'watchdog_test_event.log'

    @polarion("RHEVM3-4956")
    def test_event(self):
        """
        Test if event is displayed in log file
        """
        logger.info("Backup engine log to %s", self.engine_backup_log)
        cmd = ['cp', config.ENGINE_LOG, self.engine_backup_log]
        self.assertTrue(
            config.ENGINE_HOST.run_command(command=cmd),
            "Failed to copy engine log to %s" % self.engine_backup_log
        )

        logger.info("Kill watchdog service on vm %s", config.VM_NAME[1])
        self.kill_watchdog(config.VM_NAME[1])

        cmd = [
            'diff', config.ENGINE_LOG, self.engine_backup_log,
            '|', 'grep', 'event',
            '|', 'grep', 'Watchdog'
        ]
        logger.info("Check if new watchdog event appear under engine log")
        self.assertTrue(
            config.ENGINE_HOST.run_command(command=cmd),
            "Error: no new watchdog event under engine.log"
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove used file
        """
        cmd = ['rm', cls.engine_backup_log]
        logger.info("Remove file %s from engine", cls.engine_backup_log)
        if config.ENGINE_HOST.run_command(command=cmd)[0]:
            logger.error(
                "Failed to remove file %s from engine", cls.engine_backup_log
            )
        super(WatchdogEvents, cls).teardown_class()

#######################################################################


class WatchdogCRUDTemplate(WatchdogVM):
    """
    CRUD test for template
    """
    __test__ = True
    vm_name1 = "watchdog_template_vm1"
    vm_name2 = "watchdog_template_vm2"
    template_name = "watchdog_template"

    @bz({"1338503": {}})
    @polarion("RHEVM3-4957")
    def test_add_watchdog_template(self):
        """
        Add watchdog to clean template
        """
        self.assertTrue(
            ll_templates.add_watchdog(
                template_name=config.TEMPLATE_NAME[0],
                model='i6300esb',
                action='reset'
            )
        )

    @bz({"1338503": {}})
    @polarion("RHEVM3-4966")
    def test_detect_watchdog_template(self):
        """
        Detect watchdog
        """
        logger.info(
            "Create new vm %s from template %s",
            self.vm_name1, config.TEMPLATE_NAME[0]
        )
        self.assertTrue(
            ll_vms.createVm(
                positive=True,
                vmName=self.vm_name1,
                vmDescription="Watchdog VM",
                cluster=config.CLUSTER_NAME[0],
                template=config.TEMPLATE_NAME[0]
            ),
            "Cannot create vm %s from template %s" %
            (self.vm_name1, config.TEMPLATE_NAME[0])
        )
        logger.info("Wait until vm %s will have state down", self.vm_name1)
        self.assertTrue(
            ll_vms.waitForVMState(self.vm_name1, state=config.VM_DOWN),
            "Vm %s not in status down after creation from template" %
            self.vm_name1
        )
        logger.info("Start vm %s", self.vm_name1)
        self.assertTrue(
            ll_vms.startVm(positive=True, vm=self.vm_name1),
            "Failed to start vm %s" % self.vm_name1
        )
        self.detect_watchdog(True, self.vm_name1)

    @bz({"1338503": {}})
    @polarion("RHEVM3-4958")
    def test_remove_watchdog_template(self):
        """
        Deleting watchdog model
        """
        self.assertTrue(
            ll_templates.delete_watchdog(
                template_name=config.TEMPLATE_NAME[0]
            )
        )
        logger.info(
            "Create new vm %s from template %s",
            self.vm_name2, config.TEMPLATE_NAME[0])
        self.assertTrue(
            ll_vms.createVm(
                positive=True,
                vmName=self.vm_name2,
                vmDescription="tempalte vm",
                cluster=config.CLUSTER_NAME[0],
                template=config.TEMPLATE_NAME[0]
            ),
            "Cannot create vm %s from template %s" %
            (self.vm_name2, config.TEMPLATE_NAME[0])
        )
        logger.info("Wait until vm %s will have state down", self.vm_name2)
        self.assertTrue(
            ll_vms.waitForVMState(self.vm_name2, state=config.VM_DOWN),
            "Vm %s not in status down after creation from template" %
            self.vm_name2
        )
        logger.info("Start vm %s", self.vm_name2)
        self.assertTrue(
            ll_vms.startVm(positive=True, vm=self.vm_name2),
            "Failed to start vm %s" % self.vm_name2
        )
        self.detect_watchdog(False, self.vm_name2)

    @classmethod
    def teardown_class(cls):
        logger.info("Remove vms %s", [cls.vm_name1, cls.vm_name2])
        if not ll_vms.safely_remove_vms([cls.vm_name1, cls.vm_name2]):
            raise errors.VMException("Failed to remove vms")

######################################################################
