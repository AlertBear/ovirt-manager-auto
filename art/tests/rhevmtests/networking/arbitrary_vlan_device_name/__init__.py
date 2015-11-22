#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Test ArbitraryVlanDeviceName
Supporting vlan devices with names not in standard "dev.VLANID"
(e.g. eth0.10-fcoe, em1.myvlan10, vlan20, ...).
"""

import logging
import rhevmtests.networking as network
import rhevmtests.networking.helper as net_helper

logger = logging.getLogger("ArbitraryVlanDeviceName_Init")


def setup_package():
    """
    Setting passwordless ssh and then disabling sasl in libvirt
    """
    network.network_cleanup()
    net_helper.set_libvirt_sasl_status(
        engine_resource=network.config.ENGINE_HOST,
        host_resource=network.config.VDS_HOSTS[0],
    )


def teardown_package():
    """
    Enabling sasl in libvirt
    """
    net_helper.set_libvirt_sasl_status(
        engine_resource=network.config.ENGINE_HOST,
        host_resource=network.config.VDS_HOSTS[0], sasl=True
    )
