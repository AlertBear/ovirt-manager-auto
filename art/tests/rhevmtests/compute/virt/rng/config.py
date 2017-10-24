#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - rng config
"""
from rhevmtests.compute.virt.config import *  # flake8: noqa

# RNG DEVICE
URANDOM_RNG = 'urandom'
HW_RNG = 'hwrng'
DEST_HWRNG = "/dev/hwrng"