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
from art.rhevm_api.tests_lib.low_level import general
from art.core_api import apis_exceptions
from art.core_api import apis_utils
from art.core_api.apis_utils import getDS
from art.rhevm_api.utils import test_utils

NET_API = test_utils.get_api("network", "networks")
CL_API = test_utils.get_api("cluster", "clusters")
DC_API = test_utils.get_api("data_center", "datacenters")
VNIC_PROFILE_API = test_utils.get_api('vnic_profile', 'vnicprofiles')
LABEL_API = test_utils.get_api('network_label', 'network_labels')
HOST_NICS_API = test_utils.get_api('host_nic', 'host_nics')
NF_API = test_utils.get_api("networkfilter", "networkfilters")
OPENSTACK_NETWORK_PROVIDER_API = test_utils.get_api(
    "openstack_network_provider", "openstacknetworkproviders"
)
PROC_NET_DIR = "/proc/net"
ETHTOOL_OFFLOAD = ("tcp-segmentation-offload", "udp-fragmentation-offload")
ETHTOOL_CMD = "ethtool"

logger = logging.getLogger("ll.networks")


@general.generate_logs()
def _prepare_network_object(**kwargs):
    """
    Preparing logical network object

    Keyword Args:
        name (str): Network name
        description (str): Network description
        stp (str): Set STP on network
        data_center (str): Datacenter name for the network
        vlan_id (str): VLAN id for the network
        usages (str): VM or Non-VM network (send "" for Non-VM)
        mtu (str): Network MTU
        profile_required (str): Set if vNIC profile is required
        qos_dict (dict): QoS for the network
        dns (list): List of DNS servers
        external_network_provider_name (str): Name of the external network
            provider to create the network in

    Returns:
        Network: Network object
    """
    net = apis_utils.data_st.Network()
    name = kwargs.get("name")
    description = kwargs.get("description")
    stp = kwargs.get("stp")
    data_center = kwargs.get("data_center")
    vlan_id = kwargs.get("vlan_id")
    usages = kwargs.get("usages")
    mtu = kwargs.get("mtu")
    profile_required = kwargs.get("profile_required")
    qos_dict = kwargs.get("qos_dict")
    dns = kwargs.get("dns")
    external_network_provider_name = kwargs.get("external_provider_name")

    if name:
        net.set_name(name)

    if description:
        net.set_description(description)

    if stp:
        net.set_stp(stp)

    if data_center:
        net.set_data_center(DC_API.find(data_center))

    if "vlan_id" in kwargs:
        net.set_vlan(apis_utils.data_st.Vlan(id=vlan_id))

    if usages is not None:
        if usages:
            net.set_usages(apis_utils.data_st.Usages(usage=usages.split(",")))
        else:
            net.set_usages(apis_utils.data_st.Usages())

    if mtu:
        net.set_mtu(mtu)

    if profile_required:
        net.set_profile_required(profile_required)

    if qos_dict:
        qos_obj = prepare_qos_on_net(qos_dict)
        net.set_qos(qos_obj)

    if dns is not None:
        dns_obj = prepare_network_dns_object(dns_servers=dns)
        net.set_dns_resolver_configuration(dns_obj)

    if external_network_provider_name:
        enp = OPENSTACK_NETWORK_PROVIDER_API.find(
            external_network_provider_name
        )
        net.set_external_provider(external_provider=enp)

    return net


@general.generate_logs(step=True)
def add_network(positive, **kwargs):
    """
    Add network to data center with kwargs

    Args:
        positive (bool): True if action should succeed, False otherwise.
        kwargs (dict): Parameters for add network.

    Keyword Arguments:
        name (str): Network name
        description (str): Network description
        stp (str): Set STP on network
        data_center (str): Datacenter name for the network
        vlan_id (str): VLAN id for the network
        usages (str): VM or Non-VM network (send "" for Non-VM)
        mtu (str): Network MTU
        profile_required (str): Set if vNIC profile is required
        qos_dict (dict): QoS for the network
        dns (list): List of DNS servers
        external_network_provider_name (str): Name of the external network
            provider to create the network in

    Returns:
        bool: True if create network succeeded, False otherwise.
    """
    net_obj = _prepare_network_object(**kwargs)
    return NET_API.create(entity=net_obj, positive=positive)[1]


@general.generate_logs(step=True)
def update_network(positive, network, **kwargs):
    """
    Update network with kwargs

    Args:
        positive (bool): True if test is positive, False if negative
        network (str): Name of a network that should be updated
        kwargs (dict): Parameters for update network

    Keyword arguments:
        name (str): Network name
        description (str): Network description
        stp (str): Set STP on network
        data_center (str): Datacenter name for the network
        vlan_id (str): VLAN id for the network
        usages (str): VM or Non-VM network (send "" for Non-VM)
        mtu (str): Network MTU
        profile_required (str): Set if vNIC profile is required
        qos_dict (dict): QoS for the network
        dns (list): List of DNS servers

    Returns:
        bool: True if network was updated properly, False otherwise
    """
    net = find_network(network=network, data_center=kwargs.get("data_center"))
    net_update = _prepare_network_object(**kwargs)
    return NET_API.update(net, net_update, positive)[1]


@general.generate_logs(step=True)
def remove_network(positive, network, data_center=None):
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
    net = find_network(network, data_center)
    res = NET_API.delete(net, positive)
    return res


@general.generate_logs()
def find_network(network, data_center=None, cluster=None):
    """
    Find desired network using cluster or data center

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
    if cluster:
        from art.rhevm_api.tests_lib.low_level.clusters import (
            get_cluster_object
        )
        cluster_object = get_cluster_object(cluster_name=cluster)
        data_center_id = cluster_object.data_center.id
        data_center_name = general.get_object_name_by_id(
            object_api=DC_API, object_id=data_center_id
        )
        if data_center and data_center_name != data_center:
            return None

        data_center = data_center_name

    if data_center:
        dc_obj = DC_API.find(data_center)
        nets = NET_API.get(abs_link=False)
        for net in nets:
            if (
                net.get_data_center().get_id() == dc_obj.get_id() and
                net.get_name().lower() == network.lower()
            ):
                return net
        raise apis_exceptions.EntityNotFound(
            '%s network does not exists!' % network
        )

    else:
        return NET_API.find(network)


@ll.general.generate_logs()
def _prepare_cluster_network_object(**kwargs):
    """
    Preparing cluster network object

    Keyword Args:
        net (str): Network name to update
        usages (str): VM or Non-VM network (send "" for Non-VM)
        required (str): Set if network is required network
        display (str): Set if network is display network

    Returns:
        Network: Network object
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


@general.generate_logs(error=False)
def get_cluster_network(cluster, network):
    """
    Find a network by cluster (along with the network properties that are
    specific to the cluster).

    Args:
        cluster (Cluster): Cluster object in which the network is located.
        network (str): Name of the network.

    Returns:
        Network: Network object if found

    Raises:
        EntityNotFound: If network was not found
    """
    try:
        return CL_API.getElemFromElemColl(
            cluster, network, "networks", "network"
        )
    except apis_exceptions.EntityNotFound:
        return None


@general.generate_logs()
def get_cluster_networks(cluster, href=True):
    """
    Get href of the cluster networks or the networks objects

    Args:
        cluster (str): Name of the cluster.
        href (bool): Get cluster networks href if True

    Returns:
        str or list: Href that links to the cluster networks or list of
            networks
    """
    cluster_obj = CL_API.find(cluster)
    return CL_API.getElemFromLink(
        cluster_obj, link_name='networks', attr='network', get_href=href
    )


@general.generate_logs()
def add_network_to_cluster(positive, network, cluster, **kwargs):
    """
    Attach network to cluster

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
    net = _prepare_cluster_network_object(**kwargs)
    cluster_nets = get_cluster_networks(cluster=cluster)
    status = NET_API.create(
        entity=net, positive=positive, collection=cluster_nets
    )[1]
    return status


@general.generate_logs(step=True)
def update_cluster_network(positive, cluster, network, **kwargs):
    """
    Update network on cluster

    Args:
        positive (bool): Expected results
        cluster (Cluster): Cluster object
        network (str): Network name

    Keyword Arguments:
        required (bool): Set network as required
        usages (str): usages separated by commas 'VM,DISPLAY'. should
            contain all usages every update

    Returns:
        bool: True if network was attached properly, False otherwise
    """
    net = get_cluster_network(cluster=cluster, network=network)
    net_update = _prepare_cluster_network_object(**kwargs)
    return NET_API.update(net, net_update, positive)[1]


@general.generate_logs()
def remove_network_from_cluster(positive, network, cluster):
    """
    Remove network from cluster

    Args:
        positive (bool): Expected results
        network (str): Network name
        cluster (Cluster): Cluster object

    Returns:
        bool: True if remove network succeeded, False otherwise.
    """
    net_obj = get_cluster_network(cluster=cluster, network=network)
    return NET_API.delete(net_obj, positive)


@general.generate_logs()
def is_network_required(network, cluster):
    """
    Check if Network is required

    Args:
        network (str): Network name
        cluster (Cluster): cluster object

    Returns:
        bool: True if network is required, False otherwise.
    """
    net_obj = get_cluster_network(cluster=cluster, network=network)
    return net_obj.get_required()


@general.generate_logs()
def check_ip_rule(vds_resource, subnet, matches=2):
    """
    Check occurrence of specific ip in 'ip rule' command output

    Args:
        vds_resource (VDS): VDS resource object
        subnet (str): subnet to search for
        matches (int): Number of matches to find in ip rule command

    Returns:
        bool: True if number of matches is >=, False otherwise.
    """
    rc, out, _ = vds_resource.run_command(["ip", "rule"])
    if rc:
        return False
    return len(re.findall(subnet.replace('.', '[.]'), out)) >= matches


@general.generate_logs(step=True)
def update_vnic_profile(name, network, **kwargs):
    """
    Update VNIC profile

    Args:
        name (str): Name of vnic profile
        network (str): Network name used by profile to be updated
        kwargs (dict): kwargs for vnic profile

    Keyword Args:
        cluster (str): Name of cluster in which the network is located
        data_center (str): Name of the data center in which the network is
            located
        port_mirroring (bool): Enable or disable port mirroring for profile
        custom_properties (str): Custom properties for the profile
        description (str): Description of vnic profile
        pass_through (bool): Enable or disable pass through mode
        network_filter (str): Network filter name to use. ('None') to update
            vNIC profile with no network_filter
        migratable (bool): When profile is pass_through allow migration on it

    Returns:
        bool: True, if adding vnic profile was success, otherwise False
    """
    kwargs["name"] = name
    cluster = kwargs.get("cluster")
    data_center = kwargs.get("data_center")
    vnic_profile_obj = get_vnic_profile_from_network(
        network=network, vnic_profile=name, cluster=cluster,
        data_center=data_center
    )
    if not vnic_profile_obj:
        return False

    new_vnic_profile_obj = _prepare_vnic_profile_object(**kwargs)

    return VNIC_PROFILE_API.update(
        vnic_profile_obj, new_vnic_profile_obj, True
    )[1]


@general.generate_logs()
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
    return NET_API.getElemFromLink(
        network_object, link_name='vnicprofiles', attr='vnic_profile',
        get_href=False
    )


@general.generate_logs()
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
    matching_profiles = filter(
        lambda profile: profile.get_name() == name, get_network_vnic_profiles(
            network, cluster, data_center
        )
    )
    if matching_profiles:
        return matching_profiles[0]
    else:
        raise apis_exceptions.EntityNotFound()


@general.generate_logs()
def get_vnic_profile_attr(
    name, network=None, cluster=None, data_center=None, attr_list=list()
):
    """
    Get VNIC profile attributes.

    Args:
        name (str): Name of the VNIC profile to find.
        network (str): Name of the network used by the VNIC profile.
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
            network_filter

    Returns:
        dict: Returns the dictionary of VNIC profile attributes
    """
    vnic_profile_obj = get_vnic_profile_obj(
        name=name, network=network, cluster=cluster, data_center=data_center
    )
    attr_dict = dict()
    for arg in attr_list:
        if arg == "network_obj":
            arg = "network"

        arg_val = getattr(vnic_profile_obj, arg)
        if arg == "network_filter":
            if hasattr(arg_val, "id"):
                network_filter_id = getattr(arg_val, "id")

                all_network_filters = get_supported_network_filters()
                network_filter_name = [
                    x for x, y in all_network_filters.iteritems() if y.id ==
                    network_filter_id
                ]
                if network_filter_name:
                    arg_val = network_filter_name[0]

        attr_dict[arg] = arg_val.name if hasattr(arg_val, "name") else arg_val
    return attr_dict


@general.generate_logs(step=True)
def add_vnic_profile(positive, name, **kwargs):
    """
    Add new vnic profile to network

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
        network_filter (str): Network filter name to use. ('None') to update
            vNIC profile with no network_filter

    Returns:
        bool: True, if adding vnic profile was success, otherwise False
    """
    kwargs["name"] = name
    vnic_profile_obj = _prepare_vnic_profile_object(**kwargs)
    return VNIC_PROFILE_API.create(vnic_profile_obj, positive)[1]


@general.generate_logs(step=True)
def remove_vnic_profile(
    positive, vnic_profile_name, network=None, cluster=None, data_center=None
):
    """
    Remove vnic profile

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
    profile_obj = get_vnic_profile_object(
        vnic_profile=vnic_profile_name, network=network, cluster=cluster,
        data_center=data_center
    )
    return VNIC_PROFILE_API.delete(profile_obj, positive)


@general.generate_logs()
def is_vnic_profile_exist(vnic_profile_name):
    """
    Find specific VNIC profile on the setup

    Args:
        vnic_profile_name (str): VNIC profile name

    Returns:
        bool: True if action succeeded, otherwise False
    """
    all_profiles = get_vnic_profile_objects()
    for profile in all_profiles:
        if profile.get_name() == vnic_profile_name:
            return True
    return False


@general.generate_logs()
def get_networks_in_datacenter(datacenter):
    """
    Get all networks in datacenter.

    Args:
        datacenter (str): datacenter name

    Returns:
        list: list of all datacenter networks
    """
    dc = DC_API.find(datacenter)
    return NET_API.getElemFromLink(dc, get_href=False)


@general.generate_logs()
def get_network_in_datacenter(network, datacenter):
    """
    Find network under datacenter.

    Args:
        network (str): Network name to find
        datacenter (str): Datacenter name

    Returns:
        Network: Network object if network was found in datacenter
    """
    for net in get_networks_in_datacenter(datacenter=datacenter):
        if net.get_name() == network:
            logger.info("Get %s from %s", network, datacenter)
            return net
    return None


@general.generate_logs()
def create_network_in_datacenter(positive, datacenter, **kwargs):
    """
    Add network to datacenter

    Args:
        positive (bool): True if action should succeed, False otherwise.
        datacenter (str): Datacenter name.
        kwargs (dict): Parameters for add network.

    Keyword Arguments:
        name (str): Network name
        description (str): Network description
        stp (str): Set STP on network
        data_center (str): Datacenter name for the network
        vlan_id (str): VLAN id for the network
        usages (str): VM or Non-VM network (send "" for Non-VM)
        mtu (str): Network MTU
        profile_required (str): Set if vNIC profile is required
        qos_dict (dict): QoS for the network
        dns (list): List of DNS servers

    Returns:
        bool: True if create network succeeded, False otherwise.
    """
    dc = DC_API.find(datacenter)
    net_obj = _prepare_network_object(**kwargs)
    return NET_API.create(
        entity=net_obj, positive=positive, collection=NET_API.getElemFromLink
        (dc, get_href=True)
    )[1]


@general.generate_logs()
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
    net_to_remove = get_network_in_datacenter(
        network=network, datacenter=datacenter
    )
    if net_to_remove:
        res = NET_API.delete(net_to_remove, positive)
        return res
    return False


@general.generate_logs()
def update_network_in_datacenter(positive, network, datacenter, **kwargs):
    """
    Update existing network in datacenter

    Args:
        positive (bool): True if action should succeed, False otherwise
        network(str): name of a network that should be updated
        datacenter (str): datacenter name where the network should be updated
        kwargs (dict): Network oarams

    Keyword Args:
        name (str): Network name
        description (str): Network description
        stp (str): Set STP on network
        data_center (str): Datacenter name for the network
        vlan_id (str): VLAN id for the network
        usages (str): VM or Non-VM network (send "" for Non-VM)
        mtu (str): Network MTU
        profile_required (str): Set if vNIC profile is required
        qos_dict (dict): QoS for the network
        dns (list): List of DNS servers

    Returns:
        bool: True if result of action == positive, False otherwise
    """
    net = get_network_in_datacenter(network=network, datacenter=datacenter)
    net_update = _prepare_network_object(**kwargs)
    return NET_API.update(net, net_update, positive)[1]


@general.generate_logs(error=False)
def is_host_network_is_vm(vds_resource, net_name):
    """
    Check if network that resides on Host is VM or non-VM

    Args:
        vds_resource (resources.VDS): VDS resource object
        net_name (str): name of the network we test for being bridged

    Returns:
        bool: True if net_name is VM, False otherwise
    """
    vm_file = os.path.join(test_utils.SYS_CLASS_NET_DIR, net_name)
    return vds_resource.fs.exists(path=vm_file)


@general.generate_logs()
def is_vlan_on_host_network(vds_resource, interface, vlan):
    """
    Check for VLAN value on the network that resides on Host

    Args:
        vds_resource (VDS): VDS resource object
        interface (str): Name of the phy interface
        vlan (vlan): The value to check on the host (str)

    Returns:
        bool: True if VLAN on the host == provided VLAN, False otherwise
    """
    vid = None
    vlan_file = os.path.join(
        PROC_NET_DIR, "vlan", ".".join([interface, str(vlan)])
    )
    rc, out, _ = vds_resource.run_command(["cat", vlan_file])
    if rc:
        return False
    match_obj = re.search("VID: ([0-9]+)", out)
    if match_obj:
        vid = match_obj.group(1)
    res = vid == vlan
    return res


@ll.general.generate_logs()
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


@general.generate_logs()
def get_vnic_profile_from_network(
    network, vnic_profile, cluster=None, data_center=None
):
    """
    Get the VNIC profile object that belong to a certain network.

    Args:
        network (str):Name of the network
        vnic_profile (str): VNIC profile name
        cluster (str): Name of the cluster in which the network is located
        data_center (str): Name of the data center in which the network resides

    Returns:
        VnicProfile: VNIC profile object that belong to the provided network or
            None
    """
    network_obj = find_network(network, data_center, cluster).id
    all_vnic_profiles = get_vnic_profile_objects()
    for vnic_profile_obj in all_vnic_profiles:
        if vnic_profile_obj.name == vnic_profile:
            if vnic_profile_obj.get_network().id == network_obj:
                return vnic_profile_obj
    return None


@general.generate_logs()
def create_label(label):
    """
    Create label object with provided id

    Args:
        label (str)

    Returns:
        NetworkLabel: Network label object with provided id
    """
    label_obj = apis_utils.data_st.NetworkLabel()
    label_obj.set_id(label)
    return label_obj


@ll.general.generate_logs(step=True)
def add_label(**kwargs):
    """
    Add network label network or hostNIC

    Keyword Args:
        label (str): label to be added to network or NIC on the Host
            if string is provided will create a new label, otherwise expect
            already existed Label object
        networks (list): list of networks with labels
        host_nic_dict (dict): dictionary with hosts (Host object) as keys
            and a list of host interfaces as a value for that key
        datacenter (str): for network parameter datacenter that networks
            resides on
        cluster (str): for cluster parameter cluster that the network
            resides on

    Returns:
        bool: True if label was added properly, False otherwise

    Example:
        label_dict = {
            'label_1': {
                'host': 'host_mixed_1',
                'nic': 'enp4s0',
                'networks': ['net_1']
                }
            }
        add_label(**label_dict)
    """
    for label, param_dict in kwargs.iteritems():
        if isinstance(label, basestring):
            label_obj = create_label(label)
        else:
            label_obj = label
        datacenter = param_dict.get("datacenter")
        cluster = param_dict.get("cluster")
        networks = param_dict.get("networks", list())
        nic = param_dict.get("nic", list())
        host = param_dict.get("host")
        for network in networks:
            entity_obj = find_network(
                network, data_center=datacenter, cluster=cluster
            )
            labels_href = NET_API.getElemFromLink(
                entity_obj, "networklabels", "networklabel", get_href=True
            )
            logger.info(
                "Add label %s to network %s", label_obj.id, network
            )
            if not LABEL_API.create(
                entity=label_obj, positive=True, collection=labels_href,
                coll_elm_name="network_label"
            )[1]:
                logger.error(
                    "Can't add label %s to the network %s", label_obj.id,
                    network
                )
                return False

        if nic:
            entity_obj = ll.hosts.get_host_nic(host=host, nic=nic)
            labels_href = HOST_NICS_API.getElemFromLink(
                entity_obj, "networklabels", "networklabel",
                get_href=True
            )
            logger.info(
                "Add label %s to the NIC %s on Host %s",
                label_obj.id, nic, host.name
            )
            if not LABEL_API.create(
                entity=label_obj, positive=True,
                collection=labels_href, coll_elm_name="network_label"
            )[1]:
                logger.error(
                    "Can't add label %s to the NIC %s on Host %s",
                    label_obj.id, nic, host.name
                )
                return False
    return True


@general.generate_logs(warn=True)
def get_label_objects(**kwargs):
    """
    Get network labels from given networks list and given list NICs of any
    number of Hosts.

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
    try:
        if host_nic_dict:
            for host in host_nic_dict:
                for nic in host_nic_dict.get(host):
                    entity_obj = ll.hosts.get_host_nic(host=host, nic=nic)
                    label_obj = HOST_NICS_API.getElemFromLink(
                        entity_obj, "networklabels", "network_label"
                    )
                    label_list.extend(label_obj)
        if networks:
            for network in networks:
                entity_obj = find_network(
                    network,  data_center=kwargs.get("datacenter"),
                    cluster=kwargs.get("cluster")
                )
                label_obj = NET_API.getElemFromLink(
                    entity_obj, "networklabels", "network_label"
                )
                label_list.extend(label_obj)

        if not networks and not host_nic_dict:
            raise apis_exceptions.EntityNotFound("No correct key was provided")
    except apis_exceptions.EntityNotFound as e:
        logger.error(e)
        raise

    return label_list


def remove_label(**kwargs):
    """
    Remove network labels from given network and Host NIC dictionary

    Keyword Args:
        labels (list): list of label names if specific labels should be removed
        networks (list): list of networks with labels
        host_nic_dict (dict): dictionary with hosts as keys and a list of host
            interfaces as a value for that key
        datacenter (str): for network parameter datacenter that networks
            resides on
        cluster (str): for cluster parameter cluster that the network
            resides on

    Returns:
        bool: True if labels were properly removed, False otherwise

    Example:
    remove_label(
        host_nic_dict={
            'silver-vdsb.qa.lab.tlv.redhat.com': ['eth2']
            },
            networks=['net1', 'vlan0'],
            labels=['net1', 'net2']
            )
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

    Args:
        vds_resource (VDS): VDS resource
        bridge_name (str): name of the bridge with specific opts
        opts (str): opts name to check
        value (str): value of opts to compare to

    Returns:
        bool: True if the value for bridge_opts is equal to the value
            provided, False otherwise
    """
    bridge_file = os.path.join(
        test_utils.SYS_CLASS_NET_DIR, bridge_name, 'bridge', opts
    )
    rc, out, _ = vds_resource.run_command(["cat", bridge_file])
    logger.info(
        "Check if bridge %s opts %s have value %s", bridge_name, opts, value
    )
    if rc:
        logger.error("Bridge %s not found", bridge_name)
        return False

    res = out.strip() == value
    if not res:
        logger.error(
            "Bridge %s opts %s doesn't have value %s", bridge_name, opts, value
        )
        return False
    return True


def check_ethtool_opts(vds_resource, nic, opts, value):
    """
    Checks the ethtool_opts of specific network interface

    Args:
        vds_resource (VDS): VDS resource
        nic (str): NIC name with specific ethtool opts configured
        opts (str): ethtool_opts name to check
        value (str): value of ethtool_opts to compare to

    Returns:
     bool: True if the value for ethtool_opts is equal to the value
        provided, False otherwise
    """
    if opts in ("tx-checksumming", "rx-checksumming"):
        cmd = [ETHTOOL_CMD, "-k", nic]
    else:
        logger.error("Not implemented for opts %s" % opts)
        return False

    logger.info("Check ethtool params %s for NIC %s", opts, nic)
    rc, out, _ = vds_resource.run_command(cmd)
    if rc:
        return False

    for line in out.splitlines():
        if opts in line:
            return line.split(":")[1].lstrip() == value
    logger.error("ethtool params %s not found for NIC %s", opts, nic)
    return False


def check_bridge_file_exist(positive, vds_resource, bridge_name):
    """
    Checks if the bridge file exists for specific network

    Args:
        positive (bool): Expected results
        vds_resource (VDS): VDS resource
        bridge_name (str): name of the bridge file to check if exists

    Returns:
        bool: True if the bridge_name file exists, False otherwise
    """
    log_info = "exists" if positive else "doesn't exists"
    log_error = "exists" if not positive else "doesn't exists"
    bridge_file = os.path.join(
        test_utils.SYS_CLASS_NET_DIR, bridge_name, 'bridge'
    )
    logger.info("Check if bridge %s %s", bridge_file, log_info)
    res = vds_resource.fs.exists(bridge_file)
    if not res == positive:
        logger.error("Bridge %s %s", bridge_name, log_error)
        return False
    return True


@general.generate_logs()
def create_properties(**kwargs):
    """
    Creates Properties object that contains list of different property objects

    Keyword Args:
        bridge_opts (str): Bridge opts
        ethtool_opts (str): Ethtool opts

    Returns:
        Properties: Properties object
    """
    properties_obj = apis_utils.data_st.Properties()
    for key, val in kwargs.iteritems():
        if kwargs.get("bridge_opts") or kwargs.get("ethtool_opts"):
            property_obj = apis_utils.data_st.Property(name=key, value=val)
            properties_obj.add_property(property_obj)
    return properties_obj


@general.generate_logs()
def update_qos_on_vnic_profile(
    datacenter, qos_name, vnic_profile_name, network_name, cluster=None
):
    """
    Update QoS to vNIC profile.

    Args:
        datacenter (str): Datacenter name
        qos_name (str): QoS name to update
        vnic_profile_name (str): vNIC profile name
        network_name (str): Network name
        cluster (str): Cluster name

    Returns:
        bool: True/False
    """
    qos = ll.datacenters.get_qos_from_datacenter(
        datacenter=datacenter, qos_name=qos_name
    )
    return update_vnic_profile(
        name=vnic_profile_name, network=network_name, cluster=cluster,
        data_center=datacenter, qos=qos
    )


@general.generate_logs()
def get_vnic_profile_objects():
    """
    Get all vnic profiles objects from engine

    Returns
        list: List of vnic profiles objects
    """
    return VNIC_PROFILE_API.get(abs_link=False)


@general.generate_logs()
def get_management_network(cluster_name):
    """
    Find management network besides all networks of specific Cluster

    Args:
        cluster_name (str): Name of the Cluster

    Returns:
        Network: Management network object
    """
    try:
        net_obj = [
            i for i in get_cluster_networks(cluster_name, href=False)
            if "management" in i.get_usages().get_usage()
        ][0]
    except IndexError:
        return None

    return net_obj


@general.generate_logs(error=False)
def check_network_usage(cluster, network, attrs):
    """
    Check if usages attributes exist for specific network

    Args:
        cluster (Cluster): Cluster object
        network (str): Name of the Network
        attrs (list): list of attributes (display, migration, management,
            default_route)

    Returns:
        bool: If all attributes exist in network params, False otherwise
    """
    net_obj = get_cluster_network(cluster=cluster, network=network)
    if not net_obj:
        return False

    for attr in attrs:
        if attr not in net_obj.get_usages().get_usage():
            return False
    return True


@general.generate_logs(error=False)
def get_host_nic_labels(nic):
    """
    Get host NIC labels

    Args:
        nic (HostNic): HostNic object

    Returns:
        list: List of HostNic labels
    """
    return ll.hosts.HOST_NICS_API.getElemFromLink(
        nic, "networklabels", "network_label"
    )


@general.generate_logs(error=False)
def get_host_nic_label_objs_by_id(host_nics, labels_id):
    """
    Get host NIC label objects by label ID

    Args:
        host_nics (list): Host NICS object list
        labels_id (list): Label ID

    Returns:
        list: List of HostNic objects
    """
    label_objs_list = list()
    for nic in host_nics:
        nic_labels = get_host_nic_labels(nic)
        label_objs_list.extend(
            [i for i in nic_labels if i.get_id() in labels_id]
        )
    return label_objs_list


@general.generate_logs()
def prepare_qos_on_net(qos_dict):
    """
    Prepare QoS on network

    Args:
        qos_dict (dict): QoS values to add

    Returns:
        Qos: QoS object
    """
    # if we want to update qos to be unlimited need to send empty qos_dict,
    # otherwise update network with the QoS, given in the qos_dict
    if not qos_dict:
        qos_obj = apis_utils.data_st.Qos()
    else:
        qos_name = qos_dict.pop("qos_name")
        datacenter = qos_dict.pop("datacenter")
        qos_obj = ll.datacenters.get_qos_from_datacenter(
            datacenter, qos_name
        )
        # if qos_obj is not found on DC, need to create a new QoS object
        if not qos_obj:
            qos_type = qos_dict.pop("qos_type")
            ll.datacenters.add_qos_to_datacenter(
                datacenter=datacenter, qos_name=qos_name,
                qos_type=qos_type, **qos_dict
            )
            qos_obj = ll.datacenters.get_qos_from_datacenter(
                datacenter, qos_name
            )
    return qos_obj


@general.generate_logs()
def get_network_on_host_nic(host, nic):
    """
    Get network name from host NIC

    Args:
        host (Host): Host object
        nic (str): NIC name

    Returns:
        str: Network name
    """
    return general.get_object_name_by_id(
        NET_API, ll.hosts.get_host_nic(host, nic).get_network().get_id())


@general.generate_logs()
def _prepare_vnic_profile_object(**kwargs):
    """
    Prepare vnic profile object for create or update

    Keyword Args:
        name (str): Name of vnic profile
        network (str): Network name to be used by profile
        cluster (str): Name of cluster in which the network is located
        data_center (str): Name of the data center in which the network is
            located
        port_mirroring (bool): Enable or disable port mirroring for profile
        custom_properties (str): Custom properties for the profile
        description (str): Description of vnic profile
        pass_through (bool): Enable or disable pass through mode
        network_filter (str): Network filter name to use. ('None') to set
            vNIC profile with no network_filter
        migratable (bool): When profile is pass_through allow migration on it

    Returns:
        VnicProfile: vNIC profile object
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
    network_filter = kwargs.get("network_filter")
    migratable = kwargs.get("migratable")

    vnic_profile_obj = apis_utils.data_st.VnicProfile()

    if name:
        vnic_profile_obj.set_name(name)

    if port_mirroring is not None:
        vnic_profile_obj.set_port_mirroring(port_mirroring)

    if description:
        vnic_profile_obj.set_description(description)

    if network or new_network:
        net_obj = find_network(
            network=network or new_network, data_center=data_center,
            cluster=cluster
        )
        vnic_profile_obj.set_network(net_obj)

    if qos:
        vnic_profile_obj.set_qos(qos)

    if custom_properties:
        from art.rhevm_api.tests_lib.low_level.vms import (
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

    if network_filter:
        if network_filter != "None":
            network_filters = get_supported_network_filters()
            network_filter_object = network_filters.get(network_filter)
        else:
            network_filter_object = apis_utils.data_st.NetworkFilter()

        vnic_profile_obj.set_network_filter(network_filter_object)

    if migratable is not None:
        vnic_profile_obj.set_migratable(migratable)

    return vnic_profile_obj


@general.generate_logs()
def get_supported_network_filters():
    """
    Get all supported network filters from engine

    Returns:
        dict: Dict with NetworkFilter name as key and NetworkFilter object
            as value
    """
    network_filters = NF_API.get(abs_link=False)
    return dict((i.name, i) for i in network_filters.get_network_filter())


@general.generate_logs()
def prepare_vnic_profile_mappings_object(network_mappings):
    """
    Prepare VnicProfileMappings object for import VM from data domain

    Args:
        network_mappings (list): Map networks from the imported object to
            existing network on cluster (list of dicts)

    Returns:
        VnicProfileMappings: VnicProfileMappings object

    Examples:
        vnic_profile_mapping = network_mappings = [{
            "source_network_profile_name": "src_profile_name",
            "source_network_name": "src_network_name",
            "target_network": "target_network_name",
            "target_vnic_profile": "target_profile_name",
            "cluster": "cluster_name_for_target_vnic_profile",
            "datacenter": "datacenter_name_for_target_vnic_profile"
            }]
        prepare_vnic_profile_mappings_object(
            network_mappings=vnic_profile_mapping
            )
    """
    vnic_profile_mappings = None
    for network_mapping in network_mappings:
        target_vnic_profile = network_mapping.get("target_vnic_profile")
        target_network = network_mapping.pop("target_network", None)
        cluster = network_mapping.pop("cluster", None)
        datacenter = network_mapping.pop("datacenter", None)
        if target_vnic_profile:
            vnic_profile_object = get_vnic_profile_obj(
                name=target_vnic_profile, network=target_network,
                cluster=cluster, data_center=datacenter
            )
            network_mapping["target_vnic_profile"] = vnic_profile_object

        elif target_vnic_profile is None:
            network_mapping["target_vnic_profile"] = getDS("VnicProfile")()

        vnic_profile_mappings = getDS("VnicProfileMappings")()
        vnic_profile_mapping = getDS("VnicProfileMapping")
        vnic_profile_mappings.add_vnic_profile_mapping(
            vnic_profile_mapping(**network_mapping)
        )
    return vnic_profile_mappings


@general.generate_logs()
def get_bond_bonding_property(host, bond, property_name):
    """
    Get bond bonding property_name Mac object for host

    Args:
        host (Host): Host object
        bond (str): Bond name
        property_name (str): Property name, can be one of the following:
            "ad_partner_mac", "options", "slaves" or "active_slave"

    Returns:
        Mac: Mac object, or None if get failed
    """
    host_nics = ll.hosts.get_host_nics_list(host=host)
    bond_object = [i for i in host_nics if i.name == bond]

    if not bond_object:
        return None

    return getattr(bond_object[0].bonding, property_name)


@general.generate_logs()
def get_bond_active_slave_object(host, bond):
    """
    Get host bond active slave object.

    Args:
        host (Host): Host object.
        bond (str): Bond name.

    Returns:
        HostNic or None: HostNic objects if active slave found else None.
    """
    host_nics = ll.hosts.get_host_nics_list(host)
    bond_object = [i for i in host_nics if i.name == bond]
    bond_slave_object = (
        bond_object[0].bonding.active_slave if bond_object else None
    )
    if not bond_slave_object:
        return None

    return [i for i in host_nics if i.id == bond_slave_object.id][0]


@general.generate_logs()
def get_all_networks():
    """
    Get all networks from engine
    """
    return NET_API.get(abs_link=False)


@general.generate_logs()
def prepare_network_dns_object(dns_servers):
    """
    Prepare DNS object with dns_servers for network or network attachment

    Args:
        dns_servers (list): DNS server list

    Returns:
        DnsResolverConfiguration: DnsResolverConfiguration object
    """
    resolver_configuration = apis_utils.data_st.DnsResolverConfiguration()
    name_servers = apis_utils.data_st.name_serversType()
    name_servers.set_name_server(dns_servers)
    resolver_configuration.set_name_servers(name_servers)
    return resolver_configuration


@general.generate_logs(error=False)
def is_gluster_network(network, cluster=None):
    """
    Check if network has gluster role

    Args:
        network (str): Network name
        cluster (Cluster): Cluster object

    Returns:
        bool: True if network has gluster role, False otherwise
    """
    return check_network_usage(
        cluster=cluster, network=network, attrs=["gluster"]
    )


@general.generate_logs()
def get_network_cluster(network, datacenter=None):
    """
    Get the cluster object from network

    Args:
        network (str): Network name
        datacenter (str): Datacenter name

    Returns:
        Cluster: Cluster object or None
    """
    clusters_and_datacenter_ids_from_clusters = []
    net_obj = find_network(network=network, data_center=datacenter)
    network_dc = ll.datacenters.get_data_center(
        datacenter=datacenter or net_obj.data_center.id, key=(
            "id" if not datacenter else "name"
        )
    )
    for cl in ll.clusters.get_cluster_list():
        dc = cl.data_center
        if dc:
            clusters_and_datacenter_ids_from_clusters.append(
                (cl, dc.id)
            )

    cluster = [
        x[0] for x in clusters_and_datacenter_ids_from_clusters if
        x[1] == network_dc.id
    ]
    return cluster[0] if cluster else None


@ll.general.generate_logs(step=True)
def get_all_vnics_profiles():
    """
    Get all vNICs profiles from engine

    Returns:
        list: List of vNICs profiles
    """
    return VNIC_PROFILE_API.get(abs_link=False)


@ll.general.generate_logs(step=True)
def get_vnic_profile_object(
    vnic_profile, network=None, cluster=None, data_center=None
):
    """
    Get vNIC profile object by vnic_profile name

    Args:
        vnic_profile (str): vNIC profile name
        network (str): Network name used by profile
        cluster (str): Name of the cluster the network resides on
        data_center (str):  Name of the data center the network resides on

    Returns:
        VnicProfile: vNIC profile object
    """
    if network:
        return get_vnic_profile_obj(
            name=vnic_profile, network=network, cluster=cluster,
            data_center=data_center
        )
    else:
        profile_obj = filter(
            lambda x: x.name == vnic_profile, get_all_vnics_profiles()
        )
        return profile_obj[0] if profile_obj else None
