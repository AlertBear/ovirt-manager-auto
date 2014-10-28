"""
Hotplug test common functions
"""

from art.rhevm_api.tests_lib.low_level import disks, templates, vms
from art.rhevm_api.utils import test_utils as utils
import art.test_handler.exceptions as exceptions
from concurrent.futures import ThreadPoolExecutor
import config
import logging

__test__ = False

logger = logging.getLogger(__name__)


def start_creating_disks_for_test(storage_domain, wipe_after_delete, sd_type):
    """
    Begins asynchronous creation of disks of all permutations of disk
    interfaces, shareable/non-shareable for each storage type
    Parameters:
        * storage_domain: name of the storage domain where the disks will be
            created
        * wipe_after_delete: Boolean if wipe_after_delete should be activated
        * sd_type: storage type of the domain where the disks will be created
    Returns: list of tuples with (disk_alias, Future object)
    """
    logger.info("Creating all disks for plugging/unplugging")
    disk_args = {
        # Fixed arguments
        'positive': True,
        'provisioned_size': 2 * config.GB,
        'wipe_after_delete': wipe_after_delete,
        'storagedomain': storage_domain,
        'bootable': False,
        # Custom arguments - change for each disk
        'interface': None,
        'shareable': None,
        'alias': None,
        'format': None,
        'sparse': None
    }
    results = []
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        for disk_interface in config.DISK_INTERFACES:
            for shareable in (True, False):
                disk_args['alias'] = config.DISK_NAME_FORMAT % (
                    disk_interface,
                    'shareable' if shareable else 'non-shareable',
                    sd_type)
                disk_args['interface'] = disk_interface
                disk_args['shareable'] = shareable
                disk_args['format'] = 'raw' if shareable else 'cow'
                disk_args['sparse'] = not shareable
                results.append((
                    disk_args['alias'],
                    executor.submit(disks.addDisk, **disk_args)))
    return results


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
    if not vms.createVm(config.positive,
                        vmName=vm_name,
                        vmDescription=vm_name,
                        cluster=config.CLUSTER_NAME,
                        nic=config.HOST_NICS[0],
                        storageDomainName=storage_domain,
                        size=10 * config.GB,
                        diskInterface=config.ENUMS['interface_virtio'],
                        memory=2 * config.GB,
                        image=cobbler_image,
                        installation=True,
                        useAgent=True,
                        os_type=config.ENUMS['rhel6'],
                        user=config.VMS_LINUX_USER,
                        password=config.VMS_LINUX_PW,
                        network=config.MGMT_BRIDGE):
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
    if not vms.shutdownVm(config.positive, vm=vm_name, async='false'):
        raise exceptions.VMException("Unable to stop vm %s" % vm_name)
    logger.info("VM Stopped successfully")

    logger.info("Creating template %s from vm %s" % (template_name, vm_name))
    if not templates.createTemplate(config.positive, vm=vm_name,
                                    name=template_name,
                                    cluster=config.CLUSTER_NAME):
        raise exceptions.TemplateException("Unable to create template %s" %
                                           template_name)

    logger.info("Template %s created successfully from vm - %s" %
                (template_name, vm_name))
    logger.info("Removing master vm - %s" % vm_name)
    if not vms.removeVm(config.positive, vm=vm_name):
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
    logger.info("Cloning VM %s from template %s" % (vm_name, template_name))
    if not vms.createVm(positive=config.positive,
                        vmName=vm_name,
                        vmDescription=vm_name,
                        template=template_name,
                        storageDomainName=storage_domain,
                        start='false',
                        cluster=config.CLUSTER_NAME,
                        network=config.MGMT_BRIDGE):
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
        assert vms.removeVm(config.positive, vm_name, stopVM=str(stopVm))

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        for index in xrange(len(vm_names)):
            vm_name = vm_names[index]
            logger.info("Removing vm %s", vm_name)
            results.append(executor.submit(unattach_and_shutdown, vm_name))

    utils.raise_if_exception(results)
    logger.info("All vms removed successfully")
