"""
Storage helper functions
"""
import datetime
import logging
import os
import re
import shlex

from concurrent.futures.thread import ThreadPoolExecutor
from art.core_api.apis_utils import TimeoutingSampler
from art.core_api.apis_exceptions import APITimeout
from art.rhevm_api.utils import test_utils
import art.rhevm_api.resources.storage as storage_resources
from art.rhevm_api import resources
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
    vms as hl_vms,
    hosts as hl_hosts,
    datacenters as hl_dc,
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
from utilities.machine import Machine, LINUX
from art.test_handler import exceptions
from art.unittest_lib.common import testflow
import rhevmtests.helpers as rhevm_helpers
from rhevmtests.helpers import get_host_resource_by_name
from rhevmtests.storage import config
from utilities import errors


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
CP_CMD = 'cp %s %s'
ERROR_MSG = "Error: Boot device is protected"
TARGET_FILE = 'written_test_storage'
FILESYSTEM = 'ext4'
WAIT_DD_STARTS = 'ps -ef | grep "{0}" | grep -v grep'.format(DD_EXEC,)
INTERFACES = (config.VIRTIO, config.VIRTIO_SCSI)
if config.PPC_ARCH:
    INTERFACES = INTERFACES + (config.INTERFACE_SPAPR_VSCSI,)
FILE_SD_VOLUME_PATH_IN_FS = '/rhev/data-center/%s/%s/images/%s'
GET_FILE_SD_NUM_DISK_VOLUMES = 'ls %s | wc -l'
DISK_LV_COUNT = 'lvs -o lv_name,lv_tags | grep %s | wc -l'
LV_COUNT = 'lvs -o lv_name,lv_tags | wc -l'
ENUMS = config.ENUMS
LSBLK_CMD = 'lsblk -o NAME'
LV_CHANGE_CMD = 'lvchange -a {active} {vg_name}/{lv_name}'
PVSCAN_CACHE_CMD = 'pvscan --cache'
PVSCAN_CMD = 'pvscan'
PVS_SHOW_LUN_INFO = 'pvs 2>/dev/null | grep %s'
FIND_CMD = 'test -e %s'
ECHO_CMD = 'echo %s > %s'
CREATE_FILE_CMD = 'touch %s/%s'
CREATE_FILESYSTEM_CMD = 'mkfs.%s %s'
REGEX_DEVICE_NAME = '[sv]d[a-z]'
CREATE_DISK_LABEL_CMD = '/sbin/parted %s --script -- mklabel gpt'
CREATE_DISK_PARTITION_CMD = \
    '/sbin/parted %s --script -- mkpart primary ext4 0 100%%'
DEVICE_SIZE_CMD = 'lsblk -o NAME,SIZE | grep %s'
REGEX_UUID = (
    'UUID="(?P<uuid>[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}'
    '-?[89ab][a-f0-9]{3}-?[a-f0-9]{12})"'
)
NFS = config.STORAGE_TYPE_NFS
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP
GLUSTER = config.STORAGE_TYPE_GLUSTER
CEPH = config.STORAGE_TYPE_CEPH
POSIX = config.STORAGE_TYPE_POSIX
FILE_HANDLER_TIMEOUT = 15

BLOCK = 'block'
UNBLOCK = 'unblock'

HOST_NONOPERATIONAL = ENUMS["host_state_non_operational"]
HOST_NONRESPONSIVE = ENUMS["host_state_non_responsive"]
HOST_UP = ENUMS['search_host_state_up']


def prepare_disks_for_vm(
    vm_name, disks_to_prepare, read_only=False, interfaces=list()
):
    """
    Attach disks to VM

    Args:
        vm_name (str): The name of the VM which the disks should be attached to
        disks_to_prepare (list): Disks names
        read_only (bool): True if disks are attached in RO mode, False
            otherwise
        interfaces (list): Disk interfaces for attach

    Returns:
        bool: True for success, False otherwise

    Raises:
        AssertionError: In case of disk attachment failure
    """
    is_ro = 'Read Only' if read_only else 'Read Write'
    if not interfaces:
        interfaces = [config.VIRTIO] * len(disks_to_prepare)

    def attach_and_activate(disk, interface):
        logger.info(
            "Attaching disk %s as %s disk to vm %s", disk, is_ro, vm_name
        )
        assert ll_disks.attachDisk(
            positive=True, alias=disk, vm_name=vm_name, active=True,
            read_only=read_only, interface=interface
        ), "Failed to attach disk %s to vm %s" % (disk, vm_name)

    with ThreadPoolExecutor(max_workers=len(disks_to_prepare)) as executor:
        for disk, interface in zip(disks_to_prepare, interfaces):
            executor.submit(attach_and_activate, disk, interface)
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


def perform_dd_to_disk(
    vm_name, disk_alias, protect_boot_device=True, size=DEFAULT_DD_SIZE,
    write_to_file=False, vm_executor=None, file_name=None, key='name'
):
    """
    Args:
        vm_name (str): Name of the vm which which contains the disk on which
            the dd should be performed
        disk_alias (str): The alias of the disk on which the dd operations
            will occur
        protect_boot_device (bool): True if boot device should be protected and
            writing to this device ignored, False if boot device should be
            overwritten (use with caution!)
        size (int): Number of bytes to dd (Default size 20MB)
        write_to_file (bool): Determines whether a file should be written into
        the file system (True) or directly to the device (False)
        vm_executor (Host executor): VM executor
        file_name (str): The file name (including its full path) to write to
        key (str): key to look for disks by, it can be 'name' or 'id'

    Returns
        tuple: (bool, str) - Return code and output from 'dd' command execution

    Raises:
        AssertionError: In case of any failure


    """
    if not vm_executor:
        vm_executor = get_vm_executor(vm_name)
    if key == 'name':
        boot_disk = ll_vms.get_vm_bootable_disk(vm_name)
    else:
        boot_disk = ll_vms.get_vm_bootable_disk_id(vm_name)

    boot_device = get_logical_name_by_vdsm_client(vm_name, boot_disk, key=key)

    disk_logical_volume_name = get_logical_name_by_vdsm_client(
        vm_name, disk_alias, key=key
    )
    assert disk_logical_volume_name, (
        "Failed to get VM's %s virtual disk %s logical name" % (
            vm_name, disk_alias
        )
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
        if file_name:
            destination = file_name
        else:
            logger.info(
                "Creating label: %s",
                CREATE_DISK_LABEL_CMD % disk_logical_volume_name
            )
            rc, out, error = vm_executor.run_cmd(
                shlex.split(CREATE_DISK_LABEL_CMD % disk_logical_volume_name)
            )
            if rc:
                logger.error(
                    "Failed to create disk label with error %s" % error
                )
                return False, out
            logger.info("Output after creating disk label: %s", out)

            logger.info(
                "Creating partition %s",
                CREATE_DISK_PARTITION_CMD % disk_logical_volume_name
            )
            rc, out, error = vm_executor.run_cmd(
                shlex.split(
                    CREATE_DISK_PARTITION_CMD % disk_logical_volume_name
                )
            )
            if rc:
                logger.info(
                    "Failed to create disk partition with output %s and "
                    "error %s" % (out, error)
                )
                return False, out
            logger.info("Output after creating partition: %s", out)
            rc, mount_point = create_fs_on_disk(
                vm_name, disk_alias, vm_executor
            )
            assert rc, "Failed to create file system on disk %s" % (
                disk_logical_volume_name
            )
            destination = os.path.join(mount_point, TARGET_FILE)
            # IMPORTANT: This is exactly the size used by the ex4 partition
            # data, don't change
            size_mb -= 90
    else:
        destination = disk_logical_volume_name

    command = DD_COMMAND % (
        size_mb, "{0}".format(boot_device), destination,
    )
    logger.info("Performing command '%s'", command)

    rc, out, error = vm_executor.run_cmd(
        shlex.split(command), io_timeout=DD_TIMEOUT
    )
    if rc:
        logger.error(
            "Failed to perform DD to disk %s with error %s" % (
                disk_logical_volume_name, error
            )
        )
        out = error
    else:
        logger.info("Output for dd: %s", out)

    return not rc, out


def get_vm_ip(vm_name):
    """
    Get vm ip by name

    __author__ = "ratamir"
    :param vm_name: vm name
    :type vm_name: str
    :return: ip address of a vm, or raise EntityNotFound exception
    :rtype: str or EntityNotFound exception
    """
    return ll_vms.wait_for_vm_ip(vm_name)[1]['ip']


# flake8: noqa
def create_vm_or_clone(
    positive, vmName, vmDescription='', cluster=config.CLUSTER_NAME, **kwargs
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
    :param template_name: Name of the template
    :type template_name: str
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
    template_name = kwargs.pop('template_name', None)
    if template_name is None:
        template_name = rhevm_helpers.get_golden_template_name(cluster)

    # If the vm doesn't need installation don't waste time cloning the vm
    if installation:
        start = kwargs.get('start', 'false')
        storage_domains = ll_sd.get_storagedomain_names()

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
                'display_type', 'os_type', 'lease',
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
            kwargs['lease'] = kwargs.pop('lease', None)
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


def wait_for_dd_to_start(vm_name, timeout=20, interval=1, vm_executor=None):
    """
    Wait until dd starts execution in the VM

    Args:
        vm_name (str): The name of the VM
        timeout (int): The timeout in seconds to wait for dd to start
        interval (int): The polling interval in seconds
        vm_executor (Host resource): VM executor

    Returns:
        bool: True if 'dd' command was started, False otherwise
    """
    if not vm_executor:
        vm_executor = get_vm_executor(vm_name)
    command = shlex.split(WAIT_DD_STARTS)
    for rc, out, error in TimeoutingSampler(
            timeout, interval, vm_executor.run_cmd, shlex.split(command),
            io_timeout=DD_TIMEOUT
    ):
        if not rc:
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


def get_lv_count_for_block_disk(host_ip, password, disk_id=None):
    """
    Get amount of volumes for disk name

    Author = "ratamir"

    Arguments:
        host_ip (str): Host IP or FQDN
        password (str): Password for host
        disk_id (str): Disk ID. In case of None - all LVs

    Returns:
        Int: Number of logical volumes found for input disk in case execution
        succeeded, or 0 in case something goes wrong
    """
    if disk_id:
        cmd = DISK_LV_COUNT % disk_id
    else:
        cmd = LV_COUNT
    executor = rhevm_helpers.get_host_executor(
        ip=host_ip, password=password
    )
    rc, out, err = executor.run_cmd(shlex.split(PVSCAN_CACHE_CMD))
    if rc:
        logger.error("Failed to execute '%s' on %s: %s" % (
            PVSCAN_CACHE_CMD, host_ip, out
        ))
        return 0
    rc, out, err = executor.run_cmd(shlex.split(cmd))
    if rc:
        logger.error("Failed to execute '%s' on %s: %s" % (cmd, host_ip, out))
        return 0
    return int(out)


def get_amount_of_file_type_volumes(host_ip, sp_id, sd_id, image_id):
    """
    Get the number of volumes from a file based storage domain

    Args:
        host_ip (str): The host IP address
        sp_id (str): The storage pool id
        sd_id (str): The storage domain id
        image_id (str): The image id

    Returns:
        int: The number of volumes found on a file based storage domain's disk
    """
    # Build the path to the Disk's location on the file system
    volume_path = FILE_SD_VOLUME_PATH_IN_FS % (sp_id, sd_id, image_id)
    command = GET_FILE_SD_NUM_DISK_VOLUMES % volume_path
    executor = rhevm_helpers.get_host_executor(
        ip=host_ip, password=config.VDC_ROOT_PASSWORD
    )
    rc, output, err = executor.run_cmd(shlex.split(command))

    assert not rc, errors.CommandExecutionError("Output: %s" % output)
    # There are a total of 3 files/volume, the volume metadata (.meta),
    # the volume lease (.lease) and the volume content itself (no
    # extension)
    num_volumes = int(output)/3
    logger.debug(
        "The number of file type volumes found is '%s'",num_volumes
    )
    return num_volumes


def get_disks_volume_count(
    disk_ids, cluster_name=config.CLUSTER_NAME,
    datacenter_name=config.DATA_CENTER_NAME
):
    """
    Returns the logical volume count, with logic for block and file domain
    types

    Arguments:
        disk_ids (list): List of disk IDs
        cluster_name (str): Cluster from which to fetch a host which will
        run the disk query
        datacenter_name (str): Name of the data center where the disks' storage
        domains are located
    Returns:
        Int: Number of volumes retrieved across the disk names (file domain
        type) or the total logical volumes (block domain type)
    """
    host = ll_hosts.get_cluster_hosts(cluster_name=cluster_name)[0]
    host_ip = ll_hosts.get_host_ip(host)
    if not storage_resources.pvscan(host):
        raise exceptions.HostException(
            "Failed to execute '%s' on %s" % (PVSCAN_CMD, host_ip)
        )

    data_center_obj = ll_dc.get_data_center(datacenter_name)
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
                host_ip=host_ip, password=config.HOSTS_PW, disk_id=disk_id
            )
        else:
            sd_id = get_sduuid(disk_obj)
            logger.debug("The Storage Domain ID is: '%s'", sd_id)
            image_id = get_imguuid(disk_obj)
            logger.debug("The Image ID is: '%s'", image_id)
            volume_count += get_amount_of_file_type_volumes(
                host_ip=host_ip, sp_id=sp_id, sd_id=sd_id, image_id=image_id
            )
    return volume_count


def add_new_disk(
    sd_name, permutation, sd_type, shared=False, disk_size=config.DISK_SIZE
):
    """
    Add a new disk

    Args:
        sd_name (str): storage domain where a new disk will be added
        permutation (dict):
            alias - alias of the disk
            interface - VIRTIO, VIRTIO_SCSI or IDE
            sparse - True if thin, False if preallocated
            format - disk format 'cow' or 'raw'
        sd_type (str): type of the storage domain (nfs, iscsi, gluster)
        shared (bool): True if the disk should be shared
        disk_size (int): disk size (default is 1GB)

    Returns:
        tuple: The disk alias and permutation

    Raises:
        AssertionError: In case of add disk failure
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
        'sparse': permutation['sparse'],
        'alias': alias
    }
    logger.info("Adding new disk: %s", alias)

    assert ll_disks.addDisk(True, **new_disk_args)
    return alias, permutation['interface']


def start_creating_disks_for_test(
    shared=False, sd_name=None, disk_size=config.DISK_SIZE,
    interfaces=INTERFACES
):
    """
    Begins asynchronous creation of disks from all permutations of disk
    interfaces, formats and allocation policies

    Args:
        shared (bool): Specifies whether the disks should be shared
        sd_name (str): The name of the storage domain where the disks will be
            created
        disk_size (int): Disk size to be used with the disk creation
        interfaces (list): Interfaces to include in generating the disks
            permutations

    Returns:
        list: Dictionaries of disk aliases and interfaces
    """
    disks = []
    storage_domain_object = ll_sd.get_storage_domain_obj(sd_name)
    sd_type = storage_domain_object.get_storage().get_type()
    logger.info("Creating all disks required for test")
    disk_permutations = ll_disks.get_all_disk_permutation(
        block=sd_type in config.BLOCK_TYPES, shared=shared,
        interfaces=interfaces
    )
    # Provide a warning in the logs when the total number of disk
    # permutations is 0
    if len(disk_permutations) == 0:
        logger.warn("The number of disk permutations is 0")

    def add_disk(permutation):
        alias, interface = add_new_disk(
            sd_name=sd_name, permutation=permutation, shared=shared,
            sd_type=sd_type, disk_size=disk_size
        )
        disk = {
            'disk_name': alias,
            'disk_interface': interface
        }
        disks.append(disk)

    with ThreadPoolExecutor(max_workers=len(disk_permutations)) as executor:
        for disk in disk_permutations:
            executor.submit(add_disk, disk)
    return disks


def prepare_disks_with_fs_for_vm(storage_domain, vm_name, executor=None):
    """
    Prepare disks with filesystem for vm

    Args:
        storage_domain (str): Name of the storage domain to be used for disk
            creation
        vm_name (str): Name of the VM under which a disk with a file system
            will be created
        executor (Host resource): Host resource on which commands can
            be executed

    Returns:
        Tuple of 2 lists: disk_ids - list of new disk IDs,
        mount_points - list of mount points for each disk
    """
    disk_ids = list()
    mount_points = list()
    disk_names = []
    disk_interfaces = []
    logger.info('Creating disks for test')
    disks = start_creating_disks_for_test(sd_name=storage_domain)
    for disk in disks:
        disk_names.append(disk['disk_name'])
        disk_interfaces.append(disk['disk_interface'])
        disk_ids.append(ll_disks.get_disk_obj(disk['disk_name']).get_id())

    assert ll_disks.wait_for_disks_status(
        disk_names, timeout=CREATION_DISKS_TIMEOUT
    ), "Some disks are still locked"
    logger.info("Attaching and activating disks %s", disk_names)
    prepare_disks_for_vm(vm_name, disk_names, interfaces=disk_interfaces)

    if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
        ll_vms.startVm(
            True, vm_name, wait_for_status=config.VM_UP, wait_for_ip=True
        )
    if not executor:
        executor = get_vm_executor(vm_name)
    logger.info("Creating filesystems on disks %s", disks)

    with ThreadPoolExecutor(max_workers=len(disk_names)) as thread_executor:
        for disk_alias in disk_names:
            result = thread_executor.submit(
                create_fs_on_disk, vm_name=vm_name, disk_alias=disk_alias,
                executor=executor
            )
            ecode = result.result()[0]
            mount_point = result.result()[1]
            if not ecode:
                logger.error(
                    "Cannot create filesysem on disk %s:", disk_alias
                )
                mount_point = ''
            mount_points.append(mount_point)
    logger.info(
        "Mount points for new disks: %s", mount_points
    )
    return disk_ids, mount_points


def get_vm_boot_disk(vm_name):
    """
    Get the VM's boot device name (i.e.: /dev/vda)

    Args:
        vm_name (str): The name of the VM from which the boot disk name should
            be extracted

    Returns:
        str: The name of the boot device
    """
    vm_executor = get_vm_executor(vm_name)
    rc, out, err = vm_executor.run_cmd(shlex.split(config.BOOT_DEVICE_CMD))
    assert not rc, (
        "Failed to execute command %s on VM %s with error: %s, output: %s" % (
            config.BOOT_DEVICE_CMD, vm_name, err, out
        )
    )
    return re.search(REGEX_DEVICE_NAME, out).group()


def create_fs_on_disk(vm_name, disk_alias, executor=None):
    """
    Creates a filesystem on a disk and mounts it in the vm

    author = "cmestreg"

    Args:
        vm_name (str): Name of the vm to which disk will be attached
        disk_alias (str): The alias of the disk on which the file system will
            be created
        executor (Host executor): VM executor

    Returns:
        tuple: Operation status and the path to where the new created
            filesystem is mounted if success, error code and error message in
            case of failure
    """
    if ll_vms.get_vm_state(vm_name) == config.VM_DOWN:
        ll_vms.startVm(
            True, vm_name, wait_for_status=config.VM_UP,
            wait_for_ip=True
        )
    if not executor:
        executor = get_vm_executor(vm_name)

    logger.info(
        "Find disk logical name for disk with alias %s on vm %s",
        disk_alias, vm_name
    )
    disk_logical_volume_name = get_logical_name_by_vdsm_client(
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
    logger.info("Creating a File-system on first partition")
    mount_point = create_filesystem(
        vm_name=vm_name, device=disk_logical_volume_name, partition='1',
        fs=FILESYSTEM, executor=executor
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

    Args:
        host_name (str): The host to use for checking if a directory is empty
        dir_path (str): Full path of directory
        excluded_files (list): List of files to ignore

    Returns:
        bool: True if directory is empty, False otherwise
    """
    if dir_path is None:
        logger.error(
            "Error while checking if dir is empty, path is None"
        )
        return False
    executor = rhevm_helpers.get_host_executor(host_name, config.HOSTS_PW)
    command = ['ls', dir_path]
    rc, out, err = executor.run_cmd(command)
    assert not rc, (
        "Failed to execute command %s on host %s with error: %s and output: "
        "%s" % (command, host_name, err, out)
    )
    files = shlex.split(out)
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
        data_center=dc_name, version=comp_version
    ),  "addCluster %s with cpu %s and version %s to datacenter %s failed" % (
        cluster_name, config.CPU_NAME, comp_version, dc_name
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
            hl_sd.deactivate_domain(dc_name, sd_name, config.ENGINE)

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


def add_storage_domain(
    storage_domain, data_center, index, storage_type, **domain_kwargs
):
    """
    Add storage domain to given data-center

    Args:
        storage_domain (str): Name of the storage-domain
        data_center (str): Name of the data-center
        index (int): Index for the additional resources
        storage_type (str): Storage domain type
        domain_kwargs (dict): storage domain key args

    Raises:
        StorageDomainException : If Fails to add the storage-domain
    """
    spm = ll_hosts.get_spm_host(config.HOSTS)
    if storage_type == config.STORAGE_TYPE_ISCSI:
        status = hl_sd.add_iscsi_data_domain(
            spm,
            storage_domain,
            data_center,
            config.ISCSI_DOMAINS_KWARGS[index]['lun'],
            config.ISCSI_DOMAINS_KWARGS[index]['lun_address'],
            config.ISCSI_DOMAINS_KWARGS[index]['lun_target'],
            override_luns=True,
            **domain_kwargs
        )

    elif storage_type == config.STORAGE_TYPE_FCP:
        status = hl_sd.add_fcp_data_domain(
            spm,
            storage_domain,
            data_center,
            config.FC_DOMAINS_KWARGS[index]['fc_lun'],
            override_luns=True,
            **domain_kwargs
        )
    elif storage_type == config.STORAGE_TYPE_NFS:
        nfs_address = config.NFS_DOMAINS_KWARGS[index]['address']
        nfs_path = config.NFS_DOMAINS_KWARGS[index]['path']
        status = hl_sd.addNFSDomain(
            host=spm,
            storage=storage_domain,
            data_center=data_center,
            address=nfs_address,
            path=nfs_path,
            format=True,
            **domain_kwargs
        )
    elif storage_type == config.STORAGE_TYPE_GLUSTER:
        gluster_address = config.GLUSTER_DOMAINS_KWARGS[index]['address']
        gluster_path = config.GLUSTER_DOMAINS_KWARGS[index]['path']
        status = hl_sd.addGlusterDomain(
            host=spm,
            name=storage_domain,
            data_center=data_center,
            address=gluster_address,
            path=gluster_path,
            vfs_type=config.ENUMS['vfs_type_glusterfs'],
            **domain_kwargs
        )
    elif storage_type == config.STORAGE_TYPE_CEPH:
        posix_address = config.CEPH_DOMAINS_KWARGS[index]['address']
        posix_path = config.CEPH_DOMAINS_KWARGS[index]['path']
        status = hl_sd.addPosixfsDataDomain(
            host=spm,
            storage=storage_domain,
            data_center=data_center,
            address=posix_address,
            path=posix_path,
            vfs_type=config.STORAGE_TYPE_CEPH,
            mount_options=config.CEPH_MOUNT_OPTIONS,
            **domain_kwargs
        )
    assert status, "Creating %s storage domain '%s' failed" % (
        storage_type, storage_domain
    )
    ll_jobs.wait_for_jobs(
        [config.JOB_ADD_STORAGE_DOMAIN, config.JOB_ACTIVATE_DOMAIN]
    )
    ll_sd.wait_for_storage_domain_status(
        True, data_center, storage_domain,
        config.SD_ACTIVE
    )
    test_utils.wait_for_tasks(config.ENGINE, data_center)


def create_filesystem(
    vm_name, device, partition, fs='ext4', target_dir=None, executor=None
):
    """
    Create a filesystem on given path

    Args:
        vm_name (str): Name of the VM which the file system will be created on
            its disk
        device (str): Disk device name as seen by the guest where the file
            system will be created
        partition (str): The disk partition where the file system will be
            created
        fs (str): The file system type
        target_dir (str): The mount point location in the guest where the file
            system will be mounted on
        executor (Host executor): VM executor

    Returns:
        str: The target directory where the file system is mounted on

    Raises:
         AssertionError: In case of any failure
    """
    if not executor:
        executor = get_vm_executor(vm_name)
    device_name = device + partition
    create_fs_cmd = CREATE_FILESYSTEM_CMD % (fs, device_name)
    out = _run_cmd_on_remote_machine(vm_name, create_fs_cmd, executor)
    assert out, errors.CreateFileSystemError(create_fs_cmd, out)
    if not target_dir:
        current_date_time = (
            datetime.datetime.now().strftime("%d%H%M%S%f")
        )
        target_dir = '/mount-point_%s' % current_date_time[:10]
        out = _run_cmd_on_remote_machine(
            vm_name, config.MOUNT_POINT_CREATE_CMD % target_dir, executor
        )
        assert out, (
            errors.MountError("failed to create target directory %s" % out)
        )
    mount_fs_on_dir(
        vm_name=vm_name, device_name=device_name, target_dir=target_dir,
        fs_type=fs, executor=executor
    )
    return target_dir


def mount_fs_on_dir(vm_name, device_name, target_dir, fs_type, executor=None):
    """
    Mount a file system on a disk

    Args:
        vm_name (str): The name of the VM
        device_name (str): The name of the disk
        target_dir (str): The target directory to mount the file system to
        fs_type (str): The file system type
        executor (Host executor): VM executor

    Raises:
        AssertionError: In case of any failure
        MountError: In case of mount failure
    """
    if not executor:
        executor = get_vm_executor(vm_name)
    blkid_cmd = 'blkid %s' % device_name
    rc, out, error = executor.run_cmd(shlex.split(blkid_cmd))
    assert not rc, (
        "Failed to get the UUID of device {0} {1}".format(device_name, error)
    )
    uuid_regex = re.search(REGEX_UUID, out)
    assert uuid_regex, "Failed to find UUUID in output {0}".format(out)
    fstab_line = 'UUID="%s" %s %s defaults 0 0' % (
        uuid_regex.group('uuid'), target_dir, fs_type
    )
    insert_to_fstab = 'echo "{0}" >> {1}'.format(fstab_line, '/etc/fstab')
    out = _run_cmd_on_remote_machine(vm_name, insert_to_fstab, executor)
    assert out, errors.MountError("Failed to add mount point to fstab", out)
    mount_cmd = 'mount -a'
    out = _run_cmd_on_remote_machine(vm_name, mount_cmd, executor)
    assert out, errors.MountError("Failed to mount FS", out)


def get_hsm_host(
    job_description, step_description, wait_for_step_to_start=False
):
    """
    Get Host resource

    Arguments:
        job_description (str): Job description for retrieving is HSM host
        step_description (str): Step description for retrieving is HSM host
        wait_for_step_to_start (bool): True if wait for step to start, False
        otherwise

    Returns:
        Host resource
    """
    job_object = ll_jobs.get_job_object(job_description, config.JOB_STARTED)
    if wait_for_step_to_start:
        ll_jobs.wait_for_step_to_start(job_object, step_description)
    step_object = ll_jobs.step_by_description(job_object, step_description)
    if step_object:
        if step_object.get_execution_host():
            host_obj = ll_hosts.get_host_object(
                step_object.get_execution_host().get_id(), 'id'
            )
            return rhevm_helpers.get_host_resource(
                host_obj.get_address(), config.HOSTS_PW
            )
    return None


def kill_vdsm_on_hsm_executor(
    job_description, step_description, hsm_host=None
):
    """
    Kill 'vdsmd' service on HSM host

    Arguments:
        job_description (str): Job description for retrieving is HSM host
        step_description (str): Step description for retrieving is HSM host
        hsm_host (Host object): Host object of the HSM

    Returns:
        Bool: True if Kill vdsmd service succeeds, False otherwise
    """
    host = hsm_host or get_hsm_host(job_description, step_description)
    return ll_hosts.kill_vdsmd(host)


def get_volume_info(host, disk_object, dc_obj):
    """
    Get volume info from vdsm-client

    Author: ratamir

    Args:
        host (str): IP or fqdn of the host
        disk_object (Disk object): Disk object to return his volume info
        dc_obj (DataCenter object): Data center that the disk belongs to

    Returns:
        Volume info (dict), or None otherwise

        Example:
        {
            "status": "OK",
            "lease": {
                "owners": [],
                "version": null
            },
            "domain": "111",
            "capacity": "222",
            "voltype": "LEAF",
            "description": "",
            "parent": "00000000-0000-0000-0000-000000000000",
            "format": "RAW",
            "generation": 0,
            "image": "aaa",
            "uuid": "bbb",
            "disktype": "2",
            "legality": "LEGAL",
            "mtime": "0",
            "apparentsize": "222",
            "truesize": "222",
            "type": "PREALLOCATED",
            "children": [],
            "pool": "",
            "ctime": "123"
        }

    """
    host_resource = get_host_resource_by_name(host)

    vol_id = disk_object.get_image_id()
    sd_id = disk_object.get_storage_domains().get_storage_domain()[0].get_id()
    image_id = disk_object.get_id()
    sp_id = dc_obj.get_id()

    args = {
        "storagepoolID": sp_id,
        "storagedomainID": sd_id,
        "imageID": image_id,
        "volumeID": vol_id,
    }

    return host_resource.vds_client(cmd="Volume.getInfo", args=args)


def extend_storage_domain(storage_domain, extend_indices):
    """
    Extend storage domain

    Args:
        storage_domain (str): Storage domain name
        extend_indices (list): The indices of the LUNs for extension

    Returns:
        list: The extension LUNs

    Raises:
        AssertionError: In case of any failure
    """
    storage_type = ll_sd.get_storage_domain_storage_type(storage_domain)
    extend_kwargs = dict()
    extension_luns = list()
    spm = ll_hosts.get_spm_host(config.HOSTS)
    domain_size = ll_sd.get_total_size(storage_domain, config.DATA_CENTER_NAME)
    if storage_type == config.STORAGE_TYPE_ISCSI:
        extension_lun_addresses = list()
        extension_lun_targets = list()
        for index in range(len(extend_indices)):
            extension_luns.append(
                config.ISCSI_DOMAINS_KWARGS[extend_indices[index]]['lun']
            )
            extension_lun_addresses.append(
                config.ISCSI_DOMAINS_KWARGS[extend_indices[index]][
                    'lun_address'
                ]
            )
            extension_lun_targets.append(
                config.ISCSI_DOMAINS_KWARGS[extend_indices[index]][
                    'lun_target'
                ]
            )
        extend_kwargs = {
            'lun_list': extension_luns,
            'lun_addresses': extension_lun_addresses,
            'lun_targets': extension_lun_targets,
            'override_luns': True
        }

    elif storage_type == config.STORAGE_TYPE_FCP:
        for index in range(len(extend_indices)):
            extension_luns.append(
                config.FC_DOMAINS_KWARGS[extend_indices[index]]['fc_lun']
            )
            extend_kwargs = {'lun_list': extension_luns, 'override_luns': True}

    hl_sd.extend_storage_domain(
        storage_domain=storage_domain, type_=storage_type, host=spm,
        **extend_kwargs
    )
    assert ll_sd.wait_for_change_total_size(
        storage_domain=storage_domain, data_center=config.DATA_CENTER_NAME,
        original_size=domain_size
    ), "Storage domain %s size hasn't been changed" % storage_domain
    extended_sd_size = ll_sd.get_total_size(
        storagedomain=storage_domain, data_center=config.DATA_CENTER_NAME
    )
    logger.info(
        "Total size for domain %s after extend is %s",
        storage_domain, extended_sd_size
    )

    return extension_luns


def reduce_luns_from_storage_domain(
    storage_domain, luns, expected_size=None, wait=True, positive=True
):
    """
    Reduce LUNs from storage domain

    Args:
        storage_domain (str): The name of the storage domain to reduce the
            LUNs from
        luns (list): The LUNs IDs to remove from the storage domain
        expected_size (str): The domain size in bytes expected to be after
            LUNs reduction
        wait (bool): True for waiting for storage domain reduction, False
            otherwise
        positive (bool): True for expecting a success, False otherwise

    Raises:
        AssertionError: In case of any failure
    """
    size_before_reduce = ll_sd.get_total_size(
        storage_domain, config.DATA_CENTER_NAME
    )
    logger.info(
        "Reducing storage domain %s, size before reduce is %s",
        storage_domain, size_before_reduce
    )
    logger.info("Deactivating storage domain %s", storage_domain)
    assert hl_sd.deactivate_domain(
        dc_name=config.DATA_CENTER_NAME, sd_name=storage_domain,
        engine=config.ENGINE
    ), "Failed to deactivate storage domain %s" % storage_domain
    logger.info(
        "Reducing LUNs %s from storage domain %s" % (luns, storage_domain)
    )
    assert ll_sd.reduce_storage_domain_luns(
        storage_domain=storage_domain, logical_unit_ids=luns
    ), (
        "Failed to reduce LUNs %s from storage domain %s" % (
            luns, storage_domain
        )
    )
    if wait:
        ll_jobs.wait_for_jobs(job_descriptions=[config.JOB_REDUCE_DOMAIN])
        if positive:
            logger.info("Activating storage domain %s", storage_domain)
            assert ll_sd.activateStorageDomain(
                positive=True, datacenter=config.DATA_CENTER_NAME,
                storagedomain=storage_domain
            ), "Failed to activate storage domain %s" % storage_domain

            assert ll_sd.wait_for_change_total_size(
                storage_domain=storage_domain,
                data_center=config.DATA_CENTER_NAME,
                original_size=size_before_reduce
            ), "Storage domain %s size hasn't been changed" % storage_domain
            size_after_reduce = ll_sd.get_total_size(
                storagedomain=storage_domain,
                data_center=config.DATA_CENTER_NAME
            )
            assert size_after_reduce == expected_size, (
                "Storage domain %s size hasn't been decreased after LUN "
                "reduce" % storage_domain
            )

        else:
            failed_job_description = (
                'Reducing Storage Domain %s' % storage_domain
            )
            # Checking with the exact job description as there may be other
            # finished reduce LUNs jobs of previous tests
            job_exist, job = ll_jobs.check_recent_job(
                description=failed_job_description,
                job_status=config.ENUMS['job_failed']
            )
            assert job_exist and (
                re.match(failed_job_description, job.get_description())
            ), (
                "LUNs %s reduction from storage domain %s did not fail"
                "as should have been expected" % (luns, storage_domain)
            )


def create_test_file_and_check_existance(
    vm_name, mount_path, file_name, vm_executor=None
):
    """
    Create test file and check it exists

    Args:
        vm_name (str): name of the VM
        mount_path (str): mount path to create the file on
        vm_executor (Host resource): VM executor

    Raises:
        AssertionError: If created file does not exist
    """
    if not vm_executor:
        vm_executor = get_vm_executor(vm_name)
    full_path = os.path.join(mount_path, file_name)
    testflow.setup("Writing data to file %s", full_path)
    create_file_on_vm(
        vm_name, file_name, mount_path,
        vm_executor=vm_executor
    )
    logger.info("Checking full path %s", full_path)
    assert does_file_exist(
        vm_name, full_path, vm_executor=vm_executor
    ), "File %s does not exist" % full_path


def import_storage_domain(host, storage, index=0):
    """
    Import data storage domain

    Args:
        host (str): Host name to use for import
        storage (str): Storage type
        index (int): Index number of the unused resource

    Raises:
        AssertionError: In case of any failure
    """
    if storage == ISCSI:
        assert hl_sd.import_iscsi_storage_domain(
            host,
            lun_address=config.ISCSI_DOMAINS_KWARGS[index]['lun_address'],
            lun_target=config.ISCSI_DOMAINS_KWARGS[index]['lun_target']
        )

    elif storage == FCP:
        assert hl_sd.import_fcp_storage_domain(host)

    elif storage == NFS:
        assert ll_sd.importStorageDomain(
            True, config.TYPE_DATA, NFS,
            config.NFS_DOMAINS_KWARGS[index]['address'],
            config.NFS_DOMAINS_KWARGS[index]['path'], host
        ), """Failed to import storage domain from type %s with index %s
           using host %s""" % (storage, index, host)
    elif storage == GLUSTER:
        assert ll_sd.importStorageDomain(
            True, config.TYPE_DATA, GLUSTER,
            config.GLUSTER_DOMAINS_KWARGS[index]['address'],
            config.GLUSTER_DOMAINS_KWARGS[index]['path'], host,
            vfs_type=GLUSTER
        ), """Failed to import storage domain from type %s with index %s
           using host %s""" % (storage, index, host)
    elif storage == CEPH:
        assert ll_sd.importStorageDomain(
            True, config.TYPE_DATA, POSIX,
            config.CEPH_DOMAINS_KWARGS[index]['address'],
            config.CEPH_DOMAINS_KWARGS[index]['path'], host,
            vfs_type=CEPH, mount_options=config.CEPH_MOUNT_OPTIONS
        ), """Failed to import storage domain from type %s with index %s
           using host %s""" % (storage, index, host)

    else:
        assert False, "Storage type %s is not supported for import" % storage


def kill_vdsm_on_spm_host(dc_name):
    """
    Kill VDSM on spm host & wait for host & DC go back to up state

    Args:
        dc_name (str): Name of the data center

    Raises:
        AssertionError: If kill VDSM fails
    """
    spm_host_name = hl_dc.get_spm_host(
        positive=True, datacenter=dc_name
    ).get_name()
    testflow.step("Kill vdsmd on host %s", spm_host_name)
    host_resource = rhevm_helpers.get_host_resource_by_name(
        host_name=spm_host_name
    )
    assert ll_hosts.kill_vdsmd(host_resource), (
        "Failed to kill vdsmd on host %s" % spm_host_name
    )
    ll_hosts.wait_for_hosts_states(
        True, spm_host_name, states='connecting'
    )
    ll_dc.waitForDataCenterState(dc_name)
    ll_hosts.wait_for_hosts_states(True, spm_host_name)


def get_logical_name_by_vdsm_client(
    vm_name, disk, parse_logical_name=False, key='name'
):
    """
    Retrieves the logical name of a disk that is attached to a VM from
    vdsm-client

    Args:
        vm_name (str): Name of the VM which which contains the disk
        disk (str): The name/ID of the disk for which the logical volume
            name should be retrieved
        parse_logical_name (bool): Determines whether the logical name (e.g.
            /dev/vdb) is returned in the full format when False is
            set (this is the default), otherwise the logical name will be
            parsed to remove the /dev/ (e.g. /dev/vdb -> vdb) when True is set
        key (str): key to look for disks by, it can be 'name' or 'id'

    Returns:
        str: Disk logical name

    """
    logical_name = None
    host_ip = ll_hosts.get_host_ip(ll_vms.get_vm_host(vm_name))
    vm_id = ll_vms.get_vm_obj(vm_name).get_id()
    vds_resource = resources.VDS(
        ip=host_ip, root_password=config.ROOT_PASSWORD
    )
    if key == 'id':
        disk_id = disk
    else:
        disk_id = ll_disks.get_disk_obj(disk).get_id()

    vm_info = vds_resource.vds_client(
        cmd="VM.getStats", args={"vmID": vm_id}
    )
    if not vm_info:
        logger.error("VDS didn't return getStats for VM %s", vm_id)
        return ""
    vm_info = vm_info[0]
    vm_disks = vm_info.get('disks')
    for dev in vm_disks:
        if (vm_disks.get(dev).get("imageID") == disk_id) or (
            vm_disks.get(dev).get("lunGUID") == disk_id
        ):
            logical_name = dev
            break
    if not logical_name:
        logger.error(
            "Logical name for disk ID: '%s' wasn't found under VM %s",
            vm_id, vm_name
        )
        return ""
    if not parse_logical_name:
        logical_name = "/dev/" + logical_name
    return logical_name


def get_lun_storage_info(lun_id):
    """
    Get the LUN size (in bytes) and LUN free space (in bytes) by using
    the pvs command with an input LUN ID

    Args:
        lun_id (str): LUN ID to be queried

    Returns:
        tuple (int, int): The LUN size (in bytes), and the LUN free
            space (in bytes)
    """
    host = ll_hosts.get_spm_host(config.HOSTS)
    host_ip = ll_hosts.get_host_ip(host)
    executor = rhevm_helpers.get_host_executor(
        host_ip, config.VDC_ROOT_PASSWORD
    )
    # Execute 'pvscan' to display the latest volume info
    storage_resources.pvscan(host)
    logger.info("Executing command 'pvs | grep %s'", lun_id)
    status, output, err = executor.run_cmd(
        shlex.split(PVS_SHOW_LUN_INFO % lun_id)
    )
    if status:
        logger.info(
            "Status was False executing 'pvs | grep %s'. Err: %s",
            lun_id, err
        )
        return 0, 0

    # Format the output into the 6 expected display parameters (PV, VG,
    # Format, LV Attributes, Physical size and Physical free size)
    formatted_output = shlex.split(output)
    logger.info(
        "The output received when running pvs on LUN id %s is: %s"
        % (lun_id, formatted_output)
    )
    # The 2nd last displayed data output is needed - Physical size
    lun_size = formatted_output[-2]
    lun_size = lun_size.replace("g", "")
    lun_free_space = formatted_output[-1]
    lun_free_space = lun_free_space.replace("g", "")
    lun_size_bytes = float(lun_size) * config.GB
    logger.info("The LUN size in bytes is '%s'", str(lun_size_bytes))
    lun_free_bytes = float(lun_free_space) * config.GB
    logger.info("The LUN free space in bytes is '%s'", str(lun_free_bytes))

    return int(lun_size_bytes), int(lun_free_bytes)


def wait_for_disks_and_snapshots(vms_to_wait_for, live_operation=True):
    """
    Wait for given VMs snapshots and disks status to be 'OK'
    """
    for vm_name in vms_to_wait_for:
        if ll_vms.does_vm_exist(vm_name):
            try:
                disks = [d.get_id() for d in ll_vms.getVmDisks(vm_name)]
                ll_disks.wait_for_disks_status(disks, key='id')
                ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
            except APITimeout:
                assert False, (
                    "Snapshots failed to reach OK state on VM '%s'" % vm_name
                )
    if live_operation:
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
    else:
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])


def copy_file(
    vm_name, file_name, target_path, run_in_background=False, vm_executor=None
):
    """
    Copy given file to given target path

    Args:
        vm_name (str): The VM name
        file_name (str): The name of the file to copy
        target_path (str): The path to copy the file to
        run_in_background (bool): True for executing copy command in
            background (with '&'), False otherwise
        vm_executor (Host executor): VM executor

    Returns:
        bool: True for success, False otherwise
    """
    if not vm_executor:
        vm_executor = get_vm_executor(vm_name)
    background_flag = ' &' if run_in_background else None
    command = CP_CMD % (file_name, target_path) + background_flag
    return _run_cmd_on_remote_machine(vm_name, command, vm_executor)


def wait_for_background_process_state(
    vm_executor, process_state, timeout=config.SAMPLER_TIMEOUT,
    interval=config.SAMPLER_SLEEP/2
):
    """
    Wait for background process state

    Args:
        vm_executor (Host executor): VM executor
        process_state (str): The process state to wait for
        timeout (int): The maximum time to wait for the process to reach the
            given state
        interval (int): The time interval to poll the background processes

    Returns:
        bool: True in case the process had reached the desired state, False
            otherwise
    """
    for rc, out, error in TimeoutingSampler(
        timeout, interval, vm_executor.run_cmd, shlex.split(config.JOBS_CMD)
    ):
        if re.match(process_state, out):
            return True
    return False


def setupIptables(source, userName, password, dest, command, chain,
                  target, protocol='all', persistently=False, *ports):
    """Wrapper for resources.storage.set_ipatbles() method"""
    hostObj = Machine(source, userName, password).util('linux')
    return hostObj.setupIptables(dest, command, chain, target,
                                 protocol, persistently, *ports)


def blockOutgoingConnection(source, userName, password, dest, port=None):
    '''
    Description: Blocks outgoing connection to an address
    Parameters:
      * source - ip or fqdn of the source machine
      * userName - username on the source machine
      * password - password on the source machine
      * dest - ip or fqdn of the machine to which to prevent traffic
      * port - outgoing port we wanna block
    Return: True if commands succeeds, false otherwise.
    '''
    if port is None:
        return setupIptables(source, userName, password, dest, '--append',
                             'OUTPUT', 'DROP')
    else:
        return setupIptables(source, userName, password, dest, '--append',
                             'OUTPUT', 'DROP', 'all', False, port)


def unblockOutgoingConnection(source, userName, password, dest, port=None):
    '''
    Description: Unblocks outgoing connection to an address
    Parameters:
      * source - ip or fqdn of the source machine
      * userName - username on the source machine
      * password - password on the source machine
      * dest - ip or fqdn of the machine to which to remove traffic block
      * port - outgoing port we wanna unblock
    Return: True if commands succeeds, false otherwise.
    '''
    if port is None:
        return setupIptables(source, userName, password, dest, '--delete',
                             'OUTPUT', 'DROP')
    else:
        return setupIptables(source, userName, password, dest, '--delete',
                             'OUTPUT', 'DROP', 'all', False, port)


def flushIptables(host, userName, password, chain='', persistently=False):
    """Warpper for utilities.machine.flushIptables() method."""
    hostObj = Machine(host, userName, password).util('linux')
    return hostObj.flushIptables(chain, persistently)


def _perform_iptables_action_and_wait(action, source,
                                      s_user, s_pass,
                                      destination, wait_for_entity,
                                      expected_state):
    """
    Description: block/unblock connection from source to destination,
    and wait_for_entity state to change to expected_state
    Author: ratamir
    Parameters:
        * action - the action that need to preform
                   (i.e. BLOCK or UNBLOCK)
        * source - block/unblock connection from this ip or fdqn
        * s_user - user name for this machine
        * s_pass - password for this machine
        * destination - block/unblock connection to this ip or fqdn
        * wait_for_entity - the ip or fdqn of the machine that we wait
                            for its state
        * expected_state - the state that we wait for
    Return: True if operation executed successfully , False otherwise

    """
    logger.info("%sing connection from %s to %s", action, source,
                destination)

    function = blockOutgoingConnection if action == BLOCK else unblockOutgoingConnection
    success = function(source, s_user, s_pass, destination)
    if not success:
        logger.warning("%sing connection to %s failed. result was %s."
                       % (action, destination, success))
        return success

    logger.info("wait for state : '%s' ", expected_state)
    response = ll_hosts.wait_for_hosts_states(True, wait_for_entity,
                                           states=expected_state)

    host_state = ll_hosts.get_host_status(wait_for_entity)
    if not response:
        logger.warning("Host should be in status %s but it's in status %s"
                       % (expected_state, host_state))
    return response


def block_and_wait(source, s_user, s_pass, destination,
                   wait_for_entity,
                   expected_state=HOST_NONOPERATIONAL):
    """
    block connection from source to destination, and wait_for_entity
    state to change to expected_state
    Author: ratamir
    Parameters:
        * source - block connection from this ip or fdqn
        * s_user - user name for this machine
        * s_pass - password for this machine
        * destination - block connection to this ip or fqdn
        * wait_for_entity - the ip or fdqn of the machine that we wait
                            for its state
        * expected_state - the state that we wait for
    Return: True if operation executed successfully , False otherwise
    """
    return _perform_iptables_action_and_wait(
        BLOCK, source, s_user, s_pass,
        destination, wait_for_entity, expected_state)


def unblock_and_wait(source, s_user, s_pass, destination,
                     wait_for_entity,
                     expected_state=HOST_UP):
    """
    unblock connection from source to destination, and wait_for_entity
    state to change to expected_state
    Author: ratamir
    Parameters:
        * source - unblock connection from this ip or fdqn
        * s_user - user name for this machine
        * s_pass - password for this machine
        * destination - unblock connection to this ip or fqdn
        * wait_for_entity - the ip or fdqn of the machine that we wait
                            for its state
        * expected_state - the state that we wait for
    Return: True if operation executed successfully , False otherwise
    """

    return _perform_iptables_action_and_wait(
        UNBLOCK, source, s_user, s_pass,
        destination, wait_for_entity, expected_state)


def assign_storage_params(targets, keywords, *args):
    if len(args[0]) > 0:
        for i, target in enumerate(targets):
            for j, key in enumerate(keywords):
                target[key] = args[j][i]


def logout_iscsi_sessions(
    host_executor, mode='session', target_name=None, portal_ip=None
):
    """
    Log out all iSCSI sessions on the host

    Args:
        host_executor (Host executor): Host executor
        mode (str): The iscsiadm mode to perform the logout from (i.e, session,
            node)
        target_name (str): The name of the target to logout from
        portal_ip (str): The portal IP to disconnect from

    Raises:
        AssertionError: If there still are active iscsi sessions on the host
    """
    command = ["iscsiadm", "--mode", mode]
    if mode.lower() == "node" and target_name and portal_ip:
        command.extend(["--targetname", target_name, "--portal", portal_ip])
    command.append("-u")
    rc, out, err = host_executor.run_cmd(command)
    if rc:
        if "No matching sessions found" in err:
            rc = 0
    assert not rc, ("Failed to disconnect iSCSI sessions with error: %s" % err)


def get_iscsi_sessions(host_executor):
    """
    Get the host's iSCSI active sessions

    Args:
        host_executor (Host executor): Host executor

    Returns:
        list: iSCSI sessions, None in case no active sessions were found
    """
    rc, out, err = host_executor.run_cmd(config.ISCSIADM_SESSION)
    if rc:
        if "No active sessions" in err:
            return None
        else:
            logger.error(
                "Unable to execute command %s", config.ISCSIADM_SESSION
            )
            raise Exception(
                "Error executing %s command: %s"
                % (config.ISCSIADM_SESSION, err)
            )
    return out.rstrip().splitlines()
