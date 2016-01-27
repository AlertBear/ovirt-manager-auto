"""
Libvirt test common functions
Author: Alex Jia <ajia@redhat.com>
"""

from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.rhevm_api.tests_lib.low_level import vms, hosts
from art.rhevm_api.tests_lib.high_level.networks import TrafficMonitor, \
    checkICMPConnectivity, getIpOnHostNic
from art.rhevm_api.tests_lib.high_level.vms import check_vm_migration
from art.rhevm_api.tests_lib.low_level.vms import getVmHost
from utilities import machine
from sys import modules

import art.rhevm_api.utils.storage_api as st_api
import art.rhevm_api.utils.iptables as ip_action
from art.rhevm_api.utils.test_utils import get_api

import art.test_handler.exceptions as exceptions
import config
import logging

__test__ = False

LOGGER = logging.getLogger(__name__)

__THIS_MODULE = modules[__name__]

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
SNAPSHOT_API = get_api('snapshot', 'snapshots')

DC_TYPE = config.DATA_CENTER_TYPE

GB = 1024 ** 3

NUM_PACKETS = 1000


def install_vm(vm_name, vm_description, disk_interface,
               sparse=True, volume_format=config.COW_DISK,
               nic=config.HOST_NICS[0], size=config.DISK_SIZE,
               disk_type=config.DISK_TYPE_SYSTEM,
               vm_type=config.VM_TYPE_DESKTOP,
               display_type=config.DISPLAY_TYPE,
               memory=config.GB, cpu_cores=config.CPU_CORES,
               cpu_socket=config.CPU_SOCKET,
               nic_type=config.NIC_TYPE_VIRTIO,
               os_type=config.OS_TYPE,
               user=config.VM_USER,
               password=config.VM_PASSWORD,
               image=config.COBBLER_PROFILE,
               network=config.MGMT_BRIDGE,
               use_agent=config.USE_AGENT,
               cluster=config.CLUSTER_NAME,
               sd_name=config.SD_NAME_0):
    """
    helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    LOGGER.info("Creating VM %s" % vm_name)
    return vms.createVm(True, vm_name, vm_description, cluster=cluster,
                        nic=nic, storageDomainName=sd_name, size=size,
                        diskType=disk_type, volumeType=sparse,
                        volumeFormat=volume_format,
                        diskInterface=disk_interface, memory=memory,
                        cpu_socket=cpu_socket, cpu_cores=cpu_cores,
                        nicType=nic_type, display_type=display_type,
                        os_type=os_type, user=user, password=password,
                        type=vm_type, installation=True, slim=True,
                        image=image, network=network, useAgent=use_agent)


def add_vm_with_nic(vm_name, net_name, boot_options='hd network',
                    cluster=config.CLUSTER_NAME, os_type=config.OS_TYPE,
                    interface=config.NIC_TYPE_VIRTIO,
                    network=config.MGMT_BRIDGE):
    """
    Add a VM w/ a network interface
    """
    vms_list = []

    if not vms.addVm(positive=True, name=vm_name,
                     description=vm_name,
                     cluster=cluster,
                     os_type=os_type, boot=boot_options):
        raise exceptions.VMException("Cannot add VM %s" % vm_name)
    LOGGER.info("Successfully added VM: %s." % vm_name)

    if not vms.addNic(positive=True, vm=vm_name, name=net_name,
                      interface=interface,
                      network=network):
        raise exceptions.VMException("Cannot add NICs into VM %s" % vm_name)
    LOGGER.info("Successfully added NIC into VM: %s." % vm_name)

    if vm_name not in vms_list:
        vms_list.append(vm_name)

    return vms_list


def add_disk_into_vm(vm_name, disk_size=1*GB,
                     storage_domain=config.SD_NAME_0,
                     disk_format=config.COW_DISK,
                     disk_type=config.DISK_TYPE_DATA,
                     interface=config.INTERFACE_VIRTIO):
    """
    Add a disk into VM
    """
    disk_list = []

    assert vms.addDisk(True, vm=vm_name, size=disk_size,
                       wait='True', storagedomain=storage_domain,
                       type=disk_type, format=disk_format,
                       sparse='true', interface=interface)
    LOGGER.info("Successfully added disk into VM: %s." % vm_name)

    if storage_domain not in disk_list:
        disk_list.append(storage_domain)

    return disk_list


def get_host(vm_name):
    """
    Return host the specific VM resides on
    """
    if not vm_name:
        return

    ret, out = getVmHost(vm_name)
    if not ret:
        raise exceptions.NetworkException("Cannot get host that VM resides on")

    return out['vmHoster']


def find_ip(vm_name, host_list, nic):
    """
    Return IP address of host the specific VM resides on
    """
    if not vm_name or not host_list or not nic:
        return None, None

    orig_host = get_host(vm_name)
    dst_host = host_list[(host_list.index(orig_host)+1) % len(host_list)]
    return getIpOnHostNic(orig_host, nic), getIpOnHostNic(dst_host, nic)


def block_storage(host, user, password, sd_address, block_network=False):
    """
    Block connection from one host to storage server.
    Wait until host goes to non-operational.
    """
    if not host or not user or not password or not sd_address:
        return False

    LOGGER.info("Blocking connection from %s to %s" % (host, sd_address))
    if block_network:
        st_api.blockOutgoingConnection(host, user, password, sd_address)
    else:
        ip_action.block_and_wait(host, user, password, sd_address, host)

    return True


def unblock_storage(host, user, password, sd_address, unblock_network=False):
    """
    Unblock connection.
    Check that the host is UP again.
    """
    if not host or not user or not password or not sd_address:
        return False

    LOGGER.info("Unblocking connection from %s to %s" % (host, sd_address))
    if unblock_network:
        st_api.unblockOutgoingConnection(host, user, password, sd_address)
    else:
        ip_action.unblock_and_wait(host, user, password, sd_address, host)

    return True


def tcms_case_id(tcms_tc_list):
    """
    To map DC type to tcms test case id
    @tcms_tc_list: a basic format is [$nfs_tcms_tc_id, $iscsi_tcms_tc_id] or
                   [$spice_tcms_tc_id, $vnc_tcms_tc_id]
    """
    tcms_tc_dict = {'nfs': tcms_tc_list[0], 'iscsi': tcms_tc_list[1]}

    if DC_TYPE in tcms_tc_dict.keys():
        return tcms_tc_dict[DC_TYPE]


def kill_all_vms(host, user, password):
    """
    Kill all VMs
    """
    if not host or not user or not password:
        return False

    host_obj = machine.Machine(host, user, password).util('linux')
    if not host_obj.isConnective():
        HOST_API.logger.error("No connectivity to the host %s" % host)

    hosts.killProcesses(host_obj, 'qemu')

    return True


def perform_actions(vm_name, action):
    """
    Perform actions on specific VM
    """
    if not vm_name or not action:
        return False

    action_types = {'start': vms.startVm,
                    'stop': vms.stopVm,
                    'suspend': vms.suspendVm,
                    'shutdown': vms.shutdownVm}

    if action in action_types.keys():
        LOGGER.info("Prepare to %s %s" % (action, vm_name))
        assert action_types[action](True, vm_name)

    return True


def get_vm_snapshots(vm_name, get_href=True):
    """
    Get snapshots of the VM and return snapshot list
    """
    if not vm_name:
        return

    vm_obj = VM_API.find(vm_name)
    return SNAPSHOT_API.getElemFromLink(vm_obj, get_href=get_href)


def create_live_snapshots(vm_name, iter_num=1):
    """
    Add live snapshots into VM and return snapshot name list
    """
    snap_name_list = []

    if not vm_name:
        return snap_name_list

    for i in range(int(iter_num)):
        snap_name = "SNAP_%s" % i
        logging.info("Creating live snapshot %s", snap_name)
        assert vms.addSnapshot(True, vm_name, snap_name)
        snap_name_list.append(snap_name)

    return snap_name_list


def remove_snapshots(vm_name, snap_name_list, timeout=30 * 60):
    """
    Remove snapshot from VM
    """
    if not vm_name or not snap_name_list:
        return False

    for snap_name in snap_name_list:
        logging.info("Removing snapshot %s", snap_name)
        assert vms.removeSnapshot(True, vm_name, snap_name, timeout)
    del snap_name_list

    return True


def create_one_more_sd(sd_args, i=1, status=True):
    """
    Helper function for creating one more SD
    Return: False if the storage domains was created failed,
            True otherwise
    """
    if not sd_args:
        return False

    i = int(i)

    sd_args['name'] = config.SD_NAMES_LIST[i]
    if DC_TYPE == 'nfs':
        sd_args['address'] = config.ADDRESS[i]
        sd_args['path'] = config.PATH[i]
    elif DC_TYPE == 'iscsi':
        sd_args['lun'] = config.LUNS[i]
        sd_args['lun_address'] = config.LUN_ADDRESS[i]
        sd_args['lun_target'] = config.LUN_TARGET[i]
        sd_args['lun_port'] = config.LUN_PORT

    LOGGER.info('Creating storage domain with parameters: %s', sd_args)
    return ll_st_domains.addStorageDomain(True, **sd_args) and status


def attach_and_activate_domain(dc_name, sd_name, attach=True,
                               activate=True):
    """
    Attach and active storage domain.
    """
    if attach:
        ll_st_domains.attachStorageDomain(True, datacenter=dc_name,
                                          storagedomain=sd_name)
    if activate:
        ll_st_domains.activateStorageDomain(True, datacenter=dc_name,
                                            storagedomain=sd_name)


def migrate_vm_more_than_once(vm_name, orig_host, ht_nic, src, dst,
                              iter_num=1, ht_user=config.VDS_USER,
                              ht_pwd=config.VDS_PASSWORD[0],
                              vm_user=config.VM_USER,
                              vm_pwd=config.VM_PASSWORD):
    """
    Migrate VM and return result
    """
    if not vm_name or not orig_host or not ht_nic or not src or not dst:
        return False

    for num in range(int(iter_num)):
        LOGGER.info("Start %s time(s) migration from %s ", num, orig_host)
        if not checkICMPConnectivity(host=orig_host, user=ht_user,
                                     password=ht_pwd, ip=dst):
            LOGGER.error("ICMP wasn't established")
        with TrafficMonitor(machine=orig_host, user=ht_user,
                            password=ht_pwd,
                            nic=ht_nic,
                            src=src, dst=dst,
                            protocol='tcp', numPackets=NUM_PACKETS) as monitor:
            monitor.addTask(check_vm_migration,
                            vm_names=vm_name,
                            orig_host=orig_host, vm_user=vm_user,
                            host_password=ht_pwd,
                            vm_password=vm_pwd,
                            os_type='rhel')
        return monitor.getResult()


def move_vm_disk(vm_name, disk_name, sd_name, os_type='rhel',
                 vm_user=config.VM_USER, vm_password=config.VM_PASSWORD):
    """
    Migrate vm's disk
    """
    if not vm_name or not disk_name or not sd_name:
        return False

    # live storage migrate vm's disk
    vms.move_vm_disk(vm_name, disk_name, sd_name)

    # check VM connectivity
    vms.checkVMConnectivity(True, vm_name, os_type, user=vm_user,
                            password=vm_password)

    return True
