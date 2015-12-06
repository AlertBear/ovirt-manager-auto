"""
Scheduler - Rhevm Cluster Policies test initialization
"""

import os
import logging

from rhevmtests.sla import config
from rhevmtests.sla.scheduler_tests import helpers

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.sla as sla_api
import art.rhevm_api.tests_lib.high_level.datacenters as dc_api

logger = logging.getLogger(__name__)

#################################################

DISK_SIZE = config.GB


def setup_package():
    """
    Prepare environment for Rhevm Cluster Policies Test
    """
    if os.environ.get("JENKINS_URL"):
        if not config.GOLDEN_ENV:
            logger.info("Building setup...")
            if not dc_api.build_setup(
                config.PARAMETERS, config.PARAMETERS,
                config.STORAGE_TYPE, config.TEST_NAME
            ):
                raise errors.DataCenterException("Setup environment failed")
            logger.info("Create new vms")
            for vm in config.VM_NAME[:3]:
                if not vm_api.createVm(
                    positive=True, vmName=vm, vmDescription="Test VM",
                    cluster=config.CLUSTER_NAME[0],
                    storageDomainName=config.STORAGE_NAME[0],
                    size=DISK_SIZE, nic=config.NIC_NAME[0],
                    network=config.MGMT_BRIDGE
                ):
                    raise errors.VMException("Cannot create vm %s" % vm)
    helpers.choose_host_as_spm(
        host_name=config.HOSTS[3],
        data_center=config.DC_NAME[0],
        storage_domain=config.STORAGE_NAME[0]
    )


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        logger.info("Free all host CPU's from loading")
        sla_api.stop_cpu_loading_on_resources(config.VDS_HOSTS[:3])
        if not config.GOLDEN_ENV:
            if not dc_api.clean_datacenter(
                    True, config.DC_NAME[0], vdc=config.VDC_HOST,
                    vdc_password=config.VDC_ROOT_PASSWORD
            ):
                raise errors.DataCenterException("Clean up environment failed")
