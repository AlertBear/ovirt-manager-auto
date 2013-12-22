"""
VNIC profile feature test
"""

import logging
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
    import config
    if not prepareSetup(hosts=config.HOSTS[0], cpuName=config.CPU_NAME,
                        username=config.HOSTS_USER, password=config.HOSTS_PW,
                        datacenter=config.DC_NAME,
                        storageDomainName=config.STORAGE_NAME,
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME,
                        lun_address=config.LUN_ADDRESS,
                        lun_target=config.LUN_TARGET,
                        luns=config.LUN, version=config.VERSION,
                        cobblerAddress=config.COBBLER_ADDRESS,
                        cobblerUser=config.COBBLER_USER,
                        cobblerPasswd=config.COBBLER_PASSWORD,
                        vm_password=config.HOSTS_PW,
                        vmName=config.VM_NAME[0],
                        template_name=config.TEMPLATE_NAME):
        raise NetworkException("Cannot create setup")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME):
        raise DataCenterException("Cannot remove setup")
