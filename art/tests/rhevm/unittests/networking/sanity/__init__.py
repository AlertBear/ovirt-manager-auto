"""
Sanity Test
"""

import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
from art.test_handler.exceptions import DataCenterException
from art.test_handler.exceptions import NetworkException

logger = logging.getLogger("Sanity")

#################################################


def setup_package():
    '''
    Prepare environment
    '''
    import config
    logger.info("Creating data center, cluster, adding host and storage")
    if not prepareSetup(hosts=config.HOSTS[0],
                        cpuName=config.CPU_NAME,
                        username=config.HOSTS_USER,
                        password=config.HOSTS_PW,
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
                        vm_password=config.VMS_LINUX_PW,
                        template_flag=False, auto_nics=[config.HOST_NICS[0]]):
        raise NetworkException("Cannot create setup")


def teardown_package():
    '''
    Cleans the environment
    '''
    import config
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME,):
        raise DataCenterException("Cannot remove setup")

