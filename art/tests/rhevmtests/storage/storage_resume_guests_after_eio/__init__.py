"""
Resume guests after storage domain error package
"""
import logging

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import vms
from rhevmtests.storage.storage_resume_guests_after_eio import config
from rhevmtests.storage.helpers import create_vm_or_clone

LOGGER = logging.getLogger(__name__)


def setup_package():
    """
    Prepares environment
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config.PARAMETERS, config.PARAMETERS, config.STORAGE_TYPE,
            config.TESTNAME)

    for storage_type in config.STORAGE_SELECTOR:
        vm_name = "%s_%s" % (config.VM_NAME, storage_type)
        LOGGER.info("Creating VM %s" % vm_name)
        storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type)[0]
        assert create_vm_or_clone(
            True, vm_name, vm_name,
            cluster=config.CLUSTER_NAME,
            nic=config.NIC_NAME[0], storageDomainName=storage_domain,
            size=config.VM_DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
            volumeType=True, volumeFormat=config.COW_DISK,
            diskInterface=config.INTERFACE_VIRTIO, memory=config.GB,
            cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW, type=config.VM_TYPE_DESKTOP,
            installation=True, slim=True, image=config.COBBLER_PROFILE,
            network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT,
        )

        vms.waitForVMState(vm_name)


def teardown_package():
    """
    Cleans the environment
    """
    if not config.GOLDEN_ENV:
        assert datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )
    else:
        for storage_type in config.STORAGE_SELECTOR:
            vm_name = "%s_%s" % (config.VM_NAME, storage_type)
            vms.stop_vms_safely([vm_name])
        assert vms.removeVm(True, vm_name)
