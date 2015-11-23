#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Multiple gateways feature Init
"""

import logging
import config as conf
import rhevmtests.networking as networking
import rhevmtests.networking.helper as net_helper


logger = logging.getLogger("Multiple_Gateway_Init")

#################################################


def setup_package():
    """
    Running cleanup
    Create dummies on host
    """
    networking.network_cleanup()
    net_helper.prepare_dummies(host_resource=conf.VDS_HOST_0, num_dummy=3)
    conf.HOST_NICS = conf.VDS_HOST_0.nics


def teardown_package():
    """
    Delete dummies on host
    """
    net_helper.delete_dummies(host_resource=conf.VDS_HOST_0)
