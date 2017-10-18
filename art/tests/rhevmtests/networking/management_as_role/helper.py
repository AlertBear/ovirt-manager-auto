#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by the test cases of Management As A Role
"""

import logging
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.high_level import (
    networks as hl_networks,
    hosts as hl_hosts
)
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    networks as ll_networks,
    clusters as ll_clusters
)
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
import rhevmtests.helpers as global_helper

logger = logging.getLogger("MGMT_Net_Role_Helper")


def install_host_new_mgmt(
    dc, cl, dest_cl, net_setup, mgmt_net, host_resource=None,
    network=conf.MGMT_BRIDGE, new_setup=True, remove_setup=False,
):
    """
    Install host with MGMT network different from the previous one

    Args:
        dc (str): DC for newly created setup
        cl (str): Cluster for newly created setup
        dest_cl (str): Cluster where host should be installed
        net_setup (dict): Network setup to set on host
        mgmt_net (str): Management network name to set on host
        host_resource (VDS instance, optional): Host resource
        network (str, optional): Network name for the MGMT
        new_setup (bool, optional): Flag indicating if there is a need to
            install a new setup
        remove_setup (bool, optional): Flag indicating if there is a need to
            remove setup

    Returns:
        bool: True if install host succeeded, otherwise False
    """
    if host_resource is None:
        host_resource = conf.VDS_2_HOST

    host_name = global_helper.get_host_name_by_resource(
        host_resource=host_resource
    )

    if not host_name:
        return False

    if not prepare_host_for_installation(
        host_resource=host_resource, network=network,
        dc=dc, cl=cl, new_setup=new_setup, host_name=host_name,
    ):
        return False

    return add_host_new_mgmt(
        host_rsc=host_resource, network=network, dc=dc, cl=cl,
        new_setup=new_setup, dest_cl=dest_cl, host_name=host_name,
        remove_setup=remove_setup, net_setup=net_setup, mgmt_net=mgmt_net
    )


def prepare_host_for_installation(
    host_resource, network, dc, cl, new_setup, host_name
):
    """
    Prepares host for installation with new MGMT network

    Args:
        host_resource (VDS instance): Host resource
        network (str): Network name for the MGMT
        dc (str): DC for newly created setup
        cl (str): Cluster for newly created setup
        new_setup (bool): Flag indicating if there is a need to install a new
            setup
        host_name (str): Name of the Host

    Returns:
        bool: True if prepare host succeeded, otherwise False
    """
    vds = global_helper.get_host_resource_by_name(host_name=host_name)
    assert hl_hosts.deactivate_host_if_up(host=host_name, host_resource=vds)

    if new_setup:
        if not hl_networks.create_basic_setup(
            datacenter=dc, cluster=cl, version=conf.COMP_VERSION,
            cpu=conf.CPU_NAME
        ):
            return False
        if not move_host_new_cl(host=host_name, cl=cl):
            return False

    # Update Host MGMT bridge to be non-VM
    network_helper.call_function_and_wait_for_sn(
        func=ll_networks.update_network, content=network, positive=True,
        network=network, data_center=dc, usages=""
    )

    test_utils.wait_for_tasks(engine=conf.ENGINE, datacenter=dc)
    if not ll_hosts.remove_host(positive=True, host=host_name):
        return False

    return remove_persistence_nets(host_resource=host_resource)


def add_host_new_mgmt(
    host_rsc, network, dc, cl, new_setup, dest_cl, host_name, remove_setup,
    net_setup, mgmt_net
):
    """
    Add Host with new MGMT bridge

    Args:
        host_rsc (VDS instance): Host resource
        network (str): Network name for the MGMT
        dc (str): DC for newly created setup
        cl (str): Cluster for newly created setup
        new_setup (bool): Flag indicating if there is a need to install a new
            setup
        dest_cl (str): Cluster where host should be installed
        host_name (str): Name of the Host
        remove_setup (bool): Remove the setup
        net_setup (dict): Network setup to set on host
        mgmt_net (str): Management network name to set on host

    Returns:
        bool: True if add host succeeded, otherwise False
    """
    if new_setup:
        cluster_obj = ll_clusters.get_cluster_object(cluster_name=cl)
        if not hl_networks.create_and_attach_networks(
            data_center=dc,  clusters=[cl], networks=net_setup
        ):
            return False

        if not ll_networks.update_cluster_network(
            positive=True, cluster=cluster_obj, network=mgmt_net,
                usages=(
                    "{management},{default_route}".format(
                        management=conf.MANAGEMENT_NET_USAGE,
                        default_route=conf.DEFAULT_ROUTE_USAGE
                    )
                )
        ):
            return False

        if not ll_networks.remove_network(
            positive=True, network=network, data_center=dc
        ):
            return False

    if remove_setup:
        if not hl_networks.remove_basic_setup(datacenter=dc, cluster=cl):
            return False

    return ll_hosts.add_host(
        name=host_name, root_password=conf.HOSTS_PW,
        cluster=dest_cl, address=host_rsc.fqdn, comment=host_rsc.ip
    )


def move_host_new_cl(host, cl, positive=True, activate_host=False):
    """
    Move Host to new Cluster

    Args:
        host (str): Host name to move
        cl (str): Destination Cluster
        positive (bool): Flag if an action of moving host should succeed
        activate_host (bool): Flag if host should be activated

    Returns:
        bool: True if host move was successful, otherwise False
    """
    if not ll_hosts.update_host(positive=positive, host=host, cluster=cl):
        return False

    if activate_host:
        if not ll_hosts.activate_host(True, host=host):
            return False

    return True


def remove_persistence_nets(host_resource):
    """
    Remove networks from persistence files

    Args:
        host_resource (VDS instance): Host resource

    Returns:
        bool: True if persistence networks were removed, otherwise False
    """
    for location in ("lib/vdsm/persistence", "lib/vdsm/staging"):
        if host_resource.executor().run_cmd(
            ["rm", "-rf", "/".join(["/var", location, "netconf/nets/*"])]
        )[0]:
            return False
    return True
