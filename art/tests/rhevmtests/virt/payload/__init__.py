"""
Virt - Payloads test initialization
"""
import logging
from art.rhevm_api.tests_lib.low_level.templates import createTemplate
from art.rhevm_api.utils.test_utils import setPersistentNetwork
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.high_level.datacenters as dc_api
from rhevmtests.virt import config

logger = logging.getLogger(__name__)

# ################################################

DISK_SIZE = config.GB * 3


def setup_package():
    """
    Prepare environment for Payloads Test
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no setup")
        return

    logger.info("Building setup...")
    if not dc_api.build_setup(
        config.PARAMETERS,
        config.PARAMETERS,
        config.STORAGE_TYPE,
        config.TEST_NAME
    ):
        raise errors.DataCenterException("Setup environment failed")

    vm_name = config.VM_NAME[0]
    logger.info("Create new vm for template")
    if not vm_api.createVm(
        positive=True,
        vmName=vm_name,
        vmDescription="Payload Test",
        cluster=config.CLUSTER_NAME[0],
        storageDomainName=config.STORAGE_NAME[0],
        provisioned_size=DISK_SIZE,
        nic=config.NIC_NAME[0],
        network=config.MGMT_BRIDGE,
        display_type=config.DISPLAY_TYPE,
        installation=True,
        image=config.COBBLER_PROFILE,
        user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW,
        os_type=config.OS_TYPE
    ):
        raise errors.VMException(
            "Cannot create vm %s" %
            vm_name
        )

    status, result = vm_api.waitForIP(vm_name)
    logging.info("Seal vm %s", vm_name)
    if not setPersistentNetwork(result.get('ip'), config.VMS_LINUX_PW):
        raise errors.VMException(
            "Failed to seal vm %s" %
            vm_name
        )
    logging.info("Stop vm %s" % vm_name)
    if not vm_api.stopVm(True, vm_name):
        raise errors.VMException(
            "Failed to stop vm %s" %
            vm_name
        )

    if not createTemplate(True, vm=vm_name, name=config.TEMPLATE_NAME[0],
                          cluster=config.CLUSTER_NAME[0]):
        raise errors.TemplateException(
            "Failed create template %s from vm %s" %
            (
                config.TEMPLATE_NAME[0],
                vm_name
            )
        )


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no teardown")
        return
    logger.info("Teardown...")
    if not dc_api.clean_datacenter(
            True, config.DC_NAME[0], vdc=config.VDC_HOST,
            vdc_password=config.VDC_ROOT_PASSWORD
    ):
        raise errors.DataCenterException("Clean up environment failed")
