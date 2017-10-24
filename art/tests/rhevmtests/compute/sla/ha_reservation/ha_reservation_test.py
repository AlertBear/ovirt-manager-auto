"""
Testing memory HA reservation on Cluster, this feature should find out
if cluster is HA safe
Prerequisites: 1 DC, 2 hosts, 1 SD (NFS)
Tests covers:
    Warning on insufficient memory
    Setting system to HA safe
    multiple VMs
    host-maintenance
"""
import pytest
import rhevmtests.compute.sla.helpers as sla_helpers

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import helpers
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, tier2, SlaTest
from rhevmtests.compute.sla.fixtures import (
    activate_hosts,
    choose_specific_host_as_spm,
    create_vms,
    migrate_he_vm,
    start_vms,
    update_vms,
    update_vms_memory_to_hosts_memory
)

host_as_spm = 0
he_dst_host = 0


def update_ha_reservation_interval(ha_reservation_interval):
    """
    Update HA reservation interval via engine-config

    Args:
        ha_reservation_interval (int): HA reservation interval in minutes

    Returns:
        bool: True, if update succeed, otherwise False
    """
    cmd = [
        "{0}={1}".format(
            conf.HA_RESERVATION_INTERVAL,
            ha_reservation_interval
        )
    ]
    if not conf.ENGINE.engine_config(action='set', param=cmd).get('results'):
        return False
    return True


@pytest.fixture(scope="module")
def init_ha_reservation(request):
    """
    1) Deactivate third host
    2) Update HA reservation time interval
    3) Update cluster overcommitment and HA reservation
    4) Update cluster over commitment to None
    """
    def fin():
        """
        1) Disable cluster HA reservation option
        2) Activate third host
        3) Update HA reservation time interval
        """
        results = list()
        results.append(
            ll_clusters.updateCluster(
                positive=True,
                cluster=conf.CLUSTER_NAME[0],
                ha_reservation=False
            )
        )
        results.append(
            ll_hosts.activate_host(
                positive=True,
                host=conf.HOSTS[2],
                host_resource=conf.VDS_HOSTS[2]
            )
        )
        testflow.teardown(
            "Change HA reservation interval to %s via the engine-config",
            conf.DEFAULT_RESERVATION_INTERVAL
        )
        results.append(
            update_ha_reservation_interval(
                ha_reservation_interval=conf.DEFAULT_RESERVATION_INTERVAL
            )
        )
        assert all(results)
    request.addfinalizer(fin)

    assert ll_hosts.deactivate_host(
        positive=True, host=conf.HOSTS[2], host_resource=conf.VDS_HOSTS[2]
    )
    testflow.setup(
        "Change HA reservation interval to %s via the engine-config",
        conf.NEW_RESERVATION_INTERVAL
    )
    assert update_ha_reservation_interval(
        ha_reservation_interval=conf.NEW_RESERVATION_INTERVAL
    )
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        ha_reservation=True,
        mem_ovrcmt_prc=conf.CLUSTER_OVERCOMMITMENT_NONE
    )


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    migrate_he_vm.__name__,
    init_ha_reservation.__name__
)
class BaseHAReservation(SlaTest):
    """
    Base class for all HA reservation tests
    """
    pass


@pytest.mark.usefixtures(
    update_vms.__name__,
    start_vms.__name__
)
class TestPutHostToMaintenance(BaseHAReservation):
    """
    Moving host to maintenance should make cluster not HA safe
    """
    vms_to_params = {
        conf.VM_NAME[2]: dict(conf.GENERAL_VM_PARAMS)
    }
    vms_to_start = conf.VM_NAME[2:3]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM3-4995")
    def test_host_maintenance(self):
        """
        1) Check if cluster is HA safe
        2) Move host to maintenance
        3) Check if cluster does not HA safe
        """
        testflow.step(
            "Check if cluster %s is HA safe", conf.CLUSTER_NAME[0]
        )
        assert helpers.is_cluster_ha_safe()

        testflow.step("Deactivate host %s", conf.HOSTS[1])
        assert ll_hosts.deactivate_host(
            positive=True, host=conf.HOSTS[1], host_resource=conf.VDS_HOSTS[1]
        )

        testflow.step(
            "Check if cluster %s does not HA safe", conf.CLUSTER_NAME[0]
        )
        assert not helpers.is_cluster_ha_safe()

    @tier2
    @polarion("RHEVM3-4992")
    def test_set_cluster_ha_safe(self):
        """
        Activate host
        Check if cluster is Ha safe
        """
        assert ll_hosts.activate_host(
            positive=True, host=conf.HOSTS[1], host_resource=conf.VDS_HOSTS[1]
        )

        testflow.step(
            "Check if cluster %s is HA safe", conf.CLUSTER_NAME[0]
        )
        assert helpers.is_cluster_ha_safe()


@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vms_memory_to_hosts_memory.__name__,
    start_vms.__name__
)
class TestNotCompatibleHost(BaseHAReservation):
    """
    Cluster failing HA reservation check based on
    insufficient resources
    """
    vms_to_params = {
        conf.VM_NAME[0]: dict(conf.SPECIFIC_VMS_PARAMS[conf.VM_NAME[0]]),
        conf.VM_NAME[1]: dict(conf.SPECIFIC_VMS_PARAMS[conf.VM_NAME[1]])
    }
    update_vms_memory = conf.VM_NAME[:2]
    vms_to_start = conf.VM_NAME[:2]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM3-4987")
    def test_insufficient_resources(self):
        """
        2 host scenario, 1st host has memory allocated,
        2nd host has running HA VM
        """
        testflow.step(
            "Check if cluster %s does not HA safe", conf.CLUSTER_NAME[0]
        )
        assert not helpers.is_cluster_ha_safe()

        vm_host = ll_vms.get_vm_host(vm_name=conf.VM_NAME[0])
        host_scheduling_memory = ll_hosts.get_host_max_scheduling_memory(
            host_name=vm_host
        )
        vm_memory = ll_vms.get_vm_memory(vm_name=conf.VM_NAME[0])
        host_expected_sch_memory = host_scheduling_memory + vm_memory

        testflow.step("Stop memory allocating VM %s", conf.VM_NAME[0])
        assert ll_vms.stopVm(positive=True, vm=conf.VM_NAME[0])

        testflow.step(
            "Wait until the engine will update host %s max scheduling memory",
            vm_host
        )
        sla_helpers.wait_for_host_scheduling_memory(
            host_name=vm_host,
            expected_sch_memory=host_expected_sch_memory,
            sampler_timeout=conf.RESERVATION_TIMEOUT
        )

        testflow.step(
            "Check if cluster %s is HA safe", conf.CLUSTER_NAME[0]
        )
        assert helpers.is_cluster_ha_safe()


@pytest.mark.usefixtures(
    create_vms.__name__,
    start_vms.__name__,
    activate_hosts.__name__
)
class TestMultiVM(BaseHAReservation):
    """
    Create 8 HA VMS in HA safe cluster and put one host to maintenance
    """
    vm_list = ["%s_%d" % ("HA_reservation_VM", i) for i in range(8)]
    vms_create_params = dict(
        (vm_name, dict(conf.MULTI_VMS_PARAMS)) for vm_name in vm_list
    )
    vms_to_start = vm_list
    wait_for_vms_ip = False
    hosts_to_activate_indexes = [1]

    @tier2
    @polarion("RHEVM3-4994")
    def test_multi_vms(self):
        """
        Put host to maintenance and check cluster HA safe status
        """
        testflow.step(
            "Check if cluster %s is HA safe", conf.CLUSTER_NAME[0]
        )
        assert helpers.is_cluster_ha_safe()

        testflow.step("Deactivate host %s", conf.HOSTS[1])
        assert ll_hosts.deactivate_host(
            positive=True, host=conf.HOSTS[1], host_resource=conf.VDS_HOSTS[1]
        )

        testflow.step(
            "Check if cluster %s does not HA safe", conf.CLUSTER_NAME[0]
        )
        assert not helpers.is_cluster_ha_safe()
