"""
Numa Test - test initialization
"""

import os
import logging
from rhevmtests.sla.numa import config as c
from art.rhevm_api.resources.package_manager import YumPackageManager

import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.datacenters as ll_dc

logger = logging.getLogger(__name__)

#################################################


def setup_package():
    """
    Prepare environment for Numa Test
    """
    if os.environ.get("JENKINS_URL") and not c.GOLDEN_ENV:
        logger.info("Building setup...")
        if not ll_dc.build_setup(
                c.PARAMETERS, c.PARAMETERS,
                c.STORAGE_TYPE, c.TEST_NAME
        ):
            raise errors.DataCenterException("Setup environment failed")
        logger.info("Create vm for numa test")
        if not ll_vms.createVm(
            positive=True, vmName=c.VM_NAME[0],
            vmDescription="RHEL VM",
            cluster=c.CLUSTER_NAME[0],
            storageDomainName=c.STORAGE_NAME[0],
            size=6 * c.GB, nic=c.NIC_NAME[0],
            memory=c.GB,
            network=c.MGMT_BRIDGE,
            installation=True, image=c.COBBLER_PROFILE,
            user=c.VMS_LINUX_USER, password=c.VMS_LINUX_PW,
            os_type=c.OS_TYPE, useAgent=True
        ):
            raise errors.VMException("Failed to create vm")
        logger.info("Stop vm %s", c.VM_NAME[0])
        if not ll_vms.stopVm(True, c.VM_NAME[0]):
            raise errors.VMException(
                "Failed to stop vm %s" % c.VM_NAME[0]
            )
    host_yum_manager = YumPackageManager(c.VDS_HOSTS[0])
    logger.info(
        "Install %s package on host %s",
        c.NUMACTL_PACKAGE, c.VDS_HOSTS[0]
    )
    if not host_yum_manager.install(c.NUMACTL_PACKAGE):
        raise errors.HostException(
            "Failed to install package %s on host %s" %
            (c.NUMACTL_PACKAGE, c.VDS_HOSTS[0])
        )


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL") and not c.GOLDEN_ENV:
        if not ll_dc.clean_datacenter(
                True, c.DC_NAME[0], vdc=c.VDC_HOST,
                vdc_password=c.VDC_PASSWORD
        ):
            raise errors.DataCenterException("Clean up environment failed")
    host_yum_manager = YumPackageManager(c.VDS_HOSTS[0])
    logger.info(
        "Remove %s package from host %s",
        c.NUMACTL_PACKAGE, c.VDS_HOSTS[0]
    )
    if not host_yum_manager.remove(c.NUMACTL_PACKAGE):
        raise errors.HostException(
            "Failed to remove package %s from host %s" %
            (c.NUMACTL_PACKAGE, c.VDS_HOSTS[0])
        )
