"""
Scheduler tests fixtures
"""
import logging
from time import sleep

import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.sla.config as sla_conf
import rhevmtests.sla.helpers as sla_helpers

logger = logging.getLogger("scheduler_fixtures")


@pytest.fixture(scope="class")
def update_cluster_policy_to_none(request):
    def fin():
        """
        1) Update cluster policy to none
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=sla_conf.CLUSTER_NAME[0],
            scheduling_policy=sla_conf.POLICY_NONE
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def update_cluster_policy_to_power_saving(request):
    """
    1) Update cluster policy to PowerSaving
    """
    def fin():
        """
        1) Update cluster policy to none
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=sla_conf.CLUSTER_NAME[0],
            scheduling_policy=sla_conf.POLICY_NONE
        )
    request.addfinalizer(fin)

    assert ll_clusters.updateCluster(
        positive=True,
        cluster=sla_conf.CLUSTER_NAME[0],
        scheduling_policy=sla_conf.POLICY_POWER_SAVING,
        properties=sla_conf.DEFAULT_PS_PARAMS
    )


@pytest.fixture(scope="class")
def update_cluster_policy_to_even_distributed(request):
    """
    1) Update cluster policy to EvenlyDistributed
    """
    def fin():
        """
        1) Update cluster policy to none
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=sla_conf.CLUSTER_NAME[0],
            scheduling_policy=sla_conf.POLICY_NONE
        )

    request.addfinalizer(fin)

    assert ll_clusters.updateCluster(
        positive=True,
        cluster=sla_conf.CLUSTER_NAME[0],
        scheduling_policy=sla_conf.POLICY_EVEN_DISTRIBUTION,
        properties=sla_conf.DEFAULT_ED_PARAMS
    )


@pytest.fixture(scope="class")
def load_hosts_cpu(request):
    """
    1) Load hosts CPU
    """
    load_d = request.node.cls.load_d
    load_to_resources = {}
    for load_value, host_indexes in load_d.iteritems():
        load_to_resources[load_value] = {}
        load_to_resources[load_value][sla_conf.HOST] = []
        load_to_resources[load_value][sla_conf.RESOURCE] = []
        for host_index in host_indexes:
            load_to_resources[load_value][sla_conf.HOST].append(
                sla_conf.HOSTS[host_index]
            )
            load_to_resources[load_value][sla_conf.RESOURCE].append(
                sla_conf.VDS_HOSTS[host_index]
            )

    def fin():
        """
        1) Stop CPU load on hosts
        """
        sla_helpers.stop_load_on_resources(load_to_resources.values())
    request.addfinalizer(fin)

    sla_helpers.start_and_wait_for_cpu_load_on_resources(load_to_resources)


@pytest.fixture(scope="class")
def create_affinity_groups(request):
    """
    1) Add affinity groups
    2) Populate affinity groups by VM's
    """
    affinity_groups = request.node.cls.affinity_groups

    def fin():
        """
        1) Remove affinity groups
        """
        for affinity_group_name in affinity_groups.iterkeys():
            ll_clusters.remove_affinity_group(
                affinity_name=affinity_group_name,
                cluster_name=sla_conf.CLUSTER_NAME[0]
            )
    request.addfinalizer(fin)

    for (
        affinity_group_name, affinity_group_params
    ) in affinity_groups.iteritems():
        vms = affinity_group_params.pop("vms", None)
        assert ll_clusters.create_affinity_group(
            cluster_name=sla_conf.CLUSTER_NAME[0],
            name=affinity_group_name,
            **affinity_group_params
        )
        if vms:
            assert ll_clusters.populate_affinity_with_vms(
                affinity_name=affinity_group_name,
                cluster_name=sla_conf.CLUSTER_NAME[0],
                vms=vms
            )


@pytest.fixture(scope="class")
def update_vms_memory(request):
    """
    1) Update VM's memory to be near host's memory
    """
    vms_to_update = request.node.cls.vms_to_update

    def fin():
        """
        1) Update VM's memory to default values
        """
        for vm in vms_to_update:
            ll_vms.updateVm(
                positive=True,
                vm=vm,
                memory=sla_conf.GB,
                memory_guaranteed=sla_conf.GB
            )
    request.addfinalizer(fin)

    hosts_memory = hl_vms.calculate_memory_for_memory_filter(
        hosts_list=sla_conf.HOSTS[:2], difference=50
    )
    for i, vm in enumerate(vms_to_update):
        assert ll_vms.updateVm(
            positive=True,
            vm=vm,
            memory=hosts_memory[i],
            memory_guaranteed=hosts_memory[i]
        )


@pytest.fixture(scope="class")
def update_cluster_overcommitment(request):
    """
    1) Update cluster overcommitment to 100
    """
    def fin():
        """
        1) Update cluster overcommitment to 200
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=sla_conf.CLUSTER_NAME[0],
            mem_ovrcmt_prc=sla_conf.CLUSTER_OVERCOMMITMENT_DESKTOP
        )
    request.addfinalizer(fin)

    assert ll_clusters.updateCluster(
        positive=True,
        cluster=sla_conf.CLUSTER_NAME[0],
        mem_ovrcmt_prc=sla_conf.CLUSTER_OVERCOMMITMENT_NONE
    )


@pytest.fixture(scope="class")
def wait_for_scheduling_memory_update():
    """
    Wait until engine update host scheduling memory
    """
    sleep(sla_conf.UPDATE_SCHEDULER_MEMORY_TIMEOUT)
