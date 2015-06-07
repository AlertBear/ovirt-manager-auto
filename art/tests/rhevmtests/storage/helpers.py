"""
Storage helper functions
"""
import logging
import os
import shlex
import art.rhevm_api.tests_lib.high_level.vms as high_vms
import art.rhevm_api.tests_lib.low_level.storagedomains as storagedomains
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.tests_lib.low_level.datacenters import get_data_center
from art.rhevm_api.tests_lib.low_level.hosts import (
    getSPMHost, getHostIP, get_cluster_hosts,
)
from art.rhevm_api.utils.resource_utils import runMachineCommand
from utilities.machine import Machine, LINUX
from utilities import errors
from art.rhevm_api.tests_lib.low_level.disks import (
    wait_for_disks_status, attachDisk, addDisk, get_all_disk_permutation,
    updateDisk, get_disk_obj,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    get_vm_disk_logical_name, stop_vms_safely, get_vm_snapshots,
    removeSnapshot, activateVmDisk, waitForIP, cloneVmFromTemplate,
    createVm, startVm, getVmDisks, run_cmd_on_vm,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.test_handler import exceptions
from rhevmtests.helpers import get_golden_template_name
from rhevmtests.storage import config

logger = logging.getLogger(__name__)

DISK_TIMEOUT = 250
REMOVE_SNAPSHOT_TIMEOUT = 25 * 60
DD_TIMEOUT = 60 * 6
DD_EXEC = '/bin/dd'
DD_COMMAND = '{0} bs=1M count=%d if=%s of=%s'.format(DD_EXEC)
DEFAULT_DD_SIZE = 20 * config.MB
ERROR_MSG = "Error: Boot device is protected"
TARGET_FILE = 'written_test_storage'
FILESYSTEM = 'ext4'
WAIT_DD_STARTS = 'ps -ef | grep "{0}" | grep -v grep'.format(
    DD_EXEC,
)
INTERFACES = (config.VIRTIO, config.VIRTIO_SCSI)
FILE_SD_VOLUME_PATH_IN_FS = '/rhev/data-center/%s/%s/images/%s'
GET_FILE_SD_NUM_DISK_VOLUMES = 'ls %s | wc -l'
LV_COUNT = 'lvs -o lv_name,lv_tags | grep %s | wc -l'
PVSCAN_CMD = 'pvscan --cache'
ENUMS = config.ENUMS
LSBLK_CMD = 'lsblk -o NAME'

disk_args = {
    # Fixed arguments
    'provisioned_size': config.DISK_SIZE,
    'wipe_after_delete': config.BLOCK_FS,
    'storagedomain': config.SD_NAMES_LIST[0],
    'bootable': False,
    'shareable': False,
    'active': True,
    'interface': config.VIRTIO,
    # Custom arguments - change for each disk
    'format': config.COW_DISK,
    'sparse': True,
    'alias': '',
    'description': '',
}


def create_vm(
        vm_name, disk_interface=config.VIRTIO, sparse=True,
        volume_format=config.COW_DISK, vm_type=config.VM_TYPE_DESKTOP,
        installation=True, storage_domain=None
):
    """
    helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    logger.info("Creating VM %s", vm_name)
    return create_vm_or_clone(
        True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
        nic=config.NIC_NAME[0], storageDomainName=storage_domain,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=config.GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
        os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW, type=vm_type, installation=installation,
        slim=True, image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
        useAgent=config.USE_AGENT
    )


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
        status = attachDisk(True, disk, vm_name, active=False,
                            read_only=read_only)
        if not status:
            raise exceptions.DiskException("Failed to attach disk %s to"
                                           " vm %s"
                                           % (disk, vm_name))

        logger.info("Plugging disk %s", disk)
        status = activateVmDisk(True, vm_name, disk)
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
    stop_vms_safely([vm_name])
    snapshots = get_vm_snapshots(vm_name)
    results = [
        removeSnapshot(True, vm_name, description, REMOVE_SNAPSHOT_TIMEOUT)
        for snapshot in snapshots
        if snapshot.get_description() == description
    ]
    wait_for_jobs(
        [ENUMS['job_remove_snapshot']], timeout=REMOVE_SNAPSHOT_TIMEOUT
    )
    assert False not in results


def create_disks_from_requested_permutations(
        domain_to_use, interfaces=INTERFACES, size=config.DISK_SIZE,
        shared=False, wait=True
):
    """
    Creates disks using a list of permutations

    __author__ = "glazarov"
    :param domain_to_use: the storage domain on which to create the disks
    :type domain_to_use: str
    :param interfaces: list of interfaces to use in generating the disks.
    Default is (VIRTIO, VIRTIO_SCSI)
    :type interfaces: list
    :param size: the disk size (in bytes) to create, uses config.DISK_SIZE as a
    default
    :type size: str
    :returns: list of the disk aliases
    :rtype: list
    """
    logger.info("Generating a list of disk permutations")
    # Get the storage domain object and its type, use this to ascertain
    # whether the storage is of a block or file type
    storage_domain_object = storagedomains.getStorageDomainObj(domain_to_use)
    storage_type = storage_domain_object.get_storage().get_type()
    is_block = storage_type in config.BLOCK_TYPES
    disk_permutations = get_all_disk_permutation(block=is_block,
                                                 shared=shared,
                                                 interfaces=interfaces)
    # Provide a warning in the logs when the total number of disk
    # permutations is 0
    if len(disk_permutations) == 0:
        logger.warn("The number of disk permutations is 0")
    # List of the disk aliases that will be returned when
    # the function completes execution
    disk_aliases = []

    logger.info("Create disks for all permutations generated previously")
    for disk_permutation in disk_permutations:
        disk_alias = "Disk_%s_%s_sparse-%s_alias" \
                     % (
                         disk_permutation['interface'],
                         disk_permutation['format'],
                         disk_permutation['sparse']
                     )
        disk_description = disk_alias.replace("_alias", "_description")
        disk_aliases.append(disk_alias)
        assert addDisk(
            True, alias=disk_alias, description=disk_description,
            size=size, interface=disk_permutation['interface'],
            sparse=disk_permutation['sparse'],
            format=disk_permutation['format'],
            storagedomain=domain_to_use, bootable=False, shareable=shared
        )
    if wait:
        assert wait_for_disks_status(disk_aliases)
    return disk_aliases


def perform_dd_to_disk(
    vm_name, disk_alias, protect_boot_device=True, size=DEFAULT_DD_SIZE,
    write_to_file=False,
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
    output = vm_machine.get_boot_storage_device()
    boot_disk = 'vda' if 'vd' in output else 'sda'

    disk_logical_volume_name = get_vm_disk_logical_name(vm_name, disk_alias)
    if not disk_logical_volume_name:
        # This function is used to test whether logical volume was found,
        # raises an exception if it wasn't found
        raise exceptions.DiskException(
            "Failed to get %s disk logical name" % disk_alias
        )

    logger.info("The logical volume name for the requested disk is: '%s'",
                disk_logical_volume_name)
    if protect_boot_device:
        if disk_logical_volume_name == boot_disk:
            logger.warn("perform_dd_to_disk function aborted since the "
                        "requested disk alias translates into the boot "
                        "device, this would overwrite the OS")

            return False, ERROR_MSG

    if write_to_file:
        dev = disk_logical_volume_name.split('/')[-1]
        dev_size = vm_machine.get_storage_device_size(dev)
        # Create a partition of the size of the disk but take into account the
        # usual offset for logical partitions, setting to 10 MB
        partition = vm_machine.createPartition(
            disk_logical_volume_name, dev_size * config.GB - config.MB * 10,
        )
        assert partition
        mount_point = vm_machine.createFileSystem(
            disk_logical_volume_name, partition, FILESYSTEM, '?',
        )
        assert mount_point
        destination = os.path.join(mount_point, TARGET_FILE)
    else:
        destination = disk_logical_volume_name

    command = DD_COMMAND % (
        size / config.MB, "/dev/{0}".format(boot_disk), destination,
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
    return waitForIP(vm_name)[1]['ip']


def create_vm_or_clone(positive, vmName, vmDescription,
                       cluster, **kwargs):
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
    :return: True if successful in creating the vm, False otherwise
    :rtype: bool
    """
    storage_domain = kwargs.get('storageDomainName')
    disk_interface = kwargs.get('diskInterface')
    vol_format = kwargs.get('volumeFormat', 'cow')
    vol_allocation_policy = kwargs.get('volumeType', 'true')
    installation = kwargs.get('installation', False)
    # If the vm doesn't need installation don't waste time cloning the vm
    if config.GOLDEN_ENV and installation:
        storage_domains = storagedomains.get_storagedomain_names()
        if config.GLANCE_DOMAIN in storage_domains:
            kwargs['cluster'] = cluster
            kwargs['vmName'] = vmName
            kwargs['vmDescription'] = vmDescription
            glance_image = config.GLANCE_IMAGE_COW
            if vol_allocation_policy == 'false':
                glance_image = config.GLANCE_IMAGE_RAW

            assert high_vms.create_vm_using_glance_image(
                config.GLANCE_DOMAIN, glance_image, **kwargs
            )
        else:
            logger.info("Cloning vm %s", vmName)
            template_name = get_golden_template_name(cluster)
            if not template_name:
                logger.error(
                    "Cannot find any templates to use under cluster %s",
                    cluster
                )
                return False

            # Clone a vm from a template with the correct parameters
            args_clone = {
                'positive': True,
                'name': vmName,
                'cluster': cluster,
                'template': template_name,
                'clone': True,  # Always clone
                # If sparse is not defined, use thin by default to speed up
                # the test run
                'vol_sparse': vol_allocation_policy,
                'vol_format': vol_format,
                'storagedomain': storage_domain,
                'virtio_scsi': True,
            }
            update_keys = [
                'vmDescription', 'type', 'placement_host',
                'placement_affinity', 'highly_available',
            ]
            update_args = dict((key, kwargs.get(key)) for key in update_keys)
            args_clone.update(update_args)
            assert cloneVmFromTemplate(**args_clone)
            # Because alias is not a unique property and a lot of test use it
            # as identifier, rename the vm's disk alias to be safe
            # Since cloning doesn't allow to specify disk interface, change it
            disks_obj = getVmDisks(vmName)
            for i in range(len(disks_obj)):
                updateDisk(
                    True, vmName=vmName, id=disks_obj[i].get_id(),
                    alias="{0}_Disk_{1}".format(vmName, i),
                    interface=disk_interface
                )
            # createVm always leaves the vm up when installation is True
        return startVm(positive, vmName, wait_for_status=config.VM_UP)
    else:
        return createVm(positive, vmName, vmDescription, cluster, **kwargs)


def host_to_use():
    """
    Extract the SPM host information.  This is then used to execute commands
    directly on the host

    __author__ = "glazarov"
    :returns: Machine object on which commands can be executed
    :rtype: Machine
    """
    host = getSPMHost(config.HOSTS)
    host = getHostIP(host)
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


def get_lv_count_for_block_disk(disk_alias, host_ip, user, password):
    """
    Get amount of volumes for disk name

    __author__ = "ratamir"
    :param disk_alias: Disk alias
    :type disk_alias:  str
    :param host_ip: Host IP or FQDN
    :type host_ip: str
    :param user: Username for host
    :type user: str
    :param password: Password for host
    :type password: str
    :return: Number of logical volumes found for input disk
    :rtype: int
    """
    disk_id = get_disk_obj(disk_alias).get_id()
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
        :param img_id: Image id of the disk
        :type img_id: str
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


def get_disks_volume_count(
        disk_names=None, cluster_name=config.CLUSTER_NAME
):
    """
    Returns the logical volume count, with logic for block and file domain
    types

    __author__ = "glazarov", "ratamir"
    :param disk_names: List of disk aliases (only used with file domain type to
    retrieve the individual number of volumes per disk)
    :type disk_names: list
    :param cluster_name: Cluster from which to fetch a host which will
    run the disk query
    :type cluster_name: str
    :returns: Number of volumes retrieved across the disk names (file domain
    type) or the total logical volumes (block domain type)
    :rtype: int
    """
    host = get_cluster_hosts(cluster_name=cluster_name)[0]
    host_ip = getHostIP(host)
    rc, out = runMachineCommand(
        True, ip=host_ip, user=config.HOSTS_USER, password=config.HOSTS_PW,
        cmd=PVSCAN_CMD
    )
    if not rc:
        raise exceptions.HostException(
            "Failed to execute '%s' on %s - %s" %
            (PVSCAN_CMD, host_ip, out['out'])
        )

    data_center_obj = get_data_center(config.DATA_CENTER_NAME)
    sp_id = get_spuuid(data_center_obj)
    logger.debug("The Storage Pool ID is: '%s'", sp_id)
    # Initialize the volume count before iterating through the disk aliases
    volume_count = 0
    for disk in disk_names:
        disk_obj = get_disk_obj(disk)
        storage_id = \
            disk_obj.get_storage_domains().get_storage_domain()[0].get_id()
        storage_domain_object = storagedomains.getStorageDomainObj(
            storagedomain=storage_id, key='id'
        )
        storage_type = storage_domain_object.get_storage().get_type()

        if storage_type in config.BLOCK_TYPES:
            volume_count += get_lv_count_for_block_disk(
                disk_alias=disk, host_ip=host_ip,
                user=config.HOSTS_USER, password=config.HOSTS_PW
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


def execute_lsblk_cmd(vm_name):
    """
    Retrieves a list of storage devices returned by running the lsblk command.
    Sample return is ['vda', 'vda1', 'vda2', 'vda3', 'vdb', 'sda', 'sdb']

    :param vm_name: Name of the VM on which to execute the lsblk command
    :type vm_name: str
    :return: List of the storage devices returned by the lsblk command
    :rtype: list
    """
    rc, out = run_cmd_on_vm(vm_name, LSBLK_CMD, config.VMS_LINUX_USER,
                            config.VMS_LINUX_PW)
    if not rc:
        raise exceptions.HostException("lsblk failed to execute on '%s'" %
                                       vm_name)
    # The values are retrieved as one long string
    output_values = out.values()[0]
    return shlex.split(output_values)
