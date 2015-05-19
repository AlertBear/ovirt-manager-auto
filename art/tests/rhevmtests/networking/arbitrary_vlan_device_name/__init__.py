#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test ArbitraryVlanDeviceName
Supporting vlan devices with names not in standard "dev.VLANID"
(e.g. eth0.10-fcoe, em1.myvlan10, vlan20, ...).
"""

import helper
import logging
import rhevmtests.helpers as helpers
import rhevmtests.networking as network
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("ArbitraryVlanDeviceName_Init")


def setup_package():
    """
    Prepare environment
    """
    if network.config.GOLDEN_ENV:
        logger.info("Running on golden env, calling network_cleanup")
        network.network_cleanup()

    else:
        logger.info("Create setup with datacenter, cluster and host")
        if not hl_networks.create_basic_setup(
            datacenter=network.config.DC_NAME[0],
            storage_type=network.config.STORAGE_TYPE,
            version=network.config.COMP_VERSION,
            cluster=network.config.CLUSTER_NAME[0],
            cpu=network.config.CPU_NAME, host=network.config.HOSTS[0],
            host_password=network.config.HOSTS_PW
        ):
            raise exceptions.NetworkException("Failed to create setup")

    logger.info(
        "Setting passwordless ssh from engine (%s) to host (%s)",
        network.config.ENGINE_HOST.ip, network.config.VDS_HOSTS[0].ip
    )
    if not helpers.set_passwordless_ssh(
        network.config.ENGINE_HOST, network.config.VDS_HOSTS[0]
    ):
        raise exceptions.NetworkException(
            "Failed to set passwordless SSH to %s" % network.config.HOSTS[0]
        )

    logger.info("Disabling sasl in libvirt")
    if not helper.set_libvirtd_sasl(
        host_obj=network.config.VDS_HOSTS[0], sasl=False
    ):
        raise exceptions.NetworkException(
            "Failed to disable sasl on %s" % network.config.HOSTS[0]
        )


def teardown_package():
    """
    Cleans the environment
    """
    if network.config.GOLDEN_ENV:
        logger.info("Running on golden env, no teardown")

    else:
        if not hl_networks.remove_basic_setup(
            datacenter=network.config.DC_NAME[0],
            cluster=network.config.CLUSTER_NAME[0],
            hosts=[network.config.HOSTS[0]]
        ):
            logger.error("Failed to remove setup")

    logger.info("Enabling sasl in libvirt")
    if not helper.set_libvirtd_sasl(host_obj=network.config.VDS_HOSTS[0]):
        logger.error("Failed to enable sasl on %s", network.config.HOSTS[0])
