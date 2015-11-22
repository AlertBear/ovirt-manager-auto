"""
Sanity init
"""

import helper
import logging
import config as conf
import rhevmtests.networking as network
import art.core_api.apis_utils as apis_utils
import rhevmtests.networking.helper as net_helper
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Sanity_Init")


def setup_package():
    """
    Prepare environment
    """
    network.network_cleanup()
    net_helper.set_libvirt_sasl_status(
        engine_resource=conf.ENGINE_HOST, host_resource=conf.VDS_HOST_0,
    )
    logger.info(
        "Creating 20 dummy interfaces on %s", conf.HOST_NAME_0
    )
    if not hl_networks.create_dummy_interfaces(
        host=conf.VDS_HOST_0, num_dummy=20
    ):
        raise conf.NET_EXCEPTION(
            "Failed to create dummy interfaces on %s" % conf.VDS_HOST_0
        )
    logger.info("Refresh host capabilities")
    host_obj = ll_hosts.HOST_API.find(conf.HOST_NAME_0)
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)

    logger.info("Check if dummy_0 exist on host via engine")
    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=helper.check_dummy_on_host_interfaces, dummy_name="dummy_0"
    )
    if not sample.waitForFuncStatus(result=True):
        raise conf.NET_EXCEPTION(
            "Dummy interface does not exist on engine"
        )
    conf.HOST_0_NICS = conf.VDS_HOST_0.nics
    helper.engine_config_set_ethtool_and_queues()
    net_helper.prepare_networks_on_setup(
        networks_dict=conf.SN_DICT, dc=conf.DC_0_NAME,
        cluster=conf.CLUSTER_0_NAME
    )


def teardown_package():
    """
    Cleans the environment
    """
    net_helper.set_libvirt_sasl_status(
        engine_resource=conf.ENGINE_HOST, host_resource=conf.VDS_HOST_0,
        sasl=True
    )
    logger.info("Remove all networks from setup")
    if not hl_networks.remove_net_from_setup(
        host=conf.HOST_NAME_0, all_net=True, mgmt_network=conf.MGMT_BRIDGE,
        data_center=conf.DC_0_NAME
    ):
        logger.error("Cannot remove all networks from setup")

    logger.info("Delete all dummy interfaces")
    if not hl_networks.delete_dummy_interfaces(host=conf.VDS_HOST_0):
        logger.error("Failed to delete dummy interfaces")

    logger.info("Refresh host capabilities")
    host_obj = ll_hosts.HOST_API.find(conf.HOST_NAME_0)
    refresh_href = "{0};force".format(host_obj.get_href())
    ll_hosts.HOST_API.get(href=refresh_href)

    logger.info("Check that dummy_0 does not exist on host via engine")
    sample = apis_utils.TimeoutingSampler(
        timeout=conf.SAMPLER_TIMEOUT, sleep=1,
        func=helper.check_dummy_on_host_interfaces, dummy_name="dummy_0"
    )
    if not sample.waitForFuncStatus(result=False):
        logger.error("Dummy interface exists on engine")
