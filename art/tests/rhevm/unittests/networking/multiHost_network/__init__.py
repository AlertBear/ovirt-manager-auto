"""
MultiHost networking feature test
"""

import logging
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
    import config
    if not prepareSetup(hosts=','.join(config.HOSTS), cpuName=config.CPU_NAME,
                        username=config.HOSTS_USER,
                        password=','.join([config.HOSTS_PW, config.HOSTS_PW]),
                        datacenter=config.DC_NAME,
                        storageDomainName=config.STORAGE_NAME,
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME,
                        lun_address=config.LUN_ADDRESS,
                        lun_target=config.LUN_TARGET,
                        luns=config.LUN, version=config.VERSION,
                        vm_password=config.HOSTS_PW,
                        vmName=config.VM_NAME[0],
                        template_name=config.TEMPLATE_NAME,
                        placement_host=config.HOSTS[0],
                        mgmt_network=config.MGMT_BRIDGE):
        raise NetworkException("Cannot create setup")

    if not addVm(True, name=config.VM_NAME[1], cluster=config.CLUSTER_NAME,
                 template=config.TEMPLATE_NAME,
                 display_type=config.DISPLAY_TYPE):
        raise VMException("Cannot create VM from template")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME,
                           vdc=config.VDC, vdc_password=config.VDC_PASSWORD):
        raise NetworkException("Cannot remove setup")
