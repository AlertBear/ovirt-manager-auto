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

logger = logging.getLogger(__name__)

#################################################

DISK_SIZE = 3 * 1024 * 1024 * 1024


def setup_package():
    """
    Prepare environment for Payloads Test
    """
    import config
    logger.info("Building setup...")
    if not dc_api.build_setup(config.PARAMETERS, config.PARAMETERS,
                              config.STORAGE_TYPE, config.TEST_NAME):
        raise errors.DataCenterException("Setup environment failed")
    logger.info("Create new vm for template")
    if not vm_api.createVm(positive=True, vmName=config.template_vm,
                           vmDescription="Payload Test",
                           cluster=config.cluster_name,
                           storageDomainName=config.data_name[0],
                           size=DISK_SIZE, nic='nic1',
                           network=config.cluster_network,
                           display_type=config.vm_display_type):
            raise errors.VMException("Cannot create vm %s" %
                                     config.template_vm)
    if not prepare_vm_for_rhel_template(config.template_vm,
                                        config.vm_password,
                                        config.template_image):
        raise errors.VMException("Preparation vm %s for template failed" %
                                 config.template_vm)
    if not createTemplate(True, vm=config.template_vm,
                          name=config.template_name,
                          cluster=config.cluster_name):
        raise errors.TemplateException("Failed create template from vm %s" %
                                       config.template_vm)


def teardown_package():
    """
    Cleans the environment
    """
    import config
    logger.info("Teardown...")
    if not cleanDataCenter(True, config.dc_name, vdc=config.VDC,
                           vdc_password=config.VDC_PASSWORD):
        raise errors.DataCenterException("Clean up environment failed")
