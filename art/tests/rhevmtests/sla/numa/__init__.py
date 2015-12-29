"""
Numa Test - test initialization
"""
import os
import logging
import config as conf
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.datacenters as hl_dc
from art.rhevm_api.resources.package_manager import YumPackageManager

logger = logging.getLogger(__name__)

#################################################


def setup_package():
    """
    Prepare environment for Numa Test
    """
    if os.environ.get("JENKINS_URL") and not conf.GOLDEN_ENV:
        logger.info("Building setup...")
        if not hl_dc.build_setup(
            conf.PARAMETERS, conf.PARAMETERS,
            conf.STORAGE_TYPE, conf.TEST_NAME
        ):
            raise errors.DataCenterException("Setup environment failed")
        logger.info("Create vm for numa test")
        if not ll_vms.createVm(
            positive=True, vmName=conf.VM_NAME[0],
            vmDescription="RHEL VM",
            cluster=conf.CLUSTER_NAME[0],
            storageDomainName=conf.STORAGE_NAME[0],
            size=6 * conf.GB, nic=conf.NIC_NAME[0],
            memory=conf.GB,
            network=conf.MGMT_BRIDGE,
            installation=True, image=conf.COBBLER_PROFILE,
            user=conf.VMS_LINUX_USER, password=conf.VMS_LINUX_PW,
            os_type=conf.OS_TYPE, useAgent=True
        ):
            raise errors.VMException("Failed to create vm")
        logger.info("Stop vm %s", conf.VM_NAME[0])
        if not ll_vms.stopVm(True, conf.VM_NAME[0]):
            raise errors.VMException(
                "Failed to stop vm %s" % conf.VM_NAME[0]
            )
    host_yum_manager = YumPackageManager(conf.VDS_HOSTS[0])
    logger.info(
        "Install %s package on host %s",
        conf.NUMACTL_PACKAGE, conf.VDS_HOSTS[0]
    )
    if not host_yum_manager.install(conf.NUMACTL_PACKAGE):
        raise errors.HostException(
            "Failed to install package %s on host %s" %
            (conf.NUMACTL_PACKAGE, conf.VDS_HOSTS[0])
        )


def teardown_package():
    """
    Cleans the environment
    """
    if os.environ.get("JENKINS_URL") and not conf.GOLDEN_ENV:
        if not hl_dc.clean_datacenter(
            positive=True,
            datacenter=conf.DC_NAME[0],
            vdc=conf.VDC_HOST,
            vdc_password=conf.VDC_PASSWORD
        ):
            raise errors.DataCenterException("Clean up environment failed")
