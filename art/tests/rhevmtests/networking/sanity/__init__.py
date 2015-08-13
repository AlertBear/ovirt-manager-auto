"""
Sanity init
"""

import logging
import config as conf
import helper
import rhevmtests.networking as network
import art.rhevm_api.tests_lib.high_level.datacenters as hl_datacenters
import art.rhevm_api.utils.test_utils as test_utils
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.test_handler.exceptions as exceptions
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

logger = logging.getLogger("Sanity_Init")


def setup_package():
    """
    Prepare environment
    """
    conf.HOST_NICS = conf.VDS_HOSTS[0].nics
    conf.HOST_NAME_0 = ll_hosts.get_host_name_from_engine(conf.VDS_HOSTS[0].ip)
    network.network_cleanup()
    logger.info(
        "Configuring engine to support ethtool opts for %s version",
        conf.COMP_VERSION
    )
    cmd = [
        "UserDefinedNetworkCustomProperties=ethtool_opts=.*",
        "--cver=%s" % conf.COMP_VERSION
    ]
    if not test_utils.set_engine_properties(conf.ENGINE, cmd, restart=False):
        raise exceptions.NetworkException(
            "Failed to set ethtool via engine-config"
        )
    logger.info(
        "Configuring engine to support queues for %s version",
        conf.COMP_VERSION
    )
    param = [
        "CustomDeviceProperties='{type=interface;prop={queues=[1-9][0-9]*}}'",
        "'--cver=%s'" % conf.COMP_VERSION
    ]
    if not test_utils.set_engine_properties(
        engine_obj=conf.ENGINE, param=param
    ):
        raise exceptions.NetworkException(
            "Failed to enable queue via engine-config"
        )
    if not conf.GOLDEN_ENV:
        logger.info("Creating data center, cluster, adding host and storage")
        if not hl_networks.prepareSetup(
            hosts=conf.VDS_HOSTS[0], cpuName=conf.CPU_NAME,
            username=conf.HOSTS_USER, password=conf.HOSTS_PW,
            datacenter=conf.DC_NAME[0],
            storageDomainName=conf.STORAGE_NAME[0],
            storage_type=conf.STORAGE_TYPE, cluster=conf.CLUSTER_NAME[0],
            lun_address=conf.LUN_ADDRESS[0], lun_target=conf.LUN_TARGET[0],
            luns=conf.LUN[0], version=conf.COMP_VERSION,
            vmName=conf.VM_NAME[0], vm_password=conf.VMS_LINUX_PW,
            mgmt_network=conf.MGMT_BRIDGE,
        ):
            raise exceptions.NetworkException("Cannot create setup")
        helper.prepare_networks_on_dc()

    if conf.GOLDEN_ENV:
        helper.prepare_networks_on_dc()
        logger.info(
            "Running on golden env, starting VM %s on host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        if not net_help.run_vm_once_specific_host(
            vm=conf.VM_NAME[0], host=conf.HOSTS[0], wait_for_ip=True
        ):
            raise exceptions.NetworkException(
                "Cannot start VM %s on host %s" %
                (conf.VM_NAME[0], conf.HOSTS[0])
            )


def teardown_package():
    """
    Cleans the environment
    """
    if not conf.GOLDEN_ENV:
        if not hl_datacenters.clean_datacenter(
                positive=True, datacenter=conf.DC_NAME[0],
                vdc=conf.VDC_HOST, vdc_password=conf.VDC_ROOT_PASSWORD
        ):
            logger.error("Cannot remove setup")

    if conf.GOLDEN_ENV:
        logger.info("Running on golden env, stopping VM %s", conf.VM_NAME[0])
        if not ll_vms.stopVm(True, vm=conf.VM_NAME[0]):
            logger.error("Failed to stop VM: %s", conf.VM_NAME[0])

        logger.info("Removing all networks from setup")
        if not hl_networks.remove_net_from_setup(
            host=conf.VDS_HOSTS_0, all_net=True,
            mgmt_network=conf.MGMT_BRIDGE, data_center=conf.DC_NAME
        ):
            logger.error("Cannot remove all networks from setup")
