"""
IO_test test
"""

import logging
from art.rhevm_api.tests_lib.high_level.networks import \
    prepareSetup
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.test_handler.exceptions import NetworkException, DataCenterException

logger = logging.getLogger("IO_test")

#################################################


def setup_package():
    """
    Prepare environment
    """
    import config

    if not prepareSetup(hosts=config.HOSTS[0], cpuName=config.CPU_NAME,
                        username='root', password=config.HOSTS_PW,
                        datacenter=config.DC_NAME,
                        storageDomainName=config.DC_NAME + '_data_domain0',
                        storage_type=config.STORAGE_TYPE,
                        cluster=config.CLUSTER_NAME,
                        lun_address=config.LUN_ADDRESS,
                        lun_target=config.LUN_TARGET,
                        luns=config.LUN, version=config.VERSION,
                        cobblerAddress=config.COBBLER_ADDRESS,
                        cobblerUser=config.COBBLER_USER,
                        cobblerPasswd=config.COBBLER_PASSWORD,
                        vm_password=config.HOSTS_PW,
                        auto_nics=[config.HOST_NICS[0]]):
        raise NetworkException("Cannot create setup")


def teardown_package():
    """
    Cleans the environment
    """
    import config

    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME):
        raise DataCenterException("Cannot remove setup")
