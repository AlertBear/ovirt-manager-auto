#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Job for new host network API
"""

import config as c
import logging
import helper
import art.rhevm_api.utils.test_utils as test_utils
import art.test_handler.exceptions as exceptions
import rhevmtests.networking as network
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Host_Network_API_Init")


def setup_package():
    """
    Prepare environment
    """
    c.HOST_NICS = c.VDS_HOSTS_0.nics
    logger.info("Running network cleanup")
    network.network_cleanup()
    logger.info(
        "Create and attach networks on %s/%s", c.DC_NAME, c.CLUSTER_NAME[0])
    helper.prepare_networks_on_dc()
    logger.info("Add dummy support in VDSM conf file")
    if not hl_networks.add_dummy_vdsm_support(
        host=c.HOST_0_IP, username=c.HOSTS_USER, password=c.HOSTS_PW
    ):
        raise c.NET_EXCEPTION("Failed to add dummy support to VDSM conf file")

    logger.info("Restart vdsm and supervdsm services")
    hl_hosts.restart_services_under_maintenance_state(
        [c.VDSMD_SERVICE], c.VDS_HOSTS_0
    )
    logger.info("Creating 10 dummy interfaces")
    if not hl_networks.create_dummy_interfaces(
        host=c.HOST_0_IP, username=c.HOSTS_USER, password=c.HOSTS_PW,
        num_dummy=10
    ):
        raise c.NET_EXCEPTION("Failed to create dummy interfaces")

    logger.info("Check if dummy exists on %s", c.HOST_0)
    helper.check_dummy_on_host()

    logger.info("Configuring engine to support ethtool opts for 3.6 version")
    cmd = ["UserDefinedNetworkCustomProperties=ethtool_opts=.*", "--cver=3.6"]
    if not test_utils.set_engine_properties(network.config.ENGINE, cmd):
        raise c.NET_EXCEPTION("Failed to set ethtool via engine-config")


def teardown_package():
    """
    Cleans environment
    """
    logger.info("Running on GE, starting teardown")
    logger.info(
        "Removing all network from %s and %s", c.DC_NAME, c.HOST_0
    )
    if not hl_networks.remove_net_from_setup(
        host=c.VDS_HOSTS_0, auto_nics=[0], data_center=c.DC_NAME,
        all_net=True, mgmt_network=c.MGMT_BRIDGE
    ):
        logger.error(
            "Failed to remove networks from %s and %s", c.DC_NAME, c.HOST_0
        )
    logger.info("Remove dummy support in VDSM conf file")
    if not hl_networks.remove_dummy_vdsm_support(
        host=c.HOST_0_IP, username=c.HOSTS_USER, password=c.HOSTS_PW
    ):
        logger.error("Failed to remove dummy support to VDSM conf file")

    logger.info("Restarting %s service", c.VDSMD_SERVICE)
    try:
        hl_hosts.restart_services_under_maintenance_state(
            [c.VDSMD_SERVICE], c.VDS_HOSTS_0
        )
    except exceptions.HostException:
        logger.error("Failed to restart %s service", c.VDSMD_SERVICE)

    logger.info("Delete all dummy interfaces")
    if not hl_networks.delete_dummy_interfaces(
        host=c.HOST_0_IP, username=c.HOSTS_USER, password=c.HOSTS_PW
    ):
        logger.error("Failed to delete dummy interfaces")

    logger.info("Check if dummy does not exist on %s", c.HOST_0)
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
        logger.info("Removing all networks from %s", c.HOST_0)
        if not hl_host_network.clean_host_interfaces(c.HOST_0):
            logger.error(
                "Failed to remove all networks from %s", c.HOST_0
            )
