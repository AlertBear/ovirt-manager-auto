"""
Sanity Test
"""

import logging
from art.rhevm_api.tests_lib.low_level.vms import startVm
from art.rhevm_api.utils.test_utils import set_engine_properties
from rhevmtests.networking import config
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.high_level.networks import prepareSetup
from art.test_handler.exceptions import NetworkException

logger = logging.getLogger("Sanity_Init")

#################################################


def setup_package():
    """
    Prepare environment
    """
    logger.info("Configuring engine to support ethtool opts for 3.5 version")
    cmd = ["UserDefinedNetworkCustomProperties=ethtool_opts=.*", "--cver=3.5"]
    if not set_engine_properties(config.ENGINE, cmd, restart=False):
        raise NetworkException("Failed to set ethtool via engine-config")

    logger.info("Configuring engine to support queues for 3.5 version")
    param = [
        "CustomDeviceProperties='{type=interface;prop={queues=[1-9][0-9]*}}'",
        "'--cver=3.5'"
    ]
    if not set_engine_properties(engine_obj=config.ENGINE, param=param):
        raise NetworkException("Failed to enable queue via engine-config")

    if not config.GOLDEN_ENV:
        logger.info("Creating data center, cluster, adding host and storage")
        if not prepareSetup(
            hosts=config.VDS_HOSTS[0], cpuName=config.CPU_NAME,
            username=config.HOSTS_USER, password=config.HOSTS_PW,
            datacenter=config.DC_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            storage_type=config.STORAGE_TYPE, cluster=config.CLUSTER_NAME[0],
            lun_address=config.LUN_ADDRESS[0], lun_target=config.LUN_TARGET[0],
            luns=config.LUN[0], version=config.COMP_VERSION,
            vmName=config.VM_NAME[0], vm_password=config.VMS_LINUX_PW,
            mgmt_network=config.MGMT_BRIDGE,
        ):
            raise NetworkException("Cannot create setup")

    else:
        from rhevmtests.networking import network_cleanup
        network_cleanup()
        logger.info(
            "Running on golden env, starting VM %s", config.VM_NAME[0]
        )
        if not startVm(
            positive=True, vm=config.VM_NAME[0], wait_for_ip=True,
            placement_host=config.HOSTS[0]
        ):
            raise NetworkException("Failed to start %s" % config.VM_NAME[0])


def teardown_package():
    """
    Cleans the environment
    """
    if not config.GOLDEN_ENV:
        if not cleanDataCenter(
                positive=True, datacenter=config.DC_NAME[0],
                vdc=config.VDC_HOST, vdc_password=config.VDC_ROOT_PASSWORD
        ):
            raise NetworkException("Cannot remove setup")

    else:
        logger.info("Running on golden env, stopping VM %s", config.VM_NAME[0])
        if not vms.stopVm(True, vm=config.VM_NAME[0]):
            logger.error("Failed to stop VM: %s", config.VM_NAME[0])
