"""
High Performance VM tests
    - Create, update and remove high performance VM
    - Verify CPU cache level 3
    - Verify host single pinning with HA option
    - Create template
    - Create VM pool
    - Verify auto-pinning for IO and emulator threads
"""
import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helpers
import rhevmtests.compute.sla.helpers as sla_helpers
import rhevmtests.compute.sla.high_performance_vm.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, tier1, tier2, SlaTest
from fixtures import (
    fill_numa_nodes_constants,
    update_vm_cpu_and_numa_pinning
)
from rhevmtests.compute.sla.fixtures import (
    create_custom_numa_nodes_on_vm,
    create_equals_numa_nodes_on_vm,
    make_template_from_vm,
    make_vm_from_template,
    remove_all_numa_nodes_from_vm,
    skip_numa_tests,
    start_vms,
    update_vms
)
from rhevmtests.compute.virt.fixtures import create_vm_pool


class TestHighPerformanceVMSanity01(SlaTest):
    """
    Sanity tests for high performance VM
    """

    @tier1
    @polarion("RHEVM-23433")
    def test_create_and_remove_vm(self):
        """
        Create and remove high performance VM
        """
        assert ll_vms.addVm(
            positive=True,
            name=conf.HIGH_PERFORMANCE_VM,
            cluster=conf.CLUSTER_NAME[0],
            template=conf.BLANK_TEMPlATE,
            type=conf.VM_TYPE_HIGH_PERFORMANCE
        )
        assert ll_vms.safely_remove_vms(vms=[conf.HIGH_PERFORMANCE_VM])

    @tier1
    @polarion("RHEVM-23432")
    def test_update_vm_to_be_high_performance_vm(self):
        """
        Update existing VM to be high performance
        """
        assert ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            type=conf.VM_TYPE_HIGH_PERFORMANCE
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            type=conf.VM_TYPE_SERVER
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    make_template_from_vm.__name__,
    make_vm_from_template.__name__
)
class TestHighPerformanceVMSanity02(SlaTest):
    """
    Create template from high performance VM and verify that template inherits
    high performance type
    """
    vms_to_params = {
        conf.VM_NAME[0]: {conf.VM_TYPE: conf.VM_TYPE_HIGH_PERFORMANCE}
    }
    vm_for_template = conf.VM_NAME[0]
    template_name = conf.HIGH_PERFORMANCE_TEMPLATE
    vm_from_template_name = conf.HIGH_PERFORMANCE_VM

    @tier1
    @polarion("RHEVM-23434")
    def test_new_vm_type(self):
        """
        Verify that VM that was created from template has high performance type
        """
        testflow.step(
            "Verify that VM %s has type '%s'",
            conf.VM_NAME[0], conf.VM_TYPE_HIGH_PERFORMANCE
        )
        assert ll_vms.get_vm_type(
            vm_name=conf.VM_NAME[0]
        ) == conf.VM_TYPE_HIGH_PERFORMANCE


@pytest.mark.usefixtures(
    update_vms.__name__,
    make_template_from_vm.__name__,
    create_vm_pool.__name__
)
class TestHighPerformanceVMSanity03(SlaTest):
    """
    Create VM pool from high performance template and verify that pool has
    high performance type
    """
    vms_to_params = {
        conf.VM_NAME[0]: {conf.VM_TYPE: conf.VM_TYPE_HIGH_PERFORMANCE}
    }
    vm_for_template = conf.VM_NAME[0]
    template_name = conf.HIGH_PERFORMANCE_TEMPLATE
    vm_pool_config = {
        "name": conf.HIGH_PERFORMANCE_POOL,
        "template": conf.HIGH_PERFORMANCE_TEMPLATE,
        "cluster": conf.CLUSTER_NAME[0],
        "size": 1
    }

    @tier1
    @polarion("RHEVM-23435")
    def test_new_vm_type(self):
        """
        Verify that VM that was created from template has high performance type
        """
        vm_name = "{0}-1".format(conf.HIGH_PERFORMANCE_POOL)
        testflow.step(
            "Verify that VM %s has type '%s'",
            vm_name, conf.VM_TYPE_HIGH_PERFORMANCE
        )
        assert ll_vms.get_vm_type(
            vm_name=vm_name
        ) == conf.VM_TYPE_HIGH_PERFORMANCE


@pytest.mark.usefixtures(
    update_vms.__name__
)
class TestHighPerformanceVMSanity04(SlaTest):
    """
    Verify that high performance VM pinned to a single host
    can be high available
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_TYPE: conf.VM_TYPE_HIGH_PERFORMANCE,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    vm_for_template = conf.VM_NAME[0]
    template_name = conf.HIGH_PERFORMANCE_TEMPLATE

    @tier1
    @polarion("RHEVM-24301")
    def test_update_vm_to_be_high_available(self):
        """
        Verify that VM that was created from template has high performance type
        """
        assert ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            highly_available=True
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    start_vms.__name__
)
class TestHighPerformanceVMSanity05(SlaTest):
    """
    Verify that high performance VM has enabled CPU cache level 3
    """
    vms_to_params = {
        conf.VM_NAME[0]: {conf.VM_TYPE: conf.VM_TYPE_HIGH_PERFORMANCE}
    }
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier1
    @polarion("RHEVM-24285")
    def test_cpu_cache_level(self):
        """
        Verify that VM has enabled CPU cache level 3
        """
        helpers.get_io_and_emulator_cpu_pinning(vm_name=conf.VM_NAME[0])
        testflow.step(
            "Verify that VM %s has CPU cache level 3", conf.VM_NAME[0]
        )
        assert sla_helpers.check_vm_libvirt_parameters(
            vm_name=conf.VM_NAME[0], param="cache", substring="level='3'"
        )


@pytest.mark.usefixtures(
    skip_numa_tests.__name__,
    fill_numa_nodes_constants.__name__,
    update_vm_cpu_and_numa_pinning.__name__,
    update_vms.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    start_vms.__name__
)
class TestHighPerformanceVMAutoPinning01(SlaTest):
    """
    Verify IO and emulator threads auto-pinning when VM NUMA node and VM CPU's
    have pinning on the same host NUMA nodes
    """
    on_the_same_node = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_TYPE: conf.VM_TYPE_HIGH_PERFORMANCE,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    num_of_vm_numa_nodes = 2
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier1
    @polarion("RHEVM-24294")
    def test_io_and_emulator_pinning(self):
        """
        Verify that emulator and IO threads pinned to first two CPU's of NUMA
        node 0
        """
        assert helpers.verify_io_and_emulator_cpu_pinning(
            vm_name=conf.VM_NAME[0], numa_node=conf.NUMA_NODE_0
        )


@pytest.mark.usefixtures(
    skip_numa_tests.__name__,
    fill_numa_nodes_constants.__name__,
    update_vm_cpu_and_numa_pinning.__name__,
    update_vms.__name__,
    create_custom_numa_nodes_on_vm.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    start_vms.__name__
)
class TestHighPerformanceVMAutoPinning02(SlaTest):
    """
    Verify IO and emulator threads auto-pinning when VM NUMA node and VM CPU's
    have pinning on different host NUMA nodes
    """
    on_the_same_node = False
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_TYPE: conf.VM_TYPE_HIGH_PERFORMANCE,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    vm_numa_nodes_params = []
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM-24297")
    def test_io_and_emulator_pinning(self):
        """
        Verify that emulator and IO threads pinned to first two CPU's of NUMA
        node 1
        """
        assert helpers.verify_io_and_emulator_cpu_pinning(
            vm_name=conf.VM_NAME[0], numa_node=conf.NUMA_NODE_1
        )


@pytest.mark.usefixtures(
    skip_numa_tests.__name__,
    fill_numa_nodes_constants.__name__,
    update_vm_cpu_and_numa_pinning.__name__,
    update_vms.__name__,
    start_vms.__name__
)
class TestHighPerformanceVMAutoPinning03(SlaTest):
    """
    Verify IO and emulator threads auto-pinning when VM has only CPU pinning
    """
    on_the_same_node = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_TYPE: conf.VM_TYPE_HIGH_PERFORMANCE,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM-24300")
    def test_io_and_emulator_pinning(self):
        """
        Verify that emulator and IO threads pinned to all host CPU's
        """
        assert helpers.verify_io_and_emulator_cpu_pinning(
            vm_name=conf.VM_NAME[0], host_resource=conf.VDS_HOSTS[0]
        )


@pytest.mark.usefixtures(
    skip_numa_tests.__name__,
    fill_numa_nodes_constants.__name__,
    update_vms.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    start_vms.__name__
)
class TestHighPerformanceVMAutoPinning04(SlaTest):
    """
    Verify IO and emulator threads auto-pinning when VM has only NUMA pinning
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_TYPE: conf.VM_TYPE_HIGH_PERFORMANCE,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_CPU_CORES: 2
        }
    }
    num_of_vm_numa_nodes = 2
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM-24299")
    def test_io_and_emulator_pinning(self):
        """
        Verify that emulator and IO threads pinned to first two CPU's of NUMA
        node 0
        """
        assert helpers.verify_io_and_emulator_cpu_pinning(
            vm_name=conf.VM_NAME[0], numa_node=conf.NUMA_NODE_0
        )


@pytest.mark.usefixtures(
    skip_numa_tests.__name__,
    fill_numa_nodes_constants.__name__,
    update_vm_cpu_and_numa_pinning.__name__,
    update_vms.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    start_vms.__name__
)
class TestHighPerformanceVMAutoPinning05(SlaTest):
    """
    Verify IO and emulator threads auto-pinning on VM with more than one
    IO thread when VM NUMA node and VM CPU's have pinning
    on the same host NUMA nodes
    """
    on_the_same_node = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_TYPE: conf.VM_TYPE_HIGH_PERFORMANCE,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_IOTHREADS: 2
        }
    }
    num_of_vm_numa_nodes = 2
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM-24301")
    def test_io_and_emulator_pinning(self):
        """
        Verify that emulator and IO threads pinned to first two CPU's of NUMA
        node 0
        """
        assert helpers.verify_io_and_emulator_cpu_pinning(
            vm_name=conf.VM_NAME[0], numa_node=conf.NUMA_NODE_0
        )
