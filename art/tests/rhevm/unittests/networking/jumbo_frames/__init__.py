"""
Jumbo Frames test
"""

import logging
from art.rhevm_api.tests_lib.low_level.storagedomains import\
    createDatacenter, cleanDataCenter
from art.test_handler.exceptions import DataCenterException

logger = logging.getLogger("Jumbo")

#################################################


def setup_package():
    """
    Prepare environment
    """
    import config
    if not createDatacenter(positive=True, hosts=config.HOSTS[0],
                            cpuName=config.CPU_NAME, username='root',
                            password=config.HOSTS_PW,
                            datacenter=config.DC_NAME,
                            storage_type=config.STORAGE_TYPE,
                            cluster=config.CLUSTER_NAME,
                            version=config.VERSION,
                            lun_address=config.LUN_ADDRESS,
                            lun_target=config.LUN_TARGET,
                            luns=config.LUN, lun_port=3260):
        raise DataCenterException("Cannot create setup")


def teardown_package():
    """
    Cleans the environment
    """
    import config
    if not cleanDataCenter(positive=True, datacenter=config.DC_NAME):
        raise DataCenterException("Cannot remove setup")
