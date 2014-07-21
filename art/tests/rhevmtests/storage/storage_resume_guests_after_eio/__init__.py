"""
Resume guests after storage domain error package
"""
import logging

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import vms
from rhevmtests.storage.storage_resume_guests_after_eio import config

LOGGER = logging.getLogger(__name__)


def setup_package():
    """
    Prepares environment
    """
    datacenters.build_setup(
        config.PARAMETERS, config.PARAMETERS, config.STORAGE_TYPE,
        config.TESTNAME)
    storage_domain_name = storagedomains.getDCStorages(
        config.DC_NAME, False)[0].name
    LOGGER.info("Creating VM %s" % config.VM_NAME[0])
    assert vms.createVm(
        True, config.VM_NAME[0], config.VM_NAME[0],
        cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain_name,
        size=config.DISK_SIZE * config.GB, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=True, volumeFormat=config.COW_DISK,
        diskInterface=config.INTERFACE_IDE, memory=config.GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
        os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW, type=config.VM_TYPE_DESKTOP,
        installation=True, slim=True, image=config.COBBLER_PROFILE,
        network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT)

    vms.wait_for_vm_states(config.VM_NAME[0])


def teardown_package():
    """
    Cleans the environment
    """
    assert storagedomains.cleanDataCenter(
        True, config.DC_NAME, vdc=config.VDC, vdc_password=config.VDC_PASSWORD)
