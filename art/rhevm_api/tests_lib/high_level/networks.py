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

from utilities import machine
from art.rhevm_api.utils.test_utils import restartVdsmd
from art.rhevm_api.tests_lib.low_level.networks import addNetwork,\
    getClusterNetwork, DC_API, removeNetwork, addNetworkToCluster
from art.rhevm_api.tests_lib.low_level.hosts import sendSNRequest,\
    commitNetConfig, genSNNic
from art.rhevm_api.tests_lib.low_level.templates import createTemplate
from art.rhevm_api.tests_lib.low_level.vms import getVmMacAddress,\
    startVm, stopVm, createVm, waitForVmsStates
from art.rhevm_api.utils.test_utils import convertMacToIpAddress,\
    setPersistentNetwork
from art.rhevm_api.tests_lib.low_level.storagedomains import createDatacenter
from art.core_api.apis_exceptions import EntityNotFound
from art.core_api import is_action
from art.test_handler.settings import opts

ENUMS = opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger(__package__ + __name__)
CONNECTIVITY_TIMEOUT = 60
DISK_SIZE = 21474836480
LUN_PORT = 3260
INTERVAL = 2
ATTEMPTS = 600
TIMEOUT = 120
VDSM_CONF_FILE = "/etc/vdsm/vdsm.conf"
IFCFG_FILE_PATH = "/etc/sysconfig/network-scripts/"


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
        #doesn't contain the given network
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

    # in canse we only like to check if the network exists or not.
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
def removeMultiNetworks(positive, networks):
    '''
    Remove Multiple networks from cluster
    Author: atal
    Parameters:
        * networks- a list of networks
    return True/False
    '''
    for net in networks:
        if not removeNetwork(positive, net):
            return False
    return True


def createAndAttachNetworkSN(data_center=None, cluster=None, host=[],
                             auto_nics=[], save_config=False, network_dict={}):
    '''
        Function that creates and attach the network to the:
        a) DC, b) Cluster, c) Hosts with SetupNetworks
        **Author**: gcheresh
        **Parameters**:
        *  *data_center* - DC name
        *  *cluster* - Cluster name
        *  *host* - list or string of remote machine ip addresses or fqdns
        *  *auto_nics* - a list of nics
        *  * save_config* - flag for saving configuration
        *  *network_dict* - dictionary of dictionaries for the following
          net parameters:
            logical network name as the key for the following:
                *  *nic* - interface to create the network on
                *  *usages* - vm or ''  value (for VM or non-VM network)
                *  *cluster_usages* - migration and/or display
                    (can be set on one network)
                *  * vlan_id* - list of values, each value for specific network
                *  * mtu* - list of values, each value for specific network
                *  * required* - required/non-required network
                *  * bond* - bond name to create
                *  * slaves* - interfaces that the bond will be composed from
                *  * mode* - the mode of the bond
                *  * bootproto* - boot protocol (none, dhcp, static)
                *  * address* - list of IP addresses of the network
                     if boot is Static
                *  * netmask* - list of netmasks of the  network
                     if boot is Static
                *  * gateway* - list of gateways of the network
                     if boot is Static
        **Returns**: True value if succeeded in creating and adding net list
                to DC/Cluster and Host with all the parameters
    '''
    # Makes sure host_list is always a list
    host_list = [host] if isinstance(host, basestring) else host

    net_obj = []
    for net, net_param in network_dict.items():
        if data_center and net:
            logger.info("Adding network to DC")
            if not addNetwork(True, name=net, data_center=data_center,
                              usages=net_param.get('usages', 'vm'),
                              vlan_id=net_param.get('vlan_id'),
                              mtu=net_param.get('mtu')):
                logger.error("Cannot add network to DC")
                return False
        if cluster and net:
            logger.info("Adding network to Cluster")
            if not addNetworkToCluster(True, network=net, cluster=cluster,
                                       required=net_param.
                                       get('required'),
                                       usages=net_param.
                                       get('cluster_usages', None)):
                logger.error("Cannot add network to Cluster")
                return False
        # creating logical interface nic.vlan when host, vlan_id are provided
        if 'vlan_id' in net_param and host:
                net_param['nic'] = "%s.%s" % (net_param['nic'],
                                              net_param['vlan_id'])

    for host in host_list:
        net_obj = []
        for net, net_param in network_dict.items():
            address_list = net_param.get('address', [])
            netmask_list = net_param.get('netmask', [])
            gateway_list = net_param.get('gateway', [])

            rc, out = genSNNic(nic=net_param['nic'],
                               network=net,
                               slaves=net_param.get('slaves', None),
                               mode=net_param.get('mode', None),
                               boot_protocol=net_param.get
                               ('bootproto', None),
                               address=address_list.pop(0)
                               if address_list else None,
                               netmask=netmask_list.pop(0)
                               if netmask_list else None,
                               gateway=gateway_list.pop(0)
                               if gateway_list else None)

            if not rc:
                logger.error("Cannot generate network object")
                return False
            net_obj.append(out['host_nic'])

        logger.info("Sending SN request to host %s" % host)
        if not sendSNRequest(True,
                             host=host,
                             nics=net_obj,
                             auto_nics=auto_nics,
                             check_connectivity='true',
                             connectivity_timeout=60, force='false'):
            logger.error("Failed to send SN request to host %s" % host)
            return False
        if save_config:
            logger.info("Saving network configuration on host %s" % host)
            if not commitNetConfig(True, host=host):
                logger.error("Couldn't save network configuration")

    return True


def removeNetFromSetup(host, auto_nics=['eth0'], network=[]):
    '''
        Function that removes networks from the host, Cluster and DC:
        Author: gcheresh
        Parameters:
        * host - remote machine ip addresses or fqdns
        * auto_nics - a list of nics
        * network - list of networks to remove
        Return: True value if succeeded in deleting networks
                from Hosts, Cluster, DC
    '''
    host_list = [host] if isinstance(host, basestring) else host
    try:
        for index in range(len(network)):
            removeNetwork(True, network=network[index])

        for host_i in host_list:
            sendSNRequest(True, host=host_i,
                          auto_nics=auto_nics,
                          check_connectivity='true',
                          connectivity_timeout=CONNECTIVITY_TIMEOUT,
                          force='false')
            commitNetConfig(True, host=host_i)

    except Exception as ex:
        logger.error("Remove Network from setup failed %s", ex, exc_info=True)
        return False
    return True


@is_action()
def prepareSetup(hosts, cpuName, username, password, datacenter,
                 storage_type, cluster, version,
                 storageDomainName=None, lun_address='', lun_target='',
                 luns='', lun_port=LUN_PORT,
                 diskType='system', auto_nics=['eth0'],
                 vm_user='root', vm_password=None,
                 vmName='VMTest1', vmDescription='linux vm',
                 cobblerAddress=None, cobblerUser=None,
                 cobblerPasswd=None, nicType='virtio', display_type='spice',
                 os_type='RHEL6x64', image='rhel6.4-agent3.2',
                 nic='nic1', size=DISK_SIZE, useAgent=True,
                 template_name='tempTest1', attempt=ATTEMPTS,
                 interval=INTERVAL, placement_host=None,
                 vm_flag=True, template_flag=True):
    '''
        Function that creates DC, Cluster, Storage, Hosts
        It creates VM and Template if flag is on:
        **Author**: gcheresh
        **Parameters**:
            *  *hosts* - host\s name\s or ip\s.
                A single host, or a list of hosts separated by comma.
            *  *cpuName* - cpu type in the Cluster
            *  *username* - user name for the host machines
            *  *password* - password for the host machines
            *  *datacenter* - data center name
            *  *storage_type* - type of storage
            *  *cluster* - cluster name
            *  *version* - supported version like 3.1, 3.2...
            *  *storageDomainName* - name of the storage domain
            *  *lun_address* - address of iSCSI machine
            *  *lun_target* - LUN target
            *  *luns* - lun\s id.
                A single lun id, or a list of luns, separeted by comma.
            *  *lun_port* - lun port
            *  *diskType* - type of the disk
            *  *vm_user* - user name for the VM
            *  *vm_password* - password for the VM
            *  *auto_nics* - a list of nics
            *  *vmName* - VM name
            *  *vmDescription* - Decription of VM
            *  *cobblerAddress* - IP or hostname of cobbler server
            *  *cobblerUser* - username for cobbler
            *  *cobblerPasswd* - password for cobbler
            *  *display_type* - type of vm display (VNC or SPICE)
            *  *nicType* - type of the NIC (virtio, RTL or e1000)
            *  *os_type* - type of the OS
            *  *image* - profile in cobbler
            *  *nic* - nic name
            *  *size* - the size of the disk
            *  *useAgent* - Set to 'true', if desired to read the ip from VM.
                Agent exist on VM
            *  *template_name* - name of the template to create
            *  *attempt*- attempts to connect after installation
            *  *inerval* - interval between attempts
            *  *placement_host* - the host that will hold VM
            *  *vm_flag* - Set to true, if desired VM
            *  *template_flag* - set to true if desired template
        **Returns**: True if creation of the setup succeeded, otherwise False
    '''
    if not createDatacenter(True, hosts=hosts, cpuName=cpuName,
                            username=username, password=password,
                            datacenter=datacenter, storage_type=storage_type,
                            cluster=cluster, version=version,
                            lun_address=lun_address, lun_target=lun_target,
                            luns=luns, lun_port=lun_port):
        logger.error("Couldn't create setup (DC, Cluster, Storage, Host)")
        return False

    hostArray = hosts.split(',')
    for host in hostArray:
        try:
            sendSNRequest(True, host=host,
                          auto_nics=auto_nics,
                          check_connectivity='true',
                          connectivity_timeout=CONNECTIVITY_TIMEOUT,
                          force='false')
            commitNetConfig(True, host=host)
        except Exception as ex:
            logger.error("Cleaning host interfaces failed %s", ex,
                         exc_info=True)
            return False
    if vm_flag:
        if not createVm(True, vmName=vmName,
                        vmDescription='linux vm', cluster=cluster,
                        nic=nic, storageDomainName=storageDomainName,
                        size=size,
                        nicType=nicType,
                        display_type=display_type, os_type=os_type,
                        image=image, user=vm_user,
                        password=vm_password, installation=True,
                        cobblerAddress=cobblerAddress,
                        cobblerUser=cobblerUser,
                        cobblerPasswd=cobblerPasswd, network='rhevm',
                        useAgent=True, diskType=diskType,
                        attempt=attempt, interval=interval,
                        placement_host=placement_host):
            logger.error("Cannot create VM")
            return False
    if template_flag:
        try:
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


def createDummyInterface(host, username, password, num_dummy=1):
    '''
    Description: create (X) dummy network interfaces on host
    **Author**: myakove
    **Parameters**:
        *  *host* - IP or FDQN of the host
        *  *username* - host username
        *  *password* - host password
        *  *num_dummy* - number of dummy interfaces to create
    '''

    host_obj = machine.Machine(host, username, password).util(machine.LINUX)

    dummy_list = ['modprobe', 'dummy', 'numdummies=' + str(num_dummy)]
    rc, out = host_obj.runCmd(dummy_list)
    if not rc:
        logger.error("Create dummy interfaces failed. ERR: %s", out)
        return False

    rc, out = host_obj.runCmd(["/bin/sed", "-i", "'$afake_nics=dummy*'",
                               VDSM_CONF_FILE])
    if not rc:
        logger.error("Add dummy support to VDSM conf file failed. ERR: %s",
                     out)
        return False

    for n in range(num_dummy):
        ifcfg_file_name = "dummy%s" % n
        if not host_obj.addNicConfFile(nic=ifcfg_file_name):
            return False

    if not restartVdsmd(host, password, supervdsm=True):
        logger.error("Restart vdsm service failed")
        return False

    return True


def deleteDummyInterface(host, username, password):
    '''
    Description: Delete dummy network interfaces on host
    **Author**: myakove
    **Parameters**:
        *  *host* - IP or FDQN of the host
        *  *username* - host username
        *  *password* - host password
    '''
    host_obj = machine.Machine(host, username, password).util(machine.LINUX)

    rc, out = host_obj.runCmd(["/bin/sed", "-i", "'/^fake_nics/d'",
                               VDSM_CONF_FILE])
    if not rc:
        logger.error("Clean VDSM conf file failed. ERR: %s", out)
        return False

    unload_dummy = ["/sbin/modprobe", "-r", "dummy"]
    rc, out = host_obj.runCmd(unload_dummy)
    if not rc:
        logger.error("Unload dummy driver failed. ERR: %s", out)
        return False

    delete_dummy_ifcfg = ["/bin/rm", "-f"]
    path = os.path.join(IFCFG_FILE_PATH, "ifcfg-dummy*")
    delete_dummy_ifcfg.append(path)
    rc, out = host_obj.runCmd(delete_dummy_ifcfg)
    if not rc:
        logger.error("Delete dummy ifcfg file failed. ERR: %s", out)
        return False

    if not restartVdsmd(host, password, supervdsm=True):
        logger.error("Restart vdsm service failed")
        return False

    return True
