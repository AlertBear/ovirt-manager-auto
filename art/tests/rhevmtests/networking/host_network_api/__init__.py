#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API
"""

import logging
import art.rhevm_api.utils.test_utils as test_utils
import art.test_handler.exceptions as exceptions
import rhevmtests.networking as network
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import helper

logger = logging.getLogger("Host_Network_API_Init")

VDS_HOSTS_0 = network.config.VDS_HOSTS[0]
HOST_0_IP = network.config.HOSTS_IP[0]
HOST_USER = network.config.HOSTS_USER
HOST_PW = network.config.HOSTS_PW
HOST_NICS = None  # Filled in setup_package


def setup_package():
    """
    Prepare environment
    """
    global HOST_NICS
    HOST_NICS = VDS_HOSTS_0.nics
    logger.info("Running network cleanup")
    network.network_cleanup()
    logger.info(
        "Create and attach networks on %s/%s",
        helper.DC_NAME, network.config.CLUSTER_NAME[0]
    )
    helper.prepare_networks_on_dc()
    logger.info("Add dummy support in VDSM conf file")
    if not hl_networks.add_dummy_vdsm_support(
        host=HOST_0_IP, username=HOST_USER, password=HOST_PW
    ):
        raise exceptions.NetworkException(
            "Failed to add dummy support to VDSM conf file")

    logger.info("Restart vdsm and supervdsm services")
    hl_hosts.restart_vdsm_under_maintenance_state(helper.HOST_0, VDS_HOSTS_0)

    logger.info("Creating 10 dummy interfaces")
    if not hl_networks.create_dummy_interfaces(
        host=HOST_0_IP, username=HOST_USER, password=HOST_PW, num_dummy=10
    ):
        raise exceptions.NetworkException("Failed to create dummy interfaces")

    logger.info("Check if dummy exists on %s", helper.HOST_0)
    helper.check_dummy_on_host()

    logger.info("Configuring engine to support ethtool opts for 3.6 version")
    cmd = ["UserDefinedNetworkCustomProperties=ethtool_opts=.*", "--cver=3.6"]
    if not test_utils.set_engine_properties(network.config.ENGINE, cmd):
        raise exceptions.NetworkException(
            "Failed to set ethtool via engine-config"
        )


def teardown_package():
    """
    Cleans environment
    """
    logger.info("Running on GE, starting teardown")
    logger.info(
        "Removing all network from %s and %s", helper.DC_NAME, helper.HOST_0
    )
    if not hl_networks.remove_net_from_setup(
        host=VDS_HOSTS_0, auto_nics=[0],
        data_center=helper.DC_NAME, all_net=True,
        mgmt_network=network.config.MGMT_BRIDGE
    ):
        logger.error(
            "Failed to remove networks from %s and %s",
            helper.DC_NAME, helper.HOST_0
        )
    logger.info("Remove dummy support in VDSM conf file")
    if not hl_networks.remove_dummy_vdsm_support(
        host=HOST_0_IP, username=HOST_USER, password=HOST_PW
    ):
        logger.error("Failed to remove dummy support to VDSM conf file")

    logger.info("Restart vdsm and supervdsm services")
    if not (
            VDS_HOSTS_0.service("supervdsmd").stop() and
            VDS_HOSTS_0.service("vdsmd").restart()
    ):
        logger.error("Failed to restart vdsmd service")

    logger.info("Delete all dummy interfaces")
    if not hl_networks.delete_dummy_interfaces(
        host=HOST_0_IP, username=HOST_USER, password=HOST_PW
    ):
        logger.error("Failed to delete dummy interfaces")

    logger.info("Check if dummy does not exist on %s", helper.HOST_0)
    helper.check_dummy_on_host(positive=False)


class TestHostNetworkApiTestCaseBase(TestCase):
    """
    base class which provides teardown class method for each test case
    """

    @classmethod
    def teardown_class(cls):
        """
        Remove all networks from the host NICs.
        """
        logger.info("Starting teardown")
        logger.info("Removing all networks from %s", helper.HOST_0)
        if not hl_host_network.clean_host_interfaces(helper.HOST_0):
            logger.error(
                "Failed to remove all networks from %s", helper.HOST_0
            )
