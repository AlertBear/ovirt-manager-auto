from art.rhevm_api.tests_lib.low_level import storagedomains, vms, templates
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.utils import test_utils
from utilities.machine import LINUX, Machine
from utilities.rhevm_tools.base import Setup
from utilities.rhevm_tools.config import ConfigUtility


def setup_module():
    import config
    datacenters.build_setup(config=config.PARAMETERS,
                            storage=config.PARAMETERS,
                            storage_type=config.STORAGE_TYPE,
                            basename=config.BASENAME)

    storage_domain = storagedomains.getDCStorages(
        config.DATA_CENTER_NAME, False)[0].get_name()
    assert vms.createVm(
        True, config.VM_NAME, '', cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        diskInterface=config.DISK_INTERFACE, memory=config.GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE,
        os_type=config.OS_TYPE, user=config.VM_LINUX_USER,
        password=config.VM_LINUX_PASSWORD, installation=True,
        slim=True, cobblerAddress=config.COBBLER_ADDRESS,
        cobblerUser=config.COBBLER_USER,
        cobblerPasswd=config.COBBLER_PASSWORD, useAgent=True,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE)

    ip = vms.waitForIP(config.VM_NAME)
    assert ip[0]
    assert test_utils.setPersistentNetwork(ip[1]['ip'],
                                           config.VM_LINUX_PASSWORD)
    assert vms.stopVm(True, vm=config.VM_NAME)
    assert templates.createTemplate(True, vm=config.VM_NAME,
                                    name=config.TEMPLATE_NAME,
                                    cluster=config.CLUSTER_NAME)
    assert vms.removeVm(True, config.VM_NAME)

    machine = Machine(config.VDC, config.VDC_USER,
                      config.VDC_ROOT_PASSWORD).util(LINUX)
    setup = Setup(config.VDC, config.VDC_USER, config.VDC_ROOT_PASSWORD,
                  dbpassw=config.PGPASS, conf=config.VARS)
    config_util = ConfigUtility(setup)
    config_util(set=config.CUSTOM_PROPERTY, cver=config.VER)
    config_util(set=config.CUSTOM_PROPERTY_VNIC, cver=config.VER)
    assert test_utils.restartOvirtEngine(machine, 5, 25, 70)


def teardown_module():
    import config
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME,
                                   vdc=config.VDC,
                                   vdc_password=config.VDC_ROOT_PASSWORD)
