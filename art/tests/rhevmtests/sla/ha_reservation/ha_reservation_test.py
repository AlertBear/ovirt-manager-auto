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
import logging

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sds
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers
import pytest
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion
from rhevmtests.sla.fixtures import (
    activate_hosts,
    create_vms,
    start_vms,
    update_vms,
    update_vms_memory_to_hosts_memory
)

logger = logging.getLogger(__name__)


def update_ha_reservation_interval(ha_reservation_interval):
    """
    Update HA reservation interval via engine-config

    Args:
        ha_reservation_interval (int): HA reservation interval in minutes

    Returns:
        bool: True, if update succeed, otherwise False
    """
    logger.info(
        "Change HA reservation interval to %s via engine-config",
        ha_reservation_interval
    )
    cmd = [
        "{0}={1}".format(
            conf.HA_RESERVATION_INTERVAL,
            ha_reservation_interval
        )
    ]
    if not test_utils.set_engine_properties(conf.ENGINE, cmd):
        return False
    logger.info(
        "Wait for active status of storage domain %s", conf.STORAGE_NAME[0]
    )
    return ll_sds.waitForStorageDomainStatus(
        positive=True,
        dataCenterName=conf.DC_NAME[0],
        storageDomainName=conf.STORAGE_NAME[0],
        expectedStatus=conf.SD_ACTIVE
    )


@pytest.fixture(scope="module", autouse=True)
def deactivate_third_host(request):
    """
    1) Deactivate third host
    2) Update HA reservation time interval
    3) Update cluster overcommitment and HA reservation
    """
    def fin():
        """
        1) Update cluster to default parameters
        2) Activate third host
        3) Update HA reservation time interval
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            ha_reservation=False,
            mem_ovrcmt_prc=conf.CLUSTER_OVERCOMMITMENT_DESKTOP
        )
        ll_hosts.activateHost(positive=True, host=conf.HOSTS[2])
        update_ha_reservation_interval(
            ha_reservation_interval=conf.DEFAULT_RESERVATION_INTERVAL
        )
    request.addfinalizer(fin)

    assert ll_hosts.deactivateHost(positive=True, host=conf.HOSTS[2])
    assert update_ha_reservation_interval(
        ha_reservation_interval=conf.RESERVATION_TIMEOUT / 60
    )
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        ha_reservation=True,
        mem_ovrcmt_prc=conf.CLUSTER_OVERCOMMITMENT_NONE
    )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    start_vms.__name__
)
class PutHostToMaintenance(u_libs.SlaTest):
    """
    Moving host to maintenance should make cluster not HA safe
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[2]: dict(conf.GENERAL_VM_PARAMS)
    }
    vms_to_start = conf.VM_NAME[2:3]
    wait_for_vms_ip = False

    @polarion("RHEVM3-4995")
    def test_host_maintenance(self):
        """
        1) Check if cluster is HA safe
        2) Move host to maintenance
        3) Check if cluster does not HA safe
        """
        u_libs.testflow.step(
            "Check if cluster %s is HA safe", conf.CLUSTER_NAME[0]
        )
        assert helpers.is_cluster_ha_safe()

        u_libs.testflow.step("Deactivate host %s", conf.HOSTS[1])
        assert ll_hosts.deactivateHost(positive=True, host=conf.HOSTS[1])

        u_libs.testflow.step(
            "Check if cluster %s does not HA safe", conf.CLUSTER_NAME[0]
        )
        assert not helpers.is_cluster_ha_safe()

    @polarion("RHEVM3-4992")
    def test_set_cluster_ha_safe(self):
        """
        Activate host
        Check if cluster is Ha safe
        """
        u_libs.testflow.step("Activate host %s", conf.HOSTS[1])
        assert ll_hosts.activateHost(positive=True, host=conf.HOSTS[1])

        u_libs.testflow.step(
            "Check if cluster %s is HA safe", conf.CLUSTER_NAME[0]
        )
        assert helpers.is_cluster_ha_safe()


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    update_vms_memory_to_hosts_memory.__name__,
    start_vms.__name__
)
class NotCompatibleHost(u_libs.SlaTest):
    """
    Cluster failing HA reservation check based on
    insufficient resources
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: dict(conf.SPECIFIC_VMS_PARAMS[conf.VM_NAME[0]]),
        conf.VM_NAME[1]: dict(conf.SPECIFIC_VMS_PARAMS[conf.VM_NAME[1]])
    }
    update_vms_memory = conf.VM_NAME[:2]
    vms_to_start = conf.VM_NAME[:2]
    wait_for_vms_ip = False

    @polarion("RHEVM3-4987")
    def test_insufficient_resources(self):
        """
        2 host scenario, 1st host has memory allocated,
        2nd host has running HA VM
        """
        u_libs.testflow.step(
            "Check if cluster %s does not HA safe", conf.CLUSTER_NAME[0]
        )
        assert not helpers.is_cluster_ha_safe()

        u_libs.testflow.step("Stop memory allocating VM %s", conf.VM_NAME[0])
        assert ll_vms.stopVm(positive=True, vm=conf.VM_NAME[0])

        u_libs.testflow.step(
            "Check if cluster %s is HA safe", conf.CLUSTER_NAME[0]
        )
        assert helpers.is_cluster_ha_safe()


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_vms.__name__,
    start_vms.__name__,
    activate_hosts.__name__
)
class MultiVM(u_libs.SlaTest):
    """
    Create 8 HA VMS in HA safe cluster and put one host to maintenance
    """
    __test__ = True
    vm_list = ["%s_%d" % ("HA_reservation_VM", i) for i in range(8)]
    vms_create_params = dict(
        (vm_name, dict(conf.MULTI_VMS_PARAMS)) for vm_name in vm_list
    )
    vms_to_start = vm_list
    wait_for_vms_ip = False
    hosts_to_activate_indexes = [0]

    @polarion("RHEVM3-4994")
    def test_multi_vms(self):
        """
        Put host to maintenance and check cluster HA safe status
        """
        u_libs.testflow.step(
            "Check if cluster %s is HA safe", conf.CLUSTER_NAME[0]
        )
        assert helpers.is_cluster_ha_safe()

        u_libs.testflow.step("Deactivate host %s", conf.HOSTS[0])
        assert ll_hosts.deactivateHost(positive=True, host=conf.HOSTS[0])

        u_libs.testflow.step(
            "Check if cluster %s does not HA safe", conf.CLUSTER_NAME[0]
        )
        assert not helpers.is_cluster_ha_safe()
