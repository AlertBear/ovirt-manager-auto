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

logger = logging.getLogger("ArbitraryVlanDeviceName_Init")


def setup_package():
    """
    Setting passwordless ssh and then disabling sasl in libvirt
    """
    network.network_cleanup()
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
    Enabling sasl in libvirt
    """
    logger.info("Enabling sasl in libvirt")
    if not helper.set_libvirtd_sasl(host_obj=network.config.VDS_HOSTS[0]):
        logger.error("Failed to enable sasl on %s", network.config.HOSTS[0])
