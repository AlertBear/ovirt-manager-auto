"""
Sanity init
"""

import logging
import config as conf
import helper
import rhevmtests.networking as network
import art.rhevm_api.utils.test_utils as test_utils
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.test_handler.exceptions as exceptions
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
    helper.prepare_networks_on_dc_cluster()


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Remove all networks from setup")
    if not hl_networks.remove_net_from_setup(
        host=conf.VDS_HOST_0, all_net=True,
        mgmt_network=conf.MGMT_BRIDGE, data_center=conf.DC_NAME
    ):
        logger.error("Cannot remove all networks from setup")
