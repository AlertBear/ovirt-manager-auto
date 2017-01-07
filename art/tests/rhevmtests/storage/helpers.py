"""
Storage helper functions
"""
import datetime
import logging
import os
import re
import shlex
import hashlib
import time

from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.utils import test_utils
import art.rhevm_api.resources.storage as storage_resources
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
    vms as hl_vms,
    hosts as hl_hosts,
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.test_handler import exceptions
from art.unittest_lib.common import testflow
import rhevmtests.helpers as rhevm_helpers
from rhevmtests.storage import config
from utilities import errors
from utilities.machine import Machine, LINUX


logger = logging.getLogger(__name__)

SPM_TIMEOUT = 300
TASK_TIMEOUT = 300
SPM_SLEEP = 5
FIND_SDS_TIMEOUT = 10
SD_STATUS_OK_TIMEOUT = 15
DISK_TIMEOUT = 250
CREATION_DISKS_TIMEOUT = 600
REMOVE_SNAPSHOT_TIMEOUT = 25 * 60
DD_TIMEOUT = 60 * 6
DD_EXEC = '/bin/dd'
DD_COMMAND = '{0} bs=1M count=%d if=%s of=%s status=none'.format(DD_EXEC)
DEFAULT_DD_SIZE = 20 * config.MB
ERROR_MSG = "Error: Boot device is protected"
TARGET_FILE = 'written_test_storage'
FILESYSTEM = 'ext4'
WAIT_DD_STARTS = 'ps -ef | grep "{0}" | grep -v grep'.format(DD_EXEC,)
INTERFACES = (config.VIRTIO, config.VIRTIO_SCSI)
if config.PPC_ARCH:
    INTERFACES = INTERFACES + (config.INTERFACE_SPAPR_VSCSI,)
FILE_SD_VOLUME_PATH_IN_FS = '/rhev/data-center/%s/%s/images/%s'
GET_FILE_SD_NUM_DISK_VOLUMES = 'ls %s | wc -l'
LV_COUNT = 'lvs -o lv_name,lv_tags | grep %s | wc -l'
ENUMS = config.ENUMS
LSBLK_CMD = 'lsblk -o NAME'
LV_CHANGE_CMD = 'lvchange -a {active} {vg_name}/{lv_name}'
PVSCAN_CACHE_CMD = 'pvscan --cache'
PVSCAN_CMD = 'pvscan'
FIND_CMD = 'find / %s'
ECHO_CMD = 'echo %s > %s'
CREATE_FILE_CMD = 'touch %s/%s'
CREATE_FILESYSTEM_CMD = 'mkfs.%s %s'
REGEX_DEVICE_NAME = '[sv]d[a-z]'
CREATE_DISK_LABEL_CMD = '/sbin/parted %s --script -- mklabel gpt'
CREATE_DISK_PARTITION_CMD = \
    '/sbin/parted %s --script -- mkpart primary ext4 0 100%%'
DEVICE_SIZE_CMD = 'lsblk -o NAME,SIZE | grep %s'
NFS = config.STORAGE_TYPE_NFS
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP
GLUSTER = config.STORAGE_TYPE_GLUSTER


def prepare_disks_for_vm(vm_name, disks_to_prepare, read_only=False):
    """
    Attach disks to vm

    :param vm_name: name of vm which disk should be attached to
    :type vm_name: str
    :param disks_to_prepare: list of disks' aliases
    :type disks_to_prepare: list
    :param read_only: Determines if the disks should be attached in RO mode
    :param read_only: bool
    :returns: True if successful, or raise DiskException otherwise
    :rtype bool
    """
    is_ro = 'Read Only' if read_only else 'Read Write'
    for disk in disks_to_prepare:
        logger.info("Attaching disk %s as %s disk to vm %s",
                    disk, is_ro, vm_name)
        status = ll_disks.attachDisk(
            True, disk, vm_name, active=False, read_only=read_only
        )
        if not status:
            raise exceptions.DiskException("Failed to attach disk %s to"
                                           " vm %s"
                                           % (disk, vm_name))

        logger.info("Plugging disk %s", disk)
        status = ll_vms.activateVmDisk(True, vm_name, disk)
        if not status:
            raise exceptions.DiskException("Failed to plug disk %s "
                                           "to vm %s"
                                           % (disk, vm_name))
    return True


def remove_all_vm_snapshots(vm_name, description):
    """
    Description: Removes all snapshots with given description from a given VM
    Author: ratamir
    Parameters:
    * vm_name - name of the vm that should be cleaned out of snapshots
    * description - snapshot description
    Raise: AssertionError if something went wrong
    """
    logger.info("Removing all '%s'", description)
    ll_vms.stop_vms_safely([vm_name])
    snapshots = ll_vms.get_vm_snapshots(vm_name)
    results = [
        ll_vms.removeSnapshot(
            True, vm_name, description, REMOVE_SNAPSHOT_TIMEOUT
        ) for snapshot in snapshots if
        snapshot.get_description() == description
    ]
    ll_jobs.wait_for_jobs(
        [ENUMS['job_remove_snapshot']], timeout=REMOVE_SNAPSHOT_TIMEOUT
    )
    assert False not in results


def create_disks_from_requested_permutations(
        domain_to_use, interfaces=INTERFACES, size=config.DISK_SIZE,
        shared=False, wait=True, test_name="Test"
):
    """
    Creates disks using a list of permutations

    __author__ = "glazarov"
    :param domain_to_use: The storage domain on which to create the disks
    :type domain_to_use: str
    :param interfaces: List of interfaces to use in generating the ll_disks.
    Default is (VIRTIO, VIRTIO_SCSI)
    :type interfaces: list
    :param size: The disk size (in bytes) to create, uses config.DISK_SIZE as a
    default
    :type size: int
    :param shared: Specifies whether the disks to be created are shareable
    :type shared: bool
    :param wait: Specifies whether to wait for each disk to be created
    :type wait: bool
    :param test_name: The test name to use as part of the disk naming
    :type test_name: str
    :returns: List of the disk aliases created
    :rtype: list
    """
    logger.info("Generating a list of disk permutations")
    # Get the storage domain object and its type, use this to ascertain
    # whether the storage is of a block or file type
    storage_domain_object = ll_sd.get_storage_domain_obj(domain_to_use)
    storage_type = storage_domain_object.get_storage().get_type()
    is_block = storage_type in config.BLOCK_TYPES
    disk_permutations = ll_disks.get_all_disk_permutation(
        block=is_block, shared=shared, interfaces=interfaces
    )
    # Provide a warning in the logs when the total number of disk
    # permutations is 0
    if len(disk_permutations) == 0:
        logger.warn("The number of disk permutations is 0")
    # List of the disk aliases that will be returned when
    # the function completes execution
    disk_aliases = []

    logger.info("Create disks for all permutations generated previously")
    for disk_permutation in disk_permutations:
        disk_alias = "%s_%s" % (
            test_name,
            create_unique_object_name(
                disk_permutation['interface'] + disk_permutation['format'],
                config.OBJECT_TYPE_DISK
            )
        )
        disk_description = disk_alias.replace("_alias", "_description")
        disk_aliases.append(disk_alias)
        assert ll_disks.addDisk(
            True, alias=disk_alias, description=disk_description,
            provisioned_size=size, interface=disk_permutation['interface'],
            sparse=disk_permutation['sparse'],
            format=disk_permutation['format'],
            storagedomain=domain_to_use, bootable=False, shareable=shared
        )
    if wait:
        assert ll_disks.wait_for_disks_status(disk_aliases)
    return disk_aliases


def perform_dd_to_disk(
    vm_name, disk_alias, protect_boot_device=True, size=DEFAULT_DD_SIZE,
    write_to_file=False
):
    """
    Function that performs dd command from the bootable device to the requested
    disk (by alias)
    **** Important note: Guest Agent must be installed in the OS for this
    function to work ****

    __author__ = "glazarov"
    :param vm_name: name of the vm which which contains the disk on which
    the dd should be performed
    :type: str
    :param disk_alias: The alias of the disk on which the dd operations will
    occur
    :type disk_alias: str
    :param protect_boot_device: True if boot device should be protected and
    writing to this device ignored, False if boot device should be
    overwritten (use with caution!)
    : type protect_boot_device: bool
    :param size: number of bytes to dd (Default size 20MB)
    :type size: int
    :param write_to_file: Determines whether a file should be written into the
    file system (True) or directly to the device (False)
    :param write_to_file: bool
    :returns: ecode and output
    :rtype: tuple
    """
    vm_ip = get_vm_ip(vm_name)
    vm_machine = Machine(
        host=vm_ip, user=config.VM_USER, password=config.VM_PASSWORD
    ).util(LINUX)
    vm_disks = ll_vms.getVmDisks(vm_name)
    boot_disk = [
        disk.get_id() for disk in vm_disks if ll_vms.is_bootable_disk(
            vm_name, disk.get_id()
        )
    ][0]
    boot_device = ll_vms.get_vm_disk_logical_name(
        vm_name, boot_disk, key='id'
    )
    disk_logical_volume_name = ll_vms.get_vm_disk_logical_name(
        vm_name, disk_alias
    )
    if not disk_logical_volume_name:
        # This function is used to test whether logical volume was found,
        # raises an exception if it wasn't found
        raise exceptions.DiskException(
            "Failed to get %s disk logical name" % disk_alias
        )
    logger.info(
        "The logical volume name for the requested disk is: '%s'",
        disk_logical_volume_name
    )
    if protect_boot_device:
        if disk_logical_volume_name == boot_device:
            logger.warn(
                "perform_dd_to_disk function aborted since the requested "
                "disk alias translates into the boot device, this would "
                "overwrite the OS"
            )

            return False, ERROR_MSG

    size_mb = size / config.MB

    if write_to_file:
        logger.info(
            "Creating label: %s",
            CREATE_DISK_LABEL_CMD % disk_logical_volume_name
        )
        rc, out = vm_machine.runCmd(
            (CREATE_DISK_LABEL_CMD % disk_logical_volume_name).split()
        )
        logger.info("Output after creating disk label: %s", out)
        if not rc:
            return rc, out
        logger.info(
            "Creating partition %s",
            CREATE_DISK_PARTITION_CMD % disk_logical_volume_name
        )
        rc, out = vm_machine.runCmd(
            (CREATE_DISK_PARTITION_CMD % disk_logical_volume_name).split()
        )
        logger.info("Output after creating partition: %s", out)
        if not rc:
            return rc, out
        # '1': create the fs as the first partition
        # '?': createFileSystem will return a random mount point
        mount_point = vm_machine.createFileSystem(
            disk_logical_volume_name, '1', FILESYSTEM, '?',
        )
        assert mount_point
        destination = os.path.join(mount_point, TARGET_FILE)
        # IMPORTANT: This is exactly the size used by the ex4 partition data,
        # don't change
        size_mb -= 90
    else:
        destination = disk_logical_volume_name

    command = DD_COMMAND % (
        size_mb, "{0}".format(boot_device), destination,
    )
    logger.info("Performing command '%s'", command)

    ecode, out = vm_machine.runCmd(shlex.split(command), timeout=DD_TIMEOUT)
    logger.info("Output for dd: %s", out)
    return ecode, out


def get_vm_ip(vm_name):
    """
    Get vm ip by name

    __author__ = "ratamir"
    :param vm_name: vm name
    :type vm_name: str
    :return: ip address of a vm, or raise EntityNotFound exception
    :rtype: str or EntityNotFound exception
    """
    return ll_vms.waitForIP(vm_name)[1]['ip']


def create_vm_or_clone(
    positive, vmName, vmDescription='', cluster=config.CLUSTER_NAME,
    **kwargs
):
    """
    Create a VM from scratch for non-GE environments, clones VM from
    cluster's templates for GE environments. This function greatly improves
    runtime on GE environments by re-using existing templates instead of
    creating VMs from scratch

    :param positive: Expected result
    :type positive: bool
    :param vmName: Name of the vm
    :type vmName: str
    :param vmDescription: Description of the vm
    :type vmDescription: str
    :param cluster: Name of the cluster
    :type cluster: str
    :param clone_from_template: True if a clone from template should be
    performed, False if a glance image should be used (and is valid,
    otherwise vm will be created from scratch)
    :type clone_from_template: bool
    :param deep_copy: (Used only when clone_from_template is True)
    True in case clone vm from template should be deep copy, False if clone
    should be thin copy (Default is thin copy - False)
    :type deep_copy: bool
    :return: True if successful in creating the vm, False otherwise
    :rtype: bool
    """
    storage_domain = kwargs.get('storageDomainName')
    disk_interface = kwargs.get('diskInterface', config.VIRTIO)
    vol_format = kwargs.get('volumeFormat', config.DISK_FORMAT_COW)
    vol_allocation_policy = kwargs.get('volumeType', 'true')
    installation = kwargs.get('installation', False)
    clone_from_template = kwargs.pop('clone_from_template', True)
    deep_copy = kwargs.pop('deep_copy', False)
    # If the vm doesn't need installation don't waste time cloning the vm
    if installation:
        start = kwargs.get('start', 'false')
        storage_domains = ll_sd.get_storagedomain_names()
        template_name = rhevm_helpers.get_golden_template_name(cluster)
        # Create VM from template
        if clone_from_template and template_name:
            logger.info("Cloning vm %s", vmName)
            # Clone a vm from a template with the correct parameters
            args_clone = config.clone_vm_args.copy()
            args_clone['name'] = vmName
            args_clone['cluster'] = cluster
            args_clone['template'] = template_name
            args_clone['clone'] = deep_copy
            args_clone['vol_sparse'] = vol_allocation_policy
            args_clone['vol_format'] = vol_format
            args_clone['storagedomain'] = storage_domain
            update_keys = [
                'vmDescription', 'type', 'placement_host',
                'placement_affinity', 'highly_available',
                'display_type', 'os_type',
            ]
            update_args = dict((key, kwargs.get(key)) for key in update_keys)
            args_clone.update(update_args)
            if not ll_vms.cloneVmFromTemplate(**args_clone):
                logger.error(
                    "Failed to clone vm %s from template %s",
                    vmName, template_name
                )
                return False
            # Because alias is not a unique property and a lot of test use it
            # as identifier, rename the vm's disk alias to be safe
            # Since cloning doesn't allow to specify disk interface, change it
            disks_obj = ll_vms.getVmDisks(vmName)
            for i in range(len(disks_obj)):
                # TODO: mark the boot disk as workaround for bug:
                # https://bugzilla.redhat.com/show_bug.cgi?id=1303320
                boot = i == 0
                ll_disks.updateDisk(
                    True, vmName=vmName, id=disks_obj[i].get_id(),
                    alias="{0}_Disk_{1}".format(vmName, i),
                    interface=disk_interface, bootable=boot
                )
        # Create VM using image imported from Glance
        elif not clone_from_template and (
            config.GLANCE_DOMAIN in storage_domains and (
                config.GOLDEN_GLANCE_IMAGE in ([
                    image.get_name() for image in
                    ll_sd.get_storage_domain_images(config.GLANCE_DOMAIN)
                ])
            )
        ):
            kwargs['cluster'] = cluster
            kwargs['vmName'] = vmName
            kwargs['vmDescription'] = vmDescription
            glance_image = config.GOLDEN_GLANCE_IMAGE
            if not hl_vms.create_vm_using_glance_image(
                config.GLANCE_DOMAIN, glance_image, **kwargs
            ):
                logger.error(
                    "Failed to create vm %s from glance image %s",
                    vmName, glance_image
                )
                return False
        else:
            return False
        if start == 'true':
            return ll_vms.startVm(
                positive, vmName, wait_for_status=config.VM_UP
            )
        return True
    else:
        return ll_vms.createVm(
            positive, vmName, vmDescription, cluster, **kwargs
        )


def create_unique_object_name(object_description, object_type):
        """
        Creates a unique object name by using the object_description
        and object_type, as well as the current date/time string.
        This can be used for any objects such as VMs, disks, clusters etc.

        __author__ = 'glazarov'
        :param object_description: The user provided object description,
        to be used in generating the unique object name
        :type object_description: str
        :param object_type: The type of object for which the unique name
        will be created. For example: vm, disk, sd
        :type object_type: str
        :return: Returns a unique name utilizing the object_description,
        the object_type and the current formatted date/time stamp
        :rtype: str
        """
        current_date_time = (
            datetime.datetime.now().strftime("%d%H%M%S%f")
        )
        return "{0}_{1}_{2}".format(
            object_type, object_description[:23], current_date_time[:10]
        )


def host_to_use():
    """
    Extract the SPM host information.  This is then used to execute commands
    directly on the host

    __author__ = "glazarov"
    :returns: Machine object on which commands can be executed
    :rtype: Machine
    """
    host = ll_hosts.getSPMHost(config.HOSTS)
    host = ll_hosts.getHostIP(host)
    return Machine(host=host, user=config.HOSTS_USER,
                   password=config.HOSTS_PW).util(LINUX)


def wait_for_dd_to_start(vm_name, timeout=20, interval=1):
    """
    Waits until dd starts execution in the machine
    """
    vm_ip = get_vm_ip(vm_name)
    vm_machine = Machine(
        host=vm_ip, user=config.VM_USER, password=config.VM_PASSWORD
    ).util(LINUX)

    cmd = shlex.split(WAIT_DD_STARTS)
    for code, out in TimeoutingSampler(
            timeout, interval, vm_machine.runCmd, cmd):
        if code:
            return True
    return False


def get_spuuid(dc_obj):
    """
    Returns the Storage Pool UUID of the provided Data center object

    __author__ = "glazarov"
    :param dc_obj: Data center object
    :type dc_obj: object
    :returns: Storage Pool UUID
    :rtype: str
    """
    return dc_obj.get_id()


def get_sduuid(disk_object):
    """
    Returns the Storage Domain UUID using the provided disk object.  Note
    that this assumes the disk only has one storage domain (i.e. in the case of
    a template with a disk copy or a vm created from such as template,
    the first instance will be returned which may either be the original
    disk or its copy)

    __author__ = "glazarov"
    :param disk_object: disk object from which the Storage Domain ID will be
    :type disk_object: Disk from disks collection
    :returns: Storage Domain UUID
    :rtype: str
    """
    return disk_object.get_storage_domains().get_storage_domain()[0].get_id()


def get_imguuid(disk_object):
    """
    Returns the imgUUID using the provided disk object

    __author__ = "glazarov"
    :param disk_object: disk object from which the Image ID will be retrieved
    :type disk_object: Disk from disks collection
    :returns: Image UUID
    :rtype: str
    """
    return disk_object.get_id()


def get_voluuid(disk_object):
    """
    Returns the volUUID using the provided disk object

    __author__ = "glazarov"
    :param disk_object: disk_object from which to retrieve the Volume ID
    :type disk_object: Disk from disks collection
    :returns: Volume UUID
    :rtype: str
    """
    return disk_object.get_image_id()


def get_lv_count_for_block_disk(disk_id, host_ip, user, password):
    """
    Get amount of volumes for disk name

    __author__ = "ratamir"
    :param disk_id: Disk ID
    :type disk_id:  str
    :param host_ip: Host IP or FQDN
    :type host_ip: str
    :param user: Username for host
    :type user: str
    :param password: Password for host
    :type password: str
    :return: Number of logical volumes found for input disk
    :rtype: int
    """
    cmd = LV_COUNT % disk_id
    rc, out = runMachineCommand(
        True, ip=host_ip, user=user, password=password, cmd=cmd
    )
    if not rc:
        raise exceptions.HostException(
            "Failed to execute '%s' on %s - %s" %
            (cmd, host_ip, out['out'])
        )
    return int(out['out'])


def get_amount_of_file_type_volumes(
        host_ip, user, password, sp_id, sd_id, image_id
):
        """
        Get the number of volumes from a file based storage domain

        __author__ = "glazarov"
        :param sp_id: Storage pool id
        :type sp_id: str
        :param sd_id: Storage domain id
        :type sd_id: str
        :param image_id: Image id of the disk
        :type image_id: str
        :returns: Number of volumes found on a file based storage domain's disk
        :rtype: int
        """
        # Build the path to the Disk's location on the file system
        volume_path = FILE_SD_VOLUME_PATH_IN_FS % (sp_id, sd_id, image_id)
        cmd = GET_FILE_SD_NUM_DISK_VOLUMES % volume_path
        status, output = runMachineCommand(
            True, ip=host_ip, user=user, password=password, cmd=cmd
        )
        if not status:
            raise errors.CommandExecutionError("Output: %s" % output)
        # There are a total of 3 files/volume, the volume metadata (.meta),
        # the volume lease (.lease) and the volume content itself (no
        # extension)
        num_volumes = int(output['out'])/3
        logger.debug("The number of file type volumes found is '%s'",
                     num_volumes)
        return num_volumes


def get_disks_volume_count(disk_ids, cluster_name=config.CLUSTER_NAME):
    """
    Returns the logical volume count, with logic for block and file domain
    types

    __author__ = "glazarov", "ratamir"
    :param disk_ids: List of disk IDs
    :type disk_ids: list
    :param cluster_name: Cluster from which to fetch a host which will
    run the disk query
    :type cluster_name: str
    :returns: Number of volumes retrieved across the disk names (file domain
    type) or the total logical volumes (block domain type)
    :rtype: int
    """
    host = ll_hosts.get_cluster_hosts(cluster_name=cluster_name)[0]
    host_ip = ll_hosts.getHostIP(host)
    if not storage_resources.pvscan(host):
        raise exceptions.HostException(
            "Failed to execute '%s' on %s" % (PVSCAN_CMD, host_ip)
        )

    data_center_obj = ll_dc.get_data_center(config.DATA_CENTER_NAME)
    sp_id = get_spuuid(data_center_obj)
    logger.debug("The Storage Pool ID is: '%s'", sp_id)
    # Initialize the volume count before iterating through the disk aliases
    storage_domains_map = {}
    volume_count = 0
    for disk_id in disk_ids:
        disk_obj = ll_disks.get_disk_obj(disk_id, attribute='id')
        storage_id = (
            disk_obj.get_storage_domains().get_storage_domain()[0].get_id()
        )
        if storage_id not in storage_domains_map.keys():
            storage_domain_object = ll_sd.get_storage_domain_obj(
                storage_domain=storage_id, key='id'
            )
            storage_domains_map[storage_id] = (
                storage_domain_object.get_storage().get_type()
            )

        storage_type = storage_domains_map[storage_id]
        if storage_type in config.BLOCK_TYPES:
            volume_count += get_lv_count_for_block_disk(
                disk_id=disk_id, host_ip=host_ip,
                user=config.HOSTS_USER, password=config.HOSTS_PW,
            )
        else:
            sd_id = get_sduuid(disk_obj)
            logger.debug("The Storage Domain ID is: '%s'", sd_id)
            image_id = get_imguuid(disk_obj)
            logger.debug("The Image ID is: '%s'", image_id)
            volume_count += get_amount_of_file_type_volumes(
                host_ip=host_ip, user=config.HOSTS_USER,
                password=config.HOSTS_PW, sp_id=sp_id, sd_id=sd_id,
                image_id=image_id
            )
    return volume_count


def add_new_disk(
        sd_name, permutation, sd_type, shared=False, disk_size=config.DISK_SIZE
):
    """
    Add a new disk

    :param sd_name: storage domain where a new disk will be added
    :type sd_name: str
    :param permutation:
            * alias - alias of the disk
            * interface - VIRTIO, VIRTIO_SCSI or IDE
            * sparse - True if thin, False if preallocated
            * format - disk format 'cow' or 'raw'
    :type permutation: dict
    :param sd_type: type of the storage domain (nfs, iscsi, gluster)
    :type sd_type: str
    :param shared: True if the disk should be shared
    :type shared: bool
    :param disk_size: disk size (default is 1GB)
    :type disk_size: int
    :returns: disk's alias
    :rtype: str
    """
    if 'alias' in permutation:
        alias = permutation['alias']
    else:
        alias = create_unique_object_name(
            permutation['interface'] + permutation['format'],
            config.OBJECT_TYPE_DISK
        )

    new_disk_args = {
        # Fixed arguments
        'provisioned_size': disk_size,
        'wipe_after_delete': sd_type in config.BLOCK_TYPES,
        'storagedomain': sd_name,
        'bootable': False,
        'shareable': shared,
        'active': True,
        # Custom arguments - change for each disk
        'format': permutation['format'],
        'interface': permutation['interface'],
        'sparse': permutation['sparse'],
        'alias': alias,
    }
    logger.info("Adding new disk: %s", alias)

    assert ll_disks.addDisk(True, **new_disk_args)
    return alias


def start_creating_disks_for_test(
        shared=False, sd_name=None, sd_type=None, disk_size=config.DISK_SIZE,
        interfaces=INTERFACES
):
    """
    Begins asynchronous creation of disks from all permutations of disk
    interfaces, formats and allocation policies

    :param shared: Specifies whether the disks should be shared
    :type shared: bool
    :param sd_name: name of the storage domain where the disks will be created
    :type sd_name: str
    :param sd_type: storage type of the domain where the disks will be created
    :type sd_type: str
    :param disk_size: Disk size to be used with the disk creation
    :type disk_size: int
    :param interfaces: List of interfaces to include in generating the disks
    permutations
    :type interfaces: list
    :returns: List of disk aliases created
    :rtype: list
    """
    disk_names = []
    logger.info("Creating all disks required for test")
    disk_permutations = ll_disks.get_all_disk_permutation(
        block=sd_type in config.BLOCK_TYPES, shared=shared,
        interfaces=interfaces
    )
    for permutation in disk_permutations:
        alias = add_new_disk(
            sd_name=sd_name, permutation=permutation, shared=shared,
            sd_type=sd_type, disk_size=disk_size
        )
        disk_names.append(alias)
    return disk_names


def prepare_disks_with_fs_for_vm(storage_domain, storage_type, vm_name):
    """
    Prepare disks with filesystem for vm

    :param storage_domain: Name of the storage domain to be used for
    disk creation
    :type storage_domain: str
    :param storage_type: Storage type to be used with the disk creation
    :type storage_type: str
    :param vm_name: Name of the VM under which a disk with a file system
    will be created
    :type vm_name: str
    :return: Tuple of 2 lists:
    (
    disk_ids - list of new disk IDs
    mount_points - list of mount points for each disk
    )
    :rtype: tuple
    """
    disk_ids = list()
    mount_points = list()
    logger.info('Creating disks for test')
    disk_names = start_creating_disks_for_test(
        sd_name=storage_domain, sd_type=storage_type
    )
    for disk_alias in disk_names:
        disk_ids.append(ll_disks.get_disk_obj(disk_alias).get_id())

    if not ll_disks.wait_for_disks_status(
        disk_names, timeout=CREATION_DISKS_TIMEOUT
    ):
        raise exceptions.DiskException("Some disks are still locked")
    prepare_disks_for_vm(vm_name, disk_names)

    if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
        ll_vms.startVm(True, vm_name, wait_for_status=config.VM_UP)
    executor = get_vm_executor(vm_name)
    # TODO: Workaround for bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1239297
    executor.run_cmd(shlex.split("udevadm trigger"))

    for disk_alias in disk_names:
        ecode, mount_point = create_fs_on_disk(vm_name, disk_alias, executor)
        if not ecode:
            logger.error("Cannot create filesysem on disk %s:", mount_point)
            mount_point = ''
        mount_points.append(mount_point)
    logger.info(
        "Mount points for new disks: %s", mount_points
    )
    return disk_ids, mount_points


def get_vm_boot_disk(vm_name):
    """
    Returns the vm's boot device name (i.e.: /dev/vda)

    __author__ = "cmestreg"
    :param vm_name: Name of the vm from which the boot disk name should be
    extracted
    :type vm_name: str
    :returns: Name of the boot device
    :rtype: str
    """
    vm_ip = get_vm_ip(vm_name)
    vm_machine = Machine(
        host=vm_ip, user=config.VM_USER, password=config.VM_PASSWORD
    ).util(LINUX)
    # TODO: Workaround for bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1239297
    vm_machine.runCmd(shlex.split("udevadm trigger"))
    output = vm_machine.get_boot_storage_device()
    return re.search(REGEX_DEVICE_NAME, output).group()


def create_fs_on_disk(vm_name, disk_alias, executor=None):
    """
    Creates a filesystem on a disk and mounts it in the vm

    __author__ = "cmestreg"
    :param vm_name: Name of the vm to which disk will be attached
    :type vm_name: str
    :param disk_alias: The alias of the disk on which the file system will be
    created
    :type disk_alias: str
    :returns: Operation status and the path to where the new created filesystem
    is mounted if success, error code and error message in case of failure
    :rtype: tuple
    """
    ll_vms.start_vms([vm_name], wait_for_ip=True)
    if not executor:
        executor = get_vm_executor(vm_name)
    # TODO: Workaround for bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1144860
    executor.run_cmd(shlex.split("udevadm trigger"))

    logger.info(
        "Find disk logical name for disk with alias %s on vm %s",
        disk_alias, vm_name
    )
    disk_logical_volume_name = ll_vms.get_vm_disk_logical_name(
        vm_name, disk_alias
    )
    if not disk_logical_volume_name:
        # This function is used to test whether logical volume was found,
        # raises an exception if it wasn't found
        message = "Failed to get %s disk logical name" % disk_alias
        logger.error(message)
        return False, message

    logger.info(
        "The logical volume name for the requested disk is: '%s'",
        disk_logical_volume_name
    )

    logger.info(
        "Creating label: %s", CREATE_DISK_LABEL_CMD % disk_logical_volume_name
    )
    rc, out, _ = executor.run_cmd(
        (CREATE_DISK_LABEL_CMD % disk_logical_volume_name).split()
    )
    logger.info("Output after creating disk label: %s", out)
    if rc:
        return rc, out
    logger.info(
        "Creating partition %s",
        CREATE_DISK_PARTITION_CMD % disk_logical_volume_name
    )
    rc, out, _ = executor.run_cmd(
        (CREATE_DISK_PARTITION_CMD % disk_logical_volume_name).split()
    )
    logger.info("Output after creating partition: %s", out)
    if rc:
        return rc, out
    # '1': create the fs as the first partition
    # '?': createFileSystem will return a random mount point
    mount_point = create_filesystem(
        vm_name, disk_logical_volume_name, '1', FILESYSTEM, '?',
    )
    return True, mount_point


def get_vm_executor(vm_name):
    """
    Takes the VM name and returns the VM resource on which commands can be
    executed

    :param vm_name:  The name of the VM for which Host resource should be
    created
    :type vm_name: str
    :return: Host resource on which commands can be executed
    :rtype: Host resource
    """
    logger.info("Get IP from VM %s", vm_name)
    vm_ip = get_vm_ip(vm_name)
    logger.info("Create VM instance with root user from vm with ip %s", vm_ip)
    return rhevm_helpers.get_host_executor(
        ip=vm_ip, password=config.VMS_LINUX_PW
    )


def _run_cmd_on_remote_machine(machine_name, command, vm_executor=None):
    """
    Executes Linux command on remote machine

    :param machine_name: The machine to use for executing the command
    :type machine_name: str
    :param command: The command to execute
    :type command: str
    :return: True if the command executed successfully, False otherwise
    """
    if not vm_executor:
        vm_executor = get_vm_executor(machine_name)
    rc, _, error = vm_executor.run_cmd(cmd=shlex.split(command))
    if rc:
        logger.error(
            "Failed to run command %s on %s, error: %s",
            command, machine_name, error
        )
        return False
    return True


def get_storage_devices(vm_name, filter='vd[a-z]'):
    """
    Retrieve list of storage devices in requested linux VM

    __author__ = "ratamir, glazarov"
    :param vm_name: The VM to use for retrieving the storage devices
    :type vm_name: str
    :param filter: The regular expression to use in retrieving the storage
    devices
    :type filter: str
    :returns: List of connected storage devices found on vm using specified
    filter (e.g. [vda, vdb, sda, sdb])
    :rtype: list
    """
    vm_executor = get_vm_executor(vm_name)

    command = 'ls /sys/block | egrep \"%s\"' % filter
    rc, output, error = vm_executor.run_cmd(cmd=shlex.split(command))
    if rc:
        logger.error(
            "Error while retrieving storage devices from VM '%s, output is "
            "'%s', error is '%s'", output, error
        )
        return False
    return output.split()


def get_storage_device_size(vm_name, dev_name):
    """
    Get device size in GB

    __author__ = "ratamir"

    Args:
        vm_name (str): VM name to use
        dev_name (str): Name of device (e.g. vdb)

    Returns::
        Storage device size in GB (integer) if operation succeeded,
        or raise CommandExecutionError
    """
    vm_executor = get_vm_executor(vm_name)
    command = shlex.split(DEVICE_SIZE_CMD % dev_name)
    rc, output, error = vm_executor.run_cmd(cmd=command)
    if rc:
        raise errors.CommandExecutionError("Output error: %s" % output)
    return int(output.split()[1][:-1])


def does_file_exist(vm_name, file_name, vm_executor=None):
    """
    Check if file_name refers to an existing file

    __author__ = "ratamir"
    :param vm_name: The VM to use in checking whether file exists
    :type vm_name: str
    :param file_name: File name to look for
    :type file_name: str
    :returns: True if file exists, False otherwise
    :rtype: bool
    """
    command = FIND_CMD % file_name
    return _run_cmd_on_remote_machine(
        vm_name, command, vm_executor=vm_executor
    )


def create_file_on_vm(
    vm_name, file_name, path, vm_executor=None
):
    """
    Creates a file on vm

    __author__ = "ratamir"
    :param vm_name: The VM to use in creating the file_name requested
    :type vm_name: str
    :param file_name: The file to create
    :type file_name: str
    :param path: The path that the file will be created under
    :type path: str
    :returns: True if succeeded in creating file requested, False otherwise
    :rtype: bool
    """
    command = CREATE_FILE_CMD % (path, file_name)
    return _run_cmd_on_remote_machine(vm_name, command, vm_executor)


def checksum_file(vm_name, file_name, vm_executor=None):
    """
    Return the file file_name checksum value

    __author__ = "ratamir"
    :param vm_name: The VM name that the file needs checksum located on
    :type vm_name: str
    :param file_name: The full path to file to checksum
    :type file_name: str
    :returns: Checksum value is succeeded, None otherwise
    :rtype: str or None
    """
    command = config.MD5SUM_CMD % file_name
    if not vm_executor:
        vm_executor = get_vm_executor(vm_name)
    return vm_executor.run_cmd(shlex.split(command))[1]


def write_content_to_file(
    vm_name, file_name, content=config.TEXT_CONTENT,
    vm_executor=None
):
    """
    Write content to file_name

    __author__ = "ratamir"
    :param vm_name: The VM to use in checking whether file exists
    :type vm_name: str
    :param file_name: File name to write content to
    :type file_name: str
    :returns: True if succeeded, False otherwise
    :rtype: bool
    """
    command = ECHO_CMD % (content, file_name)
    return _run_cmd_on_remote_machine(vm_name, command, vm_executor)


def verify_lun_not_in_use(lun_id):
    """
    Checks whether specified lun_id is in use

    :param lun_id: LUN ID
    :type lun_id: str
    :return: True if LUN is not in use, False otherwise
    :rtype: bool
    """
    luns = []
    for sd in ll_sd.get_storagedomain_objects():
        if sd.get_storage().get_type() in config.BLOCK_TYPES:
            luns += (
                sd.get_storage().get_volume_group()
                .get_logical_units().get_logical_unit()
                )
    lun_ids = [lun.get_id() for lun in luns]
    return lun_id not in lun_ids


def is_dir_empty(host_name, dir_path=None, excluded_files=[]):
    """
    Check if directory is empty

    :param host_name: The host to use for checking if a directory is empty
    :type host_name: str
    :param dir_path: Full path of directory
    :type dir_path: str
    :param excluded_files: List of files to ignore
    :type excluded_files: list
    :return: True if directory is empty, False otherwise
    :rtype: bool
    """
    if dir_path is None:
        logger.error(
            "Error while checking if dir is empty, path is None"
        )
        return False

    host_ip = ll_hosts.getHostIP(host_name)
    host_machine = rhevm_helpers.get_host_resource(host_ip, config.HOSTS_PW)
    rc, out, err = host_machine.run_command(['ls', dir_path])
    files = out.split()
    for file_in_dir in files:
        if file_in_dir not in excluded_files:
            logger.error("Directory %s is not empty", dir_path)
            return False
    return True


def get_vms_for_storage(storage_type):
    """
    Returns a list of vm names with disks on storage domains of storage_type

    :param storage_type: Type of storage (nfs, iscsi, glusterfs, fcp, ...)
    :type storage_type: str
    :return: List of vm names
    :rtype: list
    """
    if storage_type == ISCSI:
        return config.ISCSI_VMS
    elif storage_type == NFS:
        return config.NFS_VMS
    elif storage_type == GLUSTER:
        return config.GLUSTER_VMS
    elif storage_type == FCP:
        return config.FCP_VMS
    else:
        return None


def clean_export_domain(export_domain, datacenter):
    """
    Remove VMs/Templates from export domain

    Arguments:
        export_domain (str): The export storage domain name
        datacenter (str): Datacenter name

    Returns:
        bool: True if successful, False otherwise
    """
    export_domain_obj = ll_sd.util.find(export_domain)
    sd_vms = ll_sd.vmUtil.getElemFromLink(
        export_domain_obj, link_name='vms', attr='vm', get_href=False,
    )
    sd_templates = ll_sd.templUtil.getElemFromLink(
        export_domain_obj, link_name='templates', attr='template',
        get_href=False,
    )
    for template in [temp.get_name() for temp in sd_templates]:
        ll_templates.removeTemplateFromExportDomain(
            True, template, export_domain
        )
    for vm in [vm.get_name() for vm in sd_vms]:
        ll_vms.remove_vm_from_export_domain(
            True, vm, datacenter, export_domain
        )


def create_data_center(
    dc_name, cluster_name, host_name, comp_version=config.COMPATIBILITY_VERSION
):
    """
    Add data-center with one host to the environment

    Args:
        dc_name (str): Name of the Data-center
        cluster_name (str): Name of the Cluster
        host_name (str): Name of the host
        comp_version (str): Data-center compatibility version
        sd_name (str): Name of the storage-domain
    Raise:
        DataCenterException : If fails to add data-center
        ClusterException: If fails to add cluster
        HostException: If fails to perform host operation
    """
    testflow.step("Add data-center %s", dc_name)
    assert ll_dc.addDataCenter(
        True, name=dc_name, local=False, version=comp_version
    ), "Failed to create dc %s" % dc_name

    testflow.step("Add cluster %s", cluster_name)
    assert ll_clusters.addCluster(
        True, name=cluster_name, cpu=config.CPU_NAME,
        data_center=dc_name, version=config.COMPATIBILITY_VERSION
    ),  "addCluster %s with cpu %s and version %s to datacenter %s failed" % (
        cluster_name, config.CPU_NAME, config.COMPATIBILITY_VERSION, dc_name
    )
    testflow.step("Move host %s to cluster %s", host_name, cluster_name)
    assert hl_hosts.move_host_to_another_cluster(
        host=host_name, cluster=cluster_name, activate=True
    ), "Failed to move host %s to cluster %s" % (host_name, cluster_name)


def clean_dc(dc_name, cluster_name, dc_host, sd_name=None):
    """
    Clean data-center, remove storage-domain and attach the host back to GE
    data-center

    Args:
        dc_name (str): Name of the Data-center
        cluster_name (str): Name of the Cluster
        dc_host (str): Name of the host
        sd_name (str): Name of the storage-domain
        remove_param (dict): Parameters for domain remove
    Raise:
        DataCenterException : If fails to remove data-center
        StorageDomainException: If fails to remove storage-domain
        HostException: If fails to perform host operation
    """
    if sd_name:
        logger.info(
            "Checking if domain %s is active in dc %s", sd_name, dc_name
        )
        if ll_sd.is_storage_domain_active(dc_name, sd_name):
            testflow.step("Deactivate storage-domain %s ", sd_name)
            hl_sd.deactivate_domain(dc_name, sd_name)

    testflow.step("Remove data-center %s", dc_name)
    assert ll_dc.remove_datacenter(True, dc_name), (
        "Failed to remove dc %s" % dc_name
    )
    testflow.step("Move host %s to cluster %s", dc_host, cluster_name)
    assert hl_hosts.move_host_to_another_cluster(
        host=dc_host, cluster=config.CLUSTER_NAME, activate=True
    ), "Failed to move host %s to cluster %s" % (dc_host, cluster_name)
    assert ll_clusters.removeCluster(True, cluster_name), (
        "Failed to remove cluster %s" % cluster_name
    )


def add_storage_domain(storage_domain, data_center, index, storage_type):
    """
    Add storage domain to given data-center

    Args:
        storage_domain (str): Name of the storage-domain
        data_center (str): Name of the data-center
        index (int): Index for the additional resources
        storage_type (str): Storage domain type
    Raises:
        StorageDomainException : If Fails to add the storage-domain
    """
    spm = ll_hosts.getSPMHost(config.HOSTS)
    if storage_type == config.STORAGE_TYPE_ISCSI:
        status = hl_sd.addISCSIDataDomain(
            spm,
            storage_domain,
            data_center,
            config.UNUSED_LUNS[index],
            config.UNUSED_LUN_ADDRESSES[index],
            config.UNUSED_LUN_TARGETS[index],
            override_luns=True
        )

    elif storage_type == config.STORAGE_TYPE_FCP:
        status = hl_sd.addFCPDataDomain(
            spm,
            storage_domain,
            data_center,
            config.UNUSED_FC_LUNS[index],
            override_luns=True
        )
    elif storage_type == config.STORAGE_TYPE_NFS:
        nfs_address = config.UNUSED_DATA_DOMAIN_ADDRESSES[index]
        nfs_path = config.UNUSED_DATA_DOMAIN_PATHS[index]
        status = hl_sd.addNFSDomain(
            host=spm,
            storage=storage_domain,
            data_center=data_center,
            address=nfs_address,
            path=nfs_path,
            format=True
        )
    elif storage_type == config.STORAGE_TYPE_GLUSTER:
        gluster_address = (
            config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[index]
        )
        gluster_path = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[index]
        status = hl_sd.addGlusterDomain(
            host=spm,
            name=storage_domain,
            data_center=data_center,
            address=gluster_address,
            path=gluster_path,
            vfs_type=config.ENUMS['vfs_type_glusterfs']
        )
    elif storage_type == config.STORAGE_TYPE_CEPH:
            posix_address = (
                config.UNUSED_CEPHFS_DATA_DOMAIN_ADDRESSES[index]
            )
            posix_path = config.UNUSED_CEPHFS_DATA_DOMAIN_PATHS[index]
            status = hl_sd.addPosixfsDataDomain(
                host=spm,
                storage=storage_domain,
                data_center=data_center,
                address=posix_address,
                path=posix_path,
                vfs_type=config.STORAGE_TYPE_CEPH,
                mount_options=config.CEPH_MOUNT_OPTIONS
            )
    assert status, "Creating %s storage domain '%s' failed" % (
        storage_type, storage_domain
    )
    ll_jobs.wait_for_jobs(
        [config.JOB_ADD_STORAGE_DOMAIN, config.JOB_ACTIVATE_DOMAIN]
    )
    ll_sd.waitForStorageDomainStatus(
        True, data_center, storage_domain,
        config.SD_ACTIVE
    )
    test_utils.wait_for_tasks(
        config.VDC, config.VDC_PASSWORD, data_center
    )


def create_filesystem(vm_name, device, partition, fs='ext4', targetDir=None):
    """
    Creates a filesystem on given path

    Args:
        vm_name (str): Name of the VM which the file system will be created on
        its disk
        device (str): Disk device name as seen by the guest where the file
        system will be created
        partition (str): The disk partition where the file system will be
        created
        fs (str): The file system type
        targetDir (str): The mount point location in the guest where the file
        system will be mounted on
    Returns:
        The target directory where the file system is mounted on
    Raises:
         Exceptions
    """
    create_fs_cmd = CREATE_FILESYSTEM_CMD % (fs, device + partition)
    out = _run_cmd_on_remote_machine(vm_name, create_fs_cmd)
    assert out, (
        errors.CreateFileSystemError(create_fs_cmd, out)
    )
    if targetDir is not None:
        if targetDir == '?':
            sha1 = hashlib.sha1("%f" % time.time()).hexdigest()
            targetDir = '/mount-point%s' % sha1
        mount_point_create_cmd = 'mkdir ' + '-p ' + targetDir
        out = _run_cmd_on_remote_machine(vm_name, mount_point_create_cmd)
        assert out, (
            errors.MountError(
                "failed to create target directory" % out
            )
        )
        fstab_line = '%s %s %s defaults 0 0' % (
            device + partition, targetDir, fs
        )
        insert_to_fstab = (
            'echo "{0}" >> {1}'.format(fstab_line, '/etc/fstab')
        )
        out = _run_cmd_on_remote_machine(vm_name, insert_to_fstab)
        assert out, (
            errors.MountError(
                "failed to add mount point to fstab", out
            )
        )
        mount_cmd = 'mount -a'
        out = _run_cmd_on_remote_machine(vm_name, mount_cmd)
        assert out, (
            errors.MountError(
                "failed to mount FS", out
            )
        )
    return targetDir
