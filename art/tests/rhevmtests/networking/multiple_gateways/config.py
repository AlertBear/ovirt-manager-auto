#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for multiple gateways feature
"""
import rhevmtests.networking.helper as network_helper
from rhevmtests.networking.config import *  # NOQA

HOST_NICS = None  # Filled in setup_package
VDS_HOST_0 = None  # Filled in setup_package
IPS = network_helper.create_random_ips(num_of_ips=10, mask=24)
