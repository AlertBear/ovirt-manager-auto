"""
IO feature init
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Network/
    3_5_Network_IO
"""

import logging
import config as conf
from rhevmtests import networking
import rhevmtests.networking.helper as network_helper

logger = logging.getLogger("IO_Test_Init")


def setup_package():
    """
    Running cleanup
    Prepare network on setup
    """
    conf.VDS_0_HOST = conf.VDS_HOSTS[0]
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST_0_NICS = conf.VDS_0_HOST.nics
    networking.network_cleanup()
    network_helper.prepare_networks_on_setup(
        networks_dict=conf.NET_DICT, dc=conf.DC_0, cluster=conf.CL_0
    )
