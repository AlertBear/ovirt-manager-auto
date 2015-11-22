#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Utilities used by MGMT network role feature
"""
import logging

import art.core_api.apis_utils as utils
import rhevmtests.networking.helper as net_helper
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import rhevmtests.networking.arbitrary_vlan_device_name.helper as virsh_helper

import config as c
logger = logging.getLogger("MGMT_Net_Role_Helper")


def install_host_new_mgmt(
    host_resource=c.VDS_HOSTS[-1], network=c.MGMT_BRIDGE, dc=c.EXT_DC_0,
    cl=c.EXTRA_CLUSTER_0, dest_cl=c.EXTRA_CLUSTER_0, new_setup=True,
    remove_setup=False
):
    """
    Install host with MGMT network different from the previous one

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param network: Network name for the MGMT
    :type network: str
    :param dc: DC for newly created setup
    :type dc: str
    :param cl: Cluster for newly created setup
    :type cl: str
    :param dest_cl: Cluster where host should be installed
    :type dest_cl: str
    :param new_setup: Flag indicating if there is a need to install a new setup
    :param remove_setup: Flag indicating if there is a need to remove setup
    :type remove_setup: bool
    :type new_setup:bool
    :raises: Network exception
    """

    host_name = ll_hosts.get_host_name_from_engine(host_resource.ip)
    prepare_host_for_installation(
        host_resource=host_resource, network=network,
        dc=dc, cl=cl, new_setup=new_setup, host_name=host_name
    )
    add_host_new_mgmt(
        host_resource=host_resource, network=network, dc=dc, cl=cl,
        new_setup=new_setup, dest_cl=dest_cl, host_name=host_name,
        remove_setup=remove_setup
    )


def prepare_host_for_installation(
    host_resource, network, dc, cl, new_setup, host_name
):
    """
    Prepares host for installation with new MGMT network

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param network: Network name for the MGMT
    :type network: str
    :param dc: DC for newly created setup
    :type dc: str
    :param cl: Cluster for newly created setup
    :type cl: str
    :param new_setup: Flag indicating if there is a need to install a new setup
    :type new_setup:bool
    :param host_name: Name of the Host
    :type host_name: str
    :raises: Network exception
    """
    net_helper.set_libvirt_sasl_status(
        engine_resource=c.ENGINE_HOST, host_resource=host_resource
    )
    deactivate_host(host=host_name)
    if new_setup:
        create_setup(dc=dc, cl=cl)
        move_host_new_cl(host=host_name, cl=cl)
    update_host_mgmt_bridge(
        host_resource=host_resource, network=network,
        dc=dc, nic=host_resource.nics[0]
    )
    remove_host(host=host_name)
    virsh_helper.virsh_delete_bridges(
        host_obj=host_resource, bridges=[network], undefine=True)


def add_host_new_mgmt(
    host_resource, network, dc, cl, new_setup, dest_cl, host_name, remove_setup
):
    """
    Add Host with new MGMT bridge

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param network: Network name for the MGMT
    :type network: str
    :param dc: DC for newly created setup
    :type dc: str
    :param cl: Cluster for newly created setup
    :type cl: str
    :param new_setup: Flag indicating if there is a need to install a new setup
    :type new_setup:bool
    :param dest_cl: Cluster where host should be installed
    :type dest_cl: str
    :param host_name: Name of the Host
    :type host_name: str
    :raises: Network exception
    """
    if new_setup:
        create_net_dc_cluster(dc=dc, cl=cl)
        update_cluster_mgmt(cl=cl)
        if not ll_networks.removeNetwork(
            positive=True, network=network, data_center=dc
        ):
            raise c.NET_EXCEPTION("Failed to remove %s", network)
    if remove_setup:
        remove_dc_cluster(dc=dc, cl=cl)
    remove_persistance_nets(host_resource=host_resource)
    add_host(host_resource=host_resource, host=host_name, cl=dest_cl)
    if not net_helper.set_libvirtd_sasl(host_obj=host_resource):
        raise c.NET_EXCEPTION("Couldn't enable sasl")


def update_host_mgmt_bridge(host_resource, network, dc, nic):
    """
    Update Host MGMT bridge to be non-VM

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param network: Network name for the MGMT
    :type network: str
    :param dc: DC where the network is located
    :type dc: str
    :param nic: NIC with the MGMT network
    :type nic: str
    :raises: Network exception
    """
    host_name = ll_hosts.get_host_name_from_engine(host_resource.ip)
    logger.info("Update network %s to be non-VM network", network)
    if not ll_networks.updateNetwork(
        True, network=network, data_center=dc, usages=""
    ):
        raise c.NET_EXCEPTION(
            "Cannot update network %s to be non-VM" % network
        )

    logger.info("Wait till the Host is updated with the change")
    sample1 = utils.TimeoutingSampler(
        timeout=c.SAMPLER_TIMEOUT,
        sleep=1,
        func=hl_networks.checkHostNicParameters,
        host=host_name,
        nic=nic,
        **{"bridge": False}
    )
    if not sample1.waitForFuncStatus(result=True):
        raise c.NET_EXCEPTION("Network should be non-VM")

    logger.info("Check that the change is reflected to Host %s", host_name)
    if ll_networks.isVmHostNetwork(
        host=host_resource.ip, user=c.HOSTS_USER, password=c.HOSTS_PW,
        net_name=network, conn_timeout=45
    ):
        raise c.NET_EXCEPTION(
            "Network on host %s was not updated to be non-VM" % host_name
        )


def deactivate_host(host):
    """
    Deactivate host

    :param host: Host name
    :type host: str
    :raises: Network exception
    """
    logger.info("Deactivate host %s", host)
    if not ll_hosts.deactivateHost(positive=True, host=host):
        raise c.NET_EXCEPTION("Cannot deactivate host %s" % host)


def remove_host(host):
    """
    Remove host

    :param host: Host name
    :type host: str
    :raises: Network exception
    """
    logger.info("Remove host %s", host)
    if not ll_hosts.removeHost(True, host):
        raise c.NET_EXCEPTION("Failed to remove %s" % host)


def add_host(host_resource, host, cl):
    """
    Add host

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :param host: Host name
    :type host: str
    :param cl: Cluster name
    :type cl: str
    :raises: Network exception
    """
    if not ll_hosts.addHost(
        True, name=host, root_password=c.HOSTS_PW, cluster=cl,
        address=host_resource.ip, comment=host_resource.fqdn
    ):
        raise c.NET_EXCEPTION("Couldn't add %s to %s" % (host_resource.ip, cl))


def create_setup(dc, cl):
    """
    Creates a new DC and Cluster in the setup

    :param dc: DC name
    :type dc: str
    :param cl: Cluster name
    :type cl: str or None
    :raises: Network exception
    """
    logger.info("Create a new DC and cluster")
    if not hl_networks.create_basic_setup(
        datacenter=dc, cluster=cl,
        version=c.COMP_VERSION,
        storage_type=c.STORAGE_TYPE, cpu=c.CPU_NAME
    ):
        raise c.NET_EXCEPTION(
            "Failed to create a new DC/cluster: %s/%s"
        )


def move_host_new_cl(host, cl, positive=True, activate_host=False):
    """
    Move Host to new Cluster

    :param host: Host name to move
    :type host: str
    :param cl: Destination Cluster
    :param positive: Flag if an action of moving host should succeed
    :type positive: bool
    :param activate_host: Flag if host should be activated
    :type activate_host: bool
    :type cl: str
    :raises: Network exception
    """
    log_err = "Cannot" if positive else "Can"
    if not ll_hosts.updateHost(positive=positive, host=host, cluster=cl):
        raise c.NET_EXCEPTION(
            "%s move host %s to Cluster %s" % (log_err, host, cl)
        )
    if activate_host:
        if not ll_hosts.activateHost(True, host=host):
            raise c.NET_EXCEPTION("Cannot activate host %s" % host)


def create_net_dc_cluster(
    dc, cl, net_dict=None
):
    """
    Create and attach network/networks to given DC and Cluster

    :param dc: DC name
    :type dc: str or None
    :param cl: Cluster name
    :type cl: str or None
    :param net_dict: dictionary with networks parameters
    :type net_dict: dict
    :raises: Network exception
    """
    if not net_dict:
        net_dict = {c.net1: {"required": "true"}}

    logger.info(
        "Create and attach network(s) %s to DC and cluster ", net_dict.keys()
    )
    if not hl_networks.createAndAttachNetworkSN(
        data_center=dc, cluster=cl, network_dict=net_dict
    ):
        raise c.NET_EXCEPTION(
            "Cannot create networks %s on DC and cluster" % net_dict.keys()
        )


def update_cluster_mgmt(cl):
    """
    Update cluster with a new MGMT

    :param cl: Cluster name
    :type cl: str
    :raises: Network exception
    """
    logger.info("Update MGMT network to be %s", c.net1)
    if not ll_networks.updateClusterNetwork(
        positive=True, cluster=cl,
        network=c.NETWORKS[0], usages="management"
    ):
        raise c.NET_EXCEPTION(
            "Couldn't update cluster MGMT network to be %s" % c.net1
        )


def remove_dc_cluster(dc=c.EXT_DC_0, cl=c.EXTRA_CLUSTER_0):
    """
    Remove DC and Cluster from setup

    :param dc: DC name
    :type dc: str
    :param cl: Cluster name
    :type cl: str or None
    :raises: Network exception
    """
    logger.info("Removing DC %s and cluster %s", dc, cl)
    if not hl_networks.remove_basic_setup(datacenter=dc, cluster=cl):
        logger.error("Failed to remove DC %s and cluster %s", dc, cl)


def remove_persistance_nets(host_resource):
    """
    Remove networks from persistence files

    :param host_resource: Host resource
    :type host_resource: VDS instance
    :raises: Network exception
    """
    for location in ("lib/vdsm/persistence", "run/vdsm"):
        if host_resource.executor().run_cmd(
            ["rm", "-rf", "/".join(["/var", location, "netconf/nets/*"])]
        )[0]:
            raise c.NET_EXCEPTION(
                "Couldn't remove network from persistent file"
            )


def add_cluster(cl=c.EXTRA_CLUSTER_0, dc=c.ORIG_DC, positive=True, **kwargs):
    """
    Add Cluster to DC

    :param cl: Cluster name
    :type cl: str
    :param dc: DC name
    :type dc: str
    :param positive: Flag if test is positive or negative
    :type positive: bool
    :param kwargs: dict of additional params (for example MGMT network)
    :type kwargs: dict
    :raises: Network exception
    """
    logger.info("Create a new cluster %s", cl)
    if not ll_clusters.addCluster(
        positive=positive, name=cl, cpu=c.CPU_NAME,
        data_center=dc, version=c.COMP_VERSION, **kwargs
    ):
        raise c.NET_EXCEPTION(
            "Failed to create a new cluster %s for DC %s" % (cl, dc)
        )


def update_mgmt_net(net=c.net1, cl=c.EXTRA_CLUSTER_0, positive=True):
    """
    Update MGMT network on Cluster

    :param net: Network name
    :type net: str
    :param cl: Cluster name
    :type cl: str
    :param positive: Flag if test is positive or negative
    :type positive: bool
    :raises: Network exception
    """
    logger.info("Update MGMT network on Cluster %s to be %s", cl, net)
    if not ll_networks.updateClusterNetwork(
        positive=positive, cluster=cl,
        network=net, usages=c.MGMT
    ):
        raise c.NET_EXCEPTION(
            "Couldn't update cluster MGMT network to be %s" % net
        )


def remove_cl(cl=c.EXTRA_CLUSTER_0):
    """
    Remove Cluster from setup

    :param cl: Cluster name
    :type cl: str
    :raises: Network exception
    """
    logger.info("Remove cluster %s", cl)
    if not ll_clusters.removeCluster(positive=True, cluster=cl):
        logger.error("Failed to remove cluster %s", cl)


def check_mgmt_net(net=c.net1, cl=c.EXTRA_CLUSTER_0):
    """
    Check MGMT network on Cluster

    :param net: Network name
    :type net: str
    :param cl: Cluster name
    :type cl: str
    :raises: Network exception
    """
    logger.info("Check that MGMT network on cluster %s is %s", cl, net)
    if not hl_networks.is_management_network(cl, net):
        raise c.NET_EXCEPTION("MGMT Network should be %s, but it's not" % net)


def remove_net(net=c.net1, dc=c.EXT_DC_0, positive=True, teardown=True):
    """
    Remove network from DC

    :param net: Network name
    :type net: str
    :param dc: DC name
    :type dc: str
    :param positive: Flag for removal a network
    :type positive: bool
    :raises: Network exception
    """
    err_msg = "Couldn't remove %s" if positive else "Could remove %s"
    logger.info("Remove network %s", net)
    if not ll_networks.removeNetwork(
        positive=positive, network=net, data_center=dc
    ):
        if teardown:
            logger.error(err_msg, net)
        else:
            raise c.NET_EXCEPTION(err_msg % net)
