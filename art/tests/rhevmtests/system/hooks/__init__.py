from art.rhevm_api.tests_lib.low_level import storagedomains, vms, templates
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.utils import test_utils
from utilities.machine import LINUX, Machine
from utilities.rhevm_tools.base import Setup
from utilities.rhevm_tools.config import ConfigUtility
from rhevmtests.system.hooks import config


def setup_module():
    datacenters.build_setup(config=config.PARAMETERS,
                            storage=config.PARAMETERS,
                            storage_type=config.STORAGE_TYPE,
                            basename=config.SYSTEM_BASE_NAME)

    storage_domain = storagedomains.getDCStorages(
        config.DC_NAME, False)[0].get_name()
    assert vms.createVm(
        True, config.VM_NAME[0], '', cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        diskInterface=config.DISK_INTERFACE, memory=config.GB,
        cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
        nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE,
        os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
        password=config.VMS_LINUX_PW, installation=True,
        slim=True, cobblerAddress=config.COBBLER_ADDRESS,
        cobblerUser=config.COBBLER_USER,
        cobblerPasswd=config.COBBLER_PASSWD, useAgent=True,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE)

    ip = vms.waitForIP(config.VM_NAME[0])
    assert ip[0]
    assert test_utils.setPersistentNetwork(ip[1]['ip'],
                                           config.VMS_LINUX_PW)
    assert vms.stopVm(True, vm=config.VM_NAME[0])
    assert templates.createTemplate(True, vm=config.VM_NAME[0],
                                    name=config.TEMPLATE_NAME,
                                    cluster=config.CLUSTER_NAME)
    assert vms.removeVm(True, config.VM_NAME[0])

    machine = Machine(config.VDC_HOST, config.VDC_USER,
                      config.VDC_ROOT_PASSWORD).util(LINUX)
    setup = Setup(config.VDC_HOST, config.VDC_USER, config.VDC_ROOT_PASSWORD,
                  dbpassw=config.PGPASS, conf=config.VARS)
    config_util = ConfigUtility(setup)
    config_util(set=config.CUSTOM_PROPERTY, cver=config.VER)
    config_util(set=config.CUSTOM_PROPERTY_VNIC, cver=config.VER)
    assert test_utils.restartOvirtEngine(machine, 5, 25, 70)


def teardown_module():
    storagedomains.cleanDataCenter(True, config.DC_NAME,
                                   vdc=config.VDC_HOST,
                                   vdc_password=config.VDC_ROOT_PASSWORD)
