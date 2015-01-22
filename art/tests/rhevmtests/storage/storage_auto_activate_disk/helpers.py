"""
Collection of helper functions for auto activate disk tests
"""
import logging
import config

import art.test_handler.exceptions as exceptions

from art.rhevm_api.tests_lib.low_level import disks, vms

from rhevmtests.storage.helpers import create_vm_or_clone

logger = logging.getLogger(__name__)


def create_and_start_vm(vm_name, storage_domain):
    """
    Creates and starts a single vm
    """

    logger.info('Creating vm and installing OS on it')

    vmArgs = {'positive': True,
              'vmName': vm_name,
              'vmDescription': vm_name,
              'diskInterface': config.VIRTIO,
              'volumeFormat': config.DISK_FORMAT_COW,
              'cluster': config.CLUSTER_NAME,
              'storageDomainName': storage_domain,
              'installation': True,
              'size': config.DISK_SIZE,
              'nic': config.NIC_NAME[0],
              'image': config.COBBLER_PROFILE,
              'useAgent': True,
              'os_type': config.ENUMS['rhel6'],
              'user': config.VM_USER,
              'password': config.VM_PASSWORD,
              'network': config.MGMT_BRIDGE
              }

    if not create_vm_or_clone(**vmArgs):
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
        'active': should_be_active
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


# Remove when patchset 11542 will be merged - disks.get_all_disk_permutation()
def get_all_disk_permutation(block=True, shared=False):
    permutations = []
    for disk_format in [config.DISK_FORMAT_COW, config.DISK_FORMAT_RAW]:
            for interface in [config.VIRTIO, config.VIRTIO_SCSI]:
                for sparse in [True, False]:
                    if disk_format is config.DISK_FORMAT_RAW and sparse and \
                            block:
                        continue
                    if disk_format is config.DISK_FORMAT_COW and not sparse:
                        continue
                    if shared and disk_format == config.DISK_FORMAT_COW:
                        continue
                    permutation = {'disk_format': disk_format,
                                   'interface': interface,
                                   'sparse': sparse,
                                   }
                    permutations.append(permutation)
    return permutations
