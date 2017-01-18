"""
NUMA test - Check creation of NUMA nodes on VM,
pin VM NUMA node to the host NUMA node and run it on the host
"""
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers
import pytest
from art.test_handler.tools import polarion
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
from rhevmtests.sla.fixtures import (
    attach_host_device,
    start_vms,
    update_vms
)


@pytest.fixture(scope="module", autouse=True)
def setup_numa_test():
    """
    1) Install numactl package on hosts
    """
    host_numa_nodes_l = ll_hosts.get_numa_nodes_from_host(conf.HOSTS[0])
    if len(host_numa_nodes_l) < 2:
        pytest.skip(
            "Number of NUMA nodes on host %s less than 2" % conf.HOSTS[0]
        )
    helpers.install_numa_package(resource=conf.VDS_HOSTS[0])


@u_libs.attr(tier=1)
class TestGetNumaStatisticFromHost(u_libs.SlaTest):
    """
    Check that engine receives correct information from host about numa nodes
    """
    __test__ = True

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
            u_libs.testflow.step(
                "Check that engine receives correct "
                "memory values for the host %s node %s",
                conf.HOSTS[0], node_index
            )
            memory_from_engine = ll_hosts.get_numa_node_memory(numa_node_obj)
            assert (
                memory_from_engine == numa_node_param[conf.NUMA_NODE_MEMORY]
            )
            u_libs.testflow.step(
                "Check that engine receives correct "
                "CPU values for the host %s node %s",
                conf.HOSTS[0], node_index
            )
            cpus_from_engine = ll_hosts.get_numa_node_cpus(numa_node_obj)
            assert (
                sorted(cpus_from_engine) ==
                sorted(numa_node_param[conf.NUMA_NODE_CPUS])
            )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(update_vms.__name__)
class TestUpdateVmWithNumaAndAutomaticMigration(u_libs.SlaTest):
    """
    Negative: add NUMA node to VM with AutomaticMigration option enabled
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }

    @polarion("RHEVM3-9565")
    def test_add_numa_node(self):
        """
        Add NUMA node to VM
        """
        u_libs.testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], conf.DEFAULT_NUMA_NODE_PARAMS
        )
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **conf.DEFAULT_NUMA_NODE_PARAMS
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(update_vms.__name__)
class TestUpdateVmWithNumaAndManualMigration(u_libs.SlaTest):
    """
    Negative: add NUMA node to VM with ManualMigration option enable
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_USER_MIGRATABLE,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }

    @polarion("RHEVM3-9564")
    def test_add_numa_node(self):
        """
        Add NUMA node to VM
        """
        u_libs.testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], conf.DEFAULT_NUMA_NODE_PARAMS
        )
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **conf.DEFAULT_NUMA_NODE_PARAMS
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(update_vms.__name__)
class TestUpdateVmWithNumaAndAnyHostPlacement(u_libs.SlaTest):
    """
    Negative: add NUMA node to VM with AnyHostInCluster option enabled
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
        }
    }

    @polarion("RHEVM3-9566")
    def test_add_numa_node(self):
        """
        Add NUMA node to VM
        """
        u_libs.testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], conf.DEFAULT_NUMA_NODE_PARAMS
        )
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **conf.DEFAULT_NUMA_NODE_PARAMS
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestStrictNumaModeOnVM(u_libs.SlaTest):
    """
    Check VM NUMA pinning under strict mode
    """
    __test__ = True
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

    @polarion("RHEVM3-9567")
    def test_cpu_pinning(self):
        """
        Check VM NUMA CPU pinning
        """
        u_libs.testflow.step(
            "Check if VM %s NUMA CPU pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.CPU_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @polarion("RHEVM3-12235")
    def test_numa_memory_mode(self):
        """
        Check VM NUMA memory mode
        """
        u_libs.testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestPreferModeOnVm(u_libs.SlaTest):
    """
    Check VM NUMA pinning under preferred mode
    """
    __test__ = True
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

    @polarion("RHEVM3-9568")
    def test_cpu_pinning(self):
        """
        Check VM NUMA CPU pinning
        """
        u_libs.testflow.step(
            "Check if VM %s NUMA CPU pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.CPU_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @polarion("RHEVM3-12236")
    def test_memory_pinning(self):
        """
        Check VM NUMA memory pinning
        """
        helpers.skip_test_because_memory_condition()
        u_libs.testflow.step(
            "Check if VM %s NUMA memory pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.MEMORY_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @polarion("RHEVM3-12237")
    def test_numa_memory_mode(self):
        """
        Check VM NUMA memory mode
        """
        u_libs.testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )


@u_libs.attr(tier=1)
@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestInterleaveModeOnVm(u_libs.SlaTest):
    """
    Check VM NUMA pinning under interleave mode
    """
    __test__ = True
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

    @polarion("RHEVM3-9569")
    def test_cpu_pinning(self):
        """
        Check VM NUMA CPU pinning
        """
        u_libs.testflow.step(
            "Check if VM %s NUMA CPU pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.CPU_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @polarion("RHEVM3-12238")
    def test_memory_pinning(self):
        """
        Check VM NUMA memory pinning
        """
        helpers.skip_test_because_memory_condition()
        u_libs.testflow.step(
            "Check if VM %s NUMA memory pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.MEMORY_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

    @polarion("RHEVM3-12239")
    def test_numa_memory_mode(self):
        """
        Check VM NUMA memory mode
        """
        u_libs.testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vm_cpu_pinning.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestCpuPinningOverrideNumaPinning(u_libs.SlaTest):
    """
    Check that CPU pinning override NUMA pinning options(for CPU's only)
    """
    __test__ = True
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
        u_libs.testflow.step(
            "Check if VM %s NUMA pinning override CPU pinning", conf.VM_NAME[0]
        )
        assert with_pinning == 1


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_custom_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestTotalVmMemoryEqualToNumaNodesMemory(u_libs.SlaTest):
    """
    Create two NUMA nodes on the VM, when nodes memory sum equal to the VM
    memory
    """
    __test__ = True
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

    @polarion("RHEVM3-9571")
    def test_vm_numa_nodes(self):
        """
        Check if VM NUMA nodes parameters equal to expected parameters
        """
        u_libs.testflow.step(
            "Check if VM %s has correct number of NUMA nodes", conf.VM_NAME[0]
        )
        assert helpers.is_vm_has_correct_number_of_numa_nodes(
            expected_number_of_vm_numa_nodes=len(self.vm_numa_nodes_params)
        )
        u_libs.testflow.step(
            "Check if VM %s NUMA nodes have correct amount of memory",
            conf.VM_NAME[0]
        )
        assert helpers.is_vm_numa_nodes_have_correct_values(
            value_type=conf.NUMA_NODE_MEMORY,
            expected_numa_params=self.vm_numa_nodes_params
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_custom_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestTotalVmCpusEqualToNumaNodesCpus(u_libs.SlaTest):
    """
    Create two NUMA nodes on the VM, when nodes CPU's sum equal to
    the total number of the VM CPU's
    """
    __test__ = True
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

    @polarion("RHEVM3-9573")
    def test_vm_numa_nodes(self):
        """
        Check if VM NUMA nodes parameters equal to expected parameters
        """
        u_libs.testflow.step(
            "Check if VM %s has correct number of NUMA nodes", conf.VM_NAME[0]
        )
        assert helpers.is_vm_has_correct_number_of_numa_nodes(
            expected_number_of_vm_numa_nodes=len(self.vm_numa_nodes_params)
        )
        u_libs.testflow.step(
            "Check if VM %s NUMA nodes have correct number of CPU's",
            conf.VM_NAME[0]
        )
        assert helpers.is_vm_numa_nodes_have_correct_values(
            value_type=conf.NUMA_NODE_CPUS,
            expected_numa_params=self.vm_numa_nodes_params
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_custom_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestTotalVmCpusNotEqualToNumaNodesCpus(u_libs.SlaTest):
    """
    Create two NUMA nodes on the VM, when nodes CPU's sum does not equal to
    the total number of the VM CPU's(guest OS just skip redundant CPU)
    """
    __test__ = True
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
            conf.NUMA_NODE_PARAMS_CORES: [0, 4],
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

    @polarion("RHEVM3-9574")
    def test_vm_numa_nodes(self):
        """
        Check if VM NUMA nodes parameters equal to expected parameters
        """
        u_libs.testflow.step(
            "Check if VM %s NUMA nodes have correct number of CPU's",
            conf.VM_NAME[0]
        )
        assert not helpers.is_vm_numa_nodes_have_correct_values(
            value_type=conf.NUMA_NODE_CPUS,
            expected_numa_params=self.vm_numa_nodes_params
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    pin_one_vm_numa_node_to_two_host_numa_nodes.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestPinningOneVNUMAToTwoPNUMA(u_libs.SlaTest):
    """
    Pin one VM NUMA node to two host NUMA nodes
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

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
        u_libs.testflow.step(
            "Check VM %s NUMA CPU pinning", conf.VM_NAME[0]
        )
        for cpu_pinning in vm_pinning.values():
            assert cpu_pinning.sort() == cores_list.sort()


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    pin_two_vm_numa_nodes_to_tone_host_numa_node.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestPinningTwoVNUMAToOnePNUMA(u_libs.SlaTest):
    """
    Pin two VM NUMA nodes to one host NUMA node
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_CPU_CORES: conf.CORES_MULTIPLIER * 2,
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vm_numa_mode = conf.INTERLEAVE_MODE
    vms_to_start = [conf.VM_NAME[0]]

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
        u_libs.testflow.step(
            "Check VM %s NUMA CPU pinning", conf.VM_NAME[0]
        )
        for cpu_pinning in vm_pinning.values():
            assert cpu_pinning.sort() == cores_list.sort()


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vm_memory_for_numa_test.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    update_vm_numa_mode.__name__,
)
class TestPinVNUMAWithLessMemoryThanOnPNUMAStrict(u_libs.SlaTest):
    """
    Pin VM NUMA node with memory less than host NUMA node has under strict mode
    """
    __test__ = True
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
        u_libs.testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], vm_numa_nodes_params[0]
        )
        assert ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **vm_numa_nodes_params[0]
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vm_memory_for_numa_test.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    update_vm_numa_mode.__name__,
)
class TestPinVNUMAWithMoreMemoryThanOnPNUMAStrict(u_libs.SlaTest):
    """
    Negative: pin VM NUMA node with memory greater than host
    NUMA node has under strict mode
    """
    __test__ = True
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
        u_libs.testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], vm_numa_nodes_params[0]
        )
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **vm_numa_nodes_params[0]
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vm_memory_for_numa_test.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    update_vm_numa_mode.__name__,
)
class TestPinVNUMAWithLessMemoryThanOnPNUMAInterleave(u_libs.SlaTest):
    """
    Pin VM NUMA node with memory greater than host
    NUMA node has under interleave mode
    """
    __test__ = True
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
        u_libs.testflow.step(
            "Add NUMA node to VM %s with parameters: %s",
            conf.VM_NAME[0], vm_numa_nodes_params[0]
        )
        assert ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **vm_numa_nodes_params[0]
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
@pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
class TestHotplugCpuUnderNumaPinning(u_libs.SlaTest):
    """
    Hotplug VM CPU and check that VM NUMA node updated accordingly
    """
    __test__ = True
    new_num_of_sockets = 4
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

    @polarion("RHEVM3-9556")
    def test_hotplug_cpu(self):
        """
        Hotplug additional CPU to VM and check the VM NUMA architecture
        """
        u_libs.testflow.step("Hotplug CPU to VM %s", conf.VM_NAME[0])
        assert ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            cpu_socket=self.new_num_of_sockets
        )
        u_libs.testflow.step("Get NUMA parameters from VM %s", conf.VM_NAME[0])
        vm_numa_params = helpers.get_numa_parameters_from_vm(
            vm_name=conf.VM_NAME[0]
        )
        assert vm_numa_params
        real_amount_of_cpus = sum(
            len(params[conf.NUMA_NODE_CPUS])
            for params in vm_numa_params.itervalues()
        )
        u_libs.testflow.step(
            "Check total number of CPU's under NUMA stats of the VM %s",
            conf.VM_NAME[0]
        )
        assert self.new_num_of_sockets == real_amount_of_cpus


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    get_pci_device_name.__name__,
    get_pci_device_numa_node.__name__,
    update_vms.__name__,
    attach_host_device.__name__,
    start_vms.__name__,
)
class TestNumaWithAttachedPciDevice(u_libs.SlaTest):
    """
    Attaching host device to the VM, must apply host
    device NUMA node on the VM in preferred mode
    """
    __test__ = True
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

    @polarion("RHEVM-17391")
    def test_vm_numa_pinning_and_mode(self):
        """
        1) Check NUMA memory pinning
        2) Check NUMA mode
        """
        if not self.pci_device_numa_node or self.pci_device_numa_node == -1:
            pytest.skip("Host device does not have correct numa node")
        helpers.skip_test_because_memory_condition()

        u_libs.testflow.step(
            "Check if VM %s NUMA memory pinning is correct",
            conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.MEMORY_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

        u_libs.testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    attach_host_device.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    create_equals_numa_nodes_on_vm.__name__,
    update_vm_numa_mode.__name__,
    start_vms.__name__
)
class TestNumaPinningOverrideHotsDeviceNuma(u_libs.SlaTest):
    """
    Setting NUMA pinning must override host device NUMA configuration
    """
    __test__ = True
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

    @polarion("RHEVM-17390")
    def test_vm_numa_pinning_and_mode(self):
        """
        1) Check NUMA CPU pinning
        2) Check NUMA memory pinning
        3) Check NUMA mode
        """
        u_libs.testflow.step(
            "Check if VM %s NUMA CPU pinning is correct", conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.CPU_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

        helpers.skip_test_because_memory_condition()

        u_libs.testflow.step(
            "Check if VM %s NUMA memory pinning is correct",
            conf.VM_NAME[0]
        )
        assert helpers.is_numa_pinning_correct(
            pinning_type=conf.MEMORY_PINNING_TYPE,
            numa_mode=self.vm_numa_mode,
            num_of_vm_numa_nodes=self.num_of_vm_numa_nodes
        )

        u_libs.testflow.step(
            "Check if VM %s NUMA memory mode is correct", conf.VM_NAME[0]
        )
        assert helpers.get_numa_mode_from_vm_process(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            numa_mode=self.vm_numa_mode
        )
