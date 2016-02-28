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
import art.core_api as core_api
import art.test_handler.settings as test_settings
import art.test_handler.exceptions as test_exceptions
import art.core_api.apis_exceptions as apis_exceptions
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

ENUMS = test_settings.opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger("art.hl_lib.networks")
CONNECTIVITY_TIMEOUT = 60
DISK_SIZE = 21474836480
LUN_PORT = 3260
INTERVAL = 2
ATTEMPTS = 600
TIMEOUT = 120
MAX_COUNTER = 60
DEFAULT_MTU = 1500
VDSM_CONF_FILE = "/etc/vdsm/vdsm.conf"
IFCFG_FILE_PATH = "/etc/sysconfig/network-scripts/"
HOST_NICS = ["eth0", "eth1", "eth2", "eth3", "eth4", "eth5"]
RHEL_IMAGE = "rhel6.5-agent3.5"
HYPERVISOR = "hypervisor"
RHEVH = "Red Hat Enterprise Virtualization Hypervisor"

# command variables
IP_CMD = "/sbin/ip"
MODPROBE_CMD = "/sbin/modprobe"


# FIXME: need to check if this function is being used else just remove.
@core_api.is_action()
def getNetworkConfig(positive, cluster, network, datacenter=None, tag=None):
    """
     Validate Datacenter/Cluster network configurations/existence.
     This function tests the network configured parameters. we look for
     networks link under cluster even though we check the DC network
     configurations only because cluster networks related
     to main networks href.

     Author: atal
     Parameters:
        * cluster - cluster name
        * network - network name
        * datacenter - data center name. in order to check if the given
                       network exists in the DC.
        * tag - the tag we are looking to validate
     return: True and value of the given filed, otherwise False and None
    """
    try:
        netObj = ll_networks.get_cluster_network(cluster, network)
    except apis_exceptions.EntityNotFound:
        return False, {'value': None}

    # validate cluster network related to the given datacenter
    if datacenter:
        try:
            dcObj = ll_networks.DC_API.find(datacenter)
        except apis_exceptions.EntityNotFound:
            return False, {'value': None}

        # return False means that given datacenter
        # doesn't contain the given network
        if dcObj.get_id() != netObj.get_data_center().get_id():
            return False, {'value': None}

    if tag:
        if hasattr(netObj, tag):
            attrValue = None
            if tag == 'status':
                attrValue = getattr(netObj.get_status(), 'state')
            else:
                attrValue = getattr(netObj, tag)
            return True, {'value': attrValue}

    # in case we only like to check if the network exists or not.
    if netObj:
        return True, {'value': netObj.get_name()}

    return False, tag


# FIXME: method is using only for checking status. need to change to a more
# simple method
@core_api.is_action()
def validateNetwork(positive, cluster, network, tag, val):
    status, output = getNetworkConfig(positive, cluster, network, tag=tag)
    return bool(status and str(output['value']).lower() == str(val).lower())


@core_api.is_action()
def remove_networks(positive, networks, data_center=None):
    """
    Remove networks

    :param positive: Expected state that the function should return
    :type positive: bool
    :param networks: List of networks
    :type networks: list
    :param data_center: DC from where to remove network
    :type data_center: str
    :return: True if remove networks succeeded, otherwise False
    :rtype: bool
    """
    for net in networks:
        logger.info("Removing %s", net)
        if not ll_networks.removeNetwork(positive, net, data_center):
            logger.error("Failed to remove %s", net)
            return False
    return True


def createAndAttachNetworkSN(
    data_center=None, cluster=None, host=list(), auto_nics=list(),
    save_config=False, network_dict=None, vlan_auto_nics=None,
    use_new_api=False
):
    """
    Function that creates and attach the network to the:
    a) DC, b) Cluster, c) Hosts with SetupNetworks

    **Author**: gcheresh
    :param data_center: DC name
    :type data_center: str
    :param cluster: Cluster name
    :type cluster: str
    :param host: list of resources.VDS objects
    :type host: list
    :param auto_nics: a list of nics indexes to preserve
    :type auto_nics: list
    :param save_config: flag for saving configuration
    :type save_config: bool
    :param vlan_auto_nics: dictionary for auto_nics with vlan
    :type vlan_auto_nics: dict
    :param use_new_api: Run with new host network API
    :type use_new_api: bool
    :param network_dict: dictionary of dictionaries
    :type network_dict: dict

    vlan_auto_nics example: {162: 0} where 162 is the vlan ID and
    0 is the host_nic index. (all int)

    network_dict parameters:
        logical network name as the key for the following:
            *  *nic* - interface to create the network on
            *  *usages* - vm or ''  value (for VM or non-VM network)
            *  *cluster_usages* - migration and/or display
                (can be set on one network)
            *  *vlan_id* - VLAD ID
            *  *mtu* - MTU
            *  *required* - required/non-required network
            *  *bond* - bond name to create
            *  *slaves* - interfaces that the bond will be composed from
            *  *mode* - the mode of the bond
            *  *bootproto* - boot protocol (none, dhcp, static)
            *  *address* - list of IP addresses of the network
                if bootproto is Static
            *  *netmask* - list of netmasks of the  network
                if bootproto is Static
            *  *gateway* - list of gateways of the network
                if bootproto is Static
            *  *profile_required* - flag to create or not VNIC profile
                for the network
            *  * properties* - property of bridge_opts and/or ethtool_opts
    :return: True value if succeeded in creating and adding net list
             to DC/Cluster and Host with all the parameters
    :rtype: bool
    """
    # Makes sure host_list is always a list
    host_list = [host] if not isinstance(host, list) else host

    for net, net_param in network_dict.items():
        if data_center and net:
            logger.info("Adding %s to %s", net, data_center)
            if not ll_networks.addNetwork(
                True, name=net, data_center=data_center,
                usages=net_param.get("usages", "vm"),
                vlan_id=net_param.get("vlan_id"),
                mtu=net_param.get("mtu"),
                profile_required=net_param.get("profile_required"),
                qos_dict=net_param.get("qos")
            ):
                logger.error("Cannot add %s to %s", net, data_center)
                return False

        if cluster and net:
            logger.info("Adding %s to %s", net, cluster)
            if not ll_networks.addNetworkToCluster(
                True, network=net, cluster=cluster,
                required=net_param.get("required", "true"),
                usages=net_param.get("cluster_usages", None),
                data_center=data_center
            ):
                logger.error("Cannot add %s to %s", net, cluster)
                return False

    for host in host_list:
        host_name = ll_hosts.get_host_name_from_engine(host.ip)
        if not host_name:
            host_name = ll_hosts.get_host_name_from_engine(host.fqdn)

        logger.info("Found host name: %s", host_name)

        host_auto_nics = []
        for index in auto_nics:
            host_auto_nics.append(host.nics[index])

        if vlan_auto_nics:
            for key, val in vlan_auto_nics.iteritems():
                host_int = host.nics[val]
                host_vlan_int = ".".join([host_int, str(key)])
                host_auto_nics.append(host_vlan_int)

        net_obj = []
        idx = 0
        setup_network_dict = {"add": {}}
        for net, net_param in network_dict.items():
            param_nic = net_param.get("nic")
            if not param_nic:
                continue
            vlan_interface = None
            slaves = None
            param_slaves = net_param.get("slaves")
            param_vlan = net_param.get("vlan_id")
            idx += 1

            if param_slaves:
                slaves = [host.nics[s] for s in param_slaves]

            nic = (
                param_nic if "bond" in str(param_nic) else host.nics[param_nic]
            )

            if "vlan_id" in net_param:
                vlan_interface = "{0}.{1}".format(nic, param_vlan)

            address_list = net_param.get("address", [])
            netmask_list = net_param.get("netmask", [])
            gateway_list = net_param.get("gateway", [])

            nic = (
                vlan_interface if "vlan_id" in net_param else nic
            )
            if use_new_api:
                sn_dict = convert_old_sn_dict_to_new_api_dict(
                    new_dict=setup_network_dict, old_dict=net_param, idx=idx,
                    nic=nic, network=net, slaves=slaves
                )
            else:
                rc, out = ll_hosts.genSNNic(
                    nic=nic, network=net, slaves=slaves,
                    mode=net_param.get("mode", 4),
                    boot_protocol=net_param.get("bootproto", None),
                    address=address_list.pop(0) if address_list else None,
                    netmask=netmask_list.pop(0) if netmask_list else None,
                    gateway=gateway_list.pop(0) if gateway_list else None,
                    properties=net_param.get("properties", None)
                )
                if not rc:
                    logger.error("Cannot generate network object for %s", net)
                    return False
                net_obj.append(out["host_nic"])

        if use_new_api:
            if not network_dict:
                if not hl_host_network.clean_host_interfaces(
                    host_name=host_name
                ):
                    logger.error("Failed to clean %s interface", host_name)
                    return False
            else:
                if not hl_host_network.setup_networks(
                    host_name=host_name, **sn_dict
                ):
                        logger.error(
                            "Failed to send SN request to host %s", host_name
                        )
                        return False
        else:
            logger.info("Sending SN request to host %s" % host_name)
            if not ll_hosts.sendSNRequest(
                True, host=host_name, nics=net_obj, auto_nics=host_auto_nics,
                check_connectivity="true", connectivity_timeout=60,
                force="false"
            ):
                logger.error(
                    "Failed to send SN request to host %s", host_name
                )
                return False

            if save_config:
                logger.info(
                    "Saving network configuration on host %s", host_name
                )
                if not ll_hosts.commitNetConfig(True, host=host_name):
                    logger.error("Could not save network configuration")
    return True


def remove_net_from_setup(
    host, network=[], data_center=None, all_net=False, mgmt_network=None
):
    """
    Function that removes networks from the host, Cluster and DC

    :param host: list or str of hosts names
    :type host: str or list
    :param network: list of networks to remove
    :type network: list
    :param data_center: DC where the network is
    :type data_center: str
    :param all_net: True to remove all networks from setup (except MGMT net)
    :rtype  all_net: bool
    :param mgmt_network: Management network
    :type mgmt_network: str
    :return: True value if succeeded in deleting networks
            from Hosts, Cluster, DC
    :rtype: bool
    """
    hosts_list = [host] if not isinstance(host, list) else host
    if all_net:
        if not remove_all_networks(
                datacenter=data_center, mgmt_network=mgmt_network
        ):
            return False
    else:
        if not remove_networks(True, network, data_center):
            return False
    try:
        for host_name in hosts_list:
            if not hl_host_network.clean_host_interfaces(host_name):
                return False

    except Exception as ex:
        logger.error("Clean hosts interfaces failed %s", ex, exc_info=True)
        return False
    return True


def create_dummy_interfaces(host, num_dummy=1, ifcfg_params=None):
    """
    create (X) dummy network interfaces on host

    :param host: VDS
    :type host: resources.VDS
    :param num_dummy: number of dummy interfaces to create
    :type num_dummy: int
    :param ifcfg_params: Ifcfg file content
    :type ifcfg_params: dict
    :return: True/False
    :rtype: bool
    """
    dummy_int = "dummy_%s"
    if ifcfg_params is None:
        ifcfg_params = {}

    for i in range(num_dummy):
        cmd = ["ip", "link", "add", dummy_int % i, "type", "dummy"]
        rc, out, error = host.run_command(cmd)
        if rc:
            return False

        nic_name = dummy_int % i
        host.network.create_ifcfg_file(nic=nic_name, params=ifcfg_params)

    return True


def delete_dummy_interfaces(host):
    """
    Delete dummy network interfaces on host

    :param host: VDS
    :type host: resources.VDS
    :return: True/False
    :rtype: bool
    """
    rhevh = RHEVH in host.get_os_info()["dist"]
    all_interfaces = host.network.all_interfaces()
    dummy_list = [i for i in all_interfaces if 'dummy' in i]
    for i in dummy_list:
        host.network.delete_interface(interface=i)
        ifcfg_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % i
        if host.fs.isfile(ifcfg_file):
            if rhevh:
                rc, out, err = host.run_command(["unpersist", ifcfg_file])
                if rc:
                    return False
            host.network.delete_ifcfg_file(nic=i)
    return True


def remove_all_networks(datacenter=None, cluster=None, mgmt_network=None):
    """
    Remove all networks from DC/CL or from entire setup
    If cluster is specified - remove all network from specified cluster
    Elif datacenter is specified - remove all networks from specified DC
    If no datacenter or cluster are specified remove all networks from all DCs
    In all cases we don't remove the management network

    :param datacenter: name of the datacenter
    :type datacenter: str
    :param cluster: name of the cluster
    :type cluster: str
    :param mgmt_netowrk: name of management network (to be excluded from
        removal)
    :type mgmt_network: str
    :return: True if removing networks succeeded, otherwise False
    :rtype: bool
    """
    networks_to_remove = []
    cluster_obj = (
        ll_clusters.get_cluster_object(cluster_name=cluster) if cluster else
        None
    )
    mgmt_networks_ids = (
        get_clusters_managements_networks_ids(
            cluster=[cluster_obj] if cluster else None
        )
    )
    if cluster:
        networks_list = ll_networks.get_cluster_networks(
            cluster=cluster, href=False
        )

    elif datacenter:
        networks_list = ll_networks.get_networks_in_datacenter(
            datacenter=datacenter
        )

    else:
        logger.info("Get all networks")
        networks_list = ll_networks.NET_API.get(absLink=False)

    for net in networks_list:
        if net.id not in mgmt_networks_ids:
            networks_to_remove.append(net.name)

    if not networks_to_remove:
        logger.info("There are no networks to remove")
        return True

    return remove_networks(True, networks_to_remove, datacenter)


def getIpOnHostNic(host, nic):
    '''
    Description: Get IP on host NIC

    **Author**: myakove
    **Parameters**:
        *  *host* - IP or FDQN of the host
        *  *nic* - NIC to get IP from, execpted NICs:
                   eth(x) - Non VLAN nic
                   eth(x).(xxx) - VLAN NIC
                   bond(x) - BOND NIC
                   bond(x).(xxx) - VLAN BOND NIC
    **Return**: IP or None
    '''
    host_nic = ll_hosts.get_host_nic(host=host, nic=nic)
    return host_nic.get_ip().get_address()


def check_host_nic_params(host, nic, **kwargs):
    """
    Check MTU, VLAN interface and bridge (VM/Non-VM) host nic parameters.

    :param host: Host name
    :type host: str
    :param nic: Nic to get parameters from
    :type nic: str
    :param kwargs:
        vlan_id: expected VLAN id on the host (str)
        mtu: expected mtu on the host (str)
        bridge: Expected VM, Non-VM network (True for VM, False for
               Non-VM) (bool)
    :type kwargs: dict
    :return: True if action succeeded, otherwise False
    :rtype: bool
    """
    res = True
    host_nic = ll_hosts.get_host_nic(host, nic)
    expected_bridge = kwargs.get("bridge")
    expected_vlan_id = kwargs.get("vlan_id")
    expected_mtu = kwargs.get("mtu")

    if expected_bridge is not None:
        bridged = host_nic.get_bridged()
        logger.info("Check that %s has bridge %s", nic, expected_bridge)
        if expected_bridge != bridged:
            logger.error(
                "%s interface has bridge %s, expected is %s", nic, bridged,
                expected_bridge
            )
            res = False

    if expected_vlan_id:
        vlan_nic = ".".join([nic, expected_vlan_id])
        logger.info("Check that %s has vlan tag %s", nic, expected_vlan_id)
        try:
            ll_hosts.get_host_nic(host, vlan_nic)
        except apis_exceptions.EntityNotFound:
            logger.error("Fail to get %s interface from %s", vlan_nic, host)
            res = False

    if expected_mtu:
        logger.info("Check that %s have MTU %s", nic, expected_mtu)
        mtu = host_nic.get_mtu()
        if int(expected_mtu) != mtu:
            logger.error(
                "MTU value on %s is %s, expected is %s", nic, mtu,
                expected_mtu
            )
            res = False

    return res


def create_basic_setup(datacenter, storage_type, version, cluster=None,
                       cpu=None, host=None, host_password=None):
    """
    Description: Create basic setup with datacenter and optional cluster and
    hosts

    Author: myakove
    Parameters:
       *  *datacenter* - Datacenter name
       *  *storage_type* - Storage type for datacenter
       *  *version* - Version of the datacenter/cluster
       *  *cluster* - Cluster name
       *  *cpu* - CPU type for cluster
       *  *host* - Host name or a list of Host names
       *  *host_password* - Password for the host
    **Return**: True if setup creation succeeded, otherwise False
    """
    if not ll_datacenters.addDataCenter(
        positive=True, name=datacenter, storage_type=storage_type,
        version=version
    ):
        logger.error("Failed to add DC")
        return False

    if cluster:
        if not ll_clusters.addCluster(
            positive=True, name=cluster, cpu=cpu, data_center=datacenter,
            version=version
        ):
            logger.error("Failed to add Cluster")
            return False

        if host:
            host_list = [host] if isinstance(host, basestring) else host
            try:
                hl_hosts.add_hosts(
                    hosts_list=host_list, cluster=cluster,
                    passwords=[host_password] * len(host_list)
                )
            except test_exceptions.HostException:
                logger.error("Failed to add host")
                return False
    return True


def remove_basic_setup(datacenter, cluster=None, hosts=[]):
    """
    Description: Remove basic setup with datacenter and optional cluster and
    hosts

    :param datacenter: Datacenter name
    :param cluster: name
    :param hosts: name or a list of Host names
    :return: True if setup removal succeeded, otherwise False
    """
    if cluster:
        for host in hosts:
            if not ll_hosts.removeHost(
                positive=True, host=host, deactivate=True
            ):
                logger.error("Failed to remove host %s ", host)
                return False

        if not ll_clusters.removeCluster(positive=True, cluster=cluster):
            logger.error("Failed to remove Cluster")
            return False

    if not ll_datacenters.removeDataCenter(
        positive=True, datacenter=datacenter
    ):
        logger.error("Failed to remove DC")
        return False
    return True


def update_network_host(host, nic, auto_nics, save_config=True, **kwargs):
    """
    Description: Updates network on Host NIC

    Author: gcheresh
    Parameters:
       *  *host* - Host name
       *  *nic* - Interface with network to be updated
       *  *auto_nics* - List of NICs, beside the NIC to be updated
       *  *save_config* - Flag to save configuration after update
       *  *kwargs* - dictionary of parameters to be updated on existing network
           Example for kwargs:
           {"address": "10.10.10.10", "netmask": "255.255.255.0",
           "boot_protocol": "static",
           "properties": {"bridge_opts": "Priority=7smax_age=1998",
                       "ethtool_opts": "--offload eth2 rx on"}}
    **Return**: True if update succeeded, otherwise False
    """
    nic_obj = ll_hosts.get_host_nic(host=host, nic=nic)
    kwargs.update({'update': nic_obj})
    rc, out = ll_hosts.genSNNic(nic=nic_obj, **kwargs)
    if not rc:
        logger.error("Cannot generate network object for nic")
        return False

    logger.info("Sending SN request to host %s", host)
    if not ll_hosts.sendSNRequest(
        True, host=host, nics=[out['host_nic']], auto_nics=auto_nics,
        check_connectivity='true', connectivity_timeout=60, force='false'
    ):
        logger.error("Failed to send SN request to host %s", host)
        return False

    if save_config:
        logger.info("Saving network configuration on host %s" % host)
        if not ll_hosts.commitNetConfig(True, host=host):
            logger.error("Couldn't save network configuration")
            return False
    return True


def is_management_network(cluster_name, network):
    """
    Check if network is MGMT network

    :param cluster_name: Name of the Cluster
    :type cluster_name: str
    :param network: network to check
    :type: str
    :return: network MGMT
    :rtype: object
    """
    mgmt_net_obj = ll_networks.get_management_network(cluster_name)
    cl_mgmt_net_obj = ll_clusters.get_cluster_management_network(cluster_name)
    if (
            mgmt_net_obj.get_name() == network and
            mgmt_net_obj.get_id() == cl_mgmt_net_obj.get_id()
    ):
        return True
    return False


def get_nic_statistics(nic, host=None, vm=None, keys=None):
    """
    Get Host NIC/VM NIC statistics value for given keys.
    Available keys are:
        data.current.rx
        data.current.tx
        errors.total.rx
        errors.total.tx
        data.total.rx
        data.total.tx

    :param nic: NIC name
    :type nic: str
    :param host: Host name
    :type host: str
    :param vm: VM name
    :type vm: str
    :param keys: Keys to get keys for
    :type keys: list
    :return: Dict with keys values
    :rtype: dict
    """
    res = dict()
    stats = ll_hosts.get_host_nic_statistics(
        host, nic
    ) if host else ll_vms.get_vm_nic_statistics(
        vm, nic
    )
    for stat in stats:
        stat_name = stat.get_name()
        if stat_name in keys:
            res[stat_name] = stat.get_values().get_value()[0].get_datum()
    return res


def convert_old_sn_dict_to_new_api_dict(
    new_dict, old_dict, idx, nic, network, slaves=list()
):
    """
    Convert old CreateAndAttachSN call dict to new network API dict to use
    in setup_networks()

    :param new_dict: New SN dict
    :type new_dict: dict
    :param old_dict: Network dict
    :type old_dict: dict
    :param idx: Index number for new API dict
    :type idx: int
    :param nic: NIC name
    :type nic: str
    :param network: Network name
    :type network: str
    :param slaves: BOND slaves list
    :type slaves: list
    :return: New dict for new API function (setup_networks())
    :rtype: dict
    """
    address = old_dict.get("address")
    netmask = old_dict.get("netmask")
    gateway = old_dict.get("gateway")
    new_dict["add"][str(idx)] = {
        "nic": nic.rsplit(".")[0],
        "slaves": slaves,
        "network": network,
        "properties": old_dict.get("properties", None),
        "ip": {
            "ip_1": {
                "address": address.pop(0) if address else None,
                "netmask": netmask.pop(0) if netmask else None,
                "gateway": gateway.pop(0) if gateway else None,
                "boot_protocol": old_dict.get("bootproto", None),
            }
        }
    }
    return new_dict


def get_clusters_managements_networks_ids(cluster=None):
    """
    Get clusters managements networks IDs for all clusters in the engine if
    not cluster else get only for the given cluster

    :param cluster: Cluster name
    :type cluster: list
    :return: managements networks ids
    :rtype: list
    """
    clusters = (
        ll_clusters.CLUSTER_API.get(absLink=False) if not cluster else cluster
    )
    logger.info(
        "Get management networks id from %s", [cl.name for cl in clusters]
    )
    return [
        ll_networks.get_management_network(cluster_name=cl.name).id
        for cl in clusters
        ]


def get_management_network_host_nic(host, cluster):
    """
    Get host NIC name that management network resides on

    Args:
        host (str): Host name
        cluster (str): Cluster name

    Returns:
        HostNic or None: Host NIC  if found else None

    """
    mgmt_net = ll_networks.get_management_network(cluster_name=cluster)
    host_nics_list = ll_hosts.get_host_nics_list(host=host)
    host_nics_with_network = filter(
        lambda nic: getattr(nic, "network"), host_nics_list
    )
    for nic in host_nics_with_network:
        if nic.network.id == mgmt_net.id:
            return nic
    return None
