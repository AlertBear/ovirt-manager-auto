"""
Resume guests after storage domain error package
"""
import logging

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import vms

LOGGER = logging.getLogger(__name__)
GB = 1024 * 1024 * 1024


def setup_package():
    """
    Prepares environment
    """
    import config
    datacenters.build_setup(
        config.PARAMETERS, config.PARAMETERS, config.STORAGE_TYPE,
        config.TESTNAME)
    storage_domain_name = storagedomains.getDCStorages(
        config.DC_NAME, False)[0].name
    LOGGER.info("Creating VM %s" % config.VM_NAME)
    assert vms.createVm(
        True, config.VM_NAME, config.VM_NAME, cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain_name,
        size=config.DISK_SIZE * GB, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=True, volumeFormat=config.ENUMS['format_cow'],
        diskInterface=config.INTERFACE_IDE, memory=GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
        os_type=config.OS_TYPE, user=config.VM_LINUX_USER,
        password=config.VM_LINUX_PASSWORD, type=config.VM_TYPE_DESKTOP,
        installation=True, slim=True, cobblerAddress=config.COBBLER_ADDRESS,
        cobblerUser=config.COBBLER_USER, cobblerPasswd=config.COBBLER_PASSWORD,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
        useAgent=config.USE_AGENT)
    vms.wait_for_vm_states(config.VM_NAME)


def teardown_package():
    """
    Cleans the environment
    """
    import config
    assert storagedomains.cleanDataCenter(
        True, config.DC_NAME, vdc=config.VDC, vdc_password=config.VDC_PASSWORD)
