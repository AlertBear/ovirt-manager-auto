"""
https://tcms.engineering.redhat.com/plan/9985

Test suite for restarting VDSM ovirt-engine during async tasks

Test suite is valid only for RHEV-M 3.3+
"""

import logging

from art.rhevm_api.utils import test_utils
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import templates

LOGGER = logging.getLogger(__name__)

GB = 1024 ** 3


def setup_module():
    """
    Creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    import config
    assert datacenters.build_setup(
        config.PARAMETERS, config.PARAMETERS, config.STORAGE_TYPE,
        basename=config.BASENAME)

    vm_name = config.VM_NAME
    storage_domain_name = storagedomains.getDCStorages(
        config.DATA_CENTER_NAME, False)[0].name
    LOGGER.info("Storage domain: %s" % storage_domain_name)
    LOGGER.info("Creating VM %s" % vm_name)
    assert vms.createVm(
        True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain_name,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=True, volumeFormat=config.ENUMS['format_cow'],
        diskInterface=config.INTERFACE_VIRTIO, memory=GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
        os_type=config.OS_TYPE, user=config.VM_LINUX_USER,
        password=config.VM_LINUX_PASSWORD, type=config.VM_TYPE_DESKTOP,
        installation=True, slim=True, cobblerAddress=config.COBBLER_ADDRESS,
        cobblerUser=config.COBBLER_USER,
        cobblerPasswd=config.COBBLER_PASSWORD,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
        useAgent=config.USE_AGENT)

    assert vms.stopVm(True, vm_name)
    disk_names = []
    for i in range(config.NUMBER_OF_DISKS - 1):
        disk_name = "%s_disk_%s" % (config.BASENAME, i)
        assert disks.addDisk(
            True, alias=disk_name, size=GB, storagedomain=storage_domain_name,
            format=config.ENUMS['format_cow'],
            interface=config.INTERFACE_VIRTIO)
        disk_names.append(disk_name)

    disks.waitForDisksState(",".join(disk_names))
    for disk_name in disk_names:
        assert disks.attachDisk(True, disk_name, vm_name)

    assert templates.createTemplate(
        True, vm=vm_name, name=config.TEMPLATE_NAME,
        cluster=config.CLUSTER_NAME)

    vms.startVm(True, vm_name, 'up')


def teardown_module():
    """
    Removes created datacenter, storages etc.
    """
    import config
    storagedomains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)
