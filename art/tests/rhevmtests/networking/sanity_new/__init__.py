"""
Sanity init
"""

import helper
import logging
import config as conf
import rhevmtests.networking as network
import rhevmtests.networking.helper as net_helper
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
    net_helper.prepare_dummies(host_resource=conf.VDS_HOST_0, num_dummy=20)
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
    net_helper.delete_dummies(host_resource=conf.VDS_HOST_0)
