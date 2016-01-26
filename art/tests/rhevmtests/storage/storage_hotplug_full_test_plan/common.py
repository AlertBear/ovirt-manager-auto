"""
Hotplug test common functions
"""

from art.rhevm_api.tests_lib.low_level import disks, templates, vms
from art.rhevm_api.utils import test_utils as utils
import art.test_handler.exceptions as exceptions
from concurrent.futures import ThreadPoolExecutor
from rhevmtests.storage.helpers import create_vm_or_clone

import config
import logging

__test__ = False

logger = logging.getLogger(__name__)


def create_vm_and_template(cobbler_image, storage_domain, storage_type):
    """
    Creates and installs a VM from the cobbler_image provided by foreman
    After creating the VM a template is created from the vm and the original
    VM is removed.
    Parameters:
        * cobbler_image - name of the image used to provision the VM
        * storage_domain - name of the storage domain to create the disk in
        * storage_type - str with type of the storage domain (nfs, iscsi, ...)
    Returns: template's name
    """
    vm_name = "%s_vm_to_remove_%s" % (config.TESTNAME, storage_type)
    template_name = config.TEMPLATE_NAME % storage_type
    logger.info("Creating VM %s and installing OS from image: %s" %
                (vm_name, cobbler_image))
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = vm_name
    vm_args['vmDescription'] = vm_name
    vm_args['storageDomainName'] = storage_domain
    vm_args['template'] = template_name
    vm_args['memory'] = 2 * config.GB
    vm_args['start'] = 'true'
    if not create_vm_or_clone(**vm_args):
        raise exceptions.VMException("Could not create vm %s" % vm_name)
    logger.info("VM %s created and started successfully" % vm_name)

    vm_ip = vms.waitForIP(vm=vm_name)[1]['ip']

    logger.info("Setting network to be persistent")
    if not utils.setPersistentNetwork(host=vm_ip,
                                      password=config.VMS_LINUX_PW):
        raise exceptions.VMException("Unable to set network persistent vm %s" %
                                     vm_name)
    logging.info("Network settings changed successfully")

    logger.info("Shutting down VM %s" % vm_name)
    if not vms.shutdownVm(True, vm=vm_name, async='false'):
        raise exceptions.VMException("Unable to stop vm %s" % vm_name)
    logger.info("VM Stopped successfully")

    logger.info("Creating template %s from vm %s" % (template_name, vm_name))
    if not templates.createTemplate(True, vm=vm_name,
                                    name=template_name,
                                    cluster=config.CLUSTER_NAME):
        raise exceptions.TemplateException("Unable to create template %s" %
                                           template_name)

    logger.info("Template %s created successfully from vm - %s" %
                (template_name, vm_name))
    logger.info("Removing master vm - %s" % vm_name)
    if not vms.removeVm(True, vm=vm_name):
        raise exceptions.VMException("Unable to remove vm - %s" % vm_name)

    return template_name


def create_vm_from_template(template_name, class_name, storage_domain,
                            storage_type):
    """
    Clones a vm from the template of the given image name
    with class name as part of the VM name:
    """
    vm_name = config.CLASS_VM_NAME_FORMAT % (
        class_name, storage_type)
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = vm_name
    vm_args['vmDescription'] = vm_name
    vm_args['storageDomainName'] = storage_domain
    vm_args['template'] = template_name
    logger.info("Cloning VM %s from template %s" % (vm_name, template_name))
    if not create_vm_or_clone(**vm_args):
        raise exceptions.VMException("Unable to clone vm %s from template %s" %
                                     (vm_name, template_name))
    logger.info("VM %s cloned successfully from template %s" %
                (vm_name, template_name))

    return vm_name


def shutdown_and_remove_vms(vm_names):
    """
    Attempts to shutdown and remove the vms with the given names.
    If a gracefull shutdown doesn't succed it stops the VM issuing a warning
    in the logs.

    Parameters:
        * vm_names - a list of vm names
    """
    results = []

    def unattach_and_shutdown(vm_name):
        """Unattached not active disks, shutdown and remove vm"""
        vmDisks = vms.getVmDisks(vm_name)
        for disk in vmDisks:
            if not disk.get_bootable():
                assert disks.detachDisk(True, disk.get_alias(), vm_name)
        stopVm = vms.get_vm_state(vm_name) == config.VM_UP
        assert vms.removeVm(True, vm_name, stopVM=str(stopVm))

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        for index in xrange(len(vm_names)):
            vm_name = vm_names[index]
            logger.info("Removing vm %s", vm_name)
            results.append(executor.submit(unattach_and_shutdown, vm_name))

    utils.raise_if_exception(results)
    logger.info("All vms removed successfully")
