"""
Scheduler tests fixtures
"""
import logging

import pytest

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.sla.config as conf
import rhevmtests.sla.helpers as sla_helpers

logger = logging.getLogger("scheduler_fixtures")


@pytest.fixture(scope="class")
def stop_vms(request):
    def fin():
        """
        1) Stop VM's
        """
        ll_vms.stop_vms_safely(conf.VM_NAME[:3])
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def start_vms_on_two_hosts(request, stop_vms):
    """
    1) Start one VM on two hosts
    """
    vm_host_d = dict(
        (vm_name, {"host": host_name})
        for vm_name, host_name in zip(conf.VM_NAME[:2], conf.HOSTS[:2])
    )
    ll_vms.run_vms_once(vms=conf.VM_NAME[:2], **vm_host_d)


@pytest.fixture(scope="class")
def start_vms_on_three_hosts(stop_vms):
    """
    1) Start one VM on three hosts
    """
    vm_host_d = dict(
        (vm_name, {"host": host_name})
        for vm_name, host_name in zip(conf.VM_NAME[:3], conf.HOSTS[:3])
    )
    ll_vms.run_vms_once(vms=conf.VM_NAME[:3], **vm_host_d)


@pytest.fixture(scope="class")
def update_cluster_policy_to_none(request):
    def fin():
        """
        1) Update cluster policy to none
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.POLICY_NONE
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def update_cluster_policy_to_power_saving(update_cluster_policy_to_none):
    """
    1) Update cluster policy to PowerSaving
    """
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        scheduling_policy=conf.POLICY_POWER_SAVING,
        properties=conf.DEFAULT_PS_PARAMS
    )


@pytest.fixture(scope="class")
def update_cluster_policy_to_even_distributed(update_cluster_policy_to_none):
    """
    1) Update cluster policy to EvenlyDistributed
    """
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        scheduling_policy=conf.POLICY_EVEN_DISTRIBUTION,
        properties=conf.DEFAULT_ED_PARAMS
    )


@pytest.fixture(scope="class")
def load_hosts_cpu(request):
    """
    1) Load hosts CPU
    """
    load_d = request.param
    load_to_resources = {}
    for load_value, host_indexes in load_d.iteritems():
        load_to_resources[load_value] = {}
        load_to_resources[load_value][conf.HOST] = []
        load_to_resources[load_value][conf.RESOURCE] = []
        for host_index in host_indexes:
            load_to_resources[load_value][conf.HOST].append(
                conf.HOSTS[host_index]
            )
            load_to_resources[load_value][conf.RESOURCE].append(
                conf.VDS_HOSTS[host_index]
            )

    def fin():
        """
        1) Stop CPU load on hosts
        """
        sla_helpers.stop_load_on_resources(load_to_resources.values())
    request.addfinalizer(fin)

    sla_helpers.start_and_wait_for_cpu_load_on_resources(load_to_resources)


@pytest.fixture(scope="class")
def activate_host(request):
    def fin():
        """
        1) Activate host
        """
        ll_hosts.activateHost(positive=True, host=conf.HOSTS[0])
    request.addfinalizer(fin)
