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
from art.unittest_lib.common import testflow
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    VirtTest,
    tier1,
    tier2,
    tier3,
)
from rhevmtests import helpers
from rhevmtests.virt import config
from rhevmtests.sla import config as sla_config
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    hosts as ll_hosts
)
from fixtures import (
    base_setup_fixture, migrate_vm_for_test,
    set_cpu_toplogy, update_vm_to_ha, create_vm_for_load
)
from rhevmtests.sla.fixtures import (  # noqa: F401
    update_cluster_to_default_parameters,
    update_cluster
)


class TestCPUHotPlug(VirtTest):
    """
    CPU hot-plug  and hot-unplug testing
    """

    cluster_to_update_params = {
        sla_config.CLUSTER_THREADS_AS_CORE: True
    }
    vm_parameters = {
        'cluster': config.CLUSTER_NAME[0],
        'template': config.TEMPLATE_NAME[0],
        'os_type': config.VM_OS_TYPE,
        'display_type': config.VM_DISPLAY_TYPE,
        'name': config.CPU_HOTPLUG_VM
    }
    vm_name = vm_parameters['name']

    @tier1
    @polarion("RHEVM3-9638")
    @bz({'1453167': {'ppc': config.PPC_ARCH}})
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    def test_migrate_vm(self):
        """
        1. Test migration after increasing the number of CPUs
        2. Test migration after decreasing the number of CPUs
        """
        helper.hot_plug_unplug_cpu(
            number_of_cpus=2, action=config.HOT_PLUG_CPU
        )
        helper.migrate_vm_and_check_cpu(number_of_cpus=2)
        # unplug CPU
        helper.hot_plug_unplug_cpu(
            number_of_cpus=1, action=config.HOT_UNPLUG_CPU
        )
        helper.migrate_vm_and_check_cpu(number_of_cpus=1)

    @tier1
    @polarion("RHEVM3-9627")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    @pytest.mark.args_marker(cpu_cores=1, cpu_socket=1)
    def test_hotplug_cpu(self):
        """
        Basic hot-plug and hot-unplug case:
        Plug CPU and check it on OS, and unplug CPU and check it on OS
        """
        helper.hot_plug_unplug_cpu(
            number_of_cpus=4, action=config.HOT_UNPLUG_CPU
        )
        helper.hot_plug_unplug_cpu(
            number_of_cpus=2, action=config.HOT_UNPLUG_CPU
        )

    @tier1
    @polarion("RHEVM3-9639")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    def test_add_max_cpu(self):
        """
        Increase The number of CPUs to host cpu number, while VM is running
        """
        vm_host = ll_vms.get_vm_host(self.vm_name)
        host_resource = helpers.get_host_executor(
            ip=ll_hosts.get_host_ip(vm_host), password=config.VMS_LINUX_PW
        )

        testflow.step("Fetch the number of cpu cores in host: %s", vm_host)
        cpu_number = min(
            helper.get_number_of_cores(host_resource), 16
        )
        testflow.step(
            "Updating number of sockets on vm: %s to %d" %
            (self.vm_name, cpu_number)
        )
        assert ll_vms.updateVm(
            True, self.vm_name, cpu_cores=1, cpu_socket=cpu_number
        )
        vm_resource = helpers.get_host_executor(
            ip=hl_vms.get_vm_ip(self.vm_name), password=config.VMS_LINUX_PW
        )
        working_cores = helper.get_number_of_cores(vm_resource)
        testflow.step(
            "Verifying that after hotplug vm: %s has %d sockets" %
            (self.vm_name, cpu_number)
        )
        assert working_cores == cpu_number, (
            "The number of working cores: %s isn't correct" % working_cores
        )

    @tier2
    @polarion("RHEVM3-9629")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    @pytest.mark.args_marker(
        cpu_cores=2, cpu_socket=2, vcpu_pinning=config.VCPU_PINNING_3,
        placement_affinity=config.VM_PINNED, placement_host=0
    )
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

    @tier2
    @polarion("RHEVM3-9637")
    @pytest.mark.args_marker(hot_plug_cpu_before=False)
    @pytest.mark.usefixtures(
        create_vm_for_load.__name__,
        migrate_vm_for_test.__name__
    )
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

    @tier2
    @polarion("RHEVM-18361")
    @pytest.mark.usefixtures(
        create_vm_for_load.__name__,
        migrate_vm_for_test.__name__,
    )
    @pytest.mark.args_marker(hot_plug_cpu_before=True)
    def test_negative_hotunplug_during_migration(self):
        """
        Test hot unplug while migrating VM
        """
        testflow.step(
            "Update VM %s cpu socket to 2", config.CPU_HOTPLUG_VM_LOAD
        )
        assert not ll_vms.updateVm(
            True, config.CPU_HOTPLUG_VM_LOAD, cpu_socket=2
        ), "hot plug  worked while migrating VM "

    @tier3
    @polarion("RHEVM-22074")
    @pytest.mark.usefixtures(
        base_setup_fixture.__name__,
        set_cpu_toplogy.__name__,
        update_cluster.__name__,
    )
    @pytest.mark.args_marker(placement_host=0)
    def test_negative_thread_cpu(self):
        """
        Test CPU hot plug while threads is enabled on the cluster
        Set number of threads to over the host threads number,
        and check that action failed.
        """
        testflow.step(
            "Update VM %s cpu socket to %d" %
            (self.vm_name, config.CPU_TOPOLOGY[0] * 10)
        )
        assert not ll_vms.updateVm(
            True, self.vm_name, cpu_socket=config.CPU_TOPOLOGY[0] * 10
        )

    @tier2
    @polarion("RHEVM3-9630")
    @pytest.mark.usefixtures(
        update_cluster.__name__,
        base_setup_fixture.__name__,
        set_cpu_toplogy.__name__,
    )
    @pytest.mark.args_marker(placement_host=0)
    def test_thread_cpu(self):
        """
        Test CPU hot plug while threads is enabled on the cluster
        Set number of threads to max cpu topology but not pass the limit of 16
        CPU.
        """

        num_of_cpus = min(config.CPU_TOPOLOGY[0], 16)
        testflow.step(
            "Update VM %s cpu socket to %d" % (self.vm_name, num_of_cpus)
        )
        assert ll_vms.updateVm(
            True, self.vm_name, cpu_socket=num_of_cpus
        )

    @tier3
    @polarion("RHEVM3-9630")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    def test_suspend_vm(self):
        """
        Hot plug CPU -> suspend VM -> resume VM -> hot unplug CPU
        """
        helper.hot_plug_unplug_cpu(
            number_of_cpus=4, action=config.HOT_PLUG_CPU
        )
        testflow.step("Suspend VM")
        assert ll_vms.suspendVm(positive=True, vm=self.vm_name)
        testflow.step("Resume VM")
        assert ll_vms.startVm(
            positive=True,
            vm=self.vm_name,
            wait_for_ip=True,
            wait_for_status=config.VM_UP
        )
        helper.hot_plug_unplug_cpu(
            number_of_cpus=2, action=config.HOT_UNPLUG_CPU
        )

    @tier3
    @polarion("RHEVM-19126")
    @pytest.mark.usefixtures(update_vm_to_ha.__name__)
    def test_ha_vm(self):
        """
        HA VM:
        Case 1: Hot plug CPU
        Case 2: Hot unplug CPU
        """
        helper.hot_plug_unplug_cpu(
            number_of_cpus=4, action=config.HOT_PLUG_CPU
        )
        helper.hot_plug_unplug_cpu(
            number_of_cpus=2, action=config.HOT_UNPLUG_CPU
        )
