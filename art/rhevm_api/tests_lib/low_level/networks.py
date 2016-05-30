#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

import logging
import os
import re
import art.rhevm_api.tests_lib.low_level as ll
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
from art.core_api import apis_exceptions
from art.core_api import apis_utils
from art.rhevm_api.utils import test_utils

NET_API = test_utils.get_api("network", "networks")
CL_API = test_utils.get_api("cluster", "clusters")
DC_API = test_utils.get_api("data_center", "datacenters")
VNIC_PROFILE_API = test_utils.get_api('vnic_profile', 'vnicprofiles')
LABEL_API = test_utils.get_api('label', 'labels')
HOST_NICS_API = test_utils.get_api('host_nic', 'host_nics')
PROC_NET_DIR = "/proc/net"
NETWORK_NAME = "NET"
ETHTOOL_OFFLOAD = ("tcp-segmentation-offload", "udp-fragmentation-offload")
ETHTOOL_CMD = "ethtool"

logger = logging.getLogger('networks')


def _prepareNetworkObject(**kwargs):
    """
    preparing logical network object
    Author: edolinin, atal
    return: logical network data structure object
    """
    net = apis_utils.data_st.Network()

    if 'name' in kwargs:
        net.set_name(kwargs.get('name'))

    if 'description' in kwargs:
        net.set_description(kwargs.get('description'))

    if 'stp' in kwargs:
        net.set_stp(kwargs.get('stp'))

    if 'data_center' in kwargs:
        dc = kwargs.get('data_center')
        net.set_data_center(DC_API.find(dc))

    ip = {}
    for k in ['address', 'netmask', 'gateway']:
        if k in kwargs:
            ip[k] = kwargs.get(k)
    ip and net.set_ip(apis_utils.data_st.IP(**ip))

    if 'vlan_id' in kwargs:
        net.set_vlan(apis_utils.data_st.VLAN(id=kwargs.get('vlan_id')))

    if 'usages' in kwargs:
        usages = kwargs.get('usages')
        if usages:
            net.set_usages(apis_utils.data_st.Usages(usage=usages.split(',')))
        else:
            net.set_usages(apis_utils.data_st.Usages())

    if 'mtu' in kwargs:
        net.set_mtu(kwargs.get('mtu'))

    if 'profile_required' in kwargs:
        net.set_profile_required(kwargs.get('profile_required'))

    if 'qos_dict' in kwargs:
        qos_obj = prepare_qos_on_net(kwargs.get("qos_dict"))
        net.set_qos(qos_obj)
    return net


def add_network(positive, **kwargs):
    """
    Add network to a data center

    __author__: 'edolinin'

    Args:
        positive (bool): True if action should succeed, False otherwise.
        kwargs (dict): Parameters for add network.

    Keyword Arguments:
        name (str): Name of a new network.
        description (str): New network description (if relevant).
        data_center (str): Data center name where a new network should be added
        address (str): Network ip address.
        netmask (str): Network ip netmask.
        gateway (str): Network ip gateway.
        stp (str): Support stp true/false (note: true/false as a strings).
        vlan_id (int): Network vlan_id.
        usages (str): Comma separated usages for example 'VM,DISPLAY'.
        mtu (int): Integer to overrule mtu on the related host nic.
        profile_required (bool): Flag to create or not VNIC profile
            for the network.

    Returns:
        bool: True if create network succeeded, False otherwise.
    """
    net_name = kwargs.get("name")
    datacenter = kwargs.get("data_center")
    log_info, log_error = ll.general.get_log_msg(
        action="Create", obj_type="network", obj_name=net_name,
        positive=positive, extra_txt="in datacenter %s" % datacenter, **kwargs
    )
    logger.info(log_info)
    net_obj = _prepareNetworkObject(**kwargs)
    status = NET_API.create(entity=net_obj, positive=positive)[1]
    if not status:
        logger.error(log_error)
    return status


def updateNetwork(positive, network, **kwargs):
    """
    Update network

    Args:
        positive (bool): True if test is positive, False if negative
        network (str): Name of a network that should be updated
        kwargs (dict): Parameters for update network

    Keyword arguments:
        name: New network name. (str)
        data_center: In case more than one network with the same name
            exists.
        address (str): Network ip address.
        netmask (str): Network ip netmask.
        gateway (str): Network ip gateway.
        description (str): New network description.
        stp (str): New network support stp.
        vlan_id (str): New network vlan id.
        usages (str): Comma separated usages for example 'VM,DISPLAY'.
        mtu (int): Integer to overrule mtu on the related host nic.

    Returns:
        bool: True if network was updated properly, False otherwise
    """
    net = find_network(network, kwargs.get("data_center"))
    log_info_txt, log_error_txt = ll.general.get_log_msg(
        action="Update", obj_type="network", obj_name=network,
        positive=positive, **kwargs
    )
    logger.info(log_info_txt)
    net_update = _prepareNetworkObject(**kwargs)
    status = NET_API.update(net, net_update, positive)[1]
    if not status:
        logger.error(log_error_txt)
        return False
    return True


def removeNetwork(positive, network, data_center=None):
    """
    Remove network

    Args:
        positive (bool): Expected result
        network (str): Name of a network that should be removed
        data_center (str): Datacenter name (in case more then one network with
            the same name exists)

    Returns:
        bool: True if network was removed properly, False otherwise
    """
    log_info, log_error = ll.general.get_log_msg(
        action="Remove", obj_type="network", obj_name=network,
        positive=positive
    )
    logger.info(log_info)
    net = find_network(network, data_center)
    res = NET_API.delete(net, positive)
    if not res:
        logger.error(log_error)
    return res


def find_network(network, data_center=None, cluster=None):
    """
    Find desired network using cluster or data center as an option to narrow
    down the search when multiple networks with the same name exist
    (needed due to BZ#741111). The network is retrieved at the data center
    level unless only the network name is passed, in which case a search is
    done among all the networks in the environment.

     __author__: 'atal, tgeft'

     Args:
         network (str): Name of the network to find.
         cluster (str): Name of the cluster in which the network is located.
         data_center (str): Name of the data center in which the network is
            located.

    Returns:
        Network: Network object if found

    Raises:
        EntityNotFound: If network was not found
    """
    logger.info("Find desired network %s", network)
    if data_center:
        dc_obj = DC_API.find(data_center)
        nets = NET_API.get(absLink=False)
        for net in nets:
            if (
                net.get_data_center().get_id() == dc_obj.get_id() and
                net.get_name().lower() == network.lower()
            ):
                return net
        raise apis_exceptions.EntityNotFound(
            '%s network does not exists!' % network
        )
    elif cluster:
        return get_dc_network_by_cluster(cluster=cluster, network=network)
    else:
        return NET_API.find(network)


def _prepareClusterNetworkObj(**kwargs):
    """
    preparing cluster network object
    Author: edolinin, atal
    return: logical network data structure object for cluster
    """
    net = kwargs.get('net', apis_utils.data_st.Network())

    if kwargs.get('usages', None) is not None:
        net.set_usages(apis_utils.data_st.Usages(
            usage=kwargs.get('usages').split(','))
        )

    if 'required' in kwargs:
        net.set_required(str(kwargs.get('required')).lower())

    if 'display' in kwargs:
        net.set_display(kwargs.get('display'))

    return net


def get_cluster_network(cluster, network):
    """
    Find a network by cluster (along with the network properties that are
    specific to the cluster).

    Args:
        cluster (str): Name of the cluster in which the network is located.
        network (str): Name of the network.

    Returns:
        Network: Network object if found

    Raises:
        EntityNotFound: If network was not found
    """
    logger.info("Get cluster %s network %s", cluster, network)
    cluster_obj = CL_API.find(cluster)
    return CL_API.getElemFromElemColl(
        cluster_obj, network, "networks", "network"
    )


def get_cluster_networks(cluster, href=True):
    """
    Get href of the cluster networks or the networks objects

    :param cluster: Name of the cluster.
    :type cluster: str
    :param href: Get cluster networks href if True
    :type href: bool
    :return: Href that links to the cluster networks or list of networks
    :rtype: str or list
    """
    cluster_obj = CL_API.find(cluster)
    logger.info("Get all networks from %s", cluster)
    return CL_API.getElemFromLink(
        cluster_obj, link_name='networks', attr='network', get_href=href
    )


def add_network_to_cluster(positive, network, cluster, **kwargs):
    """
    Attach network to cluster

    __author__: 'atal'

    Args:
        positive (bool): True if test is positive, False if negative.
        network (str): Name of a network that should be add to cluster.
        cluster (str): Cluster name.
        kwargs (dict): Parameters for add network to cluster.

    Keyword Arguments:
        required (bool): Flag if network should be required by cluster.
        usages (str): Comma separated usages for example 'VM,DISPLAY'.
        display (bool): Flag if network should display network.

    Returns:
        bool: True if network was attached properly, False otherwise
    """

    kwargs.update(net=find_network(network, kwargs.get("data_center")))
    log_info_txt, log_error_txt = ll.general.get_log_msg(
        action="Add", obj_type="network", obj_name=network,
        positive=positive, extra_txt="in cluster %s" % cluster, **kwargs
    )
    net = _prepareClusterNetworkObj(**kwargs)
    cluster_nets = get_cluster_networks(cluster=cluster)
    logger.info(log_info_txt)
    status = NET_API.create(
        entity=net, positive=positive, collection=cluster_nets
    )[1]
    if not status:
        logger.error(log_error_txt)
    return status


def update_cluster_network(positive, cluster, network, **kwargs):
    """
    Update network on cluster

    Args:
        positive (bool): Expected results
        cluster (str): Cluster name
        network (str): Network name

    Keyword Arguments:
        required (bool): Set network as required
        usages (str): usages separated by commas 'VM,DISPLAY'. should
            contain all usages every update

    Returns:
        bool: True if network was attached properly, False otherwise
    """

    log_info, log_error = ll.general.get_log_msg(
        action="Update", obj_type="network", obj_name=network,
        positive=positive, extra_txt="on cluster %s" % cluster, **kwargs
    )
    net = get_cluster_network(cluster, network)
    logger.info(log_info)
    net_update = _prepareClusterNetworkObj(**kwargs)
    status = NET_API.update(net, net_update, positive)[1]
    if not status:
        logger.error(log_error)
    return status


def remove_network_from_cluster(positive, network, cluster):
    """
    Remove network from cluster

    __author__: 'edolinin', 'atal'
    Args:
        positive (bool): Expected results
        network (str): Network name
        cluster (str): Cluster name

    Returns:
        bool: True if remove network succeeded, False otherwise.
    """

    log_info, log_error = ll.general.get_log_msg(
        action="Remove", obj_type="network", obj_name=network,
        positive=positive, extra_txt="from cluster %s" % cluster
    )
    net_obj = get_cluster_network(cluster=cluster, network=network)
    logger.info(log_info)
    status = NET_API.delete(net_obj, positive)
    if not status:
        log_error(log_error)
    return status


def is_network_required(network, cluster):
    """
    Check if Network is required

    Args:
        network (str): Network name
        cluster (str): cluster name

    Returns:
        bool: True if network is required, False otherwise.
    """
    logger.info("Check if network %s is required", network)
    net_obj = get_cluster_network(cluster, network)
    res = net_obj.get_required()
    if not res:
        logger.error("Network %s is not required", network)
    return res


def check_ip_rule(vds_resource, subnet):
    """
    Check occurence of specific ip in 'ip rule' command output

    :param vds_resource: VDS resource object
    :type vds_resource: resources.VDS
    :param subnet: subnet to search for
    :type subnet: str
    :return: True/False
    :rtype: bool
    """
    rc, out, _ = vds_resource.run_command(["ip", "rule"])
    logger.info("The output of ip rule command is:\n %s", out)
    if rc:
        return False
    return len(re.findall(subnet.replace('.', '[.]'), out)) == 2


def update_vnic_profile(name, network, **kwargs):
    """
    Description: Update VNIC profile with provided parameters in kwargs

    :param name: Name of vnic profile
    :type name: str
    :param network: Network name used by profile to be updated
    :type network: str
    :param kwargs: kwargs for vnic profile
        :param cluster: Name of cluster in which the network is located
        :type cluster: str
        :param data_center: Name of the data center in which the network is
        located
        :type data_center: str
        :param port_mirroring: Enable or disable port mirroring for profile
        :type port_mirroring: bool
        :param custom_properties: Custom properties for the profile
        :type custom_properties: str
        :param description: Description of vnic profile
        :type description: str
        :param pass_through: Enable or disable pass through mode
        :type pass_through: bool
    :return: True, if adding vnic profile was success, otherwise False
    """
    log_info, log_error = ll.general.get_log_msg(
        action="update", obj_type="vNIC profile", obj_name=name, **kwargs
    )
    kwargs["name"] = name
    cluster = kwargs.get("cluster")
    data_center = kwargs.get("data_center")
    vnic_profile_obj = getVnicProfileFromNetwork(
        network=network, vnic_profile=name, cluster=cluster,
        data_center=data_center
    )
    if not vnic_profile_obj:
        return False

    new_vnic_profile_obj = _prepare_vnic_profile_object(kwargs=kwargs)

    logger.info(log_info)
    if not VNIC_PROFILE_API.update(
        vnic_profile_obj, new_vnic_profile_obj, True
    )[1]:
        logger.error(log_error)
        return False
    return True


def get_network_vnic_profiles(network, cluster=None, data_center=None):
    """
    Get all the VNIC profiles that belong to a certain network

    Args:
        network (str): Name of the network.
        cluster (str): Name of the cluster in which the network is located.
        data_center (str): Name of the data center in which the network is
            located.

    Returns:
        list: List of VNIC profile objects that belong to the provided network
    """
    network_object = find_network(
        network=network, data_center=data_center, cluster=cluster
    )
    logger.info("Get all vNICs profiles for network %s", network)
    return NET_API.getElemFromLink(
        network_object, link_name='vnicprofiles', attr='vnic_profile',
        get_href=False
    )


def get_vnic_profile_obj(name, network, cluster=None, data_center=None):
    """
    Get VNIC profile object.

    Args:
        name (str): Name of the VNIC profile to find.
        network (str): Name of the network used by the VNIC profile.
        cluster (str): Name of the cluster in which the network is located.
        data_center (str): Name of the data center in which the network is
            located.

    Returns:
        VnicProfile: Returns the VNIC profile object if it's found

    Raises:
        EntityNotFound: if vNIC profile object not found
    """
    logger.info("Get vNIC profile %s object", name)
    matching_profiles = filter(
        lambda profile: profile.get_name() == name, get_network_vnic_profiles(
            network, cluster, data_center
        )
    )
    if matching_profiles:
        return matching_profiles[0]
    else:
        raise apis_exceptions.EntityNotFound(
            'VNIC profile %s was not found among the profiles of network %s' %
            (name, network)
        )


def get_vnic_profile_attr(
    name, network, cluster=None, data_center=None, attr_list=list()
):
    """
    Finds the VNIC profile object.

    Args:
        name (str): Name of the VNIC profile to find.
        network (str: )Name of the network used by the VNIC profile.
        cluster (str): Name of the cluster in which the network is located.
        data_center (str): Name of the data center in which the network is
            located.
        attr_list (list): attributes of VNIC profile to get:
            port_mirroring
            description
            id
            custom_properties
            network_obj
            name

    Returns:
        dict: Returns the dictionary of VNIC profile attributes
    """
    vnic_profile_obj = get_vnic_profile_obj(
        name=name, network=network, cluster=cluster, data_center=data_center
    )
    logger.info("Get vNIC profile %s attributes", name)
    attr_dict = dict()
    for arg in attr_list:
        if arg == "network_obj":
            arg = "network"
        attr_dict[arg] = getattr(vnic_profile_obj, arg)

    return attr_dict


# noinspection PyUnusedLocal
def add_vnic_profile(positive, name, **kwargs):
    """
    Add new vnic profile to network in cluster with cluster_name

    Args:
        positive (bool): Expected result
        name (str): Name of vnic profile
        kwargs (dict): kwargs for vnic profile

    Keyword Arguments:
        network (str): Network name to be used by created profile
        cluster (str): Name of cluster in which the network is located
        data_center (str): Name of the data center in which the network is
            located
        port_mirroring (bool): Enable or disable port mirroring for profile
        custom_properties (str): Custom properties for the profile
        description (str): Description of vnic profile
        pass_through (bool): Enable or disable pass through mode

    Returns:
        bool: True, if adding vnic profile was success, otherwise False
    """
    log_info_txt, log_error_txt = ll.general.get_log_msg(
        action="Add", obj_type="vNIC profile", obj_name=name,
        positive=positive, **kwargs
    )
    kwargs["name"] = name
    vnic_profile_obj = _prepare_vnic_profile_object(kwargs=kwargs)
    logger.info(log_info_txt)
    if not VNIC_PROFILE_API.create(vnic_profile_obj, positive)[1]:
        logger.error(log_error_txt)
        return False
    return True


def remove_vnic_profile(
    positive, vnic_profile_name, network, cluster=None, data_center=None
):
    """
    Remove vnic profiles with given names

    __author__ = "alukiano"

    Args:
        positive (bool): Expected result for remove vNIC profile
        vnic_profile_name (str): Vnic profile name
        network (str): Network name used by profile
        cluster (str): Name of the cluster the network resides on
        data_center (str):  Name of the data center the network resides on

    Returns:
        bool: True if action succeeded, otherwise False
    """
    log_info_txt, log_error_txt = ll.general.get_log_msg(
        action="Remove", obj_type="vNIC profile", obj_name=vnic_profile_name,
        positive=positive, network=network, cluster=None, data_center=None
    )
    profile_obj = get_vnic_profile_obj(
        vnic_profile_name, network, cluster, data_center
    )
    logger.info(log_info_txt)

    if not VNIC_PROFILE_API.delete(profile_obj, positive):
        logger.error(log_error_txt)
        return False
    return True


def is_vnic_profile_exist(vnic_profile_name):
    """
    Find specific VNIC profile on the setup

    Args:
        vnic_profile_name (str): VNIC profile name

    Returns:
        bool: True if action succeeded, otherwise False
    """
    logger.info(
        "Searching for vNIC profile %s among all the profile on setup",
        vnic_profile_name
    )
    all_profiles = VNIC_PROFILE_API.get(absLink=False)
    for profile in all_profiles:
        if profile.get_name() == vnic_profile_name:
            return True

    logger.error("vNIC profile %s was not found in setup", vnic_profile_name)
    return False


def get_networks_in_datacenter(datacenter):
    """
    Get all networks in datacenter.

    :param datacenter: datacenter name
    :type datacenter: str
    :return: list of all networks
    :rtype: list
    """
    dc = DC_API.find(datacenter)
    logger.info("Get all networks from %s", datacenter)
    return NET_API.getElemFromLink(dc, get_href=False)


def get_network_in_datacenter(network, datacenter):
    """
    Find network under datacenter.

    Args:
        network (str): Network name to find
        datacenter (str): Datacenter name

    Returns:
        Network: Network object if network was found in datacenter
    """
    logger.info("Get network %s from datacenter %s", network, datacenter)
    for net in get_networks_in_datacenter(datacenter=datacenter):
        if net.get_name() == network:
            logger.info("Get %s from %s", network, datacenter)
            return net
    logger.error("Network %s not found on datacenter %s", network, datacenter)
    return None


def create_network_in_datacenter(positive, datacenter, **kwargs):
    """
    Add network to datacenter

    Args:
        positive (bool): True if action should succeed, False otherwise.
        datacenter (str): Datacenter name.
        kwargs (dict): Parameters for add network.

    Keyword Arguments:
        name (str): Network name.
        description (str): New network description (if relevant).
        stp (str): Support stp true/false (note: true/false as a strings).
        vlan_id (int): Network vlan_id.
        usages (str): Comma separated usages 'vm' or "" for non-VM.
        mtu (int): Integer to overrule mtu on the related host nic.
        profile_required (bool): Flag to create or not VNIC profile
            for the network.

    Returns:
        bool: True if create network succeeded, False otherwise.
    """
    net_name = kwargs.get("name")
    log_info_txt, log_error_txt = ll.general.get_log_msg(
        action="Create", obj_type="network", obj_name=net_name,
        positive=positive, extra_txt="in datacenter %s" % datacenter, **kwargs
    )
    dc = DC_API.find(datacenter)
    logger.info(log_info_txt)
    net_obj = _prepareNetworkObject(**kwargs)
    status = NET_API.create(
        entity=net_obj, positive=positive, collection=NET_API.getElemFromLink
        (dc, get_href=True)
    )[1]
    if not status:
        logger.error(log_error_txt)
    return status


def delete_network_in_datacenter(positive, network, datacenter):
    """
    Delete existing network from datacenter

    Args:
        positive (bool): True if action should succeed, False otherwise
        network (str): name of a network that should be removed
        datacenter (str): datacenter where the network should be deleted from

    Returns:
        bool: True if result of action == positive, False otherwise
    """
    log_info, log_error = ll.general.get_log_msg(
        action="Delete", obj_type="network", obj_name=network,
        positive=positive, extra_txt="in datacenter %s" % datacenter
    )
    net_to_remove = get_network_in_datacenter(
        network=network, datacenter=datacenter
    )
    if net_to_remove:
        logger.info(log_info)
        res = NET_API.delete(net_to_remove, positive)
        if not res:
            logger.error(log_error)
        return res
    return False


def update_network_in_datacenter(positive, network, datacenter, **kwargs):
    """
    Update existing network in datacenter

    Args:
        positive (bool): True if action should succeed, False otherwise
        network(str): name of a network that should be updated
        datacenter (str): datacenter name where the network should be updated
        kwargs (dict): Network oarams

    Keyword Args:
        description (str): new network description (if relevant)
        stp (str): new network support stp (if relevant). (true/false string)
        vlan_id (int): new network vlan id (if relevant)
        usages (str): a string contain list of comma-separated usages 'vm'
            or "" for Non-VM. should contain all usages every update. a
            missing usage will be deleted!
        mtu (int): and integer to overrule mtu on the related host nic.

    Returns:
        bool: True if result of action == positive, False otherwise
    """
    log_info, log_error = ll.general.get_log_msg(
        action="Update", obj_type="network", obj_name=network,
        positive=positive, extra_txt="in datacenter %s" % datacenter, **kwargs
    )
    logger.info(log_info)
    net = get_network_in_datacenter(
        network=network, datacenter=datacenter
    )
    net_update = _prepareNetworkObject(**kwargs)
    res = NET_API.update(net, net_update, positive)
    if not res:
        logger.error(log_error)
    return res


def is_host_network_is_vm(vds_resource, net_name):
    """
    Check if network that resides on Host is VM or non-VM

    :param vds_resource: VDS resource object
    :type vds_resource: resources.VDS
    :param net_name: name of the network we test for being bridged
    :type net_name: str
    :return: True if net_name is VM, False otherwise
    :rtype: bool
    """
    vm_file = os.path.join(test_utils.SYS_CLASS_NET_DIR, net_name)
    logger.info("Check if network %s is VM network on host %s", vm_file,
                vds_resource.fqdn)
    res = vds_resource.fs.exists(path=vm_file)
    if not res:
        logger.error(
            "Network %s is not VM network on host %s",
            net_name, vds_resource.fqdn
        )
    return res


def is_vlan_on_host_network(vds_resource, interface, vlan):
    """
    Check for VLAN value on the network that resides on Host
    :param vds_resource: VDS resource object
    :type vds_resource: resources.VDS
    :param interface: Name of the phy interface
    :type interface: str
    :param vlan: The value to check on the host (str)
    :type vlan: str
    :return: True if VLAN on the host == provided VLAN, False otherwise
    :rtype: bool
    """
    vid = None
    vlan_file = os.path.join(
        PROC_NET_DIR, "vlan", ".".join([interface, str(vlan)])
    )
    rc, out, _ = vds_resource.run_command(["cat", vlan_file])
    if rc:
        return False
    logger.info(
        "Check if %s is tagged with vlan %s on %s",
        interface, vlan, vds_resource.fqdn
    )
    match_obj = re.search("VID: ([0-9]+)", out)
    if match_obj:
        vid = match_obj.group(1)
    res = vid == vlan
    if not res:
        logger.error(
            "%s is not tagged with vlan %s on %s",
            interface, vlan, vds_resource.fqdn
        )
    return res


def create_networks_in_datacenter(datacenter, num_of_net, prefix):
    """
    Create number of networks under datacenter.
    :param datacenter: datacenter name
    :type datacenter: str
    :param num_of_net: number of networks to create
    :type num_of_net: int
    :param prefix: Prefix for network name
    :type prefix: str
    :return: list of networks that created under datacenter
    :rtype: list
    """
    dc_net_list = list()
    for num in range(num_of_net):
        net_name = "_".join([prefix, str(num)])
        dc_net_list.append(net_name)
        if not create_network_in_datacenter(
            positive=True, datacenter=datacenter, name=net_name
        ):
            logger.error(
                'Failed to create %s net after successfully creation of %s',
                net_name, dc_net_list
            )
            return list()
    return dc_net_list


def delete_networks_in_datacenter(datacenter, mgmt_net, networks=list()):
    """
    Delete all networks under datacenter except mgmt_net.

    Args:
        datacenter (str): datacenter name
        mgmt_net (str): management network
        networks (list): List of networks to remove

    Returns:
        bool: True/False
    """
    dc_networks = (
        get_networks_in_datacenter(datacenter) if not networks else
        [get_network_in_datacenter(i, datacenter) for i in networks]
    )
    for net in dc_networks:
        net_name = net.get_name()
        if net_name == mgmt_net:
            continue
        if not delete_network_in_datacenter(
            positive=True, network=net_name, datacenter=datacenter
        ):
            return False
    return True


def getVnicProfileFromNetwork(
    network, vnic_profile, cluster=None, data_center=None
):
    """
    Returns the VNIC profile object that belong to a certain network.

    :param network:Name of the network
    :type network: str
    :param vnic_profile: VNIC profile name
    :type vnic_profile: str
    :param cluster: Name of the cluster in which the network is located
    :type cluster: str
    :param data_center: Name of the data center in which the network resides
    :type data_center: str
    :return: VNIC profile object that belong to the provided network or None
    :rtype: VnicProfile
    """
    network_obj = find_network(network, data_center, cluster).id
    all_vnic_profiles = VNIC_PROFILE_API.get(absLink=False)
    logger.info("Get vNIC profile object from %s", network)
    for vnic_profile_obj in all_vnic_profiles:
        if vnic_profile_obj.name == vnic_profile:
            if vnic_profile_obj.get_network().id == network_obj:
                return vnic_profile_obj
    logger.error("Failed to get VNIC profile object from %s", network)
    return None


def check_network_on_nic(network, host, nic):
    """
    Checks if network resides on Host NIC

    Args:
        network (str): Network name to check
        host (str): Host name
        nic (str): NIC name on Host

    Returns:
        bool: True if network resides on Host NIC, otherwise False
    """
    logger.info("Check if network %s is resides on NIC %s", network, nic)
    try:
        nic_obj = ll.hosts.get_host_nic(host, nic).get_network()
        net_obj_id = NET_API.find(network).get_id()
    except (apis_exceptions.EntityNotFound, AttributeError) as e:
        logger.error(e)
        return False
    if nic_obj is not None:
        return nic_obj.get_id() == net_obj_id
    logger.error("Network %s doesn't exist on NIC %s", network, nic)
    return False


def create_label(label):
    """
    Description: Create label object with provided id
    Author: gcheresh
    Parameters:
        *  *label* - label id to create label object
    **Return**: label object with provided id
    """
    label_obj = apis_utils.data_st.Label()
    label_obj.set_id(label)
    return label_obj


def add_label(**kwargs):
    """
    Add network label to the network in the list provided or to
    the NIC on the host for a dictionary of host: [nics] items
    Example: add_label(networks=['vlan0'], host_nic_dict={
            'silver-vdsb.qa.lab.tlv.redhat.com': ['eth3']}, label='vl1')
    Author: gcheresh

    :param kwargs: Label params
        :label: label to be added to network or NIC on the Host:
        if string is provided will create a new label, otherwise expect
        already existed Label object (str)
        :networks: list of networks with labels (list)
        :host_nic_dict: dictionary with hosts as keys and a list of host
        interfaces as a value for that key (dict)
        :datacenter: for network parameter datacenter that networks
        resides on (str)
        :cluster: for cluster parameter cluster that the network
        resides on (str)
    :type kwargs: dict
    :return: status (True if label was added properly, False otherwise)
    :rtype: bool
    """
    datacenter = kwargs.get("datacenter")
    cluster = kwargs.get("cluster")
    networks = kwargs.get("networks")
    host_nic_dict = kwargs.get("host_nic_dict")
    label = kwargs.get("label")
    status = True
    if isinstance(label, basestring):
        label_obj = create_label(label)
    else:
        label_obj = label
    try:
        if networks:
            for network in networks:
                entity_obj = find_network(
                    network, data_center=datacenter, cluster=cluster
                )
                labels_href = NET_API.getElemFromLink(
                    entity_obj, "labels", "label", get_href=True
                )
                logger.info(
                    "Add label %s to network %s", label_obj.id, network
                )
                if not LABEL_API.create(
                    entity=label_obj, positive=True, collection=labels_href,
                    coll_elm_name="label"
                )[1]:
                    logger.error(
                        "Can't add label %s to the network %s", label_obj.id,
                        network
                    )
                    status = False
        if host_nic_dict:
            for host in host_nic_dict:
                for nic in host_nic_dict.get(host):
                    entity_obj = ll.hosts.get_host_nic(host=host, nic=nic)
                    labels_href = HOST_NICS_API.getElemFromLink(
                        entity_obj, "labels", "label", get_href=True
                    )
                    logger.info(
                        "Add label %s to the NIC %s on Host %s",
                        label_obj.id, nic, host
                    )
                    if not LABEL_API.create(
                        entity=label_obj, positive=True,
                        collection=labels_href, coll_elm_name="label"
                    )[1]:
                        logger.error(
                            "Can't add label %s to the NIC %s on Host %s",
                            label_obj.id, nic, host
                        )
                        status = False

    except apis_exceptions.EntityNotFound as e:
        logger.error(e)
        return False

    return status


def get_label_objects(**kwargs):
    """
    Get network labels from given networks list and given list NICs of any
    number of Hosts.

    __author__: 'gcheresh'

    Args:
        kwargs (dict): Parameters to get label objects.

    Keyword Arguments:
        networks (list): List of networks with labels.
        host_nic_dict (dict): Dictionary with hosts as keys and a list of host
            interfaces as a value for that key.
        datacenter (str): For network parameter datacenter that networks
            resides on.
        cluster (str): For cluster parameter cluster that the network resides
            on.

    Examples:
        get_label_objects(
            host_nic_dict={
                'silver-vdsa.qa.lab.tlv.redhat.com':[eth3', 'eth2']
            },
            networks=['net1', 'net2']
        )

    Returns:
        list: List of labels objects.
            It will return the list of network labels objects for networks and
            host_nic_dict provided.
    """
    label_list = []
    networks = kwargs.get("networks")
    host_nic_dict = kwargs.get("host_nic_dict")
    logger.info("Get label objects with kwargs %s", kwargs)
    try:
        if host_nic_dict:
            for host in host_nic_dict:
                for nic in host_nic_dict.get(host):
                    entity_obj = ll.hosts.get_host_nic(host=host, nic=nic)
                    label_obj = HOST_NICS_API.getElemFromLink(
                        entity_obj, "labels", "label"
                    )
                    label_list.extend(label_obj)
        if networks:
            for network in networks:
                entity_obj = find_network(
                    network,  data_center=kwargs.get("datacenter"),
                    cluster=kwargs.get("cluster")
                )
                label_obj = NET_API.getElemFromLink(
                    entity_obj, "labels", "label"
                )
                label_list.extend(label_obj)

        if not networks and not host_nic_dict:
            raise apis_exceptions.EntityNotFound("No correct key was provided")
    except apis_exceptions.EntityNotFound as e:
        logger.error(e)
        raise

    if not label_list:
        logger.error("Label objects doesn't exists")
    return label_list


def remove_label(**kwargs):
    """
    Remove network labels from given network and Host NIC dictionary
    Example usage:
    remove_label(
        host_nic_dict={
            'silver-vdsb.qa.lab.tlv.redhat.com': ['eth2']
            },
            networks=['net1', 'vlan0'],
            labels=['net1', 'net2']
            )
    Author: gcheresh
    :param kwargs: Host NIC dict with labels params to remove

       :labels: list of label names if specific labels should be removed (list)
       :networks: list of networks with labels (list)
       :host_nic_dict: dictionary with hosts as keys and a list of host
       interfaces as a value for that key (dict)
       :datacenter: for network parameter datacenter that networks resides
       on (str)
       :cluster: for cluster parameter cluster that the network resides on
        (str)
    :return: status (True if labels were properly removed, False otherwise)
    :rtype: bool
    """
    labels_obj = get_label_objects(**kwargs)
    status = True
    if "labels" in kwargs:
        labels = kwargs.get("labels")
        remove_obj_list = []
        for obj in labels_obj:
            if obj.id in labels:
                remove_obj_list.append(obj)
        labels_obj = remove_obj_list

    for obj in labels_obj:
        logger.info("Remove label %s", obj.id)
        if not LABEL_API.delete(obj, True):
            logger.error("Fail to remove label %s", obj.id)
            status = False
    return status


def check_bridge_opts(vds_resource, bridge_name, opts, value):
    """
    Checks the bridge_opts of specific network bridge

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param bridge_name: name of the bridge with specific opts
    :type bridge_name: str
    :param opts: opts name to check
    :type opts: str
    :param value: value of opts to compare to
    :type value: str
    :return: True if the value for bridge_opts is equal to the value
             provided, False otherwise
    :rtype: bool
    """
    bridge_file = os.path.join(
        test_utils.SYS_CLASS_NET_DIR, bridge_name, 'bridge', opts
    )
    rc, out, _ = vds_resource.run_command(["cat", bridge_file])
    if rc:
        return False
    return out.strip() == value


def check_bond_mode(vds_resource, interface, mode):
    """
    Check BOND mode on BOND interface

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param interface:name of the BOND interface
    :type interface: str
    :param mode: The BOND mode
    :type mode: int
    :return: True if correct BOND mode was found, False otherwise
    :rtype: bool
    """
    mode_file = os.path.join(
        test_utils.SYS_CLASS_NET_DIR, interface, "bonding/mode"
    )
    rc, out, _ = vds_resource.run_command(["cat", mode_file])
    if rc:
        return False
    bond_mode = out.split()[1]
    return bond_mode == str(mode)


def check_ethtool_opts(vds_resource, nic, opts, value):
    """
    Checks the ethtool_opts of specific network interface

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param nic: NIC name with specific ethtool opts configured
    :type nic: str
    :param opts: ethtool_opts name to check
    :type opts: str
    :param value: value of ethtool_opts to compare to
    :type value: str
    :return: True if the value for ethtool_opts is equal to the value
             provided, False otherwise
    :rtype: bool
    """
    cmd = []
    if opts in ("tx-checksumming", "rx-checksumming"):
        cmd = [ETHTOOL_CMD, "-k", nic]
    else:
        logger.error("Not implemented for opts %s" % opts)
        return False
    rc, out, _ = vds_resource.run_command(cmd)
    if rc:
        return False
    for line in out.splitlines():
        if opts in line:
            return line.split(":")[1].lstrip() == value
    return False


def check_bridge_file_exist(vds_resource, bridge_name):
    """
    Checks if the bridge file exists for specific network

    :param vds_resource: VDS resource
    :type vds_resource: resources.VDS
    :param bridge_name: name of the bridge file to check if exists
    :type bridge_name: str
    :return: True if the bridge_name file exists, False otherwise
    :rtype: bool
    """
    bridge_file = os.path.join(
        test_utils.SYS_CLASS_NET_DIR, bridge_name, 'bridge'
    )
    return vds_resource.fs.exists(bridge_file)


def create_properties(**kwargs):
    """
    Creates Properties object that contains list of different property objects
    **Author**: gcheresh
        **Parameters**:
        *  *kwargs* - dictionary of (network customer property: value)
        elements
    **Return**: Properties object
    """
    properties_obj = apis_utils.data_st.Properties()
    for key, val in kwargs.iteritems():
        if kwargs.get("bridge_opts") or kwargs.get("ethtool_opts"):
            property_obj = apis_utils.data_st.Property(name=key, value=val)
            properties_obj.add_property(property_obj)
    return properties_obj


def get_dc_network_by_cluster(cluster, network):
    """
    Find network on cluster and return the DC network object

    Args:
        cluster (str): Name of the cluster in which the network is located.
        network (str): Name of the network.

    Returns:
        Network: DC network object if network found, None otherwise
    """
    logger.info("Find network %s on cluster %s", cluster, network)
    cluster_obj = CL_API.find(cluster)
    cluster_net = get_cluster_network(cluster=cluster, network=network)
    dc_id = cluster_obj.get_data_center().get_id()
    dc_name = DC_API.find(dc_id, attribute='id').get_name()
    dc_net = get_network_in_datacenter(network=network, datacenter=dc_name)
    if dc_net.get_id() == cluster_net.get_id():
        return dc_net
    logger.error("Network %s not found on cluster %s", network, cluster)
    return None


def update_qos_on_vnic_profile(datacenter, qos_name, vnic_profile_name,
                               network_name, cluster=None):
    """
    Update QoS to vNIC profile.
    Every vNIC profile has default QoS (Unlimited) so only update functions
    is needed (No add_qos functions)
    :param datacenter: Datacenter name
    :param qos_name: QoS name to update
    :param vnic_profile_name: vNIC profile name
    :param network_name: Network name
    :param cluster: Cluster name
    :return: True/False
    """
    qos = ll_datacenters.get_qos_from_datacenter(
        datacenter=datacenter, qos_name=qos_name
    )
    return update_vnic_profile(
        name=vnic_profile_name, network=network_name, cluster=cluster,
        data_center=datacenter, qos=qos
    )


def get_vnic_profile_objects():
    """
    Get all vnic profiles objects from engine
    :return: List of vnic objects
    :rtype: list
    """
    return VNIC_PROFILE_API.get(absLink=False)


def get_management_network(cluster_name):
    """
    Find MGMT network besides all networks of specific Cluster

    :param cluster_name: Name of the Cluster
    :type cluster_name: str
    :return: network MGMT
    :rtype: object
    """
    try:
        logger.info("Get management network from %s", cluster_name)
        net_obj = [
            i for i in get_cluster_networks(cluster_name, href=False)
            if "management" in i.get_usages().get_usage()
        ][0]
    except IndexError:
        logger.error("management networks not found in %s", cluster_name)
        return None

    return net_obj


def check_network_usage(cluster_name, network, *attrs):
    """
    Check if usages attributes exist for specific network

    Args:
        cluster_name (str): Name of the Cluster
        network (str): Name of the Network
        attrs (list): list of attributes (display, migration, management)

    Returns:
        bool: If all attributes exist in network params, False otherwise
    """
    net_obj = get_cluster_network(cluster=cluster_name, network=network)
    logger.info("Check if %s are attributes of network %s", attrs, network)
    for attr in attrs:
        if attr not in net_obj.get_usages().get_usage():
            logger.error(
                "Attribute %s is not part of network %s", attr, network
            )
            return False
    return True


def get_host_nic_labels(nic):
    """
    Get host NIC labels

    :param nic: HostNIC object
    :type nic: HostNic
    :return: List of host NIC labels
    :rtype: list
    """
    return ll.hosts.HOST_NICS_API.getElemFromLink(nic, "labels", "label")


def get_host_nic_label_objs_by_id(host_nics, labels_id):
    """
    Get host NIC label objects by label ID

    :param host_nics: Host NICS object list
    :type host_nics: list
    :param labels_id: Label ID
    :type labels_id: list
    :return: List of host NICs objects
    :rtype: list
    """
    label_objs_list = list()
    for nic in host_nics:
        nic_labels = get_host_nic_labels(nic)
        label_objs_list.extend(
            [i for i in nic_labels if i.get_id() in labels_id]
        )
    return label_objs_list


def prepare_qos_on_net(qos_dict):
    """
    Prepare QoS on network

    :param qos_dict: QoS values to add
    :type qos_dict: dict
    :return: Qos object
    :rtype: data_st.QoS()
    """
    # if we want to update qos to be unlimited need to send empty qos_dict,
    # otherwise update network with the QoS, given in the qos_dict
    if not qos_dict:
        qos_obj = apis_utils.data_st.QoS()
    else:
        qos_name = qos_dict.pop("qos_name")
        datacenter = qos_dict.pop("datacenter")
        qos_obj = ll_datacenters.get_qos_from_datacenter(
            datacenter, qos_name
        )
        # if qos_obj is not found on DC, need to create a new QoS object
        if not qos_obj:
            qos_type = qos_dict.pop("qos_type")
            ll_datacenters.add_qos_to_datacenter(
                datacenter=datacenter, qos_name=qos_name,
                qos_type=qos_type, **qos_dict
            )
            qos_obj = ll_datacenters.get_qos_from_datacenter(
                datacenter, qos_name
            )
    return qos_obj


def get_network_on_host_nic(host, nic):
    """
    Get network name from host NIC

    :param host: Host name
    :type host: str
    :param nic: NIC name
    :type nic: str
    :return: Network name
    :rtype: str
    """
    return ll.general.get_object_name_by_id(
        NET_API, ll.hosts.get_host_nic(host, nic).get_network().get_id())


def _prepare_vnic_profile_object(kwargs):
    """
    Prepare vnic profile object for create or update

    :param kwargs: kwargs for vnic profile
        :param name: Name of vnic profile
        :type name: str
        :param network: Network name to be used by profile
        :type network: str
        :param cluster: Name of cluster in which the network is located
        :type cluster: str
        :param data_center: Name of the data center in which the network is
        located
        :type data_center: str
        :param port_mirroring: Enable or disable port mirroring for profile
        :type port_mirroring: bool
        :param custom_properties: Custom properties for the profile
        :type custom_properties: str
        :param description: Description of vnic profile
        :type description: str
        :param pass_through: Enable or disable pass through mode
        :type pass_through: bool
    :return: vnic profile object
    :rtype: VnicProfile
    """
    name = kwargs.get("name")
    port_mirroring = kwargs.get("port_mirroring")
    description = kwargs.get("description")
    network = kwargs.get("network")
    new_network = kwargs.get("new_network")
    qos = kwargs.get("qos")
    custom_properties = kwargs.get("custom_properties")
    pass_through = kwargs.get("pass_through")
    data_center = kwargs.get("data_center")
    cluster = kwargs.get("cluster")

    vnic_profile_obj = apis_utils.data_st.VnicProfile()

    if name:
        vnic_profile_obj.set_name(name)

    if port_mirroring is not None:
        vnic_profile_obj.set_port_mirroring(port_mirroring)

    if description:
        vnic_profile_obj.set_description(description)

    if network:
        net_obj = find_network(
            network=network, data_center=data_center, cluster=cluster
        )
        vnic_profile_obj.set_network(net_obj)

    if new_network:
        new_net_obj = find_network(
            network=new_network, data_center=data_center, cluster=cluster
        )
        vnic_profile_obj.set_network(new_net_obj)

    if qos:
        vnic_profile_obj.set_qos(qos)

    if custom_properties:
        from art.rhevm_api.tests_lib.low_level.vms import(
            createCustomPropertiesFromArg
        )
        vnic_profile_obj.set_custom_properties(
            createCustomPropertiesFromArg(custom_properties)
        )

    if pass_through is not None:
        mode = "enabled" if pass_through else "disabled"
        vp_pass_through = apis_utils.data_st.VnicPassThrough()
        vp_pass_through.set_mode(mode)
        vnic_profile_obj.set_pass_through(vp_pass_through)

    return vnic_profile_obj
