"""
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_Manage_Storage_Connections

Test suite for restarting VDSM ovirt-engine during async tasks

Test suite is valid only for RHEV-M 3.3+
"""

import logging

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import templates
from rhevmtests.storage.storage_async_tasks import config

logger = logging.getLogger(__name__)


def setup_package():
    """
    Creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if config.GOLDEN_ENV:
        return
    assert datacenters.build_setup(
        config.PARAMETERS, config.PARAMETERS, config.STORAGE_TYPE,
        basename=config.TESTNAME)

    vm_name = config.VM_NAME[0]
    storage_domain_name = storagedomains.getDCStorages(
        config.DATA_CENTER_NAME, False)[0].name
    logger.info("Storage domain: %s" % storage_domain_name)
    logger.info("Creating VM %s" % vm_name)
    assert vms.createVm(
        True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
        nic=config.NIC_NAME[0], storageDomainName=storage_domain_name,
        provisioned_size=config.VM_DISK_SIZE,
        diskType=config.DISK_TYPE_SYSTEM,
        volumeType=True, volumeFormat=config.COW_DISK,
        diskInterface=config.INTERFACE_VIRTIO, memory=config.GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
        os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW, type=config.VM_TYPE_DESKTOP,
        installation=True, slim=True, image=config.COBBLER_PROFILE,
        network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT)

    assert vms.stopVm(True, vm_name)
    disk_names = []
    for i in range(config.NUMBER_OF_DISKS - 1):
        disk_name = "%s_disk_%s" % (config.TESTNAME, i)
        assert disks.addDisk(
            True, alias=disk_name, provisioned_size=config.GB,
            storagedomain=storage_domain_name,
            format=config.ENUMS['format_cow'],
            interface=config.INTERFACE_VIRTIO)
        disk_names.append(disk_name)

    disks.wait_for_disks_status(disk_names)
    for disk_name in disk_names:
        assert disks.attachDisk(True, disk_name, vm_name)

    assert templates.createTemplate(
        True, vm=vm_name, name=config.TEMPLATE_NAME,
        cluster=config.CLUSTER_NAME)

    vms.startVm(True, vm_name, 'up')


def teardown_package():
    """
    Removes created datacenter, storages etc.
    """
    if config.GOLDEN_ENV:
        return
    datacenters.clean_datacenter(
        True,
        config.DATA_CENTER_NAME,
        vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD
    )
