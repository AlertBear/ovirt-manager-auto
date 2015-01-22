import config
import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import getDCStorages
from art.rhevm_api.tests_lib.low_level.vms import createVm

logger = logging.getLogger(__name__)


def _create_vm(vm_name, disk_interface,
               sparse=True, volume_format=config.COW_DISK,
               vm_type=config.VM_TYPE_DESKTOP, installation=True):
    """ helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    logger.info("Creating VM %s" % vm_name)
    storage_domain_name = getDCStorages(
        config.DATA_CENTER_NAME, False)[0].name
    logger.info("storage domain: %s" % storage_domain_name)
    return createVm(
        True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
        nic=config.NIC_NAME[0], storageDomainName=storage_domain_name,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=config.GB,
        cpu_socket=config.CPU_SOCKET,
        cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
        user=config.VMS_LINUX_USER, password=config.VMS_LINUX_PW,
        type=vm_type, installation=installation, slim=True,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
        useAgent=config.USE_AGENT)
