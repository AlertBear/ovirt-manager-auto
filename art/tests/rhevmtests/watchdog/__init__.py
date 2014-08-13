"""
SLA test
"""

import os
import logging

import art.rhevm_api.tests_lib.high_level.datacenters as datacenters
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.test_handler.exceptions as errors

from rhevmtests.watchdog import config

logger = logging.getLogger("SLA")
AFFINITY = config.ENUMS['vm_affinity_user_migratable']

#################################################


def setup_package():
    """
    Prepare environment for SLA test
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Building setup...")
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TEST_NAME)

        if not vms.createVm(
            positive=True, vmName=config.VM_NAME[0],
            vmDescription="Watchdog VM",
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            size=6 * config.GB, nic=config.NIC_NAME[0],
            memory=2 * config.GB,
            placement_affinity=AFFINITY,
            placement_host=config.HOSTS[0],
            network=config.MGMT_BRIDGE
        ):
            raise errors.VMException("Cannot add VM")
        if not vms.unattendedInstallation(
            True, config.VM_NAME[0],
            image=config.COBBLER_PROFILE
        ):
            raise errors.VMException("Cannot install Linux OS")


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        cleanDataCenter(True, config.DC_NAME[0], vdc=config.VDC_HOST,
                        vdc_password=config.VDC_ROOT_PASSWORD)
