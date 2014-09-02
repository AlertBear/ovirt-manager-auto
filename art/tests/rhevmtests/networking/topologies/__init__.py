"""
Topologies Test
"""

import logging
from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
from art.rhevm_api.tests_lib.low_level.vms import stopVm
from art.test_handler.exceptions import NetworkException


logger = logging.getLogger("Topologies_init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on GE. Calling network_cleanup()")
        network_cleanup()

    else:
        logger.info("Creating data center, cluster, adding host and storage")
        if not prepareSetup(hosts=config.VDS_HOSTS[0],
                            cpuName=config.CPU_NAME,
                            username=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            datacenter=config.DC_NAME[0],
                            storageDomainName=config.STORAGE_NAME[0],
                            storage_type=config.STORAGE_TYPE,
                            cluster=config.CLUSTER_NAME[0],
                            lun_address=config.LUN_ADDRESS[0],
                            lun_target=config.LUN_TARGET[0],
                            luns=config.LUN[0], version=config.COMP_VERSION,
                            vmName=config.VM_NAME[0],
                            vm_password=config.VMS_LINUX_PW,
                            mgmt_network=config.MGMT_BRIDGE,
                            auto_nics=[0]):
            raise NetworkException("Cannot create setup")

        logger.info("Stop VM %s", config.VM_NAME[0])
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Fail to stop VM %s", config.VM_NAME[0])


def teardown_package():
    """
    Cleans the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on GE. Calling network_cleanup()")
        network_cleanup()

    else:
        if not cleanDataCenter(positive=True, datacenter=config.DC_NAME[0],
                               vdc=config.VDC_HOST,
                               vdc_password=config.VDC_ROOT_PASSWORD):
            raise NetworkException("Cannot remove setup")
