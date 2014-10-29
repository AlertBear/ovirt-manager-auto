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
import re
import os
from configobj import ConfigObj

from utilities import machine
from art.rhevm_api.utils.test_utils import restartVdsmd, sendICMP
from art.rhevm_api.tests_lib.low_level.networks import (
    addNetwork, getClusterNetwork, getNetworksInDataCenter, removeNetwork,
    addNetworkToCluster, NET_API, DC_API, updateNetwork, getClusterNetworks,
    MGMT_NETWORK,
)
from art.rhevm_api.tests_lib.low_level.hosts import (
    sendSNRequest, commitNetConfig, genSNNic, getHostNic, removeHost,
    get_host_name_from_engine)
from art.rhevm_api.tests_lib.low_level.templates import createTemplate
from art.rhevm_api.tests_lib.low_level.vms import (
    getVmMacAddress, startVm, stopVm, createVm, waitForVmsStates,
    waitForIP)
from art.rhevm_api.utils.test_utils import (
    convertMacToIpAddress, setPersistentNetwork,
)
from art.rhevm_api.tests_lib.low_level.storagedomains import (
    waitForStorageDomainStatus, cleanDataCenter,
)
from art.rhevm_api.tests_lib.low_level.clusters import (
    addCluster, removeCluster,
)
from art.rhevm_api.tests_lib.high_level.storagedomains import (
    create_storages,
)
from art.rhevm_api.tests_lib.high_level.hosts import (
    add_hosts,
)
from art.rhevm_api.tests_lib.low_level.datacenters import (
    waitForDataCenterState, addDataCenter, removeDataCenter,
)
from art.test_handler.exceptions import (
    DataCenterException, HostException, ClusterException,
    StorageDomainException,
)
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api import is_action
from art.test_handler.settings import opts
from art.rhevm_api.utils.test_utils import checkTraffic, split
from utilities.jobs import Job, JobsSet

ENUMS = opts['elements_conf']['RHEVM Enums']

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

# command variables
IP_CMD = "/sbin/ip"
MODPROBE_CMD = "/sbin/modprobe"


@is_action()
def addMultipleVlanedNetworks(networks, data_center, **kwargs):
    '''
    Adding multiple networks with vlan according to the given prefix and range
    Author: atal
    Parameters:
        * networks - a list of vlaned networks with their vlan suffix
        * date_center - the DataCenter name
        * kwargs - all arguments related to basic addNetwork
    return True with new nics name list or False with empty list
    '''

    for network in networks:
        vlan = re.search(r'(\d+)', network)
        if not addNetwork('True', name=network, data_center=data_center,
                          vlan_id=vlan.group(0), **kwargs):
            return False
    return True


# FIXME: need to check if this function is being used else just remove.
@is_action()
def getNetworkConfig(positive, cluster, network, datacenter=None, tag=None):
    '''
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
    '''
    try:
        netObj = getClusterNetwork(cluster, network)
    except EntityNotFound:
        return False, {'value': None}

    # validate cluster network related to the given datacenter
    if datacenter:
        try:
            dcObj = DC_API.find(datacenter)
        except EntityNotFound:
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
@is_action()
def validateNetwork(positive, cluster, network, tag, val):
    status, output = getNetworkConfig(positive, cluster, network, tag=tag)
    return bool(status and str(output['value']).lower() == str(val).lower())


@is_action()
def removeMultiNetworks(positive, networks, data_center=None):
    '''
    Remove Multiple networks
    Author: atal
    Parameters:
        * positive - expected state that the function should return
        * networks- a list of networks
        * data_center - In case more then one network with the same name
                        exists.
    return  True if remove networks succeeded, otherwise False
    '''
    for net in networks:
        if not removeNetwork(positive, net, data_center):
            logger.error("Failed to remove %s", net)
            return False
    return True


def createAndAttachNetworkSN(data_center=None, cluster=None, host=[],
                             auto_nics=[], save_config=False,
                             network_dict={}, vlan_auto_nics={}):
    """
    Function that creates and attach the network to the:
    a) DC, b) Cluster, c) Hosts with SetupNetworks
    **Author**: gcheresh
    :param data_center: DC name
    :param cluster: Cluster name
    :param host: list of resources.VDS objects
    :param auto_nics: a list of nics indexes to preserve
    :param save_config: flag for saving configuration
    :param vlan_auto_nics: dictionary for auto_nics with vlan.
    for example vlan_auto_nics = {162: 0} where 162 is the vlan ID and
    0 is the host_nic index. (all int)
    :param network_dict: dictionary of dictionaries for the following
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
    """
    # Makes sure host_list is always a list
    host_list = [host] if not isinstance(host, list) else host

    for net, net_param in network_dict.items():
        if data_center and net:
            logger.info("Adding network to DC")
            if not addNetwork(True, name=net, data_center=data_center,
                              usages=net_param.get('usages', 'vm'),
                              vlan_id=net_param.get('vlan_id'),
                              mtu=net_param.get('mtu'),
                              profile_required=net_param.get(
                                  'profile_required')):
                logger.info("Cannot add network to DC")
                return False

        if cluster and net:
            logger.info("Adding network to Cluster")
            if not addNetworkToCluster(True, network=net, cluster=cluster,
                                       required=net_param.
                                       get('required', "true"),
                                       usages=net_param.
                                       get('cluster_usages', None)):
                logger.info("Cannot add network to Cluster")
                return False

    for host in host_list:
        host_name = get_host_name_from_engine(host.ip)

        logger.info("Found host name: %s", host_name)

        host_auto_nics = []
        for index in auto_nics:
            host_auto_nics.append(host.nics[index])

        for key, val in vlan_auto_nics.iteritems():
            host_int = host.nics[val]
            host_vlan_int = ".".join([host_int, str(key)])
            host_auto_nics.append(host_vlan_int)

        net_obj = []
        for net, net_param in network_dict.items():
            slaves = None
            param_slaves = net_param.get('slaves')
            param_nic = net_param.get('nic')
            param_vlan = net_param.get('vlan_id')

            if param_slaves:
                slaves = [host.nics[s] for s in param_slaves]

            nic = (
                param_nic if "bond" in str(param_nic) else host.nics[param_nic]
            )

            if 'vlan_id' in net_param:
                vlan_interface = "{0}.{1}".format(nic, param_vlan)

            address_list = net_param.get('address', [])
            netmask_list = net_param.get('netmask', [])
            gateway_list = net_param.get('gateway', [])

            nic = (
                vlan_interface if 'vlan_id' in net_param else nic
            )

            rc, out = genSNNic(nic=nic, network=net,
                               slaves=slaves,
                               mode=net_param.get('mode', None),
                               boot_protocol=net_param.get('bootproto', None),
                               address=address_list.pop(0)
                               if address_list else None,
                               netmask=netmask_list.pop(0)
                               if netmask_list else None,
                               gateway=gateway_list.pop(0)
                               if gateway_list else None,
                               properties=net_param.get('properties', None))

            if not rc:
                logger.error("Cannot generate network object")
                return False
            net_obj.append(out['host_nic'])

        logger.info("Sending SN request to host %s" % host_name)

        if not sendSNRequest(True,
                             host=host_name,
                             nics=net_obj,
                             auto_nics=host_auto_nics,
                             check_connectivity='true',
                             connectivity_timeout=60, force='false'):
            logger.info("Failed to send SN request to host %s" % host_name)
            return False

        if save_config:
            logger.info("Saving network configuration on host %s" % host_name)
            if not commitNetConfig(True, host=host_name):
                logger.error("Couldn't save network configuration")

    return True


def remove_net_from_setup(host, auto_nics=[0], network=[], data_center=None,
                          all_net=False, mgmt_network=None):
    """
    Function that removes networks from the host, Cluster and DC:
    :param host: list of resources.VDS objects
    :param auto_nics: a list of nics indexes
    :param network: list of networks to remove
    :param data_center: DC where the network is
    :param all_net: True to remove all networks from setup (except MGMT net)
    :param mgmt_network: Management network
    :return: True value if succeeded in deleting networks
            from Hosts, Cluster, DC
    """
    hosts_obj = [host] if not isinstance(host, list) else host
    hosts_list = [get_host_name_from_engine(h.ip) for h in hosts_obj]

    if all_net:
        if not remove_all_networks(
                datacenter=data_center, mgmt_network=mgmt_network
        ):
            return False
    else:
        if not removeMultiNetworks(True, network, data_center):
            return False

    try:
        for host_name, host_obj in zip(hosts_list, hosts_obj):
            host_auto_nics = []
            for index in auto_nics:
                host_auto_nics.append(host_obj.nics[index])

            sendSNRequest(True, host=host_name,
                          auto_nics=host_auto_nics,
                          check_connectivity='true',
                          connectivity_timeout=CONNECTIVITY_TIMEOUT,
                          force='false')
            commitNetConfig(True, host=host_name)

    except Exception as ex:
        logger.error("Remove Network from setup failed %s", ex, exc_info=True)
        return False
    return True


@is_action()
def prepareSetup(hosts, cpuName, username, password, datacenter,
                 cluster, version, storage_type, local=False,
                 storageDomainName=None, lun_address='', lun_target='',
                 luns='', lun_port=LUN_PORT,
                 diskType='system', auto_nics=[0],
                 vm_user='root', vm_password=None,
                 vmName=None, vmDescription='linux vm',
                 nicType='virtio', display_type='spice',
                 os_type='RHEL6x64', image=RHEL_IMAGE,
                 nic='nic1', size=DISK_SIZE, useAgent=True,
                 template_name=None, attempt=ATTEMPTS,
                 interval=INTERVAL, placement_host=None,
                 mgmt_network=MGMT_NETWORK, vnic_profile=None):
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
    hosts_fqdn = [h.fqdn for h in hosts_obj]

    if not addDataCenter(
        True, name=datacenter, storage_type=storage_type,
        local=local, version=version,
    ):
        raise DataCenterException(
            "addDataCenter %s with storage type %s and version %s failed." % (
                datacenter,
                storage_type,
                version,
            )
        )
    logger.info("Datacenter %s was created successfully", datacenter)

    if not addCluster(
        True, name=cluster, cpu=cpuName, data_center=datacenter,
        version=version,
    ):
        raise ClusterException(
            "addCluster %s with cpu_type %s and version %s "
            "to datacenter %s failed" % (
                cluster, cpuName, version, datacenter
            )
        )
    logger.info("Cluster %s was created successfully", cluster)

    add_hosts(hosts_fqdn, [password] * len(hosts_fqdn), cluster)
    host_array = [get_host_name_from_engine(h.ip) for h in hosts_obj]

    storage = ConfigObj()
    storage['lun_address'] = [lun_address]
    storage['lun_target'] = [lun_target]
    storage['lun'] = split(luns)

    if not create_storages(
        storage, storage_type, host_array[0], datacenter
    ):
        raise StorageDomainException("Can not add storages: %s" % storage)

    for host_name, host_obj in zip(host_array, hosts_obj):
        host_auto_nics = []
        for index in auto_nics:
            host_auto_nics.append(host_obj.nics[index])

        try:
            logger.info("Cleaning %s interfaces", host_name)
            sendSNRequest(True, host=host_name,
                          auto_nics=host_auto_nics,
                          check_connectivity='true',
                          connectivity_timeout=CONNECTIVITY_TIMEOUT,
                          force='false')
            commitNetConfig(True, host=host_name)

        except Exception as ex:
            logger.error("Cleaning host interfaces failed %s", ex,
                         exc_info=True)
            return False

    if vmName:
        if not createVm(True, vmName=vmName,
                        vmDescription='linux vm', cluster=cluster,
                        nic=nic, storageDomainName=storageDomainName,
                        size=size, diskInterface="virtio",
                        nicType=nicType,
                        display_type=display_type, os_type=os_type,
                        image=image, user=vm_user,
                        password=vm_password, installation=True,
                        network=mgmt_network,
                        useAgent=True, diskType=diskType,
                        attempt=attempt, interval=interval,
                        placement_host=placement_host,
                        vnic_profile=vnic_profile):
            logger.error("Cannot create VM")
            return False

    if template_name:
        try:
            if useAgent:
                ip_addr = waitForIP(vmName)[1]['ip']
            else:
                rc, out = getVmMacAddress(True, vm=vmName, nic='nic1')
                mac_addr = out['macAddress'] if rc else None
                rc, out = convertMacToIpAddress(True, mac_addr)
                ip_addr = out['ip'] if rc else None
            setPersistentNetwork(host=ip_addr, password=vm_password)
            stopVm(True, vm=vmName)
            createTemplate(True, vm=vmName, cluster=cluster,
                           name=template_name)
        except Exception as ex:
            logger.error("Creating template failed %s", ex,
                         exc_info=True)
            return False
        if not startVm(True, vm=vmName):
            logger.error("Can't start VM")
            return False
        if not waitForVmsStates(True, names=vmName, timeout=TIMEOUT,
                                states='up'):
            logger.error("VM status is not up in the predefined timeout")

    return True


def create_dummy_interfaces(host, username, password, num_dummy=1):
    """
    create (X) dummy network interfaces on host
    :param host: IP or FDQN of the host
    :param username* - host username
    :param password* - host password
    :param num_dummy* - number of dummy interfaces to create
    :return: True if creation of the dummy interface succeeded,
    otherwise False
    """
    host_obj = machine.Machine(host, username, password).util(machine.LINUX)

    dummy_list = [MODPROBE_CMD, 'dummy', 'numdummies=' + str(num_dummy)]
    rc, out = host_obj.runCmd(dummy_list)

    append_dummy = ['/bin/sed', '-i', '/\\[vars\\]/a fake_nics=dummy*',
                    VDSM_CONF_FILE]

    if not rc:
        logger.error("Create dummy interfaces failed. ERR: %s", out)
        return False

    logger.info(host_obj.runCmd([IP_CMD, "a", "l", "|", "grep", "dummy"])[1])

    logger.info("Adding dummy support to %s", VDSM_CONF_FILE)
    # detect RHEV-H
    os_type = host_obj.getOsInfo().lower()
    if HYPERVISOR in os_type:
        logger.info("RHEV-H detected")
        # unperist the file, change the file, persist the file
        with host_obj.edit_files_on_rhevh(VDSM_CONF_FILE):
            rc, out = host_obj.runCmd(append_dummy)
    else:
        rc, out = host_obj.runCmd(append_dummy)
    if not rc:
        logger.error("Add dummy support to VDSM conf file failed. ERR: %s",
                     out)
        return False

    for n in range(num_dummy):
        ifcfg_file_name = "dummy%s" % n
        if not host_obj.addNicConfFile(nic=ifcfg_file_name):
            return False

    return True


def delete_dummy_interfaces(host, username, password):
    """
    Delete dummy network interfaces on host
    :param host: IP or FDQN of the host
    :param username: host username
    :param password: host password
    return: True if deletion of the dummy interface succeeded,
    otherwise False
    """
    host_obj = machine.Machine(host, username, password).util(machine.LINUX)

    logger.info("Unloading dummy module")
    unload_dummy = [MODPROBE_CMD, "-r", "dummy"]
    host_obj.runCmd(unload_dummy)

    logger.info("Removing dummy support")
    dummy_remove = ["/bin/sed", "-i", "'/^fake_nics/d'", VDSM_CONF_FILE]
    # detect RHEV-H
    os_type = host_obj.getOsInfo().lower()
    if HYPERVISOR in os_type:
        logger.info("RHEV-H detected")
        # make sure dummy0 does not exist so module can be unloaded WA for
        # BZ1107969
        assert rhevh_remove_dummy(host, username, password)

        # unpersist the file, change the file, persist the file
        with host_obj.edit_files_on_rhevh(VDSM_CONF_FILE):
            rc, out = host_obj.runCmd(dummy_remove)
    else:
        rc, out = host_obj.runCmd(dummy_remove)
    if not rc:
        logger.error("Removing dummy support from %s failed ERR: %s",
                     VDSM_CONF_FILE, out)
        return False
    logger.info("Dummy support removed")

    logger.info("Removing ifcg-dummy* files")
    delete_dummy_ifcfg = ["/bin/rm", "-f"]
    path = os.path.join(IFCFG_FILE_PATH, "ifcfg-dummy*")
    delete_dummy_ifcfg.append(path)
    host_obj.runCmd(delete_dummy_ifcfg)
    rc, out = host_obj.runCmd(["ls", path])
    if rc:
        logger.error("Delete dummy ifcfg file failed. ERR: %s", out)
        return False
    logger.info("ifcg-dummy* files removed")

    return True


def rhevh_remove_dummy(host, username, password):
    """
    Description: this function servers as workaround for #BZ1107969
    remove dummy0 interface
    unload dummy module
    **Author**: mpavlik
    **Parameters**:
        *  *host* - IP or FDQN of the host
        *  *username* - host username
        *  *password* - host password
     **Returns**: True if unloading of the dummy module succeeded,
                 otherwise False
    """
    host_obj = machine.Machine(host, username, password).util(machine.LINUX)
    dummy_args = [IP_CMD, "a", "l", "dummy0"]

    logger.info("Verifying there is no dummy0 interface left")
    rc, out = host_obj.runCmd(dummy_args)
    if rc:
        logger.warn("modprobe -r dummy failed. ERR: %s", out)
        logger.info("removing interface dummy0")
        rc, out = host_obj.runCmd([IP_CMD, "link", "del", "dev", "dummy0"])
        if not rc:
            logger.error("Removing dummy0 failed. ERR: %s", out)
            return False
        rc, out = host_obj.runCmd(dummy_args)
        if not rc:
            logger.info("Interface dummy0 succesfully removed")
            logger.info("retrying to unload dummy module")
            rc, out = host_obj.runCmd([MODPROBE_CMD, "-r", "dummy"])
            if not rc:
                logger.error("failed to unload dummy module ERR:%s", out)
                return False
            logger.info("module dummy unloaded")
    return True


def updateAndSyncMgmtNetwork(datacenter, hosts=list(), nic=[0], auto_nics=[],
                             network=MGMT_NETWORK, bridge=True):
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
    hosts_list = [get_host_name_from_engine(h.ip) for h in hosts_obj]
    mgmt_net_type = "bridge" if bridge else "bridgeless"
    network_type = "vm" if bridge else ""

    logger.info("Updating %s to %s network", network, mgmt_net_type)
    if not updateNetwork(positive=True, network=network,
                         data_center=datacenter, usages=network_type):
        logger.error("Failed to set %s as %s network",
                     network, mgmt_net_type)
        return False

    for host_name, host_obj in zip(hosts_list, hosts_obj):
        host_auto_nics = []
        for index in auto_nics:
            host_auto_nics.append(host_obj.nics[index])

        host_nic = getHostNic(host=host_name, nic=nic)
        host_nic.set_override_configuration(True)

        logger.info(
            "setupNetwork: syncing %s network on %s", network, host_name)
        if not sendSNRequest(True, host=host_name, nics=[host_nic],
                             auto_nics=host_auto_nics,
                             check_connectivity='true',
                             connectivity_timeout=CONNECTIVITY_TIMEOUT,
                             force='false'):
            logger.error("setupNetwork: Cannot sync %s network on %s",
                         network, host_name)
            return False

        commitNetConfig(True, host=host_name)

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
        self.jobs.append(Job(func, args, kwargs))
        self.expectedResults.append(expectedRes)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        '''
        Run all the jobs and report the results.
        '''
        jobSet = JobsSet()
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
        return Job(checkTraffic, args, kwargs)

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
                        mgmt_network=MGMT_NETWORK):
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
        cl_networks = getClusterNetworks(cluster)
        networks_list = NET_API.get(cl_networks)
        removal_area = "cluster " + cluster

    elif datacenter:
        networks_list = getNetworksInDataCenter(datacenter)
        removal_area = "datacenter " + datacenter

    else:
        networks_list = NET_API.get(absLink=False)
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
                    mgmt_net=MGMT_NETWORK):
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
    if not waitForStorageDomainStatus(positive=True, dataCenterName=datacenter,
                                      storageDomainName=storagedomain,
                                      expectedStatus="active"):
            logger.error("StorageDomain %s state is not UP", storagedomain)
            return False

    logger.info("Wait for %s to be UP", datacenter)
    if not waitForDataCenterState(name=datacenter):
        logger.error("%s is not in UP state")
        return False

    logger.info("Running clean Datacenter")
    if not cleanDataCenter(positive=True, datacenter=datacenter):
        raise DataCenterException("Cannot remove setup")

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
    host_nic = getHostNic(host=host, nic=nic)
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
        if not sendICMP(host=host, user=user, password=password,
                        ip=ip, count=1, packet_size=packet_size):
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
    host_nic = getHostNic(host, nic)

    if kwargs.get("bridge") is not None:
        bridged = host_nic.get_bridged()
        if kwargs.get("bridge") != bridged:
            logger.error("%s interface is bridge: %s, expected is %s", nic,
                         bridged, kwargs.get("bridge"))
            res = False

    if kwargs.get("vlan_id"):
        vlan_nic = ".".join([nic, kwargs.get("vlan_id")])
        try:
            getHostNic(host, vlan_nic)
        except EntityNotFound:
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
    if not addDataCenter(positive=True, name=datacenter,
                         storage_type=storage_type,
                         version=version):
        logger.error("Failed to add DC")
        return False

    if cluster:
        if not addCluster(positive=True, name=cluster,
                          cpu=cpu, data_center=datacenter,
                          version=version):
            logger.error("Failed to add Cluster")
            return False

        if host:
            host_list = [host] if isinstance(host, basestring) else host
            try:
                add_hosts(hosts_list=host_list, cluster=cluster,
                          passwords=[host_password] * len(host_list))
            except HostException:
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
            if not removeHost(positive=True, host=host,
                              deactivate=True):
                logger.error("Failed to remove host %s ", host)
                return False

        if not removeCluster(positive=True, cluster=cluster):
            logger.error("Failed to remove Cluster")
            return False

    if not removeDataCenter(positive=True, datacenter=datacenter):
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
    nic_obj = getHostNic(host=host, nic=nic)
    kwargs.update({'update': nic_obj})
    rc, out = genSNNic(nic=nic_obj, **kwargs)
    if not rc:
        logger.error("Cannot generate network object for nic")
        return False

    logger.info("Sending SN request to host %s", host)
    if not sendSNRequest(True,
                         host=host,
                         nics=[out['host_nic']],
                         auto_nics=auto_nics,
                         check_connectivity='true',
                         connectivity_timeout=60, force='false'):
        logger.error("Failed to send SN request to host %s", host)
        return False

    if save_config:
        logger.info("Saving network configuration on host %s" % host)
        if not commitNetConfig(True, host=host):
            logger.error("Couldn't save network configuration")
            return False
    return True
