"""
VM custom property - Hugepages
Verify hugepages custom property with different values definition
on one or more VM's
"""
import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.compute.sla.config as sla_conf
import rhevmtests.compute.sla.helpers as sla_helpers
from art.test_handler.tools import polarion, bz
from art.unittest_lib import testflow, SlaTest
from art.unittest_lib import (
    tier1,
    tier2
)
from rhevmtests.compute.sla.fixtures import (
    create_equals_numa_nodes_on_vm,
    define_hugepages_on_hosts,
    skip_numa_tests,
    remove_all_numa_nodes_from_vm,
    start_vms,
    update_vms,
)


@pytest.mark.usefixtures(
    define_hugepages_on_hosts.__name__,
    update_vms.__name__,
    start_vms.__name__
)
class Hugepages(SlaTest):
    """
    Base class for all hugepages tests
    """
    total_hugepages_size = None

    def calculate_expected_nr_hugepages(
        self, vms_memory_consumption, hugepage_size
    ):
        """
        Calculate expected number of hugepages on the host after VM start

        Args:
            vms_memory_consumption (int): VM's memory consumption
            hugepage_size (int): Hugepage size

        Returns:
            int: The expected number of hugepages on the host after VM start
        """
        host_expected_memory = (
            self.total_hugepages_size[hugepage_size] - vms_memory_consumption
        )
        return host_expected_memory / (int(hugepage_size) * 1024)


class TestHugepages01(Hugepages):
    """
    Verify that VM consumes expected number of hugepages on the host
    """
    total_hugepages_size = {
        sla_conf.DEFAULT_HUGEPAGE_SZ: sla_conf.GB_2
    }
    hosts_to_hugepages = {0: total_hugepages_size}
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_PLACEMENT_HOSTS: [0],
            sla_conf.VM_PLACEMENT_AFFINITY: sla_conf.VM_PINNED,
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
        }
    }
    vms_to_start = sla_conf.VM_NAME[:1]

    @tier1
    @bz({"1495213": {}})
    @polarion("RHEVM-23425")
    def test_hugepages_consumption(self):
        """
        Verify hugepages consumption on the host
        """
        expected_hugepages_nr = self.calculate_expected_nr_hugepages(
            vms_memory_consumption=sla_conf.GB,
            hugepage_size=sla_conf.DEFAULT_HUGEPAGE_SZ
        )
        testflow.step(
            "Verify that VM %s consumes 1Gb of hugepages on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[0]
        )
        assert sla_helpers.wait_for_host_hugepages(
            host_name=sla_conf.HOSTS[0],
            hugepage_size=sla_conf.DEFAULT_HUGEPAGE_SZ,
            expected_hugepages_nr=expected_hugepages_nr
        )


class TestHugepages02(Hugepages):
    """
    Verify that VM's consume expected number of hugepages on the host after
    start and stop action
    """
    total_hugepages_size = {
        sla_conf.DEFAULT_HUGEPAGE_SZ: sla_conf.GB_2
    }
    hosts_to_hugepages = {0: total_hugepages_size}
    vms_to_params = dict(
        (
            sla_conf.VM_NAME[i], {
                sla_conf.VM_PLACEMENT_HOSTS: [0],
                sla_conf.VM_PLACEMENT_AFFINITY: sla_conf.VM_PINNED,
                sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
            }
        ) for i in xrange(2)
    )
    vms_to_start = sla_conf.VM_NAME[:2]

    @tier1
    @bz({"1495213": {}})
    @polarion("RHEVM-23426")
    def test_hugepages_consumption(self):
        """
        Verify hugepages consumption on the host
        """
        testflow.step(
            "Verify that VM's consume all host %s hugepages", sla_conf.HOSTS[0]
        )
        assert sla_helpers.wait_for_host_hugepages(
            host_name=sla_conf.HOSTS[0],
            hugepage_size=sla_conf.DEFAULT_HUGEPAGE_SZ,
            expected_hugepages_nr=0
        )

        assert ll_vms.stopVm(positive=True, vm=sla_conf.VM_NAME[1])

        expected_hugepages_nr = self.calculate_expected_nr_hugepages(
            vms_memory_consumption=sla_conf.GB,
            hugepage_size=sla_conf.DEFAULT_HUGEPAGE_SZ
        )
        testflow.step(
            "Verify that VM %s consumes 1Gb of hugepages on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[0]
        )
        assert sla_helpers.wait_for_host_hugepages(
            host_name=sla_conf.HOSTS[0],
            hugepage_size=sla_conf.DEFAULT_HUGEPAGE_SZ,
            expected_hugepages_nr=expected_hugepages_nr
        )


class TestHugepages03(Hugepages):
    """
    Verify VM's hugepages consumption with different sizes of hugepages
    """
    total_hugepages_size = {
        sla_conf.DEFAULT_HUGEPAGE_SZ: sla_conf.GB_2,
        sla_conf.HUGEPAGE_SZ_1048576KB: sla_conf.GB_2
    }
    hosts_to_hugepages = {0: total_hugepages_size}
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_PLACEMENT_HOSTS: [0],
            sla_conf.VM_PLACEMENT_AFFINITY: sla_conf.VM_PINNED,
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
        },
        sla_conf.VM_NAME[1]: {
            sla_conf.VM_PLACEMENT_HOSTS: [0],
            sla_conf.VM_PLACEMENT_AFFINITY: sla_conf.VM_PINNED,
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.CP_HUGEPAGES_SIZE_1048576KB
        }
    }
    vms_to_start = sla_conf.VM_NAME[:2]

    @tier1
    @bz({"1495213": {}})
    @polarion("RHEVM-23427")
    def test_hugepages_consumption(self):
        """
        Verify hugepages consumption on the host
        """
        for hugepage_size in (
            sla_conf.DEFAULT_HUGEPAGE_SZ, sla_conf.HUGEPAGE_SZ_1048576KB
        ):
            expected_hugepages_nr = self.calculate_expected_nr_hugepages(
                vms_memory_consumption=sla_conf.GB,
                hugepage_size=hugepage_size
            )
            testflow.step(
                "Verify that VM's consumes 1Gb of hugepages "
                "with size %s on the host %s",
                hugepage_size, sla_conf.HOSTS[0]
            )
            assert sla_helpers.wait_for_host_hugepages(
                host_name=sla_conf.HOSTS[0],
                hugepage_size=hugepage_size,
                expected_hugepages_nr=expected_hugepages_nr
            )


class TestHugepages04(Hugepages):
    """
    Verify that the engine does not give to hot-plug memory
    to VM with hugepages
    """
    total_hugepages_size = {
        sla_conf.DEFAULT_HUGEPAGE_SZ: sla_conf.GB_2
    }
    hosts_to_hugepages = {0: total_hugepages_size}
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_PLACEMENT_HOSTS: [0],
            sla_conf.VM_PLACEMENT_AFFINITY: sla_conf.VM_PINNED,
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.DEFAULT_CP_HUGEPAGES
        }
    }
    vms_to_start = sla_conf.VM_NAME[:1]

    @tier2
    @bz({"1495535": {}})
    @polarion("RHEVM-24519")
    def test_memory_hotplug(self):
        """
        Verify VM memory hot-plug action
        """
        assert not ll_vms.updateVm(
            positive=True, vm=sla_conf.VM_NAME[0], memory=sla_conf.GB_2
        )


@pytest.mark.usefixtures(
    skip_numa_tests.__name__,
    define_hugepages_on_hosts.__name__,
    update_vms.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    start_vms.__name__
)
class TestHugepages05(SlaTest):
    """
    Verify that the engine block VM start, when it has NUMA nodes with memory
    that not divided by hugepage size(relevant for 1GB hugepages only)
    """
    total_hugepages_size = {
        sla_conf.HUGEPAGE_SZ_1048576KB: sla_conf.GB_4
    }
    hosts_to_hugepages = {0: total_hugepages_size}
    vms_to_params = {
        sla_conf.VM_NAME[0]: {
            sla_conf.VM_MEMORY: sla_conf.GB_3,
            sla_conf.VM_CPU_CORES: 2,
            sla_conf.VM_PLACEMENT_HOSTS: [0],
            sla_conf.VM_PLACEMENT_AFFINITY: sla_conf.VM_PINNED,
            sla_conf.VM_CUSTOM_PROPERTIES: sla_conf.CP_HUGEPAGES_SIZE_1048576KB
        }
    }
    num_of_vm_numa_nodes = 2
    vms_to_start = sla_conf.VM_NAME[:1]

    @tier2
    @bz({"1515933": {}})
    @polarion("RHEVM-24710")
    def test_vm_start(self):
        """
        Verify VM memory hot-plug action
        """
        assert not ll_vms.startVm(
            positive=True, vm=sla_conf.VM_NAME[0], wait_for_status=None
        )
