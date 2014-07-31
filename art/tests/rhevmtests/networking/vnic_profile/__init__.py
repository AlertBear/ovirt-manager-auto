"""
VNIC profile feature test
"""

import logging
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.low_level.storagedomains import\
    cleanDataCenter

from art.test_handler.exceptions import\
    DataCenterException, NetworkException
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
logger = logging.getLogger("VNIC Profile")

#################################################


def setup_package():
    """
    Prepare environment
    """
    if not prepareSetup(hosts=config.HOSTS[0], cpuName=config.CPU_NAME,
                        username=config.HOSTS_USER,
                        password=config.HOSTS_PW,
                        datacenter=config.DC_NAME[0],
                        storageDomainName=config.STORAGE_NAME[0],
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME[0],
                        auto_nics=[config.HOST_NICS[0]],
                        lun_address=config.LUN_ADDRESS[0],
                        lun_target=config.LUN_TARGET[0],
                        luns=config.LUN[0], version=config.COMP_VERSION,
                        vm_password=config.HOSTS_PW,
                        vmName=config.VM_NAME[0],
                        mgmt_network=config.MGMT_BRIDGE,
                        vm_network=config.MGMT_BRIDGE,
                        template_name=config.TEMPLATE_NAME[0]):
        raise NetworkException("Cannot create setup")


def teardown_package():
    """
    Cleans the environment
    """
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME[0],
                           vdc=config.VDC_HOST,
                           vdc_password=config.VDC_ROOT_PASSWORD):
        raise DataCenterException("Cannot remove setup")
