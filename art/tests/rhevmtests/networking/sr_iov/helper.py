#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by SR_IOV feature
"""

import logging
import config as conf
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest

logger = logging.getLogger("SR_IOV_Helper")


def update_host_nics():
    """
    Clear cache and update first Host NICs
    """
    logger.info("Get all NICs from host %s", conf.HOST_0_NAME)
    conf.VDS_0_HOST.cache.clear()
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics


@attr(tier=2)
class TestSriovBase(NetworkTest):
    """
    base class which provides teardown class method for each test case
    """
    pf_obj = None

    @classmethod
    def teardown_class(cls):
        """
        Set number of VFs for PF to be 0
        """
        cls.pf_obj.set_number_of_vf(0)
