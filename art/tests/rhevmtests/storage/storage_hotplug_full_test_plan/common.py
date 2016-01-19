"""
Hotplug test common functions
"""
import logging

import config
from art.rhevm_api.tests_lib.low_level import (
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.utils import test_utils as utils
import art.test_handler.exceptions as exceptions
from rhevmtests.storage import helpers as storage_helpers

__test__ = False

logger = logging.getLogger(__name__)


def create_vm_and_template(storage_domain, storage_type):
    """
    Creates and installs a VM, then creates a template from this VM

    Parameters:
        * storage_domain - name of the storage domain to create the disk in
        * storage_type - The type of storage domain (nfs, iscsi, etc.)
    Returns: Template's name
    """
    vm_name = "%s_vm_to_remove_%s" % (config.TESTNAME, storage_type)
    template_name = config.TEMPLATE_NAME % storage_type
    logger.info("Creating VM '%s'", vm_name)
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = vm_name
    vm_args['vmDescription'] = vm_name
    vm_args['storageDomainName'] = storage_domain
    vm_args['template'] = template_name
    vm_args['memory'] = 1 * config.GB
    vm_args['start'] = 'true'
    if not storage_helpers.create_vm_or_clone(**vm_args):
        raise exceptions.VMException("Could not create vm %s" % vm_name)
    logger.info("VM %s created and started successfully", vm_name)

    vm_ip = ll_vms.waitForIP(vm=vm_name)[1]['ip']

    logger.info("Setting network to be persistent")
    if not utils.setPersistentNetwork(
        host=vm_ip, password=config.VMS_LINUX_PW
    ):
        raise exceptions.VMException(
            "Unable to set network persistent vm %s" % vm_name
        )
    logging.info("Network settings changed successfully")

    logger.info("Shutting down VM %s", vm_name)
    if not ll_vms.shutdownVm(True, vm_name, 'false'):
        raise exceptions.VMException("Unable to shut down vm %s" % vm_name)
    logger.info("VM '%s' was shut down successfully", vm_name)

    logger.info("Creating template %s from vm %s", template_name, vm_name)
    if not ll_templates.createTemplate(
        True, vm=vm_name, name=template_name, cluster=config.CLUSTER_NAME
    ):
        raise exceptions.TemplateException(
            "Unable to create template %s" % template_name
        )

    logger.info(
        "Template %s created successfully from vm '%s'", template_name, vm_name
    )
    logger.info("Removing master vm '%s'", vm_name)
    if not ll_vms.removeVm(True, vm_name):
        raise exceptions.VMException("Unable to remove vm '%s'" % vm_name)

    return template_name


def create_vm_from_template(
    template_name, class_name, storage_domain, storage_type
):
    """
    Clones a vm from the template of the given image name with class name as
    part of the VM name
    """
    vm_name = config.CLASS_VM_NAME_FORMAT % (class_name, storage_type)
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = vm_name
    vm_args['vmDescription'] = vm_name
    vm_args['storageDomainName'] = storage_domain
    vm_args['template'] = template_name
    logger.info("Cloning VM %s from template %s", vm_name, template_name)
    if not storage_helpers.create_vm_or_clone(**vm_args):
        raise exceptions.VMException(
            "Unable to clone vm %s from template %s" % (vm_name, template_name)
        )
    logger.info(
        "VM %s cloned successfully from template %s", vm_name, template_name
    )
    return vm_name
