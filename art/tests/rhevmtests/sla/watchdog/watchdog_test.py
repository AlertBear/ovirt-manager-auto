"""
Tests covers:
    VM and template CRUD tests
    Installation of watchdog software
    Watchdog event in event tab of webadmin portal
    Watchdog poweroff action on HA VM
    Watchdog action with migration of VM
    Triggering watchdog actions (dump, none, pause, poweroff, reset)
"""
import re
import time

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers
import pytest
from art.test_handler.tools import polarion
from fixtures import (
    add_watchdog_device_to_vm,
    add_watchdog_device_to_template,
    backup_engine_log,
    install_watchdog_on_vm
)
from rhevmtests.sla.fixtures import (
    make_vm_from_template,
    start_vms,
    stop_vms,
    update_vms
)


@u_libs.attr(tier=1)
@pytest.mark.usefixtures(stop_vms.__name__)
class TestWatchdogCRUDVm(u_libs.SlaTest):
    """
    1) Add watchdog device to the VM
    2) Check that watchdog device appears under the VM
    3) Remove watchdog device from the VM
    """
    __test__ = True
    vms_to_stop = [conf.VM_NAME[0]]

    @staticmethod
    def start_vm_and_check_watchdog_device(positive):
        """
        1) Start the VM
        2) Check that watchdog device exists under the VM

        Args:
            positive (bool): Positive or negative behaviour
        """
        u_libs.testflow.step("Start VM %s", conf.VM_NAME[0])
        assert ll_vms.startVm(
            positive=True, wait_for_status=conf.VM_UP, vm=conf.VM_NAME[0]
        )

        log_msg = "appears under" if positive else "disappears from"
        u_libs.testflow.step(
            "Check that watchdog device %s VM %s OS",
            log_msg, conf.VM_NAME[0]
        )
        assert helpers.detect_watchdog_on_vm(
            positive=positive, vm_name=conf.VM_NAME[0]
        )

    @polarion("RHEVM3-4953")
    def test_add_watchdog(self):
        """
        Add watchdog device to VM and start the VM
        """
        u_libs.testflow.step("Add watchdog device to VM %s", conf.VM_NAME[0])
        assert ll_vms.add_watchdog(
            vm_name=conf.VM_NAME[0],
            model=conf.WATCHDOG_MODEL,
            action=conf.WATCHDOG_ACTION_RESET
        )

    @polarion("RHEVM3-4952")
    def test_detect_watchdog(self):
        """
        Check that watchdog device appears under the VM
        """
        self.start_vm_and_check_watchdog_device(positive=True)

    @polarion("RHEVM3-4965")
    def test_remove_watchdog(self):
        """
        Remove watchdog device from the VM
        """
        u_libs.testflow.step("Stop VM %s", conf.VM_NAME[0])
        assert ll_vms.stop_vms_safely(vms_list=[conf.VM_NAME[0]])

        u_libs.testflow.step(
            "Remove watchdog device from VM %s", conf.VM_NAME[0]
        )
        assert ll_vms.delete_watchdog(vm_name=conf.VM_NAME[0])

        self.start_vm_and_check_watchdog_device(positive=False)


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(start_vms.__name__)
class TestWatchdogInstall(u_libs.SlaTest):
    """
    Install watchdog on the VM
    """
    __test__ = True
    vms_to_start = [conf.VM_NAME[1]]

    @polarion("RHEVM3-4967")
    def test_install_watchdog(self):
        """
        Install watchdog and enable service
        """
        u_libs.testflow.step(
            "Install and run watchdog service on VM %s", conf.VM_NAME[1]
        )
        assert helpers.install_watchdog_on_vm(vm_name=conf.VM_NAME[1])


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    add_watchdog_device_to_vm.__name__,
    start_vms.__name__,
    install_watchdog_on_vm.__name__
)
class BaseWatchdogAction(u_libs.SlaTest):
    """
    Base class to test different watchdog action functionality
    """
    vms_to_start = [conf.VM_NAME[0]]
    watchdog_vm = conf.VM_NAME[0]

    @staticmethod
    def wait_for_watchdog_action_and_check_vm_state():
        """
        1) Wait for watchdog action
        2) Check that VM has state UP
        """
        u_libs.testflow.step(
            "Wait %s seconds for the watchdog action", conf.WATCHDOG_TIMER
        )
        time.sleep(conf.WATCHDOG_TIMER)

        u_libs.testflow.step(
            "Check that VM %s has state %s", conf.VM_NAME[0], conf.VM_UP
        )
        assert ll_vms.get_vm_state(vm_name=conf.VM_NAME[0]) == conf.VM_UP

    @staticmethod
    def kill_watchdog_and_wait_for_vm_state(vm_name, vm_state):
        """
        1) Kill watchdog process on the VM
        2) Wait for VM state

        Args:
            vm_name (str): VM name
            vm_state (str): Expected VM state
        """
        u_libs.testflow.step("Kill watchdog service on VM %s", vm_name)
        assert helpers.kill_watchdog_on_vm(vm_name=vm_name)

        u_libs.testflow.step(
            "Wait until VM %s will have state %s", vm_name, vm_state
        )
        assert ll_vms.waitForVMState(vm=vm_name, state=vm_state)


class TestWatchdogActionNone(BaseWatchdogAction):
    """
    Test watchdog action none
    """
    __test__ = True
    watchdog_action = conf.WATCHDOG_ACTION_NONE

    @polarion("RHEVM3-4959")
    def test_action_none(self):
        """
        1) Kill watchdog device on the VM
        2) Check that VM has state UP
        """
        u_libs.testflow.step("Kill watchdog service on VM %s", conf.VM_NAME[0])
        assert helpers.kill_watchdog_on_vm(vm_name=conf.VM_NAME[0])

        self.wait_for_watchdog_action_and_check_vm_state()


class TestWatchdogActionReset(BaseWatchdogAction):
    """
    Test watchdog action reset
    """
    __test__ = True
    watchdog_action = conf.WATCHDOG_ACTION_RESET

    @polarion("RHEVM3-4962")
    def test_action_reset(self):
        """
        1) Kill watchdog device on the VM
        2) Check that VM was restarted
        """
        self.kill_watchdog_and_wait_for_vm_state(
            vm_name=conf.VM_NAME[0], vm_state=conf.VM_REBOOT
        )

        u_libs.testflow.step(
            "Wait until VM %s will have state %s", conf.VM_NAME[0], conf.VM_UP
        )
        assert ll_vms.waitForVMState(vm=conf.VM_NAME[0], state=conf.VM_UP)


class TestWatchdogActionPoweroff(BaseWatchdogAction):
    """
    Test watchdog action poweroff
    """
    __test__ = True
    watchdog_action = conf.WATCHDOG_ACTION_POWEROFF

    @polarion("RHEVM3-4963")
    def test_action_poweroff(self):
        """
        1) Kill watchdog device on the VM
        2) Check that VM has state DOWN
        """
        self.kill_watchdog_and_wait_for_vm_state(
            vm_name=conf.VM_NAME[0], vm_state=conf.VM_DOWN
        )


class TestWatchdogActionPause(BaseWatchdogAction):
    """
    Test watchdog action pause
    """
    __test__ = True
    watchdog_action = conf.WATCHDOG_ACTION_PAUSE

    @polarion("RHEVM3-4961")
    def test_action_pause(self):
        """
        1) Kill watchdog device on the VM
        2) Check that VM has state PAUSED
        """
        self.kill_watchdog_and_wait_for_vm_state(
            vm_name=conf.VM_NAME[0], vm_state=conf.VM_PAUSED
        )


class TestWatchdogActionDump(BaseWatchdogAction):
    """
    Test watchdog action dump
    """
    __test__ = True
    watchdog_action = conf.WATCHDOG_ACTION_DUMP

    @staticmethod
    def get_host_dump_path(host_resource):
        """
        Get host dump path

        Args:
            host_resource (VDS): Host resource

        Returns:
            str: Host dump path
        """
        cmd = ["grep", "^auto_dump_path", conf.QEMU_CONF]
        rc, out, _ = host_resource.run_command(command=cmd)
        if rc:
            return conf.DUMP_PATH
        else:
            regex = r"auto_dump_path=\"(.+)\""
            dump_path = re.search(regex, out).group(1)
            return dump_path

    @polarion("RHEVM3-4960")
    def test_action_dump(self):
        """
        Test watchdog action dump
        """
        host_resource = conf.VDS_HOSTS[
            conf.HOSTS.index(ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]))
        ]
        dump_path = self.get_host_dump_path(host_resource=host_resource)
        cmd = ["ls", "-l", dump_path, "|", "wc", "-l"]

        u_libs.testflow.step(
            "%s: check number of dump files under %s", host_resource, dump_path
        )
        rc, out, _ = host_resource.run_command(command=cmd)
        assert not rc
        logs_count = int(out)

        u_libs.testflow.step("Kill watchdog service on VM %s", conf.VM_NAME[0])
        helpers.kill_watchdog_on_vm(vm_name=conf.VM_NAME[0])

        u_libs.testflow.step(
            "Wait %s seconds for the watchdog action", conf.WATCHDOG_TIMER
        )
        time.sleep(conf.WATCHDOG_TIMER)

        u_libs.testflow.step(
            "%s: check new number of dump files under %s",
            host_resource, dump_path
        )
        rc, out, _ = host_resource.run_command(command=cmd)
        assert not rc

        u_libs.testflow.step(
            "Old number of dump files: %s; New number of dump files %s",
            logs_count, out
        )
        assert logs_count + 1 == int(out)


class TestWatchdogMigration(BaseWatchdogAction):
    """
    Test watchdog with migration of VM
    """
    __test__ = True
    watchdog_action = conf.WATCHDOG_ACTION_POWEROFF

    @polarion("RHEVM3-4954")
    def test_migration(self):
        """
        Tess that migration does not trigger watchdog action
        """
        u_libs.testflow.step("Migrate VM %s", conf.VM_NAME[0])
        assert ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])

        self.wait_for_watchdog_action_and_check_vm_state()


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    add_watchdog_device_to_vm.__name__,
    update_vms.__name__,
    start_vms.__name__,
    install_watchdog_on_vm.__name__
)
class TestWatchdogHighAvailability(u_libs.SlaTest):
    """
    Test watchdog action poweroff on the HA VM
    """
    __test__ = True
    vms_to_start = [conf.VM_NAME[0]]
    watchdog_vm = conf.VM_NAME[0]
    watchdog_action = conf.WATCHDOG_ACTION_POWEROFF
    vms_to_params = {conf.VM_NAME[0]: {conf.VM_HIGHLY_AVAILABLE: True}}

    @polarion("RHEVM3-4955")
    def test_high_availability(self):
        """
        1) Kill watchdog device on the VM
        2) Check that the engine starts the HA VM
        """
        u_libs.testflow.step("Kill watchdog service on VM %s", conf.VM_NAME[0])
        assert helpers.kill_watchdog_on_vm(vm_name=conf.VM_NAME[0])

        u_libs.testflow.step(
            "Wait until VM %s will have state %s",
            conf.VM_NAME[0], conf.VM_POWERING_UP
        )
        assert ll_vms.waitForVMState(
            vm=conf.VM_NAME[0], state=conf.VM_POWERING_UP
        )


@pytest.mark.usefixtures(backup_engine_log.__name__)
class TestWatchdogEvents(BaseWatchdogAction):
    """
    Test watchdog events
    """
    __test__ = True
    watchdog_action = conf.WATCHDOG_ACTION_RESET

    @polarion("RHEVM3-4956")
    def test_watchdog_event(self):
        """
        1) Kill watchdog process on the VM
        2) Check that watchdog event appears under the engine log
        """
        self.kill_watchdog_and_wait_for_vm_state(
            vm_name=conf.VM_NAME[0], vm_state=conf.VM_REBOOT
        )

        u_libs.testflow.step(
            "Wait until VM %s will have state %s", conf.VM_NAME[0], conf.VM_UP
        )
        assert ll_vms.waitForVMState(vm=conf.VM_NAME[0], state=conf.VM_UP)

        cmd = [
            "diff", conf.ENGINE_LOG, conf.ENGINE_TEMP_LOG,
            "|", "grep", "event",
            "|", "grep", "Watchdog"
        ]
        u_libs.testflow.step(
            "Check that new watchdog event appears under the engine log"
        )
        assert not conf.ENGINE_HOST.run_command(command=cmd)[0]


@u_libs.attr(tier=1)
@pytest.mark.usefixtures(
    add_watchdog_device_to_template.__name__,
    make_vm_from_template.__name__,
    start_vms.__name__
)
class TestWatchdogCRUDTemplate(u_libs.SlaTest):
    """
    1) Add watchdog device to the template
    2) Create new VM from the template and
     check that new VM has watchdog device
    3) Remove watchdog device from the template
    """
    __test__ = True
    watchdog_template = conf.TEMPLATE_NAME[0]
    watchdog_action = conf.WATCHDOG_ACTION_RESET
    template_name = conf.TEMPLATE_NAME[0]
    vm_from_template_name = conf.VM_FROM_TEMPLATE_WATCHDOG
    vms_to_start = [conf.VM_FROM_TEMPLATE_WATCHDOG]

    @polarion("RHEVM3-4957")
    def test_detect_watchdog_template(self):
        """
        Detect if watchdog device exists on the new VM
        """
        u_libs.testflow.step(
            "Check that watchdog device appears under VM %s OS",
            conf.VM_FROM_TEMPLATE_WATCHDOG
        )
        helpers.detect_watchdog_on_vm(
            positive=True, vm_name=conf.VM_FROM_TEMPLATE_WATCHDOG
        )
