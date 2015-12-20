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

import re
import logging
import configobj
import utilities.jobs as jobs
import art.core_api as core_api
import art.rhevm_api.utils.cpumodel as cpumodel
import art.test_handler.settings as test_settings
import art.rhevm_api.utils.test_utils as test_utils
import art.test_handler.exceptions as test_exceptions
import art.core_api.apis_exceptions as apis_exceptions
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.high_level.datacenters as hl_datacenter
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains

ENUMS = test_settings.opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger(__name__)
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


@core_api.is_action()
def addMultipleVlanedNetworks(networks, data_center, **kwargs):
    """
    Adding multiple networks with vlan according to the given prefix and range
    Author: atal
    Parameters:
        * networks - a list of vlaned networks with their vlan suffix
        * date_center - the DataCenter name
        * kwargs - all arguments related to basic addNetwork
    return True with new nics name list or False with empty list
    """

    for network in networks:
        vlan = re.search(r'(\d+)', network)
        if not ll_networks.addNetwork(
            'True', name=network, data_center=data_center,
            vlan_id=vlan.group(0), **kwargs
        ):
            return False
    return True


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
        netObj = ll_networks.getClusterNetwork(cluster, network)
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
def removeMultiNetworks(positive, networks, data_center=None):
    """
    Remove Multiple networks
    Author: atal
    Parameters:
        * positive - expected state that the function should return
        * networks- a list of networks
        * data_center - In case more then one network with the same name
                        exists.
    return  True if remove networks succeeded, otherwise False
    """
    for net in networks:
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
            logger.info("Adding network to DC")
            if not ll_networks.addNetwork(
                True, name=net, data_center=data_center,
                usages=net_param.get("usages", "vm"),
                vlan_id=net_param.get("vlan_id"),
                mtu=net_param.get("mtu"),
                profile_required=net_param.get("profile_required"),
                qos_dict=net_param.get("qos")
            ):
                logger.info("Cannot add network to DC")
                return False

        if cluster and net:
            logger.info("Adding network to Cluster")
            if not ll_networks.addNetworkToCluster(
                True, network=net, cluster=cluster,
                required=net_param.get("required", "true"),
                usages=net_param.get("cluster_usages", None),
                data_center=data_center
            ):
                logger.info("Cannot add network to Cluster")
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
                    mode=net_param.get("mode", 1),
                    boot_protocol=net_param.get("bootproto", None),
                    address=address_list.pop(0) if address_list else None,
                    netmask=netmask_list.pop(0) if netmask_list else None,
                    gateway=gateway_list.pop(0) if gateway_list else None,
                    properties=net_param.get("properties", None)
                )
                if not rc:
                    logger.error("Cannot generate network object")
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
                        logger.info(
                            "Failed to send SN request to host %s" % host_name
                        )
                        return False
        else:
            logger.info("Sending SN request to host %s" % host_name)
            if not ll_hosts.sendSNRequest(
                True, host=host_name, nics=net_obj, auto_nics=host_auto_nics,
                check_connectivity="true", connectivity_timeout=60,
                force="false"
            ):
                logger.info("Failed to send SN request to host %s" % host_name)
                return False

            if save_config:
                logger.info(
                    "Saving network configuration on host %s" % host_name
                )
                if not ll_hosts.commitNetConfig(True, host=host_name):
                    logger.error("Could not save network configuration")
    return True


def remove_net_from_setup(
    host, network=[], data_center=None, all_net=False, mgmt_network=None
):
    """
    Function that removes networks from the host, Cluster and DC:
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
    dc_log = "from %s" % data_center if data_center else ""
    if all_net:
        logger.info("Remove all networks %s", dc_log)
        if not remove_all_networks(
                datacenter=data_center, mgmt_network=mgmt_network
        ):
            logger.error("Couldn't remove networks %s", dc_log)
            return False
    else:
        logger.info("Remove %s %s ", network, dc_log)
        if not removeMultiNetworks(True, network, data_center):
            logger.error("Couldn't remove %s %s", network, dc_log)
            return False
    try:
        for host_name in hosts_list:
            logger.info("Clean %s interfaces", host_name)
            if not hl_host_network.clean_host_interfaces(host_name):
                logger.error("Clean %s interfaces failed", host_name)
                return False

    except Exception as ex:
        logger.error("Clean hosts interfaces failed %s", ex, exc_info=True)
        return False
    return True


@core_api.is_action()
def prepareSetup(
    hosts, cpuName, username, password, datacenter, cluster, version,
    storage_type, local=False, storageDomainName=None, lun_address='',
    lun_target='', luns='', lun_port=LUN_PORT, diskType='system',
    auto_nics=[0], vm_user='root', vm_password=None, vmName=None,
    vmDescription='linux vm', nicType='virtio', display_type='spice',
    os_type='RHEL6x64', image=RHEL_IMAGE, nic='nic1', size=DISK_SIZE,
    useAgent=True, template_name=None, attempt=ATTEMPTS, interval=INTERVAL,
    placement_host=None, mgmt_network=None, vnic_profile=None
):
    """
    Function that creates DC, Cluster, Storage, Hosts
    It creates VM with a NIC connected to default network and Template if
    flag is on:
    :param hosts: list of resources.VDS objects
    :param cpuName: cpu type in the Cluster
    :param username: user name for the host machines
    :param password: password for the host machines
    :param datacenter: data center name
    :param storage_type: type of storage
    :param cluster: cluster name
    :param version: supported version like 3.1, 3.2...
    :param storageDomainName: name of the storage domain
    :param lun_address: address of iSCSI machine
    :param lun_target: LUN target
    :param luns: lun\s id. A single lun id, or a list of luns, separated by
                 comma.
    :param lun_port: lun port
    :param diskType: type of the disk
    :param vm_user: user name for the VM
    :param vm_password: password for the VM
    :param auto_nics: a list of nics indexes
    :param vmName: VM name, if not None create VM
    :param vmDescription: Description of VM
    :param display_type: type of vm display (VNC or SPICE)
    :param nicType: type of the NIC (virtio, RTL or e1000)
    :param os_type: type of the OS
    :param image: profile in cobbler
    :param nic: nic name
    :param size: the size of the disk
    :param useAgent: Set to 'true', if desired to read the ip from VM. Agent
                     exist on VM
    :param template_name: name of the template, if not None create template.
    :param attempt: attempts to connect after installation
    :param interval: interval between attempts
    :param placement_host: the host that will hold VM
    :param mgmt_network: management network
    :return: True if creation of the setup succeeded, otherwise False
    """
    hosts_obj = [hosts] if not isinstance(hosts, list) else hosts
    hosts_ip = [h.ip for h in hosts_obj]

    if not ll_datacenters.addDataCenter(
        True, name=datacenter, storage_type=storage_type,
        local=local, version=version,
    ):
        raise test_exceptions.DataCenterException(
            "addDataCenter %s with storage type %s and version %s failed." % (
                datacenter,
                storage_type,
                version,
            )
        )
    logger.info("Datacenter %s was created successfully", datacenter)

    if not ll_clusters.addCluster(
        True, name=cluster, cpu=cpuName, data_center=datacenter,
        version=version,
    ):
        raise test_exceptions.ClusterException(
            "addCluster %s with cpu_type %s and version %s "
            "to datacenter %s failed" % (
                cluster, cpuName, version, datacenter
            )
        )
    logger.info("Cluster %s was created successfully", cluster)

    hl_hosts.add_hosts(hosts_ip, [password] * len(hosts_ip), cluster)
    host_array = [ll_hosts.get_host_name_from_engine(h.ip) for h in hosts_obj]

    # setting up cpu_model
    cpu_den = cpumodel.CpuModelDenominator()
    try:
        cpu_info = cpu_den.get_common_cpu_model(hosts_obj, version=version)
    except cpumodel.CpuModelError as ex:
        logger.error("Can not determine the best cpu_model: %s", ex)
    else:
        logger.info("Cpu info %s for cluster: %s", cpu_info, cluster)
        if not ll_clusters.updateCluster(True, cluster, cpu=cpu_info['cpu']):
            logger.error(
                "Can not update cluster cpu_model to: %s", cpu_info['cpu']
            )

    storage = configobj.ConfigObj()
    storage['lun_address'] = [lun_address]
    storage['lun_target'] = [lun_target]
    storage['lun'] = test_utils.split(luns)

    if not hl_storagedomains.create_storages(
        storage, storage_type, host_array[0], datacenter
    ):
        raise test_exceptions.StorageDomainException(
            "Can not add storages: %s" % storage
        )

    for host_name, host_obj in zip(host_array, hosts_obj):
        host_auto_nics = []
        for index in auto_nics:
            host_auto_nics.append(host_obj.nics[index])

        try:
            logger.info("Cleaning %s interfaces", host_name)
            ll_hosts.sendSNRequest(
                True, host=host_name, auto_nics=host_auto_nics,
                check_connectivity='true',
                connectivity_timeout=CONNECTIVITY_TIMEOUT, force='false'
            )
            ll_hosts.commitNetConfig(True, host=host_name)

        except Exception as ex:
            logger.error(
                "Cleaning host interfaces failed %s", ex, exc_info=True
            )
            return False

    if vmName:
        if not ll_vms.createVm(
            True, vmName=vmName, vmDescription='linux vm', cluster=cluster,
            nic=nic, storageDomainName=storageDomainName, size=size,
            diskInterface="virtio", nicType=nicType,
            display_type=display_type, os_type=os_type, image=image,
            user=vm_user, password=vm_password, installation=True,
            network=mgmt_network, useAgent=True, diskType=diskType,
            attempt=attempt, interval=interval,
            placement_host=placement_host, vnic_profile=vnic_profile
        ):
            logger.error("Cannot create VM")
            return False

    if template_name:
        if useAgent:
            ip_addr = ll_vms.waitForIP(vmName)[1]['ip']
        else:
            rc, out = ll_vms.getVmMacAddress(True, vm=vmName)
            mac_addr = out['macAddress'] if rc else None
            rc, out = test_utils.convertMacToIpAddress(True, mac_addr)
            ip_addr = out['ip'] if rc else None
        if not test_utils.setPersistentNetwork(
            host=ip_addr, password=vm_password
        ):
            logger.error("Failed to setPersistentNetwork")
            return False

        if not ll_vms.stopVm(True, vm=vmName):
            logger.error("Failed to stop VM")
            return False

        if not ll_templates.createTemplate(
                True, vm=vmName, cluster=cluster, name=template_name
        ):
            logger.error("Failed to create template")
            return False

        if not ll_vms.startVm(True, vm=vmName):
            logger.error("Can't start VM")
            return False
        if not ll_vms.waitForVmsStates(
            True, names=vmName, timeout=TIMEOUT, states='up'
        ):
            logger.error("VM status is not up in the predefined timeout")

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

    host_exec = host.executor()
    for i in range(num_dummy):
        cmd = ["ip", "link", "add", dummy_int % i, "type", "dummy"]
        rc, out, error = host_exec.run_cmd(cmd)
        if rc:
            logger.error(
                "Create %s interfaces failed. ERR: %s. %s", i, out, error
            )
            return False

        nic_name = dummy_int % i
        host.network.create_ifcfg_file(nic=nic_name, params=ifcfg_params)

    logger.info(
        host_exec.run_cmd([IP_CMD, "a", "l", "|", "grep", "dummy"])[1]
    )
    return True


def delete_dummy_interfaces(host):
    """
    Delete dummy network interfaces on host

    :param host: VDS
    :type host: resources.VDS
    :return: True/False
    :rtype: bool
    """
    host_obj = host.executor()
    rhevh = (host.get_os_info()["dist"] == RHEVH)

    rc, out, err = host_obj.run_cmd(["ip", "link", "|", "grep", "dummy"])
    if rc:
        logger.error(
            "Failed to run ip link command on %s. ERR: %s", host.fqdn, err
        )
        return False

    dummy_list_ = out.splitlines()
    dummy_list = [
        re.search('([\s])([\w.]+)', i).groups()[1]
        for i in dummy_list_ if 'vdsm' not in i
        ]

    for i in dummy_list:
        cmd = ["ip", "link", "del", i]
        rc, out, err = host_obj.run_cmd(cmd)
        if rc:
            logger.error("Failed to delete %s. ERR: %s. %s", i, out, err)
            return False

        ifcfg_file = "/etc/sysconfig/network-scripts/ifcfg-%s" % i
        logger.info("Check if %s exists", ifcfg_file)
        if host.fs.isfile(ifcfg_file):
            if rhevh:
                logger.info("unpersist %s", ifcfg_file)
                rc, out, err = host_obj.run_cmd(["unpersist", ifcfg_file])
                if rc:
                    logger.error(
                        "Failed to unpersist %s. ERR: %s. %s",
                        ifcfg_file, out, err
                    )
                    return False

            logger.info("Deleting %s", ifcfg_file)
            if not host.fs.remove(ifcfg_file):
                logger.error("Failed to delete %s", ifcfg_file)
                return False
    return True


def updateAndSyncMgmtNetwork(datacenter, hosts=list(), nic=[0], auto_nics=[],
                             network=None, bridge=True):
    """
    Function that update existing network on DC and on the host, then sync it
    using SetupNetworks. This function created to enable run tests with
    management network as bridgeless network.
    :param datacenter: Datacenter to update the management network.
    :param hosts: list of resources.VDS objects.
    :param nic: the nic (ETH(X)) of the management network.
    :param network: The management network.
    :param bridge: Desired network mode (True for bridge,
                   False for bridgeless).
    :param auto_nics: Host nics to preserve on setupNetworks command.
    """
    hosts_obj = [hosts] if not isinstance(hosts, list) else hosts
    hosts_list = [ll_hosts.get_host_name_from_engine(h.ip) for h in hosts_obj]
    mgmt_net_type = "bridge" if bridge else "bridgeless"
    network_type = "vm" if bridge else ""

    logger.info("Updating %s to %s network", network, mgmt_net_type)
    if not ll_networks.updateNetwork(
        positive=True, network=network, data_center=datacenter,
        usages=network_type
    ):
        logger.error("Failed to set %s as %s network",
                     network, mgmt_net_type)
        return False

    for host_name, host_obj in zip(hosts_list, hosts_obj):
        host_auto_nics = []
        for index in auto_nics:
            host_auto_nics.append(host_obj.nics[index])

        host_nic = ll_hosts.getHostNic(host=host_name, nic=nic)
        host_nic.set_override_configuration(True)

        logger.info(
            "setupNetwork: syncing %s network on %s", network, host_name
        )
        if not ll_hosts.sendSNRequest(
            True, host=host_name, nics=[host_nic], auto_nics=host_auto_nics,
            check_connectivity='true',
            connectivity_timeout=CONNECTIVITY_TIMEOUT, force='false'
        ):
            logger.error(
                "setupNetwork: Cannot sync %s network on %s",
                network, host_name
            )
            return False

        ll_hosts.commitNetConfig(True, host=host_name)

    return True


class TrafficMonitor(object):
    '''
    A context manager for capturing traffic while concurrently running other
    functions. The traffic is captured using the 'checkTraffic' function
    while running the other functions with it.

    Example usage:

    with TrafficMonitor(machine='navy-vds1.qa.lab.tlv.redhat.com',
                        user='root', password='qum5net', nic='eth0',
                        src='10.35.128.1', dst='10.35.128.2',
                        protocol='icmp', numPackets=5) as monitor:

        monitor.addTask(sendICMP, host='10.35.128.1', user='root',
                        password='qum5net', ip='10.35.128.2')

    self.assertTrue(monitor.getResult())

    **Author**: tgeft
    '''

    def __init__(self, expectedRes=True, timeout=100, *args, **kwargs):
        '''
        Sets the parameters for capturing the traffic with the 'checkTraffic'
        function.

        **Parameters**:
            *  *expectedRes* - A boolean to indicate if traffic is expected
            *  *timeout* - Timeout for the total duration of the capture and
                           the functions that run with it.
            *  *args* - The positional arguments to be passed to 'checkTraffic'
                        (for example: machine, user, password, nic, src, dst)
            *  *kwargs* - The keyword arguments to be passed to 'checkTraffic'
                          (for example: srcPort, dstPort, protocol, numPackets)
        '''
        # A list that will hold all the jobs that will be executed
        self.jobs = [self._createCapturingJob(*args, **kwargs)]

        # A list that will hold the expected results of all the jobs
        self.expectedResults = [expectedRes]

        self.timeout = timeout

    def addTask(self, func, expectedRes=True, *args, **kwargs):
        '''
        Adds a function to run while traffic is being captured.

        **Parameters**:
            *  *func* - The function to run
            *  *expectedRes* - Expected output of 'func' (True by default)
            *  *args* - The positional arguments to be passed to 'func'
            *  *kwargs* - The keyword arguments to be passed to 'func'
        '''
        self.jobs.append(jobs.Job(func, args, kwargs))
        self.expectedResults.append(expectedRes)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        '''
        Run all the jobs and report the results.
        '''
        jobSet = jobs.JobsSet()
        jobSet.addJobs(self.jobs)
        jobSet.start()
        jobSet.join(self.timeout)

        result = True  # Overall result of the capture
        for job, expectedResult in zip(self.jobs, self.expectedResults):
            if job.exception:
                logger.error('%s raised an exception: %s', self.__jobInfo(job),
                             job.exception)
                result = False

            elif job.result != expectedResult:
                logger.error('%s failed - return value: %s, expected: %s',
                             self.__jobInfo(job), job.result, expectedResult)
                result = False

            else:
                logger.info('%s succeeded', self.__jobInfo(job))

        self.result = result

    def getResult(self):
        '''
        Get the result of the capture.

        **Return**: True if all the functions returned the expected results,
                    False otherwise.
        '''
        return self.result

    @staticmethod
    def _createCapturingJob(*args, **kwargs):
        '''
        Returns the Job object that will capture traffic when executed (can be
        modified for extensibility)
        '''
        return jobs.Job(test_utils.checkTraffic, args, kwargs)

    @staticmethod
    def __jobInfo(job):
        '''
        Returns a string representation of the function call that the job ran
        '''
        args = str(job.args)[1:-1]  # Strip brackets from the arguments list
        kwargs = '**%s' % job.kwargs if job.kwargs else ''
        return 'Func %s(%s)' % (job.target.__name__,
                                ', '.join(filter(None, [args, kwargs])))


def remove_all_networks(datacenter=None, cluster=None,
                        mgmt_network=None):
    """
    Description: Remove all networks from DC/CL or from entire setup
    If cluster is specified - remove all network from specified cluster
    Elif datacenter is specified - remove all networks from specified DC
    If no datacenter or cluster are specified remove all networks from all DCs
    In all cases we don't remove rhevm network
    **Author**: myakove
    **Editor**: mpavlik
    **Parameters**:
        *  *datacenter* - name of the datacenter
        *  *cluster* - name of the cluster
        *  *mgmt_netowrk* - name of management network (to be excluded from
        removal)

    **Returns**: True if removing networks succeeded, otherwise False
    """
    networks_to_remove = []

    if cluster:
        cl_networks = ll_networks.getClusterNetworks(cluster)
        networks_list = ll_networks.NET_API.get(cl_networks)
        removal_area = "cluster " + cluster

    elif datacenter:
        networks_list = ll_networks.get_networks_in_datacenter(datacenter)
        removal_area = "datacenter " + datacenter

    else:
        networks_list = ll_networks.NET_API.get(absLink=False)
        removal_area = "all clusters and all data centers"

    for net in networks_list:
        if net.name != mgmt_network:
            networks_to_remove.append(net.name)

    if not networks_to_remove:
        logger.info("There is no network to be removed")
        return True

    network = "network" if len(networks_to_remove) == 1 else "networks: "

    logger.info("Removing %s %s from %s",
                network,
                ', '.join(networks_to_remove),
                removal_area)

    return removeMultiNetworks(True, networks_to_remove, datacenter)


def networkTeardown(datacenter, storagedomain, hosts=list(), auto_nics=list(),
                    mgmt_net=None):
    '''
    Description: Network jobs teardown for unittests, set mgmt network to
                 bridge network (default) and run cleanDataCenter function
    **Author**: myakove
    **Parameters**:
        *  *datacenter* - name of the datacenter
        *  *storagedomain* - name of the storage domain
        *  *hosts* - list of hosts
        *  *auto_nics* - list of host nics for setupnetwork
        *  *bridge* - True for bridge network, False for bridgeless
        *  *mgmt_net* - Management network.
    return True/False
    '''
    logger.info("Updating %s network to bridge network", mgmt_net)
    if not updateAndSyncMgmtNetwork(datacenter=datacenter, hosts=hosts,
                                    auto_nics=auto_nics, bridge=True,
                                    network=mgmt_net):
        logger.error("Failed to set %s network as bridge", mgmt_net)
        return False

    logger.info("Wait for storage domain %s to be active", storagedomain)
    if not ll_storagedomains.waitForStorageDomainStatus(
        positive=True, dataCenterName=datacenter,
        storageDomainName=storagedomain, expectedStatus="active"
    ):
        logger.error("StorageDomain %s state is not UP", storagedomain)
        return False

    logger.info("Wait for %s to be UP", datacenter)
    if not ll_datacenters.waitForDataCenterState(name=datacenter):
        logger.error("%s is not in UP state")
        return False

    logger.info("Running clean Datacenter")
    if not hl_datacenter.clean_datacenter(
        positive=True, datacenter=datacenter
    ):
        raise test_exceptions.DataCenterException("Cannot remove setup")

    return True


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
    host_nic = ll_hosts.getHostNic(host=host, nic=nic)
    return host_nic.get_ip().get_address()


def checkICMPConnectivity(host, user, password, ip, max_counter=MAX_COUNTER,
                          packet_size=None):
    '''
    Description: Checks ICMP connectivity till max_counter time expires
    **Author**: gcheresh
    **Parameters**:
        *  *host* - IP or FDQN of the host originating ICMP traffic
        *  *username* - host username
        *  *password* - host password
        *  *ip* - distination IP address for ICMP traffic
        *  *max_counter* - max number of calls for sendICMP command
        *  *packet_size* - size of packet to send
    **Returns**: True if ICMP connectivity was established, otherwise False
    '''
    while (max_counter):
        if not test_utils.sendICMP(
            host=host, user=user, password=password, ip=ip, count=1,
            packet_size=packet_size
        ):
            max_counter -= 1
        else:
            return True
    return False


def checkHostNicParameters(host, nic, **kwargs):
    """
    Description: Check MTU, VLAN interface and bridge (VM/Non-VM) host nic
    parameters .
    Author: myakove
    Parameters:
       *  *host* - Host name
       *  *nic* - Nic to get parameters from
       *  *vlan_id* - expected VLAN id on the host
       *  *mtu* - expected mtu on the host
       *  *bridge* - Expected VM, Non-VM network (True for VM, False for
           Non-VM)
    **Return**: True if action succeeded, otherwise False
    """
    res = True
    host_nic = ll_hosts.getHostNic(host, nic)

    if kwargs.get("bridge") is not None:
        bridged = host_nic.get_bridged()
        if kwargs.get("bridge") != bridged:
            logger.error("%s interface is bridge: %s, expected is %s", nic,
                         bridged, kwargs.get("bridge"))
            res = False

    if kwargs.get("vlan_id"):
        vlan_nic = ".".join([nic, kwargs.get("vlan_id")])
        try:
            ll_hosts.getHostNic(host, vlan_nic)
        except apis_exceptions.EntityNotFound:
            logger.error("Fail to get %s interface from %s", vlan_nic, host)
            res = False

    if kwargs.get("mtu"):
        mtu = host_nic.get_mtu()
        if int(kwargs.get("mtu")) != mtu:
            logger.error("MTU value on %s is %s, expected is %s", nic, mtu,
                         kwargs.get("mtu"))
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
    nic_obj = ll_hosts.getHostNic(host=host, nic=nic)
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
