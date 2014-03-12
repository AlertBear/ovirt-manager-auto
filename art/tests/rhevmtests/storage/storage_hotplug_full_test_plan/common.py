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


def start_creating_disks_for_test():
    """
    Begins asynchronous creation of disks of all permutations of disk
    interfaces, shareable/non-shareable for each image to be used from cobbler
    and returns a list of Futures with calls to the creation of each disk
    """
    logger.info("Creating all disks for plugging/unplugging")
    disk_args = {
        # Fixed arguments
        'positive': True,
        'provisioned_size': 2 * config.GB,
        'wipe_after_delete': config.BLOCK_FS,
        'storagedomain': config.STORAGE_DOMAIN_NAME,
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
        for template in config.TEMPLATE_NAMES:
            for disk_interface in config.DISK_INTERFACES:
                for shareable in (True, False):
                    disk_args['alias'] = config.DISK_NAME_FORMAT % (
                        template,
                        disk_interface,
                        'shareable' if shareable else 'non-shareable')
                    disk_args['interface'] = disk_interface
                    disk_args['shareable'] = shareable
                    disk_args['format'] = 'raw' if shareable else 'cow'
                    disk_args['sparse'] = not shareable
                    results.append(executor.submit(disks.addDisk, **disk_args))
    return results


def create_vm_and_template(cobbler_image, template_name):
    """
    Creates and installs a VM from cobbler using the image specified.
    After creating the VM a template is created from the vm and the original
    VM is removed.
    parameters:
    cobbler_image - cobbler image used to provision VM
    template_name - name given to template
    """
    vm_name = "%sVM" % template_name
    logger.info("Creating VM %s and installing OS from cobbler image: %s" %
                (vm_name, cobbler_image))
    if not vms.createVm(config.positive,
                        vmName=vm_name,
                        vmDescription=vm_name,
                        cluster=config.DEFAULT_CLUSTER_NAME,
                        nic="nic1",
                        storageDomainName=config.STORAGE_DOMAIN_NAME,
                        size=10 * config.GB,
                        diskInterface=config.ENUMS['interface_virtio'],
                        memory=2 * config.GB,
                        cobblerAddress=config.COBBLER_ADDRESS,
                        cobblerUser=config.COBBLER_USER,
                        cobblerPasswd=config.COBBLER_PASSWORD,
                        image=cobbler_image,
                        installation=True,
                        useAgent=True,
                        os_type='rhel_6',
                        user='root',
                        password='qum5net',
                        network=config.MGMT_BRIDGE):
        raise exceptions.VMException("Could not create vm %s" % vm_name)
    logger.info("VM %s created and started successfully" % vm_name)

    vm_ip = vms.waitForIP(vm=vm_name)[1]['ip']

    logger.info("Setting network to be persistent")
    if not utils.setPersistentNetwork(host=vm_ip,
                                      password=config.VM_LINUX_PASSWORD):
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
                                    cluster=config.DEFAULT_CLUSTER_NAME):
        raise exceptions.TemplateException("Unable to create template %s" %
                                           template_name)

    logger.info("Template %s created successfully from vm - %s" %
                (template_name, vm_name))
    logger.info("Removing master vm - %s" % vm_name)
    if not vms.removeVm(config.positive, vm=vm_name):
        raise exceptions.VMException("Unable to remove vm - %s" % vm_name)


def start_installing_vms_for_test():
    """
    Creates a VM for each image defined in the config file and installs it
    After installation is complete creates a template for each vm
    returns a list of Futures with calls to installations and template creation
    """
    logger.info("Starting installation of all master VMs for templates")
    results = []

    with ThreadPoolExecutor(config.MAX_WORKERS) as executor:
        for image, template_name in zip(config.IMAGES, config.TEMPLATE_NAMES):
            results.append(executor.submit(create_vm_and_template,
                                           image,
                                           template_name))
    return results


def create_vm_from_template(template_name, class_name):
    """
    Clones a vm from the template of the given image name
    with class name as part of the VM name:
    """
    vm_name = config.VM_NAME_FORMAT % (template_name, class_name)
    logger.info("Cloning VM %s from template %s" % (vm_name, template_name))
    if not vms.createVm(positive=config.positive,
                        vmName=vm_name,
                        vmDescription=vm_name,
                        template=template_name,
                        start='false',
                        cluster=config.DEFAULT_CLUSTER_NAME,
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
        stopVm = vms.get_vm_state(vm_name) == config.ENUMS['vm_state_up']
        assert vms.removeVm(config.positive, vm_name, stopVM=str(stopVm))

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        for index in xrange(len(vm_names)):
            vm_name = vm_names[index]
            logger.info("Removing vm %s", vm_name)
            results.append(executor.submit(unattach_and_shutdown, vm_name))

    utils.raise_if_exception(results)
    logger.info("All vms removed successfully")
