"""
Hot Plug and Unplug CPU - Testing
- Test hot plug cpu , and hot unplug cpu
- Test that the number of CPUs changed is also changed on the VM OS
- Test hot plug with host maximum cpu
- Test migration after hot plug cpu and unplug
- Test CPU hot plug while threads is enabled on the cluster.
- Negative test: check hot plug cpu while migration
- Negative test: check hot unplug cpu while migration
- Negative test: check hot unplug while cores are pinned
"""
import pytest
import helper
from art.test_handler.tools import polarion
from art.unittest_lib import common
from rhevmtests import helpers
from rhevmtests.virt import config
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from fixtures import (
    base_setup_fixture, migrate_vm_for_test,
    set_cpu_toplogy, enable_cluster_cpu_threading
)
from _pytest_art.testlogger import TestFlowInterface

testflow = TestFlowInterface


@common.attr(tier=1)
@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class CPUHotPlugClass(common.VirtTest):
    """
    Base Class for hot plug cpu
    """

    __test__ = True
    vm_name = config.CPU_HOTPLUG_VM
    hot_plug_cpu_before = False

    @polarion("RHEVM3-9638")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    def test_migrate_vm(self):
        """
        1. Test migration after increasing the number of CPUs
        2. Test migration after decreasing the number of CPUs
        """
        testflow.step(
            "HOT-PLUG CPU CASE:\nUpdating number of cpu sockets on vm: %s to "
            "%d", self.vm_name, 2
        )
        assert ll_vms.updateVm(True, self.vm_name, cpu_socket=2)
        testflow.step("migrating vm: %s", self.vm_name)
        assert ll_vms.migrateVm(True, self.vm_name)
        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(self.vm_name), config.VMS_LINUX_PW
        )
        testflow.step(
            "Verifying that after migration vm: %s has %d cpus",
            self.vm_name, 2
        )
        assert helper.get_number_of_cores(vm_resource) == 2, (
            "The Cores number should be 2 and not: %s" %
            ll_vms.get_vm_cores(self.vm_name)
        )
        testflow.step(
            "HOT-UNPLUG CPU CASE:\nUpdating number of cpu sockets on vm: %s "
            "to %d", self.vm_name, 1
        )
        assert ll_vms.updateVm(True, self.vm_name, cpu_socket=1)
        testflow.step("migrating vm: %s", self.vm_name)
        assert ll_vms.migrateVm(True, self.vm_name)
        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(self.vm_name), config.VMS_LINUX_PW
        )
        testflow.step(
            "Verifying that after migration vm: %s has %d cpus",
            self.vm_name, 1
        )
        assert helper.get_number_of_cores(vm_resource) == 1, (
            "The Cores number should be 1 and not: %s" %
            ll_vms.get_vm_cores(self.vm_name)
        )

    @polarion("RHEVM3-9627")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    @pytest.mark.args_marker(cpu_cores=1, cpu_socket=1)
    def test_hotplug_cpu(self):
        """
        Basic hot-plug and hot-unplug case:
        Plug CPU and check it on OS, and unplug CPU and check it on OS
        """
        testflow.step(
            "HOT-PLUG CPU CASE:\nUpdating cpu sockets on vm: %s to %d",
            self.vm_name, 4
        )
        assert ll_vms.updateVm(True, self.vm_name, cpu_socket=4)
        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(self.vm_name), config.VMS_LINUX_PW
        )
        working_cores = helper.get_number_of_cores(vm_resource)
        testflow.step(
            "Verifying that after hotplug vm: %s has %d cpus",
            self.vm_name, 4
        )
        assert working_cores == 4, (
            "The number of working cores: %s isn't correct" % working_cores
        )
        testflow.step(
            "HOT-UNPLUG CPU CASE:\nUpdating cpu sockets on vm: %s to %d",
            self.vm_name, 2
        )
        assert ll_vms.updateVm(True, self.vm_name, cpu_socket=2)
        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(self.vm_name), config.VMS_LINUX_PW
        )
        working_cores = helper.get_number_of_cores(vm_resource)
        testflow.step(
            "Verifying that after hotplug vm: %s has %d cpus",
            self.vm_name, 2
        )
        assert working_cores == 2, (
            "The number of working cores: %s isn't correct" % working_cores
        )

    @polarion("RHEVM3-9639")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    def test_add_max_cpu(self):
        """
        Increase The number of CPUs to host cpu number, while VM is running
        """
        host_index = config.HOSTS.index(ll_vms.get_vm_host(self.vm_name))
        testflow.step(
            "Fetch the number of cpu cores in host: %s",
            config.VDS_HOSTS[host_index]
        )
        cpu_number = helper.get_number_of_cores(config.VDS_HOSTS[host_index])
        testflow.step(
            "Updating number of sockets on vm: %s to %d",
            self.vm_name, cpu_number
        )
        assert ll_vms.updateVm(
            True, self.vm_name, cpu_cores=1, cpu_socket=cpu_number
        )
        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(self.vm_name), config.VMS_LINUX_PW
        )
        working_cores = helper.get_number_of_cores(vm_resource)
        testflow.step(
            "Verifying that after hotplug vm: %s has %d sockets",
            self.vm_name, cpu_number
        )
        assert working_cores == cpu_number, (
            "The number of working cores: %s isn't correct" % working_cores
        )

    @polarion("RHEVM3-9629")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    @pytest.mark.args_marker(
        cpu_cores=2, cpu_socket=2, vcpu_pinning=config.VCPU_PINNING_3,
        placement_affinity=config.VM_PINNED, placement_host=0
    )
    @common.attr(tier=2)
    def test_negative_cpu_pinning(self):
        """
        Negative test - unplug vm CPUs (4 to 2) while
        cpu pinning defined to 3 first CPUs and VM is running
        """
        testflow.step(
            "Attempting to reduce number of cpu cores to 1 - expecting to fail"
        )
        assert not ll_vms.updateVm(
            True, self.vm_name, cpu_socket=1
        ), "The action of remove cores didn't failed"

    @polarion("RHEVM3-9637")
    @pytest.mark.usefixtures(migrate_vm_for_test.__name__)
    @common.attr(tier=2)
    def test_negative_hotplug_during_migration(self):
        """
        Test hot plug while migrating VM
        """
        testflow.step(
            "Update VM %s cpu socket to 2", config.CPU_HOTPLUG_VM_LOAD
        )
        assert not ll_vms.updateVm(
            True, config.CPU_HOTPLUG_VM_LOAD, cpu_socket=2
        ), "hot plug  worked while migrating VM "

    @polarion("RHEVM-18361")
    @pytest.mark.usefixtures(migrate_vm_for_test.__name__)
    @common.attr(tier=2)
    def test_negative_hotunplug_during_migration(self):
        """
        Test hot unplug while migrating VM
        """
        self.hot_plug_cpu_before = True
        testflow.step(
            "Update VM %s cpu socket to 2", config.CPU_HOTPLUG_VM_LOAD
        )
        assert not ll_vms.updateVm(
            True, config.CPU_HOTPLUG_VM_LOAD, cpu_socket=2
        ), "hot plug  worked while migrating VM "

    @polarion("RHEVM3-9630")
    @pytest.mark.usefixtures(
        set_cpu_toplogy.__name__, enable_cluster_cpu_threading.__name__,
        base_setup_fixture.__name__
    )
    @pytest.mark.args_marker(placement_host=0)
    @common.attr(tier=2)
    def test_negative_thread_cpu(self):
        """
        Test CPU hot plug while threads is enabled on the cluster
        Set number of threads to over the host threads number,
        and check that action failed.
        """
        testflow.step(
            "Update VM %s cpu socket to %d",
            self.vm_name, config.CPU_TOPOLOGY[0] * 10
        )
        assert not ll_vms.updateVm(
            True, self.vm_name, cpu_socket=config.CPU_TOPOLOGY[0] * 10
        )