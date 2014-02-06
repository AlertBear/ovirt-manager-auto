from art.rhevm_api.tests_lib.low_level import vms
import art.test_handler.exceptions as exceptions
from art.rhevm_api.tests_lib.low_level.storagedomains \
    import findMasterStorageDomain
from art.rhevm_api.tests_lib.low_level import disks
import logging
import config

logger = logging.getLogger(__name__)


def create_and_start_vm(vm_name):
    """
    Creates and starts a single vm
    """
    rc, masterSD = findMasterStorageDomain(True, config.DATA_CENTER_NAME)
    assert rc
    masterSD = masterSD['masterDomain']

    logger.info('Creating vm and installing OS on it')

    vmArgs = {'positive': True,
              'vmName': vm_name,
              'vmDescription': vm_name,
              'diskInterface': config.ENUMS['interface_virtio'],
              'volumeFormat': config.ENUMS['format_cow'],
              'cluster': config.CLUSTER_NAME,
              'storageDomainName': masterSD,
              'installation': True,
              'size': config.DISK_SIZE,
              'nic': 'nic1',
              'cobblerAddress': config.COBBLER_ADDRESS,
              'cobblerUser': config.COBBLER_USER,
              'cobblerPasswd': config.COBBLER_PASSWD,
              'image': config.COBBLER_PROFILE,
              'useAgent': True,
              'os_type': config.ENUMS['rhel6'],
              'user': config.VM_USER,
              'password': config.VM_PASSWORD,
              'network': config.MGMT_BRIDGE
              }

    if not vms.createVm(**vmArgs):
        raise exceptions.VMException('Unable to create vm %s for test'
                                     % vm_name)


def attach_new_disk(vm_name, should_be_active=True, **permutation):
    """
    Try to add a new disk. It expects the disk to be at should_be_active.
    """
    disk_alias = "%s_%s_%s_%s_disk" % (
        vm_name,
        permutation['interface'],
        permutation['disk_format'],
        permutation['sparse'])
    disk_args = {
        'interface': permutation['interface'],
        'sparse': permutation['sparse'],
        'alias': disk_alias,
        'format': permutation['disk_format'],
        'active': True
    }

    assert vms.addDisk(True, vm_name, config.DISK_SIZE, **disk_args)

    disk_obj = disks.getVmDisk(vm_name, disk_args['alias'])
    logger.info("disk_obj: %s", disk_obj)
    logger.info("active: %s", disk_obj.get_active())
    msg = "Status is %s, expected status is %s" % (disk_obj.get_active(),
                                                   should_be_active)
    logger.info(msg)
    # if it's the expected status - then we are good
    # if the expected status is False, but the real status is true,
    # then we are also good (vm was already down for example)
    if disk_obj.get_active() == should_be_active:
        logger.info("Status equals expected status")
        return True
    if disk_obj.get_active() and not should_be_active:
        logger.info("Status is True, should be active is False")
        return True

    logger.info("Status is False, should be active is True")
    return False


def get_all_disk_permutation():
    permutations = []
    for disk_format in [config.DISK_FORMAT_COW, config.DISK_FORMAT_RAW]:
            for interface in [config.VIRTIO, config.VIRTIO_SCSI]:
                for sparse in [True, False]:
                    if disk_format is config.DISK_FORMAT_RAW and sparse:
                        continue
                    if disk_format is config.DISK_FORMAT_COW and not sparse:
                        continue
                    permutation = {'disk_format': disk_format,
                                   'interface': interface,
                                   'sparse': sparse,
                                   }
                    permutations.append(permutation)
    return permutations
