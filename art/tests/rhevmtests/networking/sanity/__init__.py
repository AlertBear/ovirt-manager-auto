"""
Sanity Test
"""

import logging
from art.rhevm_api.tests_lib.high_level import vms as hl_vm
from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter
from art.rhevm_api.utils.test_utils import set_engine_properties
from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level.networks import(
    prepareSetup, add_dummy_vdsm_support, remove_dummy_vdsm_support
)
from art.test_handler.exceptions import NetworkException
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
from art.core_api.apis_utils import TimeoutingSampler

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
        network_cleanup()
        logger.info(
            "Running on golden env, starting VM %s on host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )
        if not hl_vm.start_vm_on_specific_host(
            vm=config.VM_NAME[0], host=config.HOSTS[0]
        ):
            raise NetworkException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[0], config.HOSTS[0])
            )

    logger.info("Add dummy support in VDSM conf file")
    if not add_dummy_vdsm_support(
        host=config.HOSTS_IP[0], username=config.HOSTS_USER,
        password=config.HOSTS_PW
    ):
        raise NetworkException("Failed to add dummy support to VDSM conf file")

    logger.info("Restart vdsm and supervdsm services")
    if not (
            config.VDS_HOSTS[0].service("supervdsmd").stop() and
            config.VDS_HOSTS[0].service("vdsmd").restart()
    ):
        raise NetworkException("Failed to restart vdsmd service")

    logger.info("Put the Host in up state if it's not up")
    sample = TimeoutingSampler(
        timeout=config.SAMPLER_TIMEOUT, sleep=1,
        func=hl_hosts.activate_host_if_not_up, host=config.HOSTS[0]
    )
    if not sample.waitForFuncStatus(result=True):
        raise NetworkException(
            "Failed to activate host: %s" % config.HOSTS[0]
        )


def teardown_package():
    """
    Cleans the environment
    """
    if not config.GOLDEN_ENV:
        if not clean_datacenter(
                positive=True, datacenter=config.DC_NAME[0],
                vdc=config.VDC_HOST, vdc_password=config.VDC_ROOT_PASSWORD
        ):
            logger.error("Cannot remove setup")

    else:
        logger.info("Running on golden env, stopping VM %s", config.VM_NAME[0])
        if not vms.stopVm(True, vm=config.VM_NAME[0]):
            logger.error("Failed to stop VM: %s", config.VM_NAME[0])

    logger.info("Remove dummy support in VDSM conf file")
    if not remove_dummy_vdsm_support(
        host=config.HOSTS_IP[0], username=config.HOSTS_USER,
        password=config.HOSTS_PW
    ):
        logger.error("Failed to remove dummy support to VDSM conf file")

    logger.info("Restart vdsm and supervdsm services")
    if not (
            config.VDS_HOSTS[0].service("supervdsmd").stop() and
            config.VDS_HOSTS[0].service("vdsmd").restart()
    ):
        logger.error("Failed to restart vdsmd service")
