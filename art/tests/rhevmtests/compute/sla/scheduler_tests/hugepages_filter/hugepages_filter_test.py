"""
Scheduler - Hugepages filter test
Verify scheduler hugepages filter under different workloads, start of VM,
migration of VM, start of number of VM's
"""
import pytest
import rhevmtests.compute.sla.config as sla_conf

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, SlaTest
from art.unittest_lib import (
    tier1,
    tier2
)
from rhevmtests.compute.sla.fixtures import (
    start_vms,
    stop_vms,
    update_vms,
    define_hugepages_on_hosts,
)


@pytest.mark.usefixtures(
    define_hugepages_on_hosts.__name__,
    update_vms.__name__,
    stop_vms.__name__
)
class TestHugepagesFilter01(SlaTest):
    """
    Verify that scheduler can start VM with hugepages
    on the host with enough hugepages
    """
    hosts_to_hugepages = {0: {sla_conf.DEFAULT_HUGEPAGE_SZ: 2 * sla_conf.GB}}
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
        }
    }
    vms_to_stop = sla_conf.VM_NAME[:1]

    @tier1
    @polarion("RHEVM-23375")
    def test_vm_host(self):
        """
        Verify that VM succeeded to start on the host with hugepages
        """
        assert ll_vms.startVm(
            positive=True, vm=sla_conf.VM_NAME[0], wait_for_ip=False
        )
        testflow.step(
            "Verify that VM %s, started on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[0]
        )
        assert sla_conf.HOSTS[0] == ll_vms.get_vm_host(
            vm_name=sla_conf.VM_NAME[0]
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestHugepagesFilter02(SlaTest):
    """
    Verify that scheduler can not start VM with hugepages
    if it does not have host with enough hugepages in the same cluster
    """
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
        }
    }
    vms_to_stop = sla_conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM-23376")
    def test_vm_start(self):
        """
        Verify that VM failed to start
        """
        assert not ll_vms.startVm(
            positive=True, vm=sla_conf.VM_NAME[0], wait_for_ip=False
        )


@pytest.mark.usefixtures(
    define_hugepages_on_hosts.__name__,
    update_vms.__name__,
    start_vms.__name__
)
class TestHugepagesFilter03(SlaTest):
    """
    Verify that scheduler can migrate VM with hugepages
    on the host with enough hugepages
    """
    hosts_to_hugepages = {
        0: {sla_conf.DEFAULT_HUGEPAGE_SZ: 2 * sla_conf.GB},
        1: {sla_conf.DEFAULT_HUGEPAGE_SZ: 2 * sla_conf.GB}
    }
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
        }
    }
    vms_to_start = sla_conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier1
    @polarion("RHEVM-23377")
    def test_vm_host(self):
        """
        Verify that VM succeeded to migrate on the host with hugepages
        """
        src_host = ll_vms.get_vm_host(vm_name=sla_conf.VM_NAME[0])
        dst_host = (
            sla_conf.HOSTS[1] if src_host == sla_conf.HOSTS[0]
            else sla_conf.HOSTS[0]
        )

        assert ll_vms.migrateVm(positive=True, vm=sla_conf.VM_NAME[0])
        testflow.step(
            "Verify that VM %s, migrated on the host %s",
            sla_conf.VM_NAME[0], dst_host
        )
        assert dst_host == ll_vms.get_vm_host(
            vm_name=sla_conf.VM_NAME[0]
        )


@pytest.mark.usefixtures(
    define_hugepages_on_hosts.__name__,
    update_vms.__name__,
    start_vms.__name__
)
class TestHugepagesFilter04(SlaTest):
    """
    Verify that scheduler can not migrate VM with hugepages
    if it does not have host with enough hugepages in the same cluster
    """
    hosts_to_hugepages = {
        0: {sla_conf.DEFAULT_HUGEPAGE_SZ: 2 * sla_conf.GB}
    }
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
        }
    }
    vms_to_start = sla_conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM-23379")
    def test_vm_migration(self):
        """
        Verify that VM failed to migrate
        """
        assert not ll_vms.migrateVm(positive=True, vm=sla_conf.VM_NAME[0])


@pytest.mark.usefixtures(
    define_hugepages_on_hosts.__name__,
    update_vms.__name__,
    stop_vms.__name__
)
class TestHugepagesFilter05(SlaTest):
    """
    Verify that scheduler can not start both VM's,
    when host has hugepages only for one VM
    """
    hosts_to_hugepages = {
        0: {sla_conf.DEFAULT_HUGEPAGE_SZ: sla_conf.GB}
    }
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
        },
        sla_conf.VM_NAME[1]: {
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
        }
    }
    vms_to_stop = sla_conf.VM_NAME[:2]

    @tier2
    @polarion("RHEVM-23380")
    def test_vms_start(self):
        """
        Verify that only one VM succeeded to start
        """
        started = 0
        failed_to_start = 0
        for vm_name in sla_conf.VM_NAME[:2]:
            if not ll_vms.startVm(
                positive=True,
                vm=vm_name,
                wait_for_ip=False,
                wait_for_status=None,
                async=True
            ):
                failed_to_start += 1
            else:
                started += 1
        testflow.step("Verify that only one VM succeeded to start")
        assert started == failed_to_start


@pytest.mark.usefixtures(
    define_hugepages_on_hosts.__name__,
    update_vms.__name__,
    stop_vms.__name__
)
class TestHugepagesFilter06(SlaTest):
    """
    Verify that scheduler can not start a VM with hugepages that has a little
    bit more memory than amount of host hugepages
    """
    hosts_to_hugepages = {0: {sla_conf.DEFAULT_HUGEPAGE_SZ: sla_conf.GB}}
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES,
            sla_conf.VM_MEMORY: 1088 * sla_conf.MB
        }
    }
    vms_to_stop = sla_conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM-23381")
    def test_vm_host(self):
        """
        Verify that VM failed to start
        """
        assert not ll_vms.startVm(
            positive=True, vm=sla_conf.VM_NAME[0], wait_for_ip=False
        )
