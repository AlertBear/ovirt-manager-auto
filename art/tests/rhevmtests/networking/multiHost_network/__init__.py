"""
MultiHost networking feature test
"""

import logging
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.low_level.storagedomains import\
    cleanDataCenter
from art.rhevm_api.tests_lib.low_level.vms import addVm
from art.test_handler.exceptions import NetworkException, VMException
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup

logger = logging.getLogger("MultiHost")

#################################################


def setup_package():
    """
    Prepare environment
    """
    if not prepareSetup(hosts=','.join(config.HOSTS), cpuName=config.CPU_NAME,
                        username=config.HOSTS_USER,
                        password=config.HOSTS_PW,
                        datacenter=config.DC_NAME[0],
                        storageDomainName=config.STORAGE_NAME[0],
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME[0],
                        lun_address=config.LUN_ADDRESS[0],
                        lun_target=config.LUN_TARGET[0],
                        luns=config.LUN[0], version=config.COMP_VERSION,
                        vm_password=config.VMS_LINUX_PW,
                        vmName=config.VM_NAME[0],
                        template_name=config.TEMPLATE_NAME[0],
                        placement_host=config.HOSTS[0],
                        mgmt_network=config.MGMT_BRIDGE,
                        vm_network=config.MGMT_BRIDGE):
        raise NetworkException("Cannot create setup")

    if not addVm(True, name=config.VM_NAME[1], cluster=config.CLUSTER_NAME[0],
                 template=config.TEMPLATE_NAME[0],
                 display_type=config.DISPLAY_TYPE):
        raise VMException("Cannot create VM from template")


def teardown_package():
    """
    Cleans the environment
    """
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME[0],
                           vdc=config.VDC_HOST,
                           vdc_password=config.VDC_ROOT_PASSWORD):
        raise NetworkException("Cannot remove setup")
