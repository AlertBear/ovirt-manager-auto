"""
Scheduler - Scheduler Sanity Test
Check working of all build-in filter, weight and balance units.
"""
import random

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.scheduling_policies as ll_sch
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import pytest
from art.test_handler.tools import polarion
from art.unittest_lib import attr
from fixtures import (
    create_network,
    create_new_scheduling_policy,
    update_vms_nics
)
from rhevmtests.networking.fixtures import (
    setup_networks_fixture,
    clean_host_interfaces  # flake8: noqa
)
from rhevmtests.sla.fixtures import choose_specific_host_as_spm
from rhevmtests.sla.fixtures import (
    deactivate_hosts,
    start_vms,
    stop_vms,
    update_vms,
    update_vms_cpus_to_hosts_cpus,
    update_vms_memory_to_hosts_memory,
    update_vms_to_default_parameters,
)
from rhevmtests.sla.scheduler_tests.fixtures import (
    update_cluster_policy,
    update_cluster_overcommitment
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
        u_libs.testflow.teardown(
            "Update cluster %s scheduling policy to %s",
            conf.CLUSTER_NAME[0], conf.POLICY_NONE
        )
        ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.POLICY_NONE
        )
        sched_policies = ll_sch.get_scheduling_policies()
        sched_policies = filter(
            lambda x: x.get_name() not in conf.ENGINE_POLICIES, sched_policies
        )
        for policy in sched_policies:
            policy_name = policy.get_name()
            u_libs.testflow.teardown(
                "Remove the scheduling policy %s", policy_name
            )
            ll_sch.remove_scheduling_policy(policy_name=policy_name)
        if not conf.PPC_ARCH:
            u_libs.testflow.teardown("Activate the host %s", conf.HOSTS[2])
            ll_hosts.activateHost(positive=True, host=conf.HOSTS[2])
    request.addfinalizer(fin)

    if not conf.PPC_ARCH:
        u_libs.testflow.setup("Deactivate the host %s", conf.HOSTS[2])
        assert ll_hosts.deactivateHost(positive=True, host=conf.HOSTS[2])


@attr(tier=2)
@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    init_scheduler_sanity_test.__name__,
    create_new_scheduling_policy.__name__,
    update_cluster_policy.__name__
)
class BaseSchedulerSanity(u_libs.SlaTest):
    """
    Base class for all scheduler tests
    """
    pass


@attr(tier=1)
class TestCRUD(u_libs.SlaTest):
    """
    Test class to create, update and remove the scheduling policy
    """
    __test__ = True
    policy_name = 'crud_policy'
    new_policy_name = 'new_crud_policy'

    @polarion("RHEVM3-9486")
    def test_crud_check(self):
        """
        Create, update and remove the scheduling policy
        """
        u_libs.testflow.step(
            "Create new scheduling policy %s.", self.policy_name
        )
        assert ll_sch.add_new_scheduling_policy(name=self.policy_name)

        u_libs.testflow.step(
            "Update the scheduling policy %s name to %s",
            self.policy_name, self.new_policy_name
        )
        assert ll_sch.update_scheduling_policy(
            policy_name=self.policy_name, name=self.new_policy_name
        )

        u_libs.testflow.step(
            "Remove the scheduling policy %s", self.new_policy_name
        )
        assert ll_sch.remove_scheduling_policy(
            policy_name=self.new_policy_name
        )


class TestDeletePolicyInUse(BaseSchedulerSanity):
    """
    Delete attached to the cluster scheduling policy
    """
    __test__ = True
    policy_name = "delete_policy_in_use"
    cluster_policy = {
        "delete_policy_in_use": None
    }

    @polarion("RHEVM3-9477")
    def test_delete_policy(self):
        """
        Delete attached policy
        """
        u_libs.testflow.step(
            "Delete the scheduling policy %s", self.policy_name
        )
        assert not ll_sch.remove_scheduling_policy(self.policy_name)


@attr(tier=1)
class TestRemoveBuildInPolicy(u_libs.SlaTest):
    """
    Delete build-in scheduling policy
    """
    __test__ = True

    @polarion("RHEVM3-9478")
    def test_delete_policy(self):
        """
        Delete build-in policy
        """
        policy_to_remove = random.choice(conf.ENGINE_POLICIES)
        u_libs.testflow.step(
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
    __test__ = True
    policy_name = "check_pin_to_host"
    cluster_policy = {
        "check_pin_to_host": None
    }
    policy_units = {conf.FILTER_PIN_TO_HOST: conf.FILTER_TYPE}
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @polarion("RHEVM3-9479")
    def test_pin_to_host_filter(self):
        """
        Test pin to host filter
        """
        u_libs.testflow.step(
            "Check if the VM %s, started on the host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert conf.HOSTS[0] == ll_vms.get_vm_host(vm_name=conf.VM_NAME[0])

        u_libs.testflow.step("Migrate the VM %s", conf.VM_NAME[0])
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
    __test__ = True
    policy_name = "negative_check_pin_to_host"
    cluster_policy = {
        "negative_check_pin_to_host": None
    }
    policy_units = {conf.FILTER_PIN_TO_HOST: conf.FILTER_TYPE}
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    hosts_to_maintenance = [0]
    vms_to_stop = conf.VM_NAME[:1]

    @polarion("RHEVM3-9485")
    def test_pin_to_host_filter(self):
        """
        Test pin to host filter
        """
        u_libs.testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert not ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    update_cluster_overcommitment.__name__,
    update_vms_memory_to_hosts_memory.__name__,
    update_vms_to_default_parameters.__name__,
    start_vms.__name__
)
class TestMemoryFilter(BaseSchedulerSanity):
    """
    Start two VM's with the memory near hosts memory
    """
    __test__ = True
    policy_name = "memory_filter"
    cluster_policy = {
        "memory_filter": None
    }
    policy_units = {conf.FILTER_MEMORY: conf.FILTER_TYPE}
    update_vms_memory = conf.VM_NAME[:2]
    update_to_default_params = conf.VM_NAME[:2]
    vms_to_start = conf.VM_NAME[:2]
    wait_for_vms_ip = False

    @polarion("RHEVM3-9480")
    def test_memory_filter(self):
        """
        Test memory filter
        """
        u_libs.testflow.step(
            "Check if VM's %s and %s run on different hosts",
            conf.VM_NAME[0], conf.VM_NAME[1]
        )
        assert (
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) !=
            ll_vms.get_vm_host(vm_name=conf.VM_NAME[1])
        )

        u_libs.testflow.step("Migrate the VM %s", conf.VM_NAME[0])
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
    __test__ = True
    policy_name = "cpu_filter"
    cluster_policy = {
        "cpu_filter": None
    }
    policy_units = {
        conf.FILTER_CPU: conf.FILTER_TYPE,
        conf.FILTER_PIN_TO_HOST: conf.FILTER_TYPE
    }
    vms_to_hosts_cpus = {conf.VM_NAME[0]: 0}
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @polarion("RHEVM3-9481")
    def test_cpu_filter(self):
        """
        Test CPU filter
        """
        u_libs.testflow.step(
            "Check that VM %s started on the host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert conf.HOSTS[0] == ll_vms.get_vm_host(vm_name=conf.VM_NAME[0])

        src_host_topology = ll_hosts.get_host_topology(host_name=conf.HOSTS[0])
        src_host_cpus = src_host_topology.cores * src_host_topology.sockets

        dst_host_topology = ll_hosts.get_host_topology(host_name=conf.HOSTS[1])
        dst_host_cpus = dst_host_topology.cores * dst_host_topology.sockets

        migrate_bool = True if dst_host_cpus >= src_host_cpus else False
        u_libs.testflow.step("Migrate the VM %s", conf.VM_NAME[0])
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
    __test__ = True
    policy_name = "negative_cpu_filter"
    cluster_policy = {
        "negative_cpu_filter": None
    }
    policy_units = {
        conf.FILTER_CPU: conf.FILTER_TYPE,
        conf.FILTER_PIN_TO_HOST: conf.FILTER_TYPE
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

    @polarion("RHEVM3-9476")
    def test_cpu_filter(self):
        """
        Test CPU filter
        """
        u_libs.testflow.step(
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
    __test__ = True
    apis = set(["rest", "java", "sdk"])
    policy_name = conf.NETWORK_FILTER_NAME
    cluster_policy = {
        conf.NETWORK_FILTER_NAME: None
    }
    policy_units = {
        conf.FILTER_NETWORK: conf.FILTER_TYPE,
        conf.FILTER_PIN_TO_HOST: conf.FILTER_TYPE
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

    @polarion("RHEVM3-9482")
    def test_network_filter(self):
        """
        Test network filter
        """
        u_libs.testflow.step(
            "Check if the VM %s runs on the host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) == conf.HOSTS[0]

        u_libs.testflow.step("Migrate the VM %s", conf.VM_NAME[0])
        assert not ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])

        u_libs.testflow.step("Start the VM %s", conf.VM_NAME[1])
        assert not ll_vms.startVm(positive=True, vm=conf.VM_NAME[1])
