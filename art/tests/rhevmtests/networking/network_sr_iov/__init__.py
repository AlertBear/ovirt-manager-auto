#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV feature init
"""
import logging
import config as conf
from rhevmtests import networking
import art.rhevm_api.tests_lib.low_level.sriov as ll_sriov

logger = logging.getLogger("SR_IOV_Init")


def setup_package():
    """
    Prepare environment
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    networking.network_cleanup()

    conf.HOST_O_SRIOV_NICS_OBJ = ll_sriov.SriovHostNics(conf.HOST_0_NAME)
    conf.HOST_0_PF_LIST = conf.HOST_O_SRIOV_NICS_OBJ.get_all_pf_nics_objects()
    conf.HOST_0_PF_NAMES = conf.HOST_O_SRIOV_NICS_OBJ.get_all_pf_nics_names()
