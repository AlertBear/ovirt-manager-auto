"""
multiple_queue_nics job
"""

import logging
from art.rhevm_api.tests_lib.low_level.vms import stopVm
from art.rhevm_api.utils.test_utils import set_engine_properties
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup

logger = logging.getLogger("multiple_queue_nics_init")

# ################################################


def setup_package():
    """
    Prepare environment
    """
    logger.info("Configuring engine to support queues for 3.5 version")
    param = [
        "CustomDeviceProperties='{type=interface;prop={queues=[1-9][0-9]*}}'",
        "'--cver=3.5'"
    ]
    if not set_engine_properties(engine_obj=config.ENGINE, param=param):
        raise NetworkException("Failed to enable queue via engine-config")

    if config.GOLDEN_ENV:
        logger.info("Running on GE. No need for further setup")

    else:
        if not prepareSetup(
            hosts=config.VDS_HOSTS, cpuName=config.CPU_NAME,
            username=config.HOSTS_USER, password=config.HOSTS_PW,
            datacenter=config.DC_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            storage_type=config.STORAGE_TYPE, cluster=config.CLUSTER_NAME[0],
            lun_address=config.LUN_ADDRESS[0], lun_target=config.LUN_TARGET[0],
            luns=config.LUN[0], version=config.COMP_VERSION,
            vmName=config.VM_NAME[0], vm_password=config.VMS_LINUX_PW,
            mgmt_network=config.MGMT_BRIDGE
        ):
            raise NetworkException("Cannot create setup")

        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Failed to stop %s" % config.VM_NAME[0])


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Removing queues support from engine for 3.5 version")
    param = ["CustomDeviceProperties=''", "'--cver=3.5'"]
    if not set_engine_properties(engine_obj=config.ENGINE, param=param):
        raise NetworkException("Failed to remove queues support via "
                               "engine-config")
    if config.GOLDEN_ENV:
        logger.info("Running on GE. No need for teardown")

    else:
        if not cleanDataCenter(
            positive=True, datacenter=config.DC_NAME[0],
            vdc=config.VDC_HOST, vdc_password=config.VDC_ROOT_PASSWORD
        ):
            raise NetworkException("Cannot remove setup")
