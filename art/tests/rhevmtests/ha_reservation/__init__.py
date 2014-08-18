"""
Ha reservation test initialization and teardown
"""

import os
import logging
import art.test_handler.exceptions as errors
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.high_level.datacenters import build_setup
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import vms

from rhevmtests.ha_reservation import config
from rhevmtests.system.rhevm_utils import unittest_conf

logger = logging.getLogger("HA_Reservation")

#################################################


def setup_package():
    """
    Prepare environment for MOM test
    """

    if os.environ.get("JENKINS_URL"):
        logger.info("Building setup...")
        if not unittest_conf.GOLDEN_ENV:
            build_setup(
                config.PARAMETERS, config.PARAMETERS,
                config.STORAGE_TYPE, config.TEST_NAME
            )
        for (vm, ha, placement, affinity) in [
                (config.HA_RESERVATION_ALLOC, False, 0, 'vm_affinity_pinned'),
                (config.HA_RESERVATION_VM, True, 1, 'vm_affinity_migratable')]:
            if not vms.createVm(
                True, vmName=vm,
                vmDescription="VM for test 336832",
                highly_available=ha, network=config.MGMT_BRIDGE,
                cluster=config.CLUSTER_NAME[0],
                storageDomainName=config.STORAGE_NAME[0],
                size=config.DISK_SIZE, nic=config.NIC_NAME[0],
                memory=7*config.GB, placement_host=config.HOSTS[placement],
                placement_affinity=config.ENUMS[affinity],
                installation=True, image=config.COBBLER_PROFILE,
                user="root", password=config.VMS_LINUX_PW,
                os_type=config.OS_TYPE
            ):
                raise errors.VMException("Failed to create VM for allocation")
            if not vms.stopVm(True, vm):
                raise errors.VMException("Failed to stop VM")
        logger.info("RHEL successfully installed on testing VMs")
        if not clusters.updateCluster(
            True, config.CLUSTER_NAME[0], ha_reservation=True,
            mem_ovrcmt_prc=100
        ):
            raise errors.ClusterException("Failed to update cluster")
        logger.info("Cluster configuration updated")


def teardown_package():
    """
    Cleans the environment
    """

    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        if not vms.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0],
            config.VM_NAME
        ):
            raise errors.VMException("Failed to remove all vms")
        if not unittest_conf.GOLDEN_ENV:
            storagedomains.cleanDataCenter(
                True, config.DC_NAME, vdc=config.VDC_HOST,
                vdc_password=config.VDC_ROOT_PASSWORD
            )
