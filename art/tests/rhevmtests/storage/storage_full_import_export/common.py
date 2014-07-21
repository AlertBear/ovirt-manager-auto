import config
import logging
from art.rhevm_api.tests_lib.low_level import vms, storagedomains

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS


def _create_vm(vm_name, disk_interface=config.VIRTIO_SCSI,
               sparse=True, volume_format=ENUMS['format_cow'],
               vm_type=config.VM_TYPE_DESKTOP):
    """
    helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    storage_domain = storagedomains.findMasterStorageDomain(
        True, config.DATA_CENTER_NAME)[1]['masterDomain']
    logger.info("Creating VM %s at SD %s" % (vm_name, storage_domain))
    return vms.createVm(
        True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=config.GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
        os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW, type=vm_type, installation=True,
        slim=True, image=config.COBBLER_PROFILE, useAgent=config.USE_AGENT)
