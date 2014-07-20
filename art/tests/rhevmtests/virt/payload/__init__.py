"""
Virt - Payloads test initialization
"""
import logging
from art.rhevm_api.tests_lib.high_level.vms import \
    prepare_vm_for_rhel_template
from art.rhevm_api.tests_lib.low_level.templates import createTemplate
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.high_level.datacenters as dc_api
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from rhevmtests.virt import config

logger = logging.getLogger(__name__)

#################################################

DISK_SIZE = 3 * 1024 * 1024 * 1024


def setup_package():
    """
    Prepare environment for Payloads Test
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no setup")
        return

    logger.info("Building setup...")
    if not dc_api.build_setup(config.PARAMETERS, config.PARAMETERS,
                              config.STORAGE_TYPE, config.TEST_NAME):
        raise errors.DataCenterException("Setup environment failed")

    logger.info("Create new vm for template")
    if not vm_api.createVm(positive=True, vmName=config.VM_NAMES[0],
                           vmDescription="Payload Test",
                           cluster=config.CLUSTER_NAME[0],
                           storageDomainName=config.STORAGE_NAME[0],
                           size=DISK_SIZE, nic='nic1',
                           network=config.MGMT_BRIDGE,
                           display_type=config.DISPLAY_TYPE):
            raise errors.VMException("Cannot create vm %s" %
                                     config.VM_NAMES[0])
    if not prepare_vm_for_rhel_template(config.VM_NAMES[0],
                                        config.VMS_LINUX_PW,
                                        config.COBBLER_PROFILE):
        raise errors.VMException("Preparation vm %s for template failed" %
                                 config.VM_NAMES[0])
    if not createTemplate(True, vm=config.VM_NAMES[0],
                          name=config.TEMPLATE_NAME[0],
                          cluster=config.CLUSTER_NAME[0]):
        raise errors.TemplateException("Failed create template %s from vm %s" %
                                       config.TEMPLATE_NAME[0],
                                       config.VM_NAMES[0])


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on golden env, no teardown")
        return
    logger.info("Teardown...")
    if not cleanDataCenter(True, config.dc_name, vdc=config.VDC_HOST,
                           vdc_password=config.VDC_ROOT_PASSWORD):
        raise errors.DataCenterException("Clean up environment failed")
