"""
Scheduler - Scheduler Sanity Test
Check working of all build-in filter, weight and balance units.
"""
import random

import pytest
from rhevmtests.compute.sla.fixtures import (  # noqa: F401
    choose_specific_host_as_spm,
    deactivate_hosts,
    start_vms,
    stop_vms,
    update_cluster,
    update_vms,
    update_vms_cpus_to_hosts_cpus,
    update_vms_memory_to_hosts_memory,
    update_vms_to_default_parameters,
    update_cluster_to_default_parameters
)

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.scheduling_policies as ll_sch
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, SlaTest
from art.unittest_lib import (
    tier1,
    tier2,
)
from fixtures import (
    create_network,
    update_vms_nics
)
from rhevmtests.compute.sla.scheduler_tests.fixtures import (
    create_new_scheduling_policy,
    wait_for_scheduling_memory_update
)
from rhevmtests.networking.fixtures import (  # noqa: F401
    setup_networks_fixture,
    clean_host_interfaces
)

host_as_spm = 1


@pytest.fixture(scope="module")
def init_scheduler_sanity_test(request):
    """
    1) Deactivate third host
    """
    def fin():
        """
        1) Change cluster scheduler policy to none
        2) Remove all redundant scheduler policies
        3) Activate third host
        """
        results = list()
        results.append(
            ll_clusters.updateCluster(
                positive=True,
                cluster=conf.CLUSTER_NAME[0],
                scheduling_policy=conf.POLICY_NONE
            )
        )
        sched_policies = ll_sch.get_scheduling_policies()
        sched_policies = filter(
            lambda x: x.get_name() not in conf.ENGINE_POLICIES, sched_policies
        )
        for policy in sched_policies:
            policy_name = policy.get_name()
            testflow.teardown(
                "Remove the scheduling policy %s", policy_name
            )
            results.append(
                ll_sch.remove_scheduling_policy(policy_name=policy_name)
            )
        if not conf.PPC_ARCH:
            results.append(
                ll_hosts.activate_host(
                    positive=True,
                    host=conf.HOSTS[2],
                    host_resource=conf.VDS_HOSTS[2]
                )
            )
        assert all(results)
    request.addfinalizer(fin)

    if not conf.PPC_ARCH:
        assert ll_hosts.deactivate_host(
            positive=True, host=conf.HOSTS[2], host_resource=conf.VDS_HOSTS[2]
        )


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    init_scheduler_sanity_test.__name__,
    create_new_scheduling_policy.__name__,
    update_cluster.__name__
)
class BaseSchedulerSanity(SlaTest):
    """
    Base class for all scheduler tests
    """
    pass


class TestCRUD(SlaTest):
    """
    Test class to create, update and remove the scheduling policy
    """
    policy_name = 'crud_policy'
    new_policy_name = 'new_crud_policy'

    @tier1
    @polarion("RHEVM3-9486")
    def test_crud_check(self):
        """
        Create, update and remove the scheduling policy
        """
        testflow.step(
            "Create new scheduling policy %s.", self.policy_name
        )
        assert ll_sch.add_new_scheduling_policy(name=self.policy_name)

        testflow.step(
            "Update the scheduling policy %s name to %s",
            self.policy_name, self.new_policy_name
        )
        assert ll_sch.update_scheduling_policy(
            policy_name=self.policy_name, name=self.new_policy_name
        )

        testflow.step(
            "Remove the scheduling policy %s", self.new_policy_name
        )
        assert ll_sch.remove_scheduling_policy(
            policy_name=self.new_policy_name
        )


class TestDeletePolicyInUse(BaseSchedulerSanity):
    """
    Delete attached to the cluster scheduling policy
    """
    policy_name = "delete_policy_in_use"
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: "delete_policy_in_use"
    }

    @tier2
    @polarion("RHEVM3-9477")
    def test_delete_policy(self):
        """
        Delete attached policy
        """
        testflow.step(
            "Delete the scheduling policy %s", self.policy_name
        )
        assert not ll_sch.remove_scheduling_policy(self.policy_name)


class TestRemoveBuildInPolicy(SlaTest):
    """
    Delete build-in scheduling policy
    """

    @tier1
    @polarion("RHEVM3-9478")
    def test_delete_policy(self):
        """
        Delete build-in policy
        """
        policy_to_remove = random.choice(conf.ENGINE_POLICIES)
        testflow.step(
            "Delete the scheduling policy %s", policy_to_remove
        )
        assert not ll_sch.remove_scheduling_policy(policy_to_remove)


@pytest.mark.usefixtures(
    update_vms.__name__,
    start_vms.__name__
)
class TestPinToHostFilter(BaseSchedulerSanity):
    """
    Start and migrate the VM under PinToHost filter
    """
    policy_name = "check_pin_to_host"
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: "check_pin_to_host"
    }
    policy_units = {
        conf.FILTER_PIN_TO_HOST: {conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER}
    }
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM3-9479")
    def test_pin_to_host_filter(self):
        """
        Test pin to host filter
        """
        testflow.step(
            "Check if the VM %s, started on the host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert conf.HOSTS[0] == ll_vms.get_vm_host(vm_name=conf.VM_NAME[0])

        testflow.step("Migrate the VM %s", conf.VM_NAME[0])
        assert not ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__,
    deactivate_hosts.__name__
)
class TestNegativePinToHostFilter(BaseSchedulerSanity):
    """
    Pin the VM to the deactivated host and start it
    """
    policy_name = "negative_check_pin_to_host"
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: "negative_check_pin_to_host"
    }
    policy_units = {
        conf.FILTER_PIN_TO_HOST: {conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER}
    }
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    hosts_to_maintenance = [0]
    vms_to_stop = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM3-9485")
    def test_pin_to_host_filter(self):
        """
        Test pin to host filter
        """
        testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert not ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    wait_for_scheduling_memory_update.__name__,
    update_vms_memory_to_hosts_memory.__name__,
    update_vms_to_default_parameters.__name__,
    start_vms.__name__
)
class TestMemoryFilter(BaseSchedulerSanity):
    """
    Start two VM's with the memory near hosts memory
    """
    policy_name = "memory_filter"
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: "memory_filter",
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }
    policy_units = {
        conf.FILTER_MEMORY: {conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER}
    }
    update_vms_memory = conf.VM_NAME[:2]
    update_to_default_params = conf.VM_NAME[:2]
    vms_to_start = conf.VM_NAME[:2]
    wait_for_vms_ip = False
    wait_for_vms_state = conf.VM_UP

    @tier2
    @polarion("RHEVM3-9480")
    def test_memory_filter(self):
        """
        Test memory filter
        """
        testflow.step(
            "Check if VM's %s and %s run on different hosts",
            conf.VM_NAME[0], conf.VM_NAME[1]
        )
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) !=
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )

        testflow.step("Migrate the VM %s", conf.VM_NAME[0])
        assert not ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    update_vms_cpus_to_hosts_cpus.__name__,
    update_vms.__name__,
    start_vms.__name__
)
class TestCpuFilter(BaseSchedulerSanity):
    """
    Check that CPU filter does not prevent to start and migrate the VM,
    when VM has equal or less CPU's than host
    """
    policy_name = "cpu_filter"
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: "cpu_filter"
    }
    policy_units = {
        conf.FILTER_CPU: {conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER},
        conf.PREFERRED_HOSTS: {
            conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_WEIGHT,
            conf.WEIGHT_FACTOR: 99
        }
    }
    vms_to_hosts_cpus = {conf.VM_NAME[0]: 0}
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vms_to_start = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM3-9481")
    def test_cpu_filter(self):
        """
        Test CPU filter
        """
        testflow.step(
            "Check that VM %s started on the host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert conf.HOSTS[0] == ll_vms.get_vm_host(vm_name=conf.VM_NAME[0])

        src_host_topology = ll_hosts.get_host_topology(host_name=conf.HOSTS[0])
        src_host_cpus = src_host_topology.cores * src_host_topology.sockets

        dst_host_topology = ll_hosts.get_host_topology(host_name=conf.HOSTS[1])
        dst_host_cpus = dst_host_topology.cores * dst_host_topology.sockets

        migrate_bool = True if dst_host_cpus >= src_host_cpus else False
        testflow.step("Migrate the VM %s", conf.VM_NAME[0])
        assert ll_vms.migrateVm(positive=migrate_bool, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    update_vms_cpus_to_hosts_cpus.__name__,
    update_vms.__name__,
    stop_vms.__name__
)
class TestNegativeCpuFilter(BaseSchedulerSanity):
    """
    Check that CPU filter prevents to start and migrate the VM,
    when VM has more CPU's than host
    """
    policy_name = "negative_cpu_filter"
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: "negative_cpu_filter"
    }
    policy_units = {
        conf.FILTER_CPU: {conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER},
        conf.FILTER_PIN_TO_HOST: {conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER}
    }
    vms_to_hosts_cpus = {conf.VM_NAME[0]: 0}
    double_vms_cpus = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    vms_to_stop = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM3-9476")
    def test_cpu_filter(self):
        """
        Test CPU filter
        """
        testflow.step(
            "Start the VM %s on the host %s", conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert not ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    create_network.__name__,
    setup_networks_fixture.__name__,
    update_vms.__name__,
    update_vms_nics.__name__,
    start_vms.__name__
)
class TestNetworkFilter(BaseSchedulerSanity):
    """
    Check that network filter does not prevent to start VM on the host with
    the network and prevents to start and migrate VM
    on the host without the network
    """
    policy_name = conf.NETWORK_FILTER_NAME
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.NETWORK_FILTER_NAME
    }
    policy_units = {
        conf.FILTER_NETWORK: {conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER},
        conf.FILTER_PIN_TO_HOST: {conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER}
    }
    network_name = conf.NETWORK_FILTER_NAME
    hosts_nets_nic_dict = {
        0: {
            conf.NETWORK_FILTER_NAME: {
                "datacenter": conf.DC_NAME[0],
                "network": conf.NETWORK_FILTER_NAME,
                "nic": 1
            }
        }
    }
    vms_to_params = {
        conf.VM_NAME[1]: {
            conf.VM_PLACEMENT_HOSTS: [1],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    vms_nics_to_params = dict(
        (
            vm_name, {conf.NIC_NAME[0]: {"network": conf.NETWORK_FILTER_NAME}}
        ) for vm_name in conf.VM_NAME[:2]
    )
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM3-9482")
    def test_network_filter(self):
        """
        Test network filter
        """
        testflow.step(
            "Check if the VM %s runs on the host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) == conf.HOSTS[0]

        testflow.step("Migrate the VM %s", conf.VM_NAME[0])
        assert not ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])

        testflow.step("Start the VM %s", conf.VM_NAME[1])
        assert not ll_vms.startVm(positive=True, vm=conf.VM_NAME[1])
