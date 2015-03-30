"""
Scheduler - Power Saving with Power Management test initialization
"""

import os
import time
import logging
from rhevmtests.sla import config
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
import art.rhevm_api.tests_lib.high_level.datacenters as dc_api

logger = logging.getLogger(__name__)

#################################################


def setup_package():
    """
    Prepare environment for Power Saving with Power Management Test
    """
    if os.environ.get("JENKINS_URL"):
        if not config.GOLDEN_ENV:
            logger.info("Building setup...")
            if not dc_api.build_setup(
                config.PARAMETERS, config.PARAMETERS,
                config.STORAGE_TYPE, config.TEST_NAME
            ):
                raise errors.DataCenterException("Setup environment failed")
            logger.info("Create three new vms")
            for vm in config.VM_NAME[:3]:
                if not vm_api.createVm(
                    True, vm, vmDescription="Test VM",
                    cluster=config.CLUSTER_NAME[0],
                    storageDomainName=config.STORAGE_NAME[0], size=config.GB,
                    nic=config.NIC_NAME[0], network=config.MGMT_BRIDGE
                ):
                    raise errors.VMException("Cannot create %s" % vm)
        logger.info("Select host %s as SPM", config.HOSTS[0])
        if not host_api.checkHostSpmStatus(True, config.HOSTS[0]):
            if not host_api.select_host_as_spm(
                True, config.HOSTS[0], config.DC_NAME[0]
            ):
                raise errors.DataCenterException(
                    "Selecting host as SPM failed"
                )
        hosts_resource = dict(zip(config.HOSTS[:3], config.VDS_HOSTS[:3]))
        for host, host_resource in hosts_resource.iteritems():
            host_pm = config.pm_mapping.get(host_resource.network.hostname)
            if host_pm is None:
                raise errors.SkipTest(
                    "Host %s with fqdn don't have power management" % host
                )
            if not host_api.updateHost(
                    True, host, pm=True, pm_automatic=True, **host_pm
            ):
                raise errors.HostException("Can not update host %s" % host)


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL"):
        logger.info("Teardown...")
        for host in config.HOSTS[:3]:
            logger.info("Check if host %s in state down", host)
            host_status = host_api.getHostState(host) == config.HOST_DOWN
            if host_status:
                logger.info(
                    "Wait %d seconds between fence operations",
                    config.FENCE_TIMEOUT
                )
                time.sleep(config.FENCE_TIMEOUT)
                logger.info("Start host %s", host)
                if not host_api.fenceHost(True, host, 'start'):
                    raise errors.HostException("Failed to start host")
            if not host_api.updateHost(True, host, pm=False):
                raise errors.HostException("Can not update host %s" % host)
        if not config.GOLDEN_ENV:
            if not dc_api.clean_datacenter(
                    True, config.DC_NAME[0], vdc=config.VDC_HOST,
                    vdc_password=config.VDC_ROOT_PASSWORD
            ):
                raise errors.DataCenterException("Clean up environment failed")
