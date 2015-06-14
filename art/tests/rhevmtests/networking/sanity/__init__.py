"""
Sanity Test
"""

import logging
from rhevmtests.networking import config, network_cleanup
import art.rhevm_api.tests_lib.high_level.vms as hl_vm
import art.rhevm_api.tests_lib.high_level.datacenters as hl_datacenters
import art.rhevm_api.utils.test_utils as test_utils
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts

logger = logging.getLogger("Sanity_Init")
VDSMD_SERVICE = "vdsmd"


def setup_package():
    """
    Prepare environment
    """
    logger.info(
        "Configuring engine to support ethtool opts for %s version",
        config.COMP_VERSION
    )
    cmd = [
        "UserDefinedNetworkCustomProperties=ethtool_opts=.*",
        "--cver=%s" % config.COMP_VERSION
    ]
    if not test_utils.set_engine_properties(config.ENGINE, cmd, restart=False):
        raise exceptions.NetworkException(
            "Failed to set ethtool via engine-config"
        )

    logger.info(
        "Configuring engine to support queues for %s version",
        config.COMP_VERSION
    )
    param = [
        "CustomDeviceProperties='{type=interface;prop={queues=[1-9][0-9]*}}'",
        "'--cver=%s'" % config.COMP_VERSION
    ]
    if not test_utils.set_engine_properties(
        engine_obj=config.ENGINE, param=param
    ):
        raise exceptions.NetworkException(
            "Failed to enable queue via engine-config"
        )

    if not config.GOLDEN_ENV:
        logger.info("Creating data center, cluster, adding host and storage")
        if not hl_networks.prepareSetup(
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
            raise exceptions.NetworkException("Cannot create setup")

    logger.info("Add dummy support in VDSM conf file")
    if not hl_networks.add_dummy_vdsm_support(
        host=config.HOSTS_IP[0], username=config.HOSTS_USER,
        password=config.HOSTS_PW
    ):
        raise exceptions.NetworkException(
            "Failed to add dummy support to VDSM conf file"
        )
    logger.info("Restarting %s service on %s", VDSMD_SERVICE, config.HOSTS[0])
    hl_hosts.restart_services_under_maintenance_state(
        [VDSMD_SERVICE], config.VDS_HOSTS[0]
    )
    if config.GOLDEN_ENV:
        network_cleanup()
        logger.info(
            "Running on golden env, starting VM %s on host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )
        if not hl_vm.start_vm_on_specific_host(
            vm=config.VM_NAME[0], host=config.HOSTS[0]
        ):
            raise exceptions.NetworkException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[0], config.HOSTS[0])
            )


def teardown_package():
    """
    Cleans the environment
    """
    if not config.GOLDEN_ENV:
        if not hl_datacenters.clean_datacenter(
                positive=True, datacenter=config.DC_NAME[0],
                vdc=config.VDC_HOST, vdc_password=config.VDC_ROOT_PASSWORD
        ):
            logger.error("Cannot remove setup")

    else:
        logger.info("Running on golden env, stopping VM %s", config.VM_NAME[0])
        if not ll_vms.stopVm(True, vm=config.VM_NAME[0]):
            logger.error("Failed to stop VM: %s", config.VM_NAME[0])

    logger.info("Remove dummy support in VDSM conf file")
    if not hl_networks.remove_dummy_vdsm_support(
        host=config.HOSTS_IP[0], username=config.HOSTS_USER,
        password=config.HOSTS_PW
    ):
        logger.error("Failed to remove dummy support to VDSM conf file")

    logger.info("Restarting %s service on %s", VDSMD_SERVICE, config.HOSTS[0])
    try:
        hl_hosts.restart_services_under_maintenance_state(
            [VDSMD_SERVICE], config.VDS_HOSTS[0]
        )
    except exceptions.HostException:
        logger.error(
            "Failed to restart %s service on %s",
            VDSMD_SERVICE, config.HOSTS[0]
        )
