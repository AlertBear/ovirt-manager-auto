"""
Sync network feature test
"""

import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import\
    cleanDataCenter

from art.test_handler.exceptions import DataCenterException, NetworkException
from art.rhevm_api.tests_lib.low_level.datacenters import\
    addDataCenter, removeDataCenter
from art.rhevm_api.tests_lib.low_level.clusters import\
    addCluster, removeCluster
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
logger = logging.getLogger("Sync")

#################################################


def setup_package():
    """
    Prepare environment
    """
    import config
    if not prepareSetup(hosts=config.HOSTS[0], cpuName=config.CPU_NAME,
                        username='root', password=config.HOSTS_PW,
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
                        auto_nics=[config.HOST_NICS[0]]):
        raise NetworkException("Cannot create setup")

    if not (addDataCenter(positive=True, name=config.DC_NAME2,
                          storage_type=config.STORAGE_TYPE,
                          version=config.VERSION) and
            addCluster(positive=True, name=config.CLUSTER_NAME2,
                       cpu=config.CPU_NAME, data_center=config.DC_NAME2,
                       version=config.VERSION)):
        raise DataCenterException("Cannot create second DC and Cluster")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME):
        raise DataCenterException("Cannot remove setup")
    if not removeCluster(True, config.CLUSTER_NAME2):
        raise DataCenterException("Cannot remove Cluster2 from setup")
    if not removeDataCenter(True, datacenter=config.DC_NAME2):
        raise DataCenterException("Cannot remove DC2 from setup")
