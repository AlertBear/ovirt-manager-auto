"""
Sanity init
"""

import helper
import logging
import config as conf
import rhevmtests.networking as network
from art.test_handler import exceptions
from art.rhevm_api.utils import test_utils
import art.core_api.apis_utils as apis_utils
import rhevmtests.networking.helper as net_helper
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Sanity_Init")


def setup_package():
    """
    Prepare environment
    """
    conf.HOST_NAME_0 = ll_hosts.get_host_name_from_engine(conf.VDS_HOSTS[0].ip)
    network.network_cleanup()
    logger.info(
        "Creating 20 dummy interfaces on %s", conf.HOST_0
    )
    if not hl_networks.create_dummy_interfaces(
        host=conf.VDS_HOST_0, num_dummy=20
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create dummy interfaces on %s" % conf.VDS_HOST_0
        )
    logger.info("Refresh host capabilities")
    host_obj = ll_hosts.HOST_API.find(conf.HOSTS[0])
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)

    logger.info("Check if dummy_0 exist on host via engine")
    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=helper.check_dummy_on_host_interfaces, dummy_name="dummy_0"
    )
    if not sample.waitForFuncStatus(result=True):
        raise exceptions.NetworkException(
            "Dummy interface does not exist on engine"
        )
    conf.HOST_NICS = conf.VDS_HOSTS[0].nics
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

    logger.info(
        "Create %s on %s/%s", conf.NETS_DICT, conf.DC_NAME, conf.CLUSTER
    )
    net_helper.prepare_networks_on_setup(
        networks_dict=conf.NETS_DICT, dc=conf.DC_NAME, cluster=conf.CLUSTER
    )


def teardown_package():
    """
    Cleans the environment
    """
    logger.info("Remove all networks from setup")
    if not hl_networks.remove_net_from_setup(
        host=conf.HOST_0, all_net=True, mgmt_network=conf.MGMT_BRIDGE,
        data_center=conf.DC_NAME
    ):
        logger.error("Cannot remove all networks from setup")

    logger.info("Delete all dummy interfaces")
    if not hl_networks.delete_dummy_interfaces(host=conf.VDS_HOST_0):
        logger.error("Failed to delete dummy interfaces")

    logger.info("Refresh host capabilities")
    host_obj = ll_hosts.HOST_API.find(conf.HOST_0)
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)

    logger.info("Check that dummy_0 does not exist on host via engine")
    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=helper.check_dummy_on_host_interfaces, dummy_name="dummy_0"
    )
    if not sample.waitForFuncStatus(result=False):
        logger.error("Dummy interface exists on engine")
