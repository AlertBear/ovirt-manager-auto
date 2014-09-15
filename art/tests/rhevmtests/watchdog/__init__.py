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
        for vm in (
            config.VM_NAME[0], config.WATCHDOG_CRUD_VM,
            config.WATCHDOG_TEMPLATE_VM
        ):
            if not vms.createVm(
                positive=True, vmName=vm,
                vmDescription="Watchdog VM",
                cluster=config.CLUSTER_NAME[0],
                storageDomainName=config.STORAGE_NAME[0],
                size=6 * config.GB, nic=config.NIC_NAME[0],
                memory=2 * config.GB,
                placement_affinity=AFFINITY,
                placement_host=config.HOSTS[0],
                network=config.MGMT_BRIDGE,
                installation=True, image=config.COBBLER_PROFILE,
                user="root", password=config.VMS_LINUX_PW,
                os_type=config.OS_TYPE
            ):
                raise errors.VMException("Cannot add VM %s" % vm)
            if not vms.stopVm(True, vm):
                raise errors.VMException("Cannot stop VM %s" % vm)


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        cleanDataCenter(True, config.DC_NAME[0], vdc=config.VDC_HOST,
                        vdc_password=config.VDC_ROOT_PASSWORD)
