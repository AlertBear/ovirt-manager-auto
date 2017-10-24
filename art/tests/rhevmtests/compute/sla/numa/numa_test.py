"""
NUMA test - Check creation of NUMA nodes on VM,
pin VM NUMA node to the host NUMA node and run it on the host
"""
import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import helpers
from art.test_handler.tools import polarion, bz
from art.unittest_lib import testflow, tier1, tier2, SlaTest
from fixtures import (
    create_equals_numa_nodes_on_vm,
    create_custom_numa_nodes_on_vm,
    get_pci_device_name,
    get_pci_device_numa_node,
    pin_one_vm_numa_node_to_two_host_numa_nodes,
    pin_two_vm_numa_nodes_to_tone_host_numa_node,
    remove_all_numa_nodes_from_vm,
    update_vm_cpu_pinning,
    update_vm_memory_for_numa_test,
    update_vm_numa_mode
)
from rhevmtests.compute.sla.fixtures import (
    attach_host_device,
    start_vms,
    update_vms
)


@pytest.fixture(scope="module", autouse=True)
def setup_numa_test():
    """
    1) Install numactl package on hosts
    """
    host_numa_nodes_l = helpers.get_filtered_numa_parameters_from_resource(
        resource=conf.VDS_HOSTS[0]
    )
    if len(host_numa_nodes_l) < 2:
        pytest.skip(
            "Number of NUMA nodes with the memory greater "
            "than zero on the host %s less than 2" %
            conf.HOSTS[0]
        )
    helpers.install_numa_package(resource=conf.VDS_HOSTS[0])


class TestGetNumaStatisticFromHost(SlaTest):
    """
    Check that engine receives correct information from host about numa nodes
    """

    @tier1
    @polarion("RHEVM3-9546")
    def test_numa_statistics(self):
        """
        Check that information about numa nodes in engine and on host the same
        """
        numa_nodes_params = helpers.get_numa_parameters_from_resource(
            resource=conf.VDS_HOSTS[0]
        )
        for node_index, numa_node_param in numa_nodes_params.iteritems():
            numa_node_obj = ll_hosts.get_numa_node_by_index(
                conf.HOSTS[0], node_index
            )
            testflow.step(
                "Check that engine receives correct "
                "memory values for the host %s node %s",
                conf.HOSTS[0], node_index
            )
            memory_from_engine = ll_hosts.get_numa_node_memory(numa_node_obj)
            assert (
                memory_from_engine == numa_node_param[conf.NUMA_NODE_MEMORY]
            )
            testflow.step(
                "Check that engine receives correct "
                "CPU values for the host %s node %s",
                conf.HOSTS[0], node_index
            )
            cpus_from_engine = ll_hosts.get_numa_node_cpus(numa_node_obj)
            assert (
                sorted(cpus_from_engine) ==
                sorted(numa_node_param[conf.NUMA_NODE_CPUS])
            )


@pytest.mark.usefixtures(update_vms.__name__)
class TestUpdateVmWithNumaAndAutomaticMigration(SlaTest):
    """
    Negative: add NUMA node to VM with AutomaticMigration option enabled
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }

    @tier2
    @polarion("RHEVM3-9565")
    def test_add_numa_node(self):
        """
        Add NUMA node to VM
        """
        testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], conf.DEFAULT_NUMA_NODE_PARAMS
        )
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **conf.DEFAULT_NUMA_NODE_PARAMS
        )


@pytest.mark.usefixtures(update_vms.__name__)
class TestUpdateVmWithNumaAndManualMigration(SlaTest):
    """
    Negative: add NUMA node to VM with ManualMigration option enable
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_USER_MIGRATABLE,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }

    @tier2
    @polarion("RHEVM3-9564")
    def test_add_numa_node(self):
        """
        Add NUMA node to VM
        """
        testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], conf.DEFAULT_NUMA_NODE_PARAMS
        )
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **conf.DEFAULT_NUMA_NODE_PARAMS
        )


@pytest.mark.usefixtures(update_vms.__name__)
class TestUpdateVmWithNumaAndAnyHostPlacement(SlaTest):
    """
    Negative: add NUMA node to VM with AnyHostInCluster option enabled
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
        }
    }

    @tier2
    @polarion("RHEVM3-9566")
    def test_add_numa_node(self):
        """
        Add NUMA node to VM
        """
        testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], conf.DEFAULT_NUMA_NODE_PARAMS
        )
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **conf.DEFAULT_NUMA_NODE_PARAMS
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestStrictNumaModeOnVM(SlaTest):
    """
    Check VM NUMA pinning under strict mode
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER * 2,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    num_of_vm_numa_nodes = 2
    vm_numa_mode = conf.STRICT_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM3-9567")
    def test_cpu_pinning(self):
        """
        Check VM NUMA CPU pinning
        """
        testflow.step(
            "Check if VM %s NUMA CPU pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.CPU_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @tier2
    @polarion("RHEVM3-12235")
    def test_numa_memory_mode(self):
        """
        Check VM NUMA memory mode
        """
        testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestPreferModeOnVm(SlaTest):
    """
    Check VM NUMA pinning under preferred mode
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    num_of_vm_numa_nodes = 1
    vm_numa_mode = conf.PREFER_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM3-9568")
    def test_cpu_pinning(self):
        """
        Check VM NUMA CPU pinning
        """
        testflow.step(
            "Check if VM %s NUMA CPU pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.CPU_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @tier2
    @polarion("RHEVM3-12236")
    def test_memory_pinning(self):
        """
        Check VM NUMA memory pinning
        """
        testflow.step(
            "Check if VM %s NUMA memory pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.MEMORY_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @tier2
    @polarion("RHEVM3-12237")
    def test_numa_memory_mode(self):
        """
        Check VM NUMA memory mode
        """
        testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestInterleaveModeOnVm(SlaTest):
    """
    Check VM NUMA pinning under interleave mode
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER * 2,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    num_of_vm_numa_nodes = 2
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @tier1
    @polarion("RHEVM3-9569")
    def test_cpu_pinning(self):
        """
        Check VM NUMA CPU pinning
        """
        testflow.step(
            "Check if VM %s NUMA CPU pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.CPU_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @tier1
    @polarion("RHEVM3-12238")
    def test_memory_pinning(self):
        """
        Check VM NUMA memory pinning
        """
        testflow.step(
            "Check if VM %s NUMA memory pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.MEMORY_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @tier1
    @polarion("RHEVM3-12239")
    def test_numa_memory_mode(self):
        """
        Check VM NUMA memory mode
        """
        testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vm_cpu_pinning.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestCpuPinningOverrideNumaPinning(SlaTest):
    """
    Check that CPU pinning override NUMA pinning options(for CPU's only)
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    num_of_vm_numa_nodes = 1
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM3-9570")
    def test_check_cpu_pinning(self):
        """
        Check NUMA CPU pinning
        """
        host_online_cpu = ll_sla.get_list_of_online_cpus_on_resource(
            resource=conf.VDS_HOSTS[0]
        )[0]
        vm_pinning = helpers.get_vm_numa_pinning(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            pinning_type=conf.CPU_PINNING_TYPE
        )
        with_pinning = sum(
            x == [host_online_cpu] for x in vm_pinning.values()
        )
        testflow.step(
            "Check if VM %s NUMA pinning override CPU pinning", conf.VM_NAME[0]
        )
        assert with_pinning == 1


@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_custom_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestTotalVmMemoryEqualToNumaNodesMemory(SlaTest):
    """
    Create two NUMA nodes on the VM, when nodes memory sum equal to the VM
    memory
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER * 2,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vm_numa_nodes_params = [
        {
            conf.NUMA_NODE_PARAMS_INDEX: 0,
            conf.NUMA_NODE_PARAMS_CORES: [0],
            conf.NUMA_NODE_PARAMS_MEMORY: 768
        },
        {
            conf.NUMA_NODE_PARAMS_INDEX: 1,
            conf.NUMA_NODE_PARAMS_CORES: [1],
            conf.NUMA_NODE_PARAMS_MEMORY: 256
        }
    ]
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @tier2
    @bz({"1472167": {}})
    @polarion("RHEVM3-9571")
    def test_vm_numa_nodes(self):
        """
        Check if VM NUMA nodes parameters equal to expected parameters
        """
        testflow.step(
            "Check if VM %s has correct number of NUMA nodes", conf.VM_NAME[0]
        )
        assert helpers.is_vm_has_correct_number_of_numa_nodes(
            expected_number_of_vm_numa_nodes=len(self.vm_numa_nodes_params)
        )
        testflow.step(
            "Check if VM %s NUMA nodes have correct amount of memory",
            conf.VM_NAME[0]
        )
        assert helpers.is_vm_numa_nodes_have_correct_values(
            value_type=conf.NUMA_NODE_MEMORY,
            expected_numa_params=self.vm_numa_nodes_params
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_custom_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestTotalVmCpusEqualToNumaNodesCpus(SlaTest):
    """
    Create two NUMA nodes on the VM, when nodes CPU's sum equal to
    the total number of the VM CPU's
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER * 2,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vm_numa_nodes_params = [
        {
            conf.NUMA_NODE_PARAMS_INDEX: 0,
            conf.NUMA_NODE_PARAMS_CORES: [0],
            conf.NUMA_NODE_PARAMS_MEMORY: 512
        },
        {
            conf.NUMA_NODE_PARAMS_INDEX: 1,
            conf.NUMA_NODE_PARAMS_CORES: [1, 2, 3],
            conf.NUMA_NODE_PARAMS_MEMORY: 512
        }
    ]
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @tier2
    @bz({"1472167": {}})
    @polarion("RHEVM3-9573")
    def test_vm_numa_nodes(self):
        """
        Check if VM NUMA nodes parameters equal to expected parameters
        """
        testflow.step(
            "Check if VM %s has correct number of NUMA nodes", conf.VM_NAME[0]
        )
        assert helpers.is_vm_has_correct_number_of_numa_nodes(
            expected_number_of_vm_numa_nodes=len(self.vm_numa_nodes_params)
        )
        testflow.step(
            "Check if VM %s NUMA nodes have correct number of CPU's",
            conf.VM_NAME[0]
        )
        assert helpers.is_vm_numa_nodes_have_correct_values(
            value_type=conf.NUMA_NODE_CPUS,
            expected_numa_params=self.vm_numa_nodes_params
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__
)
class TestCreateVmNumaNodeWithIncorrectCpu(SlaTest):
    """
    Negative: create the NUMA node with incorrect CPU core
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER * 2,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }

    @tier2
    @polarion("RHEVM3-9574")
    def test_vm_numa_nodes(self):
        """
        Try to create NUMA nodes on the VM
        """
        numa_node_params = {
            conf.NUMA_NODE_PARAMS_INDEX: 0,
            conf.NUMA_NODE_PARAMS_CORES: [0, 4],
            conf.NUMA_NODE_PARAMS_MEMORY: 512
        }
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **numa_node_params
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    pin_one_vm_numa_node_to_two_host_numa_nodes.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestPinningOneVNUMAToTwoPNUMA(SlaTest):
    """
    Pin one VM NUMA node to two host NUMA nodes
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM3-9552")
    def test_vm_cpu_pinning(self):
        """
        Check VM CPU pinning
        """
        vm_pinning = helpers.get_vm_numa_pinning(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            pinning_type=conf.CPU_PINNING_TYPE
        )
        host_numa_nodes_indexes = ll_hosts.get_numa_nodes_indexes(
            host_name=conf.HOSTS[0]
        )[:2]
        cores_list = []
        for numa_node_index in host_numa_nodes_indexes:
            h_numa_node_obj = ll_hosts.get_numa_node_by_index(
                host_name=conf.HOSTS[0], index=numa_node_index
            )
            cores_list.extend(
                ll_hosts.get_numa_node_cpus(numa_node_obj=h_numa_node_obj)
            )
        testflow.step(
            "Check VM %s NUMA CPU pinning", conf.VM_NAME[0]
        )
        for cpu_pinning in vm_pinning.values():
            assert cpu_pinning.sort() == cores_list.sort()


@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    pin_two_vm_numa_nodes_to_tone_host_numa_node.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestPinningTwoVNUMAToOnePNUMA(SlaTest):
    """
    Pin two VM NUMA nodes to one host NUMA node
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER * 2,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM3-9555")
    def test_vm_cpu_pinning(self):
        """
        Check VM CPU pinning
        """
        vm_pinning = helpers.get_vm_numa_pinning(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            pinning_type=conf.CPU_PINNING_TYPE
        )
        host_numa_node_index = ll_hosts.get_numa_nodes_indexes(
            host_name=conf.HOSTS[0]
        )[0]
        h_numa_node_obj = ll_hosts.get_numa_node_by_index(
            host_name=conf.HOSTS[0], index=host_numa_node_index
        )
        cores_list = ll_hosts.get_numa_node_cpus(numa_node_obj=h_numa_node_obj)
        testflow.step(
            "Check VM %s NUMA CPU pinning", conf.VM_NAME[0]
        )
        for cpu_pinning in vm_pinning.values():
            assert cpu_pinning.sort() == cores_list.sort()


@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vm_memory_for_numa_test.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    update_vm_numa_mode.__name__,
)
class TestPinVNUMAWithLessMemoryThanOnPNUMAStrict(SlaTest):
    """
    Pin VM NUMA node with memory less than host NUMA node has under strict mode
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0],
        }
    }
    negative_test = False
    num_of_vm_numa_nodes = 1
    vm_numa_mode = conf.STRICT_MODE

    @tier2
    @polarion("RHEVM3-9575")
    def test_pin_virtual_numa_node(self):
        """
        Add VM NUMA node with pinning
        """
        vm_numa_nodes_params = helpers.create_number_of_equals_numa_nodes(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            num_of_numa_nodes=self.num_of_vm_numa_nodes
        )
        testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], vm_numa_nodes_params[0]
        )
        assert ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **vm_numa_nodes_params[0]
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vm_memory_for_numa_test.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    update_vm_numa_mode.__name__,
)
class TestPinVNUMAWithMoreMemoryThanOnPNUMAStrict(SlaTest):
    """
    Negative: pin VM NUMA node with memory greater than host
    NUMA node has under strict mode
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    negative_test = True
    num_of_vm_numa_nodes = 1
    vm_numa_mode = conf.STRICT_MODE

    @tier2
    @polarion("RHEVM3-9576")
    def test_pin_virtual_numa_node(self):
        """
        Add VM NUMA node with pinning
        """
        vm_numa_nodes_params = helpers.create_number_of_equals_numa_nodes(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            num_of_numa_nodes=self.num_of_vm_numa_nodes
        )
        testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], vm_numa_nodes_params[0]
        )
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **vm_numa_nodes_params[0]
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vm_memory_for_numa_test.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    update_vm_numa_mode.__name__,
)
class TestPinVNUMAWithLessMemoryThanOnPNUMAInterleave(SlaTest):
    """
    Pin VM NUMA node with memory greater than host
    NUMA node has under interleave mode
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    negative_test = True
    num_of_vm_numa_nodes = 1
    vm_numa_mode = conf.INTERLEAVE_MODE

    @tier2
    @polarion("RHEVM3-9549")
    def test_pin_virtual_numa_node(self):
        """
        Add VM NUMA node with pinning
        """
        vm_numa_nodes_params = helpers.create_number_of_equals_numa_nodes(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            num_of_numa_nodes=self.num_of_vm_numa_nodes
        )
        testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], vm_numa_nodes_params[0]
        )
        assert ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **vm_numa_nodes_params[0]
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestHotplugCpuUnderNumaPinning(SlaTest):
    """
    Hotplug VM CPU and check that VM NUMA node updated accordingly
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_SOCKET: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    num_of_vm_numa_nodes = 2
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @staticmethod
    def _check_hotplug_unplug_cpu(new_num_of_sockets):
        """
        Hot plug / unplug cpu and check Numa

        Args:
            new_num_of_sockets (int): number of CPU

        """
        assert ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            cpu_socket=new_num_of_sockets
        )
        testflow.step(
            "Get NUMA parameters from VM %s", conf.VM_NAME[0]
        )
        vm_numa_params = helpers.get_numa_parameters_from_vm(
            vm_name=conf.VM_NAME[0]
        )
        assert vm_numa_params
        real_amount_of_cpus = sum(
            len(params[conf.NUMA_NODE_CPUS])
            for params in vm_numa_params.itervalues()
        )
        testflow.step(
            "Check total number of CPU's under NUMA stats of the VM %s",
            conf.VM_NAME[0]
        )
        assert new_num_of_sockets == real_amount_of_cpus

    @tier2
    @bz({"1472167": {}})
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-9556")
    def test_hotplug_cpu(self):
        """
        Case 1: Hot plug additional CPU to VM and check the VM NUMA
        architecture
        Case 2: Hot unplug CPU to VM and check the VM NUMA architecture
        """
        testflow.step(
            "Hotplug CPU to VM %s to %s ", conf.VM_NAME[0], 4
        )
        self._check_hotplug_unplug_cpu(4)
        testflow.step(
            "Hot unplug CPU to VM %s to %s", conf.VM_NAME[0], 2
        )
        self._check_hotplug_unplug_cpu(2)


@pytest.mark.usefixtures(
    get_pci_device_name.__name__,
    get_pci_device_numa_node.__name__,
    update_vms.__name__,
    attach_host_device.__name__,
    start_vms.__name__,
)
class TestNumaWithAttachedPciDevice(SlaTest):
    """
    Attaching host device to the VM, must apply host
    device NUMA node on the VM in preferred mode
    """
    pci_device_name = None
    pci_device_numa_node = None
    num_of_vm_numa_nodes = 1
    vm_numa_mode = conf.PREFER_MODE
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vms_to_start = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM-17391")
    def test_vm_numa_pinning_and_mode(self):
        """
        1) Check NUMA memory pinning
        2) Check NUMA mode
        """
        testflow.step(
            "Check if VM %s NUMA memory pinning is correct",
            conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.MEMORY_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

        testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    attach_host_device.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestNumaPinningOverrideHotsDeviceNuma(SlaTest):
    """
    Setting NUMA pinning must override host device NUMA configuration
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER * 2,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    num_of_vm_numa_nodes = 2
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM-17390")
    def test_vm_numa_pinning_and_mode(self):
        """
        1) Check NUMA CPU pinning
        2) Check NUMA memory pinning
        3) Check NUMA mode
        """
        testflow.step(
            "Check if VM %s NUMA CPU pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.CPU_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

        testflow.step(
            "Check if VM %s NUMA memory pinning is correct",
            conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.MEMORY_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

        testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )
