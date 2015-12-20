"""
Bridgeless network feature test
"""

import logging
import config as conf
import rhevmtests.networking as networking
import rhevmtests.networking.helper as networking_helper
logger = logging.getLogger("Bridgeless_Networks_Init")

#################################################


def setup_package():
    """
    running cleanup
    Obtain host NICs for the first Network Host
    Create dummy interfaces
    Create networks
    """
    networking.network_cleanup()
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST0_NICS = conf.VDS_HOSTS[0].nics
    networking_helper.prepare_dummies(
        host_resource=conf.VDS_HOSTS[0], num_dummy=conf.NUM_DUMMYS
    )
    networking_helper.prepare_networks_on_setup(
        networks_dict=conf.NET_DICT, dc=conf.DC_NAME[0],
        cluster=conf.CLUSTER_NAME[0]
    )


def teardown_package():
    """
    Cleans the environment
    """
    networking_helper.remove_networks_from_setup(hosts=conf.HOST_0_NAME)
    networking_helper.delete_dummies(host_resource=conf.VDS_HOSTS[0])
