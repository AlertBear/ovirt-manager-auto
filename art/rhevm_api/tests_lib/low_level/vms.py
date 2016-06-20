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
import random
import re
import shlex
import time
from art.rhevm_api import resources
from Queue import Queue
from operator import and_
from threading import Thread

from concurrent.futures import ThreadPoolExecutor

import art.rhevm_api.tests_lib.low_level.general as ll_general
from art.core_api.apis_exceptions import (
    APITimeout, EntityNotFound, TestCaseError,
)
from art.core_api.apis_utils import data_st, TimeoutingSampler, getDS
from art.rhevm_api.tests_lib.high_level.disks import delete_disks
from art.rhevm_api.tests_lib.low_level.disks import (
    _prepareDiskObject, getVmDisk, getObjDisks, get_other_storage_domain,
    wait_for_disks_status, get_disk_storage_domain_name,
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.networks import get_vnic_profile_obj
from art.rhevm_api.utils.name2ip import LookUpVMIpByName
from art.rhevm_api.utils.provisioning_utils import ProvisionProvider
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils.test_utils import (
    searchForObj, getImageByOsType, convertMacToIpAddress,
    checkHostConnectivity, update_vm_status_in_database, get_api, split,
    waitUntilPingable, restoringRandomState, waitUntilGone,
)
from art.test_handler import exceptions
from art.test_handler.exceptions import CanNotFindIP
from art.test_handler.settings import opts
from utilities.jobs import Job, JobsSet
from utilities.machine import Machine, LINUX
from utilities.utils import pingToVms, makeVmList

ENUMS = opts['elements_conf']['RHEVM Enums']
RHEVM_UTILS_ENUMS = opts['elements_conf']['RHEVM Utilities']
DEFAULT_CLUSTER = 'Default'
NAME_ATTR = 'name'
ID_ATTR = 'id'
DEF_SLEEP = 10
VM_SNAPSHOT_ACTION = 600
VM_ACTION_TIMEOUT = 600
# Live merge requires a long timeout for snapshot removal
VM_REMOVE_SNAPSHOT_TIMEOUT = 2400
VM_DISK_CLONE_TIMEOUT = 720
VM_IMAGE_OPT_TIMEOUT = 900
VM_INSTALL_TIMEOUT = 1800
CLONE_FROM_SNAPSHOT = 1500
VM_SAMPLING_PERIOD = 3

GUEST_AGENT_TIMEOUT = 60 * 6

SNAPSHOT_SAMPLING_PERIOD = 5
SNAPSHOT_APPEAR_TIMEOUT = 120
FILTER_DEVICE = '[sv]d'
DD_COMMAND = 'dd if=/dev/%s of=/dev/%s bs=1M oflag=direct'
DD_TIMEOUT = 1500

BLANK_TEMPLATE = '00000000-0000-0000-0000-000000000000'
ADD_DISK_KWARGS = [
    'size', 'type', 'interface', 'format', 'bootable', 'sparse',
    'wipe_after_delete', 'propagate_errors', 'alias', 'active', 'read_only'
]
VM_WAIT_FOR_IP_TIMEOUT = 600
SNAPSHOT_TIMEOUT = 15 * 60
PREVIEW = ENUMS['preview_snapshot']
UNDO = ENUMS['undo_snapshot']
COMMIT = ENUMS['commit_snapshot']
LIVE_SNAPSHOT_DESCRIPTION = ENUMS['live_snapshot_description']

VM_API = get_api('vm', 'vms')
VNIC_PROFILE_API = get_api('vnic_profile', 'vnicprofiles')
DC_API = get_api('data_center', 'datacenters')
CLUSTER_API = get_api('cluster', 'clusters')
TEMPLATE_API = get_api('template', 'templates')
HOST_API = get_api('host', 'hosts')
STORAGE_DOMAIN_API = get_api('storage_domain', 'storagedomains')
DISKS_API = get_api('disk', 'disks')
NIC_API = get_api('nic', 'nics')
SNAPSHOT_API = get_api('snapshot', 'snapshots')
TAG_API = get_api('tag', 'tags')
CDROM_API = get_api('cdrom', 'cdroms')
NETWORK_API = get_api('network', 'networks')
WATCHDOG_API = get_api('watchdog', 'watchdogs')
CAP_API = get_api('version', 'capabilities')
NUMA_NODE_API = get_api("vm_numa_node", "vm_numa_nodes")
HOST_DEVICE_API = get_api("host_device", "host_devices")

Snapshots = getDS('Snapshots')
NUMA_NODE_LINK = "numanodes"
HOST_DEVICE_LINK = "hostdevices"
SAMPLER_TIMEOUT = 120
SAMPLER_SLEEP = 5
VM = "vm"
MIGRATION_TIMEOUT = 300
VM_PASSWORD = "qum5net"

logger = logging.getLogger("art.ll_lib.vms")

ProvisionContext = ProvisionProvider.Context()


class DiskNotFound(Exception):
    pass


def _prepareVmObject(**kwargs):
    """
    Prepare vm object

    :param name: vm name
    :type name: str
    :param description: new vm description
    :type description: str
    :param cluster: new vm cluster
    :type cluster: str
    :param memory: vm memory size in bytes
    :type memory: int
    :param cpu_socket: number of cpu sockets
    :type cpu_socket: int
    :param cpu_cores: number of cpu cores
    :type cpu_cores: int
    :param cpu_mode: mode of cpu
    :type cpu_mode: str
    :param os_type: OS type of new vm
    :type os_type: str
    :param boot: type of boot
    :type boot: str
    :param template: name of template that should be used
    :type template: str
    :param type: vm type (SERVER or DESKTOP)
    :type type: str
    :param display_monitors: number of display monitors
    :type display_monitors: int
    :param display_type: type of vm display (VNC or SPICE)
    :type display_type: str
    :param kernel: kernel path
    :type kernel: str
    :param initrd: initrd path
    :type initrd: str
    :param cmdline: kernel parameters
    :type cmdline: str
    :param vcpu_pinning: vcpu pinning affinity
    :type vcpu_pinning: dict
    :param highly_available: set high-availability for vm ('true' or 'false')
    :type highly_available: str
    :param placement_affinity: vm to host affinity
    :type placement_affinity: str
    :param placement_host: host that the affinity holds for
    :type placement_host: str
    :param placement_hosts: multiple hosts for vm placement
    :type placement_hosts: list
    :param availablity_priority: priority for high-availability
    (an integer in range 0-100 where 0 - Low, 50 - Medium, 100 - High priority)
    :type availablity_priority: int
    :param custom_properties: custom properties set to the vm
    :type custom_properties: str
    :param stateless: if vm stateless or not
    :type stateless: bool
    :param memory_guaranteed: size of guaranteed memory in bytes
    :type memory_guaranteed: int
    :param ballooning: True of False - enable ballooning on vm
    :type ballooning: bool
    :param quota: vm quota id
    :type quota: str
    :param protected: true if vm is delete protected
    :type protected: bool
    :param templateUuid: id of template to be used
    :type templateUuid: str
    :param clusterUuid: uuid of cluster
    :type clusterUuid: str
    :param storagedomain: name of storagedomain
    :type storagedomain: str
    :param disk_clone: defines whether disk should be cloned from template
    :type disk_clone: str
    :param domainName: sys.prep domain name
    :type domainName: str
    :param snapshot: description of snapshot to use. Causes error if not unique
    :type snapshot: str
    :param copy_permissions: True if perms should be copied from template
    :type : bool
    :param cpu_profile_id: cpu profile id
    :type cpu_profile_id: str
    :param numa_mode: numa mode for vm(strict, preferred, interleave)
    :type numa_mode: str
    :param cpu_shares: cpu shares
    :type cpu_shares: int
    :param serial_number: serial number to use
    :type serial_number: str
    :param start_in_pause: start vm in pause
    :type start_in_pause: bool
    :param comment: vm comment
    :type comment: str
    :returns: vm object
    :rtype: instance of VM
    """
    add = kwargs.pop("add", False)
    description = kwargs.pop("description", None)
    if description is None or description == "":
        vm = data_st.Vm(name=kwargs.pop("name", None))
    else:
        vm = data_st.Vm(name=kwargs.pop("name", None), description=description)

    # snapshot
    snapshot_name = kwargs.pop("snapshot", None)
    if snapshot_name:
        add = False
        vms = VM_API.get(absLink=False)
        for temp_vm in vms:
            try:
                snapshot_obj = _getVmSnapshot(temp_vm.name, snapshot_name)
            except EntityNotFound:
                pass
            else:
                snapshots = Snapshots()
                snapshots.add_snapshot(snapshot_obj)
                vm.set_snapshots(snapshots)
                break

    # template
    template_name = kwargs.pop("template", "Blank" if add else None)
    template_id = kwargs.pop("templateUuid", None)
    search_by = NAME_ATTR
    if template_id:
        template_name = template_id
        search_by = ID_ATTR
    if template_name:
        template = TEMPLATE_API.find(template_name, search_by)
        vm.set_template(data_st.Template(id=template.id))

    # cluster
    cluster_name = kwargs.pop("cluster", DEFAULT_CLUSTER if add else None)
    cluster_id = kwargs.pop("clusterUuid", None)
    search_by = NAME_ATTR
    if cluster_id:
        cluster_name = cluster_id
        search_by = ID_ATTR
    if cluster_name:
        cluster = CLUSTER_API.find(cluster_name, search_by)
        vm.set_cluster(cluster)

    # memory
    vm.memory = kwargs.pop("memory", None)

    # cpu topology & cpu pinning
    cpu_socket = kwargs.pop("cpu_socket", None)
    cpu_cores = kwargs.pop("cpu_cores", None)
    vcpu_pinning = kwargs.pop("vcpu_pinning", None)
    cpu_mode = kwargs.pop("cpu_mode", None)
    if (
            cpu_socket or cpu_cores or
            vcpu_pinning is not None or
            cpu_mode is not None
    ):
        cpu = data_st.Cpu()
        if cpu_socket or cpu_cores:
            cpu.set_topology(
                topology=data_st.CpuTopology(
                    sockets=cpu_socket, cores=cpu_cores
                )
            )
        if vcpu_pinning is not None and vcpu_pinning == []:
            cpu.set_cpu_tune(data_st.CpuTune())
        elif vcpu_pinning:
            cpu.set_cpu_tune(
                data_st.CpuTune(
                    data_st.VcpuPins(
                        vcpu_pin=[
                            data_st.VcpuPin(
                                elm.keys()[0],
                                elm.values()[0]
                            ) for elm in vcpu_pinning
                        ]
                    )
                )
            )
        if cpu_mode is not None and cpu_mode == "":
            cpu.set_mode("CUSTOM")
        elif cpu_mode:
            cpu.set_mode(cpu_mode)
        vm.set_cpu(cpu)

    # os options
    apply_os = False
    os_type = kwargs.pop("os_type", None)
    if os_type is not None:
        if os_type.startswith("windows_"):
            os_type = ENUMS.get(os_type, os_type)
        else:
            os_type = ENUMS.get(os_type.lower(), os_type.lower())
        apply_os = True
    os_type = data_st.OperatingSystem(type_=os_type)
    for opt_name in "kernel", "initrd", "cmdline":
        opt_val = kwargs.pop(opt_name, None)
        if opt_val:
            apply_os = True
            setattr(os_type, opt_name, opt_val)
    boot_seq = kwargs.pop("boot", None)
    if boot_seq:
        if isinstance(boot_seq, basestring):
            boot_seq = boot_seq.split()
        os_type.set_boot(
            boot=data_st.Boot(
                devices=data_st.devicesType(
                    device=boot_seq
                )
            )
        )
        apply_os = True
    if apply_os:
        vm.set_os(os_type)

    # type
    vm.set_type(kwargs.pop("type", None))

    # display monitors and type
    display_type = kwargs.pop("display_type", None)
    display_monitors = kwargs.pop("display_monitors", None)
    if display_monitors or display_type:
        vm.set_display(
            data_st.Display(
                type_=display_type, monitors=display_monitors
            )
        )

    # stateless
    vm.set_stateless(kwargs.pop("stateless", None))

    # high availablity
    ha = kwargs.pop("highly_available", None)
    ha_priority = kwargs.pop("availablity_priority", None)
    if ha is not None or ha_priority:
        vm.set_high_availability(
            data_st.HighAvailability(
                enabled=ha, priority=ha_priority
            )
        )

    # custom properties
    custom_prop = kwargs.pop("custom_properties", None)
    if custom_prop:
        vm.set_custom_properties(createCustomPropertiesFromArg(custom_prop))

    # memory policy memory_guaranteed and ballooning
    guaranteed = kwargs.pop("memory_guaranteed", None)
    ballooning = kwargs.pop('ballooning', None)
    if ballooning or guaranteed:
        vm.set_memory_policy(
            data_st.MemoryPolicy(
                guaranteed=guaranteed,
                ballooning=ballooning,
            )
        )

    # placement policy: placement_affinity & placement_host
    affinity = kwargs.pop("placement_affinity", None)
    placement_host = kwargs.pop("placement_host", None)
    placement_hosts = kwargs.pop("placement_hosts", [])
    if placement_host or affinity or placement_hosts:
        placement_policy = data_st.VmPlacementPolicy()
        if affinity:
            placement_policy.set_affinity(affinity)
        if placement_host and placement_host != ENUMS[
            "placement_host_any_host_in_cluster"
        ]:
            placement_hosts.append(placement_host)
        if placement_hosts:
            hosts = [
                data_st.Host(id=HOST_API.find(host).get_id())
                for host in placement_hosts
            ]
            placement_policy.set_hosts(data_st.Hosts(host=hosts))
        vm.set_placement_policy(placement_policy)

    # storagedomain
    sd_name = kwargs.pop("storagedomain", None)
    if sd_name:
        sd = STORAGE_DOMAIN_API.find(sd_name)
        vm.set_storage_domain(sd)

    #  domain_name
    domain_name = kwargs.pop("domainName", None)
    if domain_name:
        vm.set_domain(data_st.Domain(name=domain_name))

    # disk_clone
    disk_clone = kwargs.pop("disk_clone", None)
    if disk_clone and disk_clone.lower() == "true":
        disk_array = data_st.Disks()
        disk_array.set_clone(disk_clone)
        vm.set_disks(disk_array)

    # quota
    quota_id = kwargs.pop("quota", None)
    if quota_id == '':
        vm.set_quota(data_st.Quota())
    elif quota_id:
        vm.set_quota(data_st.Quota(id=quota_id))

    # payloads
    payloads = kwargs.pop("payloads", None)
    if payloads:
        payload_array = []
        payload_files = data_st.Files()
        for payload_type, payload_fname, payload_file_content in payloads:
            payload_file = data_st.File(
                name=payload_fname, content=payload_file_content
            )
            payload_files.add_file(payload_file)
            payload = data_st.Payload(payload_type, payload_files)
            payload_array.append(payload)
        payloads = data_st.Payloads(payload_array)
        vm.set_payloads(payloads)

    # delete protection
    protected = kwargs.pop("protected", None)
    if protected is not None:
        vm.set_delete_protected(protected)

    # copy_permissions
    copy_permissions = kwargs.pop("copy_permissions", None)
    if copy_permissions:
        perms = data_st.Permissions()
        perms.set_clone(True)
        vm.set_permissions(perms)

    # initialization
    initialization = kwargs.pop("initialization", None)
    if initialization:
        vm.set_initialization(initialization)

    # timezone
    time_zone = kwargs.pop("time_zone", None)
    time_zone_offset = kwargs.pop("time_zone_offset", None)
    if time_zone is not None or time_zone_offset is not None:
        vm.set_time_zone(data_st.TimeZone(
            name=time_zone, utc_offset=time_zone_offset)
        )

    # cpu_profile
    cpu_profile_id = kwargs.pop("cpu_profile_id", None)
    if cpu_profile_id:
        vm.set_cpu_profile(data_st.CpuProfile(id=cpu_profile_id))

    # virtio_scsi
    virtio_scsi = kwargs.pop("virtio_scsi", None)
    if virtio_scsi is not None:
        vm.set_virtio_scsi(data_st.VirtioScsi(enabled=virtio_scsi))

    # numa mode
    numa_mode = kwargs.pop("numa_mode", None)
    if numa_mode:
        vm.set_numa_tune_mode(numa_mode)

    # cpu shares
    cpu_shares = kwargs.pop("cpu_shares", None)
    if cpu_shares is not None:
        vm.set_cpu_shares(cpu_shares)

    # serial number
    serial_number = kwargs.pop("serial_number", None)
    if serial_number is not None:
        sr = data_st.SerialNumber()
        sr.set_policy('custom')
        sr.set_value(serial_number)
        vm.set_serial_number(sr)
    # start_in_pause
    start_in_pause = kwargs.pop("start_in_pause", None)
    if start_in_pause:
        vm.set_start_paused(start_in_pause)
    # comment
    comment = kwargs.pop("comment", None)
    if comment:
        vm.set_comment(comment=comment)
    return vm


def createCustomPropertiesFromArg(prop_arg):
    """
    Create custom properties object
    :param prop_arg: Custom properties to create (send clear to remove any
    configured custom properties)
    :type prop_arg: str
    :return: cps
    :rtype: object
    """
    cps = data_st.CustomProperties()
    if prop_arg == "clear":
        return cps

    props = prop_arg.split(';')
    for prop in props:
        try:
            name, value = prop.split('=', 1)
        except ValueError:
            e = "Custom Properties should be in form " \
                "'name1=value1;name2=value2'. Got '%s' instead."
            raise Exception(e % prop_arg)
        cps.add_custom_property(
            data_st.CustomProperty(name=name, value=value)
        )
    return cps


def addVm(positive, wait=True, **kwargs):
    """
    Description: add new vm (without starting it)

    :param name: vm name
    :type name: str
    :param description: new vm description
    :type description: str
    :param cluster: new vm cluster
    :type cluster: str
    :param memory: vm memory size in bytes
    :type memory: int
    :param cpu_socket: number of cpu sockets
    :type cpu_socket: int
    :param cpu_cores: number of cpu cores
    :type cpu_cores: int
    :param cpu_mode: mode of cpu
    :type cpu_mode: str
    :param os_type: OS type of new vm
    :type os_type: str
    :param boot: type of boot
    :type boot: str
    :param template: name of template that should be used
    :type template: str
    :param type: vm type (SERVER or DESKTOP)
    :type type: str
    :param display_monitors: number of display monitors
    :type display_monitors: int
    :param display_type: type of vm display (VNC or SPICE)
    :type display_type: str
    :param kernel: kernel path
    :type kernel: str
    :param initrd: initrd path
    :type initrd: str
    :param cmdline: kernel parameters
    :type cmdline: str
    :param vcpu_pinning: vcpu pinning affinity
    :type vcpu_pinning: dict
    :param highly_available: set high-availability for vm ('true' or 'false')
    :type highly_available: str
    :param placement_affinity: vm to host affinity
    :type placement_affinity: str
    :param placement_host: host that the affinity holds for
    :type placement_host: str
    :param placement_hosts: multiple hosts for vm placement
    :type placement_hosts: list
    :param availablity_priority: priority for high-availability
    (an integer in range 0-100 where 0 - Low, 50 - Medium, 100 - High priority)
    :type availablity_priority: int
    :param custom_properties: custom properties set to the vm
    :type custom_properties: str
    :param stateless: if vm stateless or not
    :type stateless: bool
    :param memory_guaranteed: size of guaranteed memory in bytes
    :type memory_guaranteed: int
    :param ballooning: memory ballooning device enable or disable
    :type balloning: bool
    :param quota: vm quota id
    :type quota: str
    :param protected: true if vm is delete protected
    :type protected: bool
    :param templateUuid: id of template to be used
    :type templateUuid: str
    :param wait: if True wait until end of action, False return without waiting
    :type wait: bool
    :param clusterUuid: uuid of cluster
    :type clusterUuid: str
    :param storagedomain: name of storagedomain
    :type storagedomain: str
    :param disk_clone: defines whether disk should be cloned from template
    :type disk_clone: str
    :param disk_parameters: disk parameters
    :type disk_parameters: dict
    :param domainName: sys.prep domain name
    :type domainName: str
    :param snapshot: description of snapshot to use. Causes error if not unique
    :type snapshot: str
    :param copy_permissions: True if perms should be copied from template
    :type : bool
    :param timeout: waiting timeout
    :type timeout: int
    :param cpu_profile_id: cpu profile id
    :type cpu_profile_id: str
    :param numa_mode: numa mode for vm(strict, preferred, interleave)
    :type numa_mode: str
    :param initialization: should be created as an Initialization object with
                           relevant parameters
                           (sysprep, ovf, username, root_password etc)
    :type initialization: Initialization
    :param cpu_shares: cpu shares
    :type cpu_shares:int
    :param serial_number: serial number to use
    :type serial_number: str
    :param start_in_pause: start vm in pause mode
    :type start_in_pause: bool
    :returns: True, if add vm success, otherwise False
    :rtype: bool
    """
    kwargs.update(add=True)
    vm_obj = _prepareVmObject(**kwargs)
    expected_vm = _prepareVmObject(**kwargs)
    log_info, log_error = ll_general.get_log_msg(
        action="add", obj_type="vm", obj_name=kwargs.get('name'),
        positive=positive, **kwargs
    )
    logger.info(log_info)
    if False in [positive, wait]:
        vm_obj, status = VM_API.create(
            vm_obj, positive, expectedEntity=expected_vm
        )
        if not status:
            logging.error(log_error)
        return status

    disk_clone = kwargs.pop('disk_clone', None)

    wait_timeout = kwargs.pop('timeout', VM_ACTION_TIMEOUT)
    if disk_clone and disk_clone.lower() == 'true':
        expected_vm.set_template(data_st.Template(id=BLANK_TEMPLATE))
        wait_timeout = VM_DISK_CLONE_TIMEOUT

    vm_obj, status = VM_API.create(
        vm_obj, positive, expectedEntity=expected_vm
    )

    if status:
        status = VM_API.waitForElemStatus(vm_obj, "DOWN", wait_timeout)
    else:
        logging.error(log_error)

    return status


def updateVm(positive, vm, **kwargs):
    """
    Update existed vm

    :param vm: name of vm
    :type : str
    :param name: new vm name
    :type name: str
    :param description: new vm description
    :type description: str
    :param data_center: new vm data center
    :type data_center: str
    :param cluster: new vm cluster
    :type cluster: str
    :param memory: vm memory size in bytes
    :type memory: int
    :param cpu_socket: number of cpu sockets
    :type cpu_socket: int
    :param cpu_cores: number of cpu cores
    :type cpu_cores: int
    :param cpu_mode: mode of cpu
    :type cpu_mode: str
    :param os_type: OS type of new vm
    :type os_type: str
    :param boot: type of boot
    :type boot: str
    :param template: name of template that should be used
    :type template: str
    :param type: vm type (SERVER or DESKTOP)
    :type type: str
    :param display_monitors: number of display monitors
    :type display_monitors: int
    :param display_type: type of vm display (VNC or SPICE)
    :type display_type: str
    :param kernel: kernel path
    :type kernel: str
    :param initrd: initrd path
    :type initrd: str
    :param cmdline: kernel parameters
    :type cmdline: str
    :param highly_available: set high-availability for vm ('true' or 'false')
    :type highly_available: str
    :param availablity_priority: priority for high-availability
    (an integer in range 0-100 where 0 - Low, 50 - Medium, 100 - High priority)
    :type availablity_priority: int
    :param custom_properties: custom properties set to the vm
    :type custom_properties: str
    :param stateless: if vm stateless or not
    :type stateless: bool
    :param memory_guaranteed: size of guaranteed memory in bytes
    :type memory_guaranteed: int
    :param ballooning: memory ballooning device enable or disable
    :type ballooning: bool
    :param domainName: sys.prep domain name
    :type domainName: str
    :param placement_affinity: vm to host affinity
    :type placement_affinity: str
    :param placement_host: host that the affinity holds for
    :type placement_host: str
    :param placement_hosts: multiple hosts for vm placement
    :type placement_hosts: list
    :param quota: vm quota id
    :type quota: str
    :param protected: true if vm is delete protected
    :type protected: bool
    :param watchdog_model: model of watchdog card (ib6300)
    :type watchdog_model: str
    :param watchdog_action: action of watchdog card
    :type watchdog_action: str
    :param time_zone: set to timezone out of product possible timezones
    :type time_zone: str
    :param time_zone_offset: set to utc_offset out of product possible offsets
    :type time_zone_offset: str
    :param compare: disable or enable validation for update
    :type compare: bool
    :param cpu_profile_id: cpu profile id
    :type cpu_profile_id: str
    :param numa_mode: numa mode for vm(strict, preferred, interleave)
    :type numa_mode: str
    :param initialization: Initialization obj for cloud init
    :type initialization: Initialization
    :param cpu_shares: cpu shares
    :type cpu_shares: int
    :param start_in_pause: start vm in pause mode
    :type start_in_pause: bool
    :param comment: vm comment
    :type comment: str
    :returns: True, if update success, otherwise False
    :rtype: bool
    """
    log_info, log_error = ll_general.get_log_msg(
        action="update", obj_type=VM, obj_name=vm, positive=positive,
        **kwargs
    )
    vm_obj = VM_API.find(vm)
    vm_new_obj = _prepareVmObject(**kwargs)
    compare = kwargs.get("compare", True)
    logger.info(log_info)
    vm_new_obj, status = VM_API.update(
        vm_obj, vm_new_obj, positive, compare=compare
    )
    if not status:
        logger.error(log_error)
    return status


def removeVm(positive, vm, **kwargs):
    """
    Remove VM

    Args:
        positive (bool): Expected status
        vm (str): VM name
        kwargs (dict): Extra kwargs for remove VM

    Keyword arguments:
        force (bool): Force remove if True
        stopVM (bool): Stop VM before removal
        wait (bool): Wait for removal if True
        timeout (int): Waiting timeout
        waitTime (int): Waiting time interval

    Returns:
        bool: True if VM was removed properly, False otherwise
    """
    body = None
    force = kwargs.pop('force', None)
    if force:
        body = data_st.Action(force=True)

    vm_obj = VM_API.find(vm)
    vm_status = vm_obj.get_status()
    stop_vm = kwargs.pop('stopVM', 'false')
    if str(stop_vm).lower() == 'true' and vm_status != ENUMS['vm_state_down']:
        if not stopVm(positive, vm):
            return False
    logger.info("Remove VM %s", vm)
    status = VM_API.delete(vm_obj, positive, body=body, element_name='action')

    if not status:
        logger.error("Failed to remove VM %s", vm)

    wait = kwargs.pop('wait', True)
    if positive and wait and status:
        return waitForVmsGone(
            positive, vm, kwargs.pop('timeout', 60),
            kwargs.pop('waitTime', 10)
        )
    return status


def removeVmAsynch(positive, tasksQ, resultsQ, stopVmBool=False):
    '''
    Removes the cluster. It's supposed to be a worker of Thread.
    Author: jhenner
    Parameters:
        * tasksQ - A input Queue of VM names to remove
        * resultsQ - A output Queue of tuples tuple(VM name, VM removal status)
        * stopVm - if True will attempt to stop VM before actually remove it
                   (False by default)
    '''
    vm = tasksQ.get(True)
    status = False
    try:
        vmObj = VM_API.find(vm)
        if stopVmBool and vmObj.get_status() != 'down':
            if not stopVm(positive, vm):
                logger.error("failed to stop vm %s before async removal", vm)
                return

        status = VM_API.delete(vmObj, positive)
    except EntityNotFound as e:
        logger.warn(str(e))
        status = True
    finally:
        resultsQ.put((vm, status))
        tasksQ.task_done()


def removeVms(positive, vms, stop='false', timeout=180):
    '''
    Removes the VMs specified by `vms` commas separated list of VM names.
    Author: jhenner
    Parameters:
        * vms - a list or a string list separated by comma of vms
        * stop - will attempt to stop VMs if 'true' ('false' by default)
        * timeout -in secs, used for waitForVmsGone
    '''
    assert positive
    tasksQ = Queue()
    resultsQ = Queue()
    threads = set()
    if isinstance(vms, basestring):
        # 'vm1, vm2' -> [vm1, vm2]
        vmsList = split(vms)
    else:
        vmsList = vms
    if not vmsList:
        raise ValueError("vms cannot be empty")

    if str(stop).lower() == 'true':
        stopVms(vmsList)

    for i in vmsList:
        t = Thread(target=removeVmAsynch, name='VM removing',
                   args=(positive, tasksQ, resultsQ))
        threads.add(t)
        t.daemon = False
        t.start()

    for vm in vmsList:
        tasksQ.put(vm)

    tasksQ.join()  # block until all tasks are done
    logger.info(threads)
    for t in threads:
        t.join()

    status = True
    while not resultsQ.empty():
        vm, removalOK = resultsQ.get()
        if removalOK:
            logger.info("VM '%s' deleted asynchronously." % vm)
        else:
            logger.error("Failed to asynchronously remove VM '%s'." % vm)
        status = status and removalOK
    return waitForVmsGone(positive, vmsList, timeout=timeout) and status


def waitForVmsGone(positive, vms, timeout=60, samplingPeriod=10):
    '''
    Wait for VMs to disappear from the setup. This function will block up to
    `timeout` seconds, sampling the VMs list every `samplingPeriod` seconds,
    until no VMs specified by names in `vms` exists.

    Parameters:
        * vms - comma (and no space) separated string of VM names to wait for
                or list of names
        * timeout - Time in seconds for the vms to disapear.
        * samplingPeriod - Time in seconds for sampling the vms list.
    '''
    return waitUntilGone(positive, vms, VM_API, timeout, samplingPeriod)


def waitForVmsStates(positive, names, states=ENUMS['vm_state_up'], *args,
                     **kwargs):
    '''
    Wait until all of the vms identified by names exist and have the desired
    status.
    Parameters:
        * names - List or comma separated string of VM's names with
                  status to wait for.
        * states - A state of the vms to wait for.
    Author: jhenner
    Return True if all events passed, otherwise False
    '''
    if isinstance(names, basestring):
        names = split(names)
    for vm in names:
        VM_API.find(vm)

    for vm in names:
        if not waitForVMState(vm, states):
            return False
    return True


def waitForVMState(vm, state='up', **kwargs):
    '''
    Wait until vm has the desired status
    Author: atal
    Parameters:
        * vm - name of vm
        * state - vm status should wait for (default is "powering_up")
          List of available statuses/states of VM:
          [unassigned, up, down, powering_up, powering_down,
          paused, migrating_from, migrating_to, unknown,
          not_responding, wait_for_launch, reboot_in_progress,
          saving_state, restoring_state, suspended,
          image_illegal, image_locked]
    Return True if event passed, otherwise False
    '''
    query = "name={0} and status={1}".format(
        vm, state.lower().replace('_', ''))

    return VM_API.waitForQuery(query, **kwargs)


def changeVMStatus(positive, vm, action, expectedStatus, async='true'):
    '''
    Description: change vm status
    Author: edolinin
    Parameters:
       * positive - indicates positive/negative test's flow
       * vm - name of vm
       * action - action that should be run on vm -
       (start/stop/suspend/shutdown/detach)
       * expectedStatus - status of vm in case the action succeeded
       * async - don't wait for VM status if 'true' ('false' by default)
    Return: status (True if vm status is changed properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)

    asyncMode = async.lower() == 'true'
    status = bool(VM_API.syncAction(vmObj, action, positive, async))
    if status and positive and not asyncMode:
        return VM_API.waitForElemStatus(vmObj, expectedStatus,
                                        VM_ACTION_TIMEOUT)
    return status


def restartVm(vm, wait_for_ip=False, timeout=VM_ACTION_TIMEOUT, async='false',
              wait_for_status=ENUMS['vm_state_up'], placement_host=None):
    '''
    Description: Stop and start vm.
    Parameters:
      * vm - name of vm
      * wait_for_ip - True/False wait for ip
      * timeout - timeout of wait for vm
      * async - stop VM asynchronously if 'true' ('false' by default)
      * wait_for_status - status which should have vm after starting it
      * placement_host - host where the vm should be started
    '''
    if not checkVmState(True, vm, ENUMS['vm_state_down']):
        if not stopVm(True, vm, async=async):
            return False
    return startVm(True, vm, wait_for_status=wait_for_status,
                   wait_for_ip=True, timeout=timeout,
                   placement_host=placement_host)


def startVm(
    positive, vm, wait_for_status=ENUMS['vm_state_powering_up'],
    wait_for_ip=False, timeout=VM_ACTION_TIMEOUT, placement_host=None,
    use_cloud_init=False
):
    """
    Start VM

    :param vm: name of vm
    :type vm: str
    :param wait_for_status: vm status should wait for (default is
    "powering_up") list of available statuses/states of VM:
           [unassigned, up, down, powering_up, powering_down,
           paused, migrating_from, migrating_to, unknown,
           not_responding, wait_for_launch, reboot_in_progress,
           saving_state, restoring_state, suspended,
           image_illegal, image_locked, None]
    :type wait_for_status: str
    :param wait_for_ip: wait for VM ip
    :type wait_for_ip: bool
    :param timeout: timeout to wait for ip to start
    :type timeout: int
    :param placement_host: host where the VM should start
    :type placement_host: str
    :param use_cloud_init: initialize vm with cloud-init if true
    :type use_cloud_init: bool
    :return: status (True if vm was started properly, False otherwise)
    :rtype: bool
    """
    logger.info("Starting VM %s", vm)
    if not positive:
        wait_for_status = None

    vmObj = VM_API.find(vm)
    action_params = {}
    if placement_host:
        logging.info("Update vm %s to run on host %s", vm, placement_host)
        if not updateVm(True, vm, placement_host=placement_host):
            return False
    if use_cloud_init:
        action_params['use_cloud_init'] = 'true'
    log_info, log_error = ll_general.get_log_msg(
        action="start", obj_type=VM, obj_name=vm, positive=positive,
        **action_params
    )
    logger.info(log_info)
    if not VM_API.syncAction(vmObj, 'start', positive, **action_params):
        logger.error(log_error)
        return False

    if wait_for_status is None:
        return True

    query = "name={0} and status={1} or name={0} and status=up".format(
        vm, wait_for_status.lower().replace('_', ''))
    started = VM_API.waitForQuery(query, timeout=timeout, sleep=10)
    if started and wait_for_ip:
        started = waitForIP(vm)[0]
        if started != positive:
            VM_API.logger.error("waitForIP returned %s, positive is set to %s",
                                started, positive)

    return started == positive


def startVms(vms, wait_for_status=ENUMS['vm_state_powering_up']):
    '''
    Start several vms simultaneously. Only action response is checked, no
    checking for vm UP status is performed.

    Parameters:
      * vms - Names of VMs to start.
    Returns: True iff all VMs started.
    '''
    if isinstance(vms, basestring):
        vms = split(vms)
    jobs = [Job(target=startVm,
                args=(True, vm, wait_for_status)) for vm in vms]
    js = JobsSet()
    js.addJobs(jobs)
    js.start()
    js.join()

    status = True
    for job in jobs:
        if job.exception:
            status = False
            logger.error('Starting vm %s failed: %s.',
                         job.args[1], job.exception)
        elif not job.result:
            status = False
            logger.error('Starting %s failed.', job.args[1])
        else:
            logger.info('Starting vm %s succeed.', job.args[1])
    return status


def stopVm(positive, vm, async='false'):
    """
    Stop vm

    :param positive: Expected status
    :type positive: bool
    :param vm: Name of vm
    :type vm: str
    :param async: Stop VM asynchronously if 'true' ('false' by default)
    :type async: str
    :return: Status (True if vm was stopped properly, False otherwise)
    :rtype: bool
    """
    log_info, log_error = ll_general.get_log_msg(
        action="stop", obj_type=VM, obj_name=vm, positive=positive
    )
    logger.info(log_info)
    if not changeVMStatus(positive, vm, 'stop', 'DOWN', async):
        logger.error(log_error)
        return False
    return True


def stopVms(vms, wait='true'):
    '''
    Stop vms.
    Author: mbenenso
    Parameters:
       * vms - comma separated string of VM names or list
       * wait - if 'true' will wait till the end of stop action
               ('true' by default)
    Return: True iff all VMs stopped, False otherwise
    '''
    vmObjectsList = []
    if isinstance(vms, basestring):
        vms = split(vms)
    wait = wait.lower() == 'true'
    async = 'false' if not wait else 'true'
    for vm in vms:
        stopVm(True, vm, async)
        try:
            vmObj = VM_API.find(vm)
        except EntityNotFound:
            logger.error("failed to find VM %s" % vm)
        else:
            vmObjectsList.append(vmObj)

    if not wait:
        return True

    resultsList = []
    query_fmt = 'name={0} and status=down'
    for vmObj in vmObjectsList:
        query = query_fmt.format(vmObj.get_name())
        querySt = VM_API.waitForQuery(query, timeout=VM_ACTION_TIMEOUT,
                                      sleep=DEF_SLEEP)
        resultsList.append(querySt)

    return all(resultsList)


def searchForVm(positive, query_key, query_val, key_name=None, **kwargs):
    '''
    Description: search for a data center by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in data center object equivalent to query_key
    Return: status (True if expected number of data centers equal to
                    found by search, False otherwise)
    '''

    return searchForObj(VM_API, query_key, query_val, key_name, **kwargs)


def detachVm(positive, vm):
    '''
    Description: run detach vm action
    Author: edolinin
    Parameters:
       * vm - name of vm
    Return: status (True if vm was detached properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    log_info, log_error = ll_general.get_log_msg(
        action="detach", obj_type=VM, obj_name=vm, positive=positive
    )
    expectedStatus = vmObj.get_status()

    status = bool(VM_API.syncAction(vmObj, "detach", positive))
    logger.info(log_info)
    if not status:
        logger.error(log_error)
        return False
    if status and positive:
        return VM_API.waitForElemStatus(vmObj, expectedStatus,
                                        VM_ACTION_TIMEOUT)
    return status


def getVmDisks(vm, storage_domain=None):
    """
    Returns a list of the vm's disks formatted as data structured objects,
    and sorted based on the disk aliases
    Raises: EntityNotFound if vm does not exist

    __author__ = cmestreg
    :param vm: name of the vm which the disks will be retrieved
    :type vm: str
    :param storage_domain: name of the storage domain. This is needed in
    case the vm's disks are stored in an export domain
    :type storage_domain: str
    :return: list of disks' objects attached to the vm
    :rtype: list
    """
    if storage_domain:
        storage_domain_obj = STORAGE_DOMAIN_API.find(storage_domain)
        storage_domain_vms = VM_API.getElemFromLink(
            storage_domain_obj, link_name='vms', attr='vm', get_href=False,
        )
        vm_obj = VM_API.find(vm, collection=storage_domain_vms)

    else:
        vm_obj = VM_API.find(vm)

    disks = VM_API.getElemFromLink(vm_obj, link_name='disks', attr='disk',
                                   get_href=False)
    disks.sort(key=lambda disk: disk.get_alias())
    return disks


def _getVmDiskById(vm, diskId):
    """
    Description: Searches for vm's disk by id
    Author: jlibosva
    Parameters"
        * vm - Name of vm we want disk from
        * diskId - disk's id
    Return: Disk object
    """
    disks = getVmDisks(vm)
    found = [disk for disk in disks if disk.get_id() == diskId]
    if not found:
        raise DiskNotFound("Disk with id %s was not found in vm's %s disk \
collection" % (diskId, vm))

    return found[0]


def _getVmFirstDiskByName(vm, diskName, idx=0):
    """
    Description: Searches for vm's disk by name
                 Name is not unique!
    Author: jlibosva
    Parameters"
        * vm - Name of vm we want disk from
        * diskId - disk's id
        * idx - index of found disk to return
    Return: Disk object
    """
    disks = getVmDisks(vm)
    found = [disk for disk in disks if disk.get_name() == diskName]
    if not found:
        raise DiskNotFound("Disk %s was not found in vm's %s disk collection" %
                           (diskName, vm))
    return found[idx]


def addDisk(positive, vm, provisioned_size, wait=True, storagedomain=None,
            timeout=VM_IMAGE_OPT_TIMEOUT, **kwargs):
    '''
    Description: add disk to vm
    Parameters:
        * vm - vm name
        * wait - wait until finish if True or exit without waiting
        * storagedomain - storage domain name(relevant only for the first disk)
        * timeout - waiting timeout
       * kwargs:
        * type - disk type
        * interface - disk interface
        * format - disk format type
        * sparse - if disk sparse or pre-allocated
        * bootable - if disk bootable or not
        * wipe_after_delete - if disk should be wiped after deletion or not
        * propagate_errors - if propagate errors or not
        * quota - disk quota
        * active - automatically activate the disk
        * alias - alias for the disk
        * description - description for the disk
        * read_only - if disk should be read only
        * shareable = True if disk should be shared, False otherwise
        * provisioned_size - disk's provisioned size
    Return: status (True if disk was added properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    disk = data_st.Disk(provisioned_size=provisioned_size,
                        format=ENUMS['format_cow'],
                        interface=ENUMS['interface_ide'], sparse=True,
                        alias=kwargs.pop('alias', None),
                        description=kwargs.pop('description', None),
                        active=kwargs.get('active', True))

    # replace disk params from kwargs
    for param_name in ADD_DISK_KWARGS:
        param_val = kwargs.pop(param_name, None)
        if param_val is not None:
            logger.debug("addDisk parameter %s is %s", param_name, param_val)
            setattr(disk, param_name, param_val)

    # read_only
    read_only = kwargs.pop('read_only', None)
    if read_only is not None:
        disk.set_read_only(read_only)

    # shareable
    shareable = kwargs.pop('shareable', None)
    if shareable is not None:
        disk.set_shareable(shareable)

    # provisioned_size
    provisioned_size = kwargs.pop('provisioned_size', None)
    if provisioned_size is not None:
        disk.set_provisioned_size(provisioned_size)

    # quota
    quota_id = kwargs.pop('quota', None)
    if quota_id == '':
        disk.set_quota(data_st.Quota())
    elif quota_id:
        disk.set_quota(data_st.Quota(id=quota_id))

    # Report the unknown arguments that remains.
    if 0 < len(kwargs):
        E = "addDisk() got an unexpected keyword arguments %s"
        raise TypeError(E % kwargs)

    if storagedomain:
        sd = STORAGE_DOMAIN_API.find(storagedomain)
        diskSds = data_st.StorageDomains()
        diskSds.add_storage_domain(sd)
        disk.set_storage_domains(diskSds)

    disks = DISKS_API.getElemFromLink(vmObj, get_href=True)
    disk, status = DISKS_API.create(disk, positive, collection=disks)
    if status and positive and wait:
        return DISKS_API.waitForElemStatus(disk, "OK", timeout)
    return status


def removeDisk(positive, vm, disk=None, wait=True, disk_id=None):
    """
    Remove disk from vm

    __Author__ = 'ratamir'
    :param positive: Determines whether the case is positive or negative
    :type positive: bool
    :param vm: VM name
    :type vm: str
    :param disk: Name of disk that should be removed
    :type disk: str
    :param wait: Specifies whether to wait until the the remove disk
    execution completes
    :type wait: bool
    :param disk_id: ID of the disk that should be removed
    :type disk_id: str
    :return: True if disk was removed successfully, False otherwise
    :rtype: bool
    """
    def does_disk_exist(disk_list):
        for disk_object in disk_list:
            if disk_id:
                if disk_object.get_id() == disk_id:
                    return disk_object
            elif disk:
                if disk_object.name == disk:
                    return disk_object
        return None
    disk_obj = does_disk_exist(getVmDisks(vm))
    if disk_obj:
        status = VM_API.delete(disk_obj, positive)
    else:
        logger.error("Disk %s not found in vm %s", disk, vm)
        return False
    if positive and status and wait:
        logger.debug('Waiting for disk to be removed.')
        for disk_obj in TimeoutingSampler(
            VM_IMAGE_OPT_TIMEOUT, VM_SAMPLING_PERIOD, does_disk_exist,
                getVmDisks(vm)
        ):
            if not disk_obj:
                return True
    return status


def removeDisks(positive, vm, num_of_disks, wait=True):
    '''
    Description: remove certain number of disks from vm
    Parameters:
      * vm - vm name
      * num_of_disks - number of disks that should be removed
      * wait - wait until finish if True
    Return: status (True if disks were removed properly, False otherwise)
    '''
    rc = True
    disks = getVmDisks(vm)
    if disks:
        cnt = int(num_of_disks)
        actual_cnt = len(disks)
        cnt_rm = actual_cnt if actual_cnt < cnt else cnt
        for i in xrange(cnt_rm):
            disk = disks.pop()
            rc = rc and removeDisk(positive, vm, disk.name, wait)
    return rc


def waitForDisksStat(vm, stat=ENUMS['disk_state_ok'],
                     timeout=VM_IMAGE_OPT_TIMEOUT):
    '''
    Wait for VM disks status
    Author: atal
    Parameters:
        * vm - vm name
        * stat = status we are waiting for
        * timeout - waiting period.
    Return True if all events passed, otherwise False
    '''
    status = True
    disks = getVmDisks(vm)
    for disk in disks:
        status = DISKS_API.waitForElemStatus(disk, stat, timeout)
    return status


def checkVmHasCdromAttached(positive, vmName):
    '''
    Check whether vm has cdrom attached
    Author: jvorcak
    Parameters:
       * vmName - name of the virtual machine
    Return (True if vm has at least one cdrom attached, False otherwise)
    '''
    vmObj = VM_API.find(vmName)
    cdroms = VM_API.getElemFromLink(vmObj, link_name='cdroms', attr='cdrom',
                                    get_href=True)

    if not cdroms:
        VM_API.logger.warning('There are no cdroms attached to vm %s', vmName)
        return not positive
    return positive


def _prepareNicObj(**kwargs):
    nic_obj = data_st.Nic()
    vnic_profile_obj = data_st.VnicProfile()

    if 'name' in kwargs:
        nic_obj.set_name(kwargs.get('name'))

    if 'interface' in kwargs:
        nic_obj.set_interface(kwargs.get('interface'))

    if 'mac_address' in kwargs:
        nic_obj.set_mac(data_st.Mac(address=kwargs.get('mac_address')))

    if 'plugged' in kwargs:
        nic_obj.set_plugged(str(kwargs.get('plugged')).lower())

    if 'linked' in kwargs:
        nic_obj.set_linked(kwargs.get('linked'))

    if 'network' in kwargs:
        vm_obj = VM_API.find(kwargs['vm'])
        cluster_id = vm_obj.get_cluster().get_id()
        cluster_obj = CLUSTER_API.find(cluster_id, attribute='id')

        if kwargs.get('network') is None:
            nic_obj.set_vnic_profile(vnic_profile_obj)
        else:
            vnic_profile_obj = get_vnic_profile_obj(
                kwargs.get('vnic_profile') if 'vnic_profile' in kwargs
                else kwargs.get('network'),
                kwargs.get('network'), cluster_obj.get_name()
            )

            nic_obj.set_vnic_profile(vnic_profile_obj)

    return nic_obj


def get_vm_nics(vm):
    """
    Get VM NICS href

    Args:
        vm (str): VM name

    Returns:
        str: VM NICs href
    """
    vm_obj = VM_API.find(vm)
    logger.info("Get NICs href from VM %s", vm)
    return VM_API.getElemFromLink(
        vm_obj, link_name='nics', attr='vm_nic', get_href=True
    )


def get_vm_nic(vm, nic):
    """
    Get VM NIC

    Args:
        vm (str): VM name
        nic (str): NIC name

    Returns:
        NIC: VM NIC object
    """
    vm_obj = VM_API.find(vm)
    logger.info("Get %s vNIC object from %s", nic, vm)
    return VM_API.getElemFromElemColl(vm_obj, nic, 'nics', 'nic')


def addNic(positive, vm, **kwargs):
    """
    Add NIC to VM

    Args:
        positive (bool): Expected status
        vm (str): VM name where nic should be added
        kwargs (dict): Parameters for add NIC

    Keyword Args:
        name (str): NIC name
        network (str): Network name
        vnic_profile (str): The VNIC profile that will be selected for the NIC
        interface (str): NIC type. (virtio, rtl8139, e1000 and passthrough)
        mac_address (str): NIC mac address
        plugged (bool): Add the NIC with plugged/unplugged state
        linked (bool): Add the NIC with linked/unlinked state

    Returns:
        bool: True if NIC was added properly, False otherwise
    """
    nic_name = kwargs.get("name")
    vm_obj = VM_API.find(vm)
    expected_status = vm_obj.get_status()

    nic_obj = _prepareNicObj(vm=vm, **kwargs)
    nics_coll = get_vm_nics(vm)
    log_info, log_error = ll_general.get_log_msg(
        action="Add", obj_type="vNIC", obj_name=nic_name, positive=positive,
        extra_txt="to VM %s" % vm, **kwargs
    )
    logger.info(log_info)
    res, status = NIC_API.create(nic_obj, positive, collection=nics_coll)
    if not status:
        logger.error(log_error)
        return False

    # TODO: remove wait section. func need to be atomic. wait can be done
    # externally!
    if positive and status:
        return VM_API.waitForElemStatus(
            vm_obj, expected_status, VM_ACTION_TIMEOUT
        )
    return status


def updateVmDisk(positive, vm, disk, **kwargs):
    """
    Update already existing vm disk

    :param positive: Determines whether the case is positive or negative
    :type positive: bool
    :param vm: VM where disk should be updated
    :type vm: str
    :param disk: Name of the disk that should be updated
    :type disk: str
    :param alias: New name of the disk
    :type alias: str
    :param interface: IDE, virtio or virtio_scsi
    :type interface: str
    :param bootable: Specifies whether the disk should be marked as bootable
    :type bootable: bool
    :param shareable: Specifies whether the disk should be shareable
    :type shareable: bool
    :param provisioned_size: New disk provisioned_size in bytes
    :type size: int
    :param quota: The disk's quote in bytes
    :type quota: str
    :param disk_id: ID of the disk that should be updated
    :type disk_id: str
    :return: Status of the operation's result dependent on positive value
    :rtype: bool
    """
    if kwargs.get('disk_id', None) is not None:
        disk_obj = getVmDisk(vm, disk_id=kwargs.pop('disk_id'))
    else:
        disk_obj = getVmDisk(vm, alias=disk)
    new_disk = _prepareDiskObject(**kwargs)
    return DISKS_API.update(disk_obj, new_disk, positive)[1]


def updateNic(positive, vm, nic, **kwargs):
    """
    Update VM NIC

    Args:
        positive (bool): Expected status
        vm (str): VM name where nic should be updated
        nic (str): NIC name that should be updated
        kwargs (dict): kwargs for update VM NIC

    Keyword Arguments:
        name (str): NIC name
        network (str): Network name
        vnic_profile (str): The VNIC profile that will be selected for the NIC
        interface (str): NIC type. (virtio, rtl8139, e1000 and passthrough)
        mac_address (str): NIC mac address
        plugged (bool): Update the NIC with plugged/unplugged state
        linked (bool): Update the NIC with linked/unlinked state

    Returns:
        bool: status (True if NIC was updated properly, False otherwise)
    """
    log_info, log_error = ll_general.get_log_msg(
        action="update", obj_type="vNIC", obj_name=nic,
        positive=positive, extra_txt="on VM %s" % vm,  **kwargs
    )
    nic_new = _prepareNicObj(vm=vm, **kwargs)
    nic_obj = get_vm_nic(vm, nic)
    logger.info(log_info)
    if not NIC_API.update(nic_obj, nic_new, positive)[1]:
        logger.error(log_error)
        return False
    return True


def removeNic(positive, vm, nic):
    """
    Remove nic from vm

    Args:
        positive (bool): Expected status
        vm (str): VM where nic should be removed from
        nic (str): NIC name that should be removed

    Returns:
        bool: True if nic was removed properly, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Remove", obj_type="NIC", obj_name=nic, positive=positive,
        extra_txt="from VM %s" % vm
    )
    vm_obj = VM_API.find(vm)
    nic_obj = get_vm_nic(vm, nic)
    expected_status = vm_obj.get_status()

    logger.info(log_info)
    status = NIC_API.delete(nic_obj, positive)
    if not status:
        logger.error(log_error)
        return False

    # TODO: remove wait section. func need to be atomic. wait can be done
    # externally!
    if positive and status:
        return VM_API.waitForElemStatus(
            vm_obj, expected_status, VM_ACTION_TIMEOUT
        )
    return status


def hotPlugNic(positive, vm, nic):
    '''
    Description: implement hotPlug nic.
    Author: atal
    Parameters:
        * vm - vm name
        * nic - nic name to plug.
    Return: True in case of succeed, False otherwise
    '''
    try:
        nic_obj = get_vm_nic(vm, nic)
    except EntityNotFound:
        logger.error('Entity %s not found!' % nic)
        return not positive

    return bool(NIC_API.syncAction(nic_obj, "activate", positive))


def hotUnplugNic(positive, vm, nic):
    """
    Implement hotUnplug nic.

    __author__: 'atal'

    Args:
        positive (bool): Expected status.
        vm (str): VM name.
        nic (str): NIC name to unplug.

    Returns:
        bool: True if un-plug was succeed, False otherwise.
    """
    log_info, log_error = ll_general.get_log_msg(
        action="un-plug", obj_type="NIC", obj_name=nic, positive=positive,
        extra_txt="from VM %s" % vm
    )

    try:
        nic_obj = get_vm_nic(vm, nic)
    except EntityNotFound:
        logger.error('Entity %s not found!' % nic)
        return not positive

    logger.info(log_info)
    status = bool(NIC_API.syncAction(nic_obj, "deactivate", positive))

    if not status:
        logger.error(log_error)

    return status


def remove_locked_vm(vm_name, vdc, vdc_pass,
                     psql_username=RHEVM_UTILS_ENUMS['RHEVM_DB_USER'],
                     psql_db=RHEVM_UTILS_ENUMS['RHEVM_DB_NAME'],
                     psql_password=RHEVM_UTILS_ENUMS['RHEVM_DB_PASSWORD']):
    """
    Remove locked vm with flag force=true
    Make sure that vm no longer exists, otherwise set it's status to down,
    and remove it
    Author: jvorcak
    Parameters:
       * vm_name - name of the VM
       * vdc - address of the setup
       * vdc_pass - password for the vdc
       * psql_username - psql username
       * psql_db - name of the DB
    """
    vm_obj = VM_API.find(vm_name)

    if removeVm(True, vm_obj.get_name(), force='true'):
        return True

    # clean if vm has not been removed
    logger.error('Locked vm has not been removed with force flag')

    update_vm_status_in_database(vm_obj.get_name(), 0, vdc, vdc_pass,
                                 psql_username, psql_db, psql_password)

    return removeVm("true", vm_obj.get_name())


def _getVmSnapshots(vm, get_href=True, all_content=False):
    """
    Get the requested vm's snapshot collection

    :param vm: vm name
    :type vm: str
    :param get_href: If True, get vm's snapshots' href
    :type get_href: bool
    :param all_content: If True, snapshots will return with all content
    :type all_content: bool
    :return: vm's snapshot collection
    :rtype: list
    """
    vmObj = VM_API.find(vm)
    return SNAPSHOT_API.getElemFromLink(
        vmObj, get_href=get_href, all_content=all_content)


def _getVmSnapshot(vm, snap, all_content=False):
    """
    Get a specific vm snapshot

    :param vm: vm name
    :type vm: str
    :param snap: Snapshot description
    :type snap: str
    :param all_content: If True, snapshots will return with all content
    :type all_content: bool
    :return: vm snapshot
    :rtype: Snapshot object
    """
    snapshot_objects = _getVmSnapshots(vm, False, all_content=all_content)
    logger.info(
        "Snapshots found: %s", [
            snapshot.get_description() for snapshot in snapshot_objects
        ]
    )
    for snapshot in snapshot_objects:
        if snapshot.get_description() == snap:
            return snapshot
    return None


def addSnapshot(
    positive, vm, description, wait=True, persist_memory=None, disks_lst=None
):
    """
    Description: Add snapshot to VM

    __author__ = "ratamir"

    :param positive: True if operation should succeed, False otherwise
    :type positive: bool
    :param vm: Name of the VM for which a snapshot will be created
    :type vm: str
    :param description: Snapshot name
    :type description: str
    :param wait: Specifies whether to wait until the snapshot
    operation has been completed
    waiting when False
    :type wait: bool
    :param persist_memory: True when memory state should be saved with the
    snapshot, False when the memory state doesn't need to be saved with the
    snapshot. The default is False
    :param disks_lst: If not None, this list of disks names will be included in
    snapshot's disks (Single disk snapshot)
    :type disks_lst: list
    :return: Status (True if snapshot was added properly, False otherwise)
    :rtype: bool
    """

    snapshot = data_st.Snapshot()
    snapshot.set_description(description)
    snapshot.set_persist_memorystate(persist_memory)

    if disks_lst:
        disks_coll = data_st.Disks()
        for disk in disks_lst:

            diskObj = DISKS_API.find(disk)

            disk = data_st.Disk()
            disk.set_id(diskObj.get_id())

            disks_coll.add_disk(disk)

        snapshot.set_disks(disks_coll)

    vmSnapshots = _getVmSnapshots(vm)

    snapshot, status = SNAPSHOT_API.create(snapshot, positive,
                                           collection=vmSnapshots,
                                           compare=wait)

    if wait:
        wait_for_jobs([ENUMS['job_create_snapshot']])

    try:
        snapshot = _getVmSnapshot(vm, description)
    except EntityNotFound:
        return False == positive

    snapshotStatus = True
    if status and positive and wait:
        snapshotStatus = SNAPSHOT_API.waitForElemStatus(
            snapshot, 'ok', VM_IMAGE_OPT_TIMEOUT,
            collection=_getVmSnapshots(vm, False))
        if snapshotStatus:
            snapshotStatus = validateSnapshot(positive, vm, description)
    return status and snapshotStatus


def validateSnapshot(positive, vm, snapshot):
    '''
    Description: Validate snapshot if exist
    Author: egerman
    Parameters:
       * vm - vm where snapshot should be restored
       * snapshot - snapshot name
    Return: status (True if snapshot exist, False otherwise)
    '''
    try:
        _getVmSnapshot(vm, snapshot)
        return True
    except EntityNotFound:
        return False


def wait_for_snapshot_gone(
        vm_name, snapshot, timeout=VM_REMOVE_SNAPSHOT_TIMEOUT
):
    """
    Wait for snapshot to disappear from the setup. This function will block
    up to `timeout` seconds, sampling the snapshots list until the specified
    snapshot is gone

    :param vm_name: Name of the vm that the snapshot created on
    :type vm_name: str
    :param snapshot: Snapshot description
    :type snapshot: str
    :param timeout: How long should wait until the snapshot is removed
    :type timeout: int
    :return: True if snapshot removed from setup in the given timeout,
    False otherwise
    :rtype: bool
    """
    logger.info(
        "Waiting until snapshot: %s of vm: %s is gone",
        snapshot, vm_name
    )
    for sample in TimeoutingSampler(
            timeout, SNAPSHOT_SAMPLING_PERIOD, get_vm_snapshots, vm_name
    ):
        if snapshot not in [snap.get_description() for snap in sample]:
            return True
    logger.error(
        "Snapshot: %s is not removed from vm: %s",
        snapshot, vm_name
        )
    return False


def removeSnapshot(
    positive, vm, description, timeout=VM_REMOVE_SNAPSHOT_TIMEOUT,
    wait=True
):
    """
    Remove vm snapshot

    __author__ = 'ratamir'
    :param positive: Determines whether the case is positive or negative
    :type positive: bool
    :param vm: Name of the vm that the snapshot created on
    :type vm: str
    :param description: Snapshot description to remove
    :type description: str
    :param timeout: How long to wait for the snapshot removeal
    :type timeout: int
    :param wait: True in case of async
    :type wait: bool
    :return: True if snapshot removed successfully, False otherwise
    :rtype: bool
    """
    # TODO: Old implementation used 'timeout' parameter to determine if should
    # wait or not - timeout < 0 means don't wait - need refactor all these
    # places
    if timeout < 0:
        wait = False
    snapshot = _getVmSnapshot(vm, description)
    logger.info("Removing snapshot %s", description)
    if not SNAPSHOT_API.delete(snapshot, positive):
        return False

    if wait and positive:
        status = wait_for_snapshot_gone(vm, description, timeout)
        return status
    return True


def runVmOnce(
    positive, vm, pause=None, display_type=None, stateless=None,
    cdrom_image=None, floppy_image=None, boot_dev=None, host=None,
    domainName=None, user_name=None, password=None,
    wait_for_state=ENUMS['vm_state_powering_up'],
    use_cloud_init=False, initialization=None,
    use_sysprep=False,
):
    """
    Run once vm with specific parameters

    :param positive: if run must succeed or not
    :type positive: bool
    :param vm: vm name to run
    :type vm: str
    :param pause: if vm must started in pause state
    :type pause: str
    :param display_type: display type of vm
    :type display_type: str
    :param stateless: if vm must be stateless
    :type stateless: bool
    :param cdrom_image: cdrom image to attach
    :type cdrom_image: str
    :param floppy_image: floppy image to attach
    :type floppy_image: str
    :param boot_dev: boot vm from device
    :type boot_dev: str
    :param host: run vm on host
    :type host: str
    :param domainName: vm domain
    :type domainName: str
    :param user_name: domain user name
    :type user_name: str
    :param password: domain password name
    :type password: str
    :param wait_for_state: wait for specific vm state after run
    :type wait_for_state:
    :param use_cloud_init: If to use cloud init
    :type use_cloud_init: bool
    :param initialization: Initialization obj for cloud init
    :type initialization: initialization
    :param use_sysprep: True if sysprep should be used, False otherwise
    :type use_sysprep: boolean
    :return: True, if positive and action succeed
    or negative and action failed, otherwise False
    :rtype: bool
    """
    # TODO Consider merging this method with the startVm.
    vm_obj = VM_API.find(vm)
    action_params = {}
    vm_for_action = data_st.Vm()
    if display_type:
        vm_for_action.set_display(data_st.Display(type_=display_type))

    if None is not stateless:
        vm_for_action.set_stateless(stateless)
    if use_cloud_init:
        action_params['use_cloud_init'] = 'true'
        if initialization:
            vm_for_action.set_initialization(initialization)
    if cdrom_image:
        cdrom = data_st.Cdrom()
        vm_cdroms = data_st.Cdroms()
        cdrom.set_file(data_st.File(id=cdrom_image))
        vm_cdroms.add_cdrom(cdrom)
        vm_for_action.set_cdroms(vm_cdroms)

    if floppy_image:
        floppy = data_st.Floppy()
        floppies = data_st.Floppies()
        floppy.set_file(data_st.File(id=floppy_image))
        floppies.add_floppy(floppy)
        vm_for_action.set_floppies(floppies)

    if boot_dev:
        os_type = data_st.OperatingSystem()
        os_type.set_boot(
            boot=data_st.Boot(
                devices=data_st.devicesType(
                    device=boot_dev.split(",")
                )
            )
        )
        vm_for_action.set_os(os_type)

    if host:
        vm_policy = data_st.VmPlacementPolicy()
        vm_hosts = data_st.Hosts()
        vm_hosts.add_host(HOST_API.find(host))
        vm_policy.set_hosts(vm_hosts)
        vm_for_action.set_placement_policy(vm_policy)
        # host_obj = HOST_API.find(host)
        # placement_policy = data_st.VmPlacementPolicy(hosts=host_obj)
        # vm_for_action.set_placement_policy(placement_policy)

    if domainName:
        domain = data_st.Domain()
        domain.set_name(domainName)

        if user_name and password is not None:
            domain.set_user(
                data_st.User(user_name=user_name, password=password)
            )
        vm_for_action.set_domain(domain)

    action_params["vm"] = vm_for_action
    action_params['use_sysprep'] = use_sysprep
    if pause and pause.lower() == 'true':
        wait_for_state = ENUMS['vm_state_paused']
        action_params["pause"] = pause
    status = bool(
        VM_API.syncAction(vm_obj, 'start', positive, **action_params)
    )
    if status and positive:
        return VM_API.waitForElemStatus(
            vm_obj, wait_for_state, VM_ACTION_TIMEOUT
        )
    return status


def suspendVm(positive, vm, wait=True):
    """
    Suspend VM:
    Wait for status UP, then the suspend action is performed
    and then it awaits status SUSPENDED, sampling every 10 seconds.

    __Author__: jhenner

     Args:
        positive (bool): Expected status
        vm (str): Name of vm
        wait (bool) wait until and of action when positive equal to True
    Returns:
        bool: True if vm suspended and test is positive, False otherwise
    """

    log_info, log_error = ll_general.get_log_msg(
        action="suspend", obj_type="vm", obj_name=vm, positive=positive,
    )
    vmObj = VM_API.find(vm)
    logger.info(log_info)

    if not VM_API.waitForElemStatus(vmObj, 'up', VM_ACTION_TIMEOUT):
        logger.error(log_error)
        return False

    async = 'false'
    if not wait:
        async = 'true'

    if not VM_API.syncAction(vmObj, 'suspend', positive, async=async):
        logger.error(log_error)
        return False
    if wait and positive:
        return VM_API.waitForElemStatus(
            vmObj, 'suspended', timeout=VM_ACTION_TIMEOUT,
            ignoreFinalStates=True
        )
    return True


def shutdownVm(positive, vm, async='true'):
    '''
    Description: shutdown vm
    Author: edolinin
    Parameters:
       * vm - name of vm
       * async - if false, wait for VM to shutdown
    Return: status (True if vm was stopped properly, False otherwise)
    '''
    collect_vm_logs(vm)
    return changeVMStatus(positive, vm, 'shutdown', 'down', async=async)


def migrateVm(
        positive,
        vm,
        host=None,
        wait=True,
        force=False,
        timeout=MIGRATION_TIMEOUT
):
    """
    Migrate the VM.

    If the host was specified, after the migrate action was performed,
    the method is checking whether the VM status is UP and whether
    the VM runs on required destination host.

    If the host was not specified, after the migrate action was performed, the
    method is checking whether the VM is UP and whether the VM runs
    on host different to the source host.

    :param positive: Expected result
    :type positive: bool
    :param vm: name of vm
    :type vm: str
    :param host: Name of the destination host to migrate VM on, or
                 None for RHEVM destination host autodetect.
    :type host: str
    :param wait: When True wait until end of action, False return without
                 waiting.
    :type wait: bool
    :param force: <Don't know what is force. please comment>
    :type force: bool
    :param timeout: Timeout to check if vm is update after migration is done
    :type timeout: int
    :return: True if vm was migrated and test is positive, False otherwise.
    :rtype: bool
    """
    vm_obj = VM_API.find(vm)
    if not vm_obj.get_host():
        logger.error("VM has no attribute 'host': %s", dir(vm_obj))
        return False
    action_params = {}

    # If the host is not specified, we should let RHEVM to autodetect the host.
    if host:
        dest_host_obj = HOST_API.find(host)
        action_params["host"] = data_st.Host(id=dest_host_obj.id)

    if force:
        action_params["force"] = True

    log_info, log_error = ll_general.get_log_msg(
        action="Migrate", obj_type=VM, obj_name=vm, positive=positive,
    )
    logger.info(log_info)
    if not VM_API.syncAction(vm_obj, "migrate", positive, **action_params):
        logger.error(log_error)
        return False

    # Check the VM only if we do the positive test. We know the action status
    # failed so with fingers crossed we can assume that VM didn't migrate.
    if not wait or not positive:
        logger.warning(
            "Not going to wait till VM migration completes. wait=%s, "
            "positive=%s" % (str(wait), positive)
        )
        return True

    # Barak: change status to up from powering up, since all migrations ends in
    # up, but diskless VM skips the powering_up phase
    if not VM_API.waitForElemStatus(vm_obj, "up", timeout):
        return False

    # Check whether we tried to migrate vm to different cluster
    # in this case we return False, since this action shouldn't be allowed.
    logger.info("Getting the %s host after VM migrated.", vm)
    real_dest_host_id = VM_API.find(vm).host.id
    real_dest_host_obj = HOST_API.find(real_dest_host_id, "id")
    if vm_obj.cluster.id != real_dest_host_obj.cluster.id:
        logger.error("%s migrated to a different cluster", vm)
        return False

    # Validating that the vm did migrate to a different host
    if vm_obj.host.id == real_dest_host_id:
        logger.error("%s stayed on the same host", vm)
        return False

    return True


def ticketVm(positive, vm, expiry):
    '''
    Description: ticket vm
    Author: edolinin
    Parameters:
       * vm - vm to ticket
       * expiry - ticket expiration time
    Return: status (True if vm was ticketed properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)

    ticket = data_st.Ticket()
    ticket.set_expiry(int(expiry))

    return bool(VM_API.syncAction(vmObj, "ticket", positive, ticket=ticket))


def addTagToVm(positive, vm, tag):
    '''
    Description: add tag to vm
    Author: edolinin
    Parameters:
       * vm - vm to add tag to
       * tag - tag name
    Return: status (True if tag was added properly, False otherwise)
    '''

    vmObj = VM_API.find(vm)
    vmTags = VM_API.getElemFromLink(vmObj, link_name='tags', attr='tag',
                                    get_href=True)

    tagObj = data_st.Tag()
    tagObj.set_name(tag)

    tagObj, status = TAG_API.create(tagObj, positive, collection=vmTags)
    return status


def removeTagFromVm(positive, vm, tag):
    '''
    Description: remove tag from vm
    Author: edolinin
    Parameters:
       * vm - vm to remove tag from
       * tag - tag name
    Return: status (True if tag was removed properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    tagObj = VM_API.getElemFromElemColl(vmObj, tag, 'tags', 'tag')
    return VM_API.delete(tagObj, positive)


def exportVm(
    positive, vm, storagedomain, exclusive='false',
    discard_snapshots='false', timeout=VM_ACTION_TIMEOUT, async=False
):
    """
    Export vm to export storage domain

    __Author__: edolinin, jhenner

    Args:
        positive (bool): Expected status
        vm (str): Name of vm to export
        storagedomain (str): Name of export storage domain where to export
            vm to
        exclusive (str): Overwrite any existing vm of the same name in the
            destination domain ('false' by default)
        discard_snapshots (str): Do not include vm snapshots with the
            exported vm ('false' by default)
        timeout (int): Timeout for the export operation
        async (bool): Specifies whether the operation should be asynchronous

    Returns:
        bool: True if vm was exported properly, False otherwise
    """
    vm_obj = VM_API.find(vm)
    sd = data_st.StorageDomain(name=storagedomain)
    expected_status = vm_obj.get_status()
    action_params = dict(
        storage_domain=sd, exclusive=exclusive,
        discard_snapshots=discard_snapshots
    )
    status = bool(
        VM_API.syncAction(vm_obj, "export", positive, async, **action_params)
    )
    logger.info("Export VM %s to export domain %s", vm, storagedomain)
    if status and positive:
        return VM_API.waitForElemStatus(
            vm_obj, expected_status, timeout)
    logger.error(
        "Failed to export VM %s to export domain %s", vm, storagedomain
    )
    return status


def importVm(
    positive, vm, export_storagedomain, import_storagedomain, cluster,
    name=None, async=False, collapse=False, clone=False,
    timeout=VM_ACTION_TIMEOUT
):
    """
    Import a vm from an export domain

    __author__ = "edolinin, cmestreg"

    Args:
        positive (bool): True when importVm is expected to succeed, False
            otherwise
        vm (str): Name of the vm to import
        export_storagedomain (str): Storage domain where to export vm from
        import_storagedomain (str): Storage domain where to import vm to
        cluster (str): Name of cluster to import the vm into
        name (str): New name for the imported vm
        async (bool): If the action should be asynchronous
        collapse (bool): If the snapshots should be collapsed, default False
        clone (bool): If the disk should be cloned, default False

    Returns:
        bool: True if vm was imported properly, False otherwise
    """
    export_domain_obj = STORAGE_DOMAIN_API.find(export_storagedomain)
    sd_vms = VM_API.getElemFromLink(
        export_domain_obj, link_name='vms', attr='vm', get_href=False,
    )
    vm_obj = VM_API.find(vm, collection=sd_vms)

    expected_status = vm_obj.get_status()
    expected_name = vm_obj.get_name()

    sd = data_st.StorageDomain(name=import_storagedomain)
    cl = data_st.Cluster(name=cluster)

    action_params = {
        'storage_domain': sd,
        'cluster': cl,
        'async': async
    }

    action_name = 'import'
    if opts['engine'] in ('cli', 'sdk'):
        action_name = 'import_vm'

    new_vm = data_st.Vm()
    if name:
        new_vm.set_name(name)
        clone = True
        expected_name = name

    if clone:
        action_params['clone'] = True
        collapse = True

    if collapse:
        new_vm.snapshots = data_st.Snapshots()
        new_vm.snapshots.collapse_snapshots = True
        action_params['vm'] = new_vm

    logger.info("Import VM %s into cluster %s", vm, cluster)
    status = bool(
        VM_API.syncAction(vm_obj, action_name, positive, **action_params)
    )

    if async:
        return status

    if status and positive:
        return waitForVMState(expected_name, expected_status, timeout=timeout)
    logger.error("Failed to import VM %s into cluster %s", vm, cluster)
    return status


def moveVm(positive, vm, storagedomain, wait=True):
    '''
    Description: move vm to another storage domain
    Author: edolinin
    Parameters:
       * vm - name of vm
       * storagedomain - name of storage domain to move vm to
    Return: status (True if vm was moved properly, False otherwise)
    '''
    vmObj = VM_API.find(vm)
    expectedStatus = vmObj.get_status()
    storageDomainId = STORAGE_DOMAIN_API.find(storagedomain).id
    sd = data_st.StorageDomain(id=storageDomainId)

    async = 'false'
    if not wait:
        async = 'true'
    status = bool(
        VM_API.syncAction(
            vmObj, "move", positive, storage_domain=sd, async=async
        )
    )
    if positive and status and wait:
        return VM_API.waitForElemStatus(
            vmObj, expectedStatus, VM_IMAGE_OPT_TIMEOUT)
    return status


def changeCDWhileRunning(vm_name, cdrom_image):
    '''
    Description: Change cdrom image while vm is running
    Since the change is for current session only, there is
    no change in the API except of event, that's why there's no validation
    in this method.
    To check whether cdrom has been changed, event test must follow
    after this test case
    Author: jvorcak
    Parameters:
       * vm_name - name of the virtual machine
       * cdrom_image - image to be changed
    Return (True if reponse code is 200 for change request,
            False otherwise)
    '''
    cdroms = getCdRomsObjList(vm_name)
    newCdrom = data_st.Cdrom()
    newCdrom.set_file(data_st.File(id=cdrom_image))

    cdrom, status = CDROM_API.update(cdroms[0], newCdrom, True, current=True)

    return status


def attach_cdrom_vm(positive, vm_name, cdrom_image):
    """
    Attach a cdrom image to a vm
    Author: cmestreg
     * vm_name: name of the vm
     * cdrom_image: name of the image to attach to
    Returns: True in case of success/False otherwise
    """
    cdroms = getCdRomsObjList(vm_name)
    newCdrom = data_st.Cdrom()
    newCdrom.set_file(data_st.File(id=cdrom_image))

    cdrom, status = CDROM_API.update(cdroms[0], newCdrom, positive)
    return status


def eject_cdrom_vm(vm_name):
    """
    Eject the CD/DVD from the vm

    :param vm_name: name of the vm
    :type vm_name: str
    :return True in case of success/False otherwise
    :rtype bool
    """
    cdroms = getCdRomsObjList(vm_name)
    newCdrom = data_st.Cdrom()
    # Eject action is done through setting the File property to empty
    newCdrom.set_file(data_st.File())

    # Is important to pass current=True so the action takes place in the
    # current execution
    cdrom, status = CDROM_API.update(cdroms[0], newCdrom, True, current=True)
    return status


def getCdRomsObjList(vm_name, href=False):
    """
    Description: Returns a list of cdrom objects
    Author: cmestreg
    Parameters:
        * vm_name: name of the vm
        * href: boolean, return href link or not
    Returns a list of cdrom object
    """
    vmObj = VM_API.find(vm_name)
    return CDROM_API.getElemFromLink(vmObj, link_name='cdroms',
                                     attr='cdrom', get_href=href)


def remove_cdrom_vm(positive, vm_name):
    """
    Description: Removes the cdrom object from the vm
    Author: cmestreg
    Parameters:
        * vm_name: name of the vm to remove the cdrom from
    Returns: True is action succeeded, False otherwise
    """
    cdroms = getCdRomsObjList(vm_name)
    return CDROM_API.delete(cdroms[0], positive)


def _createVmForClone(
    name, template=None, cluster=None, clone=None, vol_sparse=None,
    vol_format=None, storagedomain=None, snapshot=None, vm_name=None,
    **kwargs
):
    """
    Description: helper function - creates VM objects for VM_API.create call
                 when VM is created from template, sets all required attributes
    Author: kjachim
    Parameters:
       * template - template name
       * name - vm name
       * cluster - cluster name
       * clone - true/false - if true, template disk will be copied
       * vol_sparse - true/false - convert VM disk to sparse/preallocated
       * vol_format - COW/RAW - convert VM disk format
       * storagedomain - storage domain to clone the VM disk
       * snapshot - description of the snapshot to clone
       * vm_name - name of the snapshot's vm
    Returns: VM object
    """
    # TODO: Probaly better split this since the disk parameter is not that
    # similar for template and snapshots
    # Create the vm object
    vm = _prepareVmObject(name=name, cluster=cluster, **kwargs)
    if template:
        templObj = TEMPLATE_API.find(template)
        vm.set_template(templObj)
        disks_from = templObj
    elif snapshot and vm_name:
        # better pass both elements and don't search in all vms
        snapshotObj = _getVmSnapshot(vm_name, snapshot)
        snapshots = Snapshots()
        snapshots.add_snapshot(snapshotObj)
        vm.set_snapshots(snapshots)
        disks_from = snapshotObj
    else:
        raise ValueError("Either template or snapshot and vm parameters "
                         "must be set")

    diskArray = data_st.Disks()
    diskArray.set_clone(clone.lower())

    disks = DISKS_API.getElemFromLink(disks_from, link_name='disks',
                                      attr='disk', get_href=False)
    for dsk in disks:
        if template:
            disk = data_st.Disk(id=dsk.get_id())
        else:
            disk = data_st.Disk()
            disk.set_image_id(dsk.get_id())
        storage_domains = data_st.StorageDomains()
        if vol_sparse is not None:
            disk.set_sparse(vol_sparse)
        if vol_format is not None:
            disk.set_format(vol_format)
        if storagedomain is not None:
            sd = [STORAGE_DOMAIN_API.find(storagedomain)]
        else:
            # StorageDomain property is needed when include any disk
            # on the request
            sd = []
            for elem in dsk.get_storage_domains().get_storage_domain():
                sd.append(
                    STORAGE_DOMAIN_API.find(
                        elem.get_id(), attribute="id")
                )
        for elem in sd:
            storage_domains.add_storage_domain(elem)
        disk.storage_domains = storage_domains
        diskArray.add_disk(disk)
    vm.set_disks(diskArray)

    return vm


def cloneVmFromTemplate(positive, name, template, cluster,
                        timeout=VM_IMAGE_OPT_TIMEOUT, clone=True,
                        vol_sparse=None, vol_format=None, wait=True,
                        storagedomain=None, **kwargs):
    '''
    Description: clone vm from a pre-defined template
    Author: edolinin
    Parameters:
       * name - vm name
       * template - template name
       * cluster - cluster name
       * timeout - action timeout (depends on disk size or system load
       * clone - true/false - if true, template disk will be copied
       * vol_sparse - True/False - convert VM disk to sparse/preallocated
       * vol_format - COW/RAW - convert VM disk format
    Return: status (True if vm was cloned properly, False otherwise)
    '''
    clone = str(clone).lower()
    # don't even try to use deepcopy, it will fail
    expectedVm = _createVmForClone(name, template, cluster, clone, vol_sparse,
                                   vol_format, storagedomain,
                                   **kwargs)
    newVm = _createVmForClone(name, template, cluster, clone, vol_sparse,
                              vol_format, storagedomain,
                              **kwargs)

    if clone == 'true':
        expectedVm.set_template(data_st.Template(id=BLANK_TEMPLATE))
    vm, status = VM_API.create(newVm, positive, expectedEntity=expectedVm,
                               async=(not wait), compare=wait)
    if positive and status and wait:
        return VM_API.waitForElemStatus(vm, "DOWN", timeout)
    return status


def cloneVmFromSnapshot(positive, name, cluster, vm, snapshot,
                        storagedomain=None, wait=True, sparse=True,
                        vol_format=ENUMS['format_cow'],
                        timeout=VM_IMAGE_OPT_TIMEOUT, compare=True,
                        **kwargs):
    '''
    Description: clone vm from a snapshot
    Author: cmestreg
    Parameters:
       * name - vm name
       * cluster - cluster name
       * vm - name of vm where the snapshot was taken
       * snapshot - snapshot to clone from
       * wait
       * timeout - action timeout
       * compare - True if need validator to work
    Return: True if vm was cloned properly, False otherwise
    '''
    # don't even try to use deepcopy, it will fail
    expectedVm = _createVmForClone(
        name, cluster=cluster, clone="true", vol_sparse=sparse,
        vol_format=vol_format, storagedomain=storagedomain, snapshot=snapshot,
        vm_name=vm, **kwargs)
    newVm = _createVmForClone(
        name, cluster=cluster, clone="true", vol_sparse=sparse,
        vol_format=vol_format, storagedomain=storagedomain, snapshot=snapshot,
        vm_name=vm, **kwargs)

    expectedVm.set_snapshots(None)
    expectedVm.set_template(data_st.Template(id=BLANK_TEMPLATE))
    vm, status = VM_API.create(newVm, positive, expectedEntity=expectedVm,
                               compare=compare)
    if positive and status and wait:
        return VM_API.waitForElemStatus(vm, "DOWN", timeout)
    return status


def checkVmStatistics(positive, vm):
    '''
    Description: check existence and format of vm statistics values
    Author: edolinin
    Parameters:
        * vm - vm where to check statistics
    Return: status (True if all statistics appear and in correct format,
                    False otherwise)
    '''
    status = True
    vmObj = VM_API.find(vm)

    expectedStatistics = ['memory.installed', 'memory.used',
                          'cpu.current.guest', 'cpu.current.hypervisor',
                          'cpu.current.total']

    numOfExpStat = len(expectedStatistics)
    statistics = VM_API.getElemFromLink(vmObj, link_name='statistics',
                                        attr='statistic')

    for stat in statistics:
        datum = str(stat.get_values().get_value()[0].get_datum())
        if not re.match('(\d+\.\d+)|(\d+)', datum):
            logger.error('Wrong value for ' + stat.get_name() + ': ' + datum)
            status = False
        else:
            logger.info('Correct value for ' + stat.get_name() + ': ' + datum)

        if stat.get_name() in expectedStatistics:
            expectedStatistics.remove(stat.get_name())

    if len(expectedStatistics) == 0:
        logger.info('All ' + str(numOfExpStat) + ' statistics appear')
    else:
        logger.error(
            'The following statistics are missing: %s',
            expectedStatistics,
        )
        status = False

    return status


def createVm(
    positive, vmName, vmDescription=None, cluster='Default', nic=None,
    nicType=None, mac_address=None, storageDomainName=None,
    provisioned_size=None,
    diskType=ENUMS['disk_type_data'], volumeType='true',
    volumeFormat=ENUMS['format_cow'], diskActive=True,
    diskInterface=ENUMS['interface_virtio'], bootable='true',
    wipe_after_delete='false', start='false', template='Blank',
    templateUuid=None, type=None, os_type=None, memory=None,
    cpu_socket=None, cpu_cores=None, cpu_mode=None, display_type=None,
    installation=False, slim=False, user=None, password=None,
    attempt=60, interval=60, cobblerAddress=None, cobblerUser=None,
    cobblerPasswd=None, image=None, async=False, hostname=None,
    network=None, vnic_profile=None, useAgent=False,
    placement_affinity=None, placement_host=None, placement_hosts=None,
    vcpu_pinning=None,
    highly_available=None, availablity_priority=None, vm_quota=None,
    disk_quota=None, plugged='true', linked='true', protected=None,
    copy_permissions=False, custom_properties=None,
    watchdog_model=None, watchdog_action=None, cpu_profile_id=None,
    numa_mode=None, ballooning=None, memory_guaranteed=None,
    initialization=None, cpu_shares=None, serial_number=None
):
    """
    Create new vm with nic, disk and OS

    :param vmName: vm name
    :type vmName: str
    :param vmDescription: description of vm
    :type vmDescription: str
    :param cluster: cluster name
    :type cluster: str
    :param nic: nic name
    :type nic: str
    :param storageDomainName: storage domain name
    :type storageDomainName: str
    :param provisioned_size: size of disk (in bytes)
    :type provisioned_size: int
    :param diskType: disk type (SYSTEM, DATA)
    :type diskType: str
    :param volumeType: true means sparse (thin provision),
    false - pre-allocated
    :type volumeType: str
    :param volumeFormat: format type (COW)
    :type volumeFormat: str
    :param diskInterface: disk interface (VIRTIO or IDE ...)
    :type diskInterface: str
    :param bootable: if disk bootable
    :type bootable: str
    :param wipe_after_delete: wipe after delete
    :type wipe_after_delete: str
    :param type: vm type (SERVER or DESKTOP)
    :type type: str
    :param start: in case of true the function start vm
    :type start: str
    :param display_type: type of vm display (VNC or SPICE)
    :type display_type: str
    :param installation: true for install os and check connectivity in the end
    :type installation: bool
    :param user: user to connect to vm after installation
    :type user: str
    :param password: password to connect to vm after installation
    :type password: str
    :param attempt: attempts to connect after installation
    :type attempt: int
    :param interval: interval between attempts
    :type interval: int
    :param os_type: type of OS as it appears in art/conf/elements.conf
    :type os_type: str
    :param useAgent: Set to True, if desired to read the ip from VM
    :type useAgent: bool
    :param placement_affinity: vm to host affinity
    :type placement_affinity: str
    :param placement_host: host that the affinity holds for
    :type placement_host: str
    :param placement_hosts: multiple hosts for vm placement
    :type placement_hosts: list
    :param vcpu_pinning: vcpu pinning affinity
    :type vcpu_pinning: dict
    :param vm_quota: quota id for vm
    :type vm_quota: str
    :param disk_quota: quota id for vm disk
    :type disk_quota: str
    :param plugged: shows if specific VNIC is plugged/unplugged
    :type plugged: str
    :param linked: shows if specific VNIC is linked or not
    :type linked: str
    :param protected: true if VM is delete protected
    :type protected: str
    :param cpu_mode: cpu mode
    :type cpu_mode: str
    :param cobblerAddress: backward compatibility with cobbler provisioning,
    should be removed
    :type cobblerAddress: str
    :param cobblerUser: backward compatibility with cobbler provisioning,
    should be removed
    :type cobblerUser: str
    :param cobblerPasswd: backward compatibility with cobbler provisioning,
    should be removed
    :type cobblerPasswd: str
    :param network: The network that the VM's VNIC will be attached to
    (If 'vnic_profile' is not specified as well, a profile without port
    mirroring will be selected for the VNIC arbitrarily
    from the network's profiles)
    :type network: str
    :param vnic_profile: The VNIC profile to set on the VM VNIC
    (It should be for the network specified above)
    :type vnic_profile: str
    :param watchdog_model: model of watchdog card
    :type watchdog_model: str
    :param watchdog_action: action of watchdog card
    :type watchdog_action: str
    :param cpu_profile_id: cpu profile id
    :type cpu_profile_id: str
    :param numa_mode: numa mode for vm(strict, preferred, interleave)
    :type numa_mode: str
    :param ballooning: memory ballooning device enable or disable
    :type ballooning: bool
    :param memory_guaranteed: size of guaranteed memory in bytes
    :type memory_guaranteed: int
    :param initialization: Initialization obj for cloud init
    :type initialization: Initialization
    :param cpu_shares: cpu_shares
    :type cpu_shares: int
    :param serial_number: serial number to use
    :type serial_number: str
    :returns: True, if create vm success, otherwise False
    :rtype: bool
    """
    ip = False
    if not vmDescription:
        vmDescription = vmName
    if not addVm(
        positive, name=vmName, description=vmDescription,
        cluster=cluster, template=template, templateUuid=templateUuid,
        os_type=os_type, type=type, memory=memory,
        cpu_socket=cpu_socket, cpu_cores=cpu_cores,
        display_type=display_type, async=async,
        placement_affinity=placement_affinity,
        placement_host=placement_host, vcpu_pinning=vcpu_pinning,
        highly_available=highly_available,
        availablity_priority=availablity_priority, quota=vm_quota,
        protected=protected, cpu_mode=cpu_mode,
        copy_permissions=copy_permissions,
        custom_properties=custom_properties,
        cpu_profile_id=cpu_profile_id, numa_mode=numa_mode,
        ballooning=ballooning, memory_guaranteed=memory_guaranteed,
        initialization=initialization, cpu_shares=cpu_shares,
        serial_number=serial_number, placement_hosts=placement_hosts
    ):
        return False

    if nic:
        profile = vnic_profile if vnic_profile is not None else network
        if not addNic(
            positive, vm=vmName, name=nic, interface=nicType,
            mac_address=mac_address, network=network, vnic_profile=profile,
            plugged=plugged, linked=linked
        ):
            return False

    if template == "Blank" and storageDomainName and templateUuid is None:
        if not addDisk(
            positive, vm=vmName, provisioned_size=provisioned_size,
            type=diskType, storagedomain=storageDomainName, sparse=volumeType,
            interface=diskInterface, format=volumeFormat,
            bootable=bootable, quota=disk_quota,
            wipe_after_delete=wipe_after_delete, active=diskActive
        ):
            return False

    if watchdog_action and watchdog_model:
        if not add_watchdog(
            vm_name=vmName,
            watchdog_model=watchdog_model,
            watchdog_action=watchdog_action
        ):
            return False

    if installation:
        floppy = None
        if image is None:
            status, res = getImageByOsType(positive, os_type, slim)
            if not status:
                return False
            image = res["osBoot"]
            floppy = res["floppy"]

        try:
            if not unattendedInstallation(
                positive, vmName, image, nic=nic, floppyImage=floppy,
                hostname=hostname,
            ):
                return False
            if not waitForVMState(vmName):
                return False
            mac = getVmMacAddress(positive, vmName, nic=nic)
            if not mac[0]:
                return False
            mac = mac[1]["macAddress"]

            if not waitForSystemIsReady(
                mac,
                interval=interval,
                timeout=VM_INSTALL_TIMEOUT
            ):
                return False

            if useAgent:
                ip = waitForIP(vmName)[1]["ip"]

            logger.debug("%s has ip %s", vmName, ip)
            if not checkVMConnectivity(
                positive, vmName, os_type, attempt=attempt, interval=interval,
                nic=nic, user=user, password=password, ip=ip,
            ):
                return False
        finally:
            # FIXME: it doesn't work when it runs in parallel
            ProvisionContext.clear()
        return True
    else:
        if start.lower() == "true":
            return startVm(positive, vmName)

        return True


def waitForIP(
    vm, timeout=600, sleep=DEF_SLEEP, get_all_ips=False,
    vm_password=VM_PASSWORD
):
    """
    Waits until agent starts reporting IP address

    Args:
        vm (str): name of the virtual machine
        timeout (int): how long to wait
        sleep (int): polling interval
        get_all_ips (bool): Get all VM ips
        vm_password (str): VM root password

    Returns:
        tuple: True/False whether it obtained the IP, IP if fetched or None
    """
    #  import is done here to avoid loop
    import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
    vm_id = None
    vm_host = get_vm_host(vm_name=vm)
    if not vm_host:
        return False, {'ip': None}

    host_ip = ll_hosts.get_host_ip_from_engine(host=vm_host)
    vds_resource = resources.VDS(ip=host_ip, root_password=vm_password)
    out = vds_resource.vds_client("list", ["table"])
    for vm_info in out["vmList"]:
        if vm_info["vmName"] == vm:
            vm_id = vm_info["vmId"]
    if not vm_id:
        logger.error("Vm id for VM %s not found on VDSM %s", vm, vm_host)
        return False, {'ip': None}

    def _get_ip(vm, vds_resource, vm_id):
        """
        Get VM IP using vdsClient command on VDSM

        Args:
            vm (str): VM name
            vds_resource (VDS): VDSM resource
            vm_id (str): VM id in VDSM

        Returns:
            str or list: IP or list of IPs depend on get_all_ips param
        """
        vm_out = vds_resource.vds_client('getVmStats', [vm_id])
        try:
            vm_ips = vm_out['statsList'][0]['netIfaces'][0]['inet']
            ip = vm_ips if get_all_ips else vm_ips[0]
            ping_ip = ip[0] if isinstance(ip, list) else ip
            logger.info("Send ICMP to %s", ping_ip)
            if not vds_resource.network.send_icmp(dst=ping_ip):
                return None

        except (KeyError, IndexError):
            return None

        VM_API.logger.debug("Got IP %s for %s", ip, vm)
        return ip

    try:
        for ip in TimeoutingSampler(
            timeout, sleep, _get_ip, vm, vds_resource, vm_id
        ):
            if ip:
                return True, {'ip': ip}
    except APITimeout:
        logger.error("Failed to get IP for VM %s", vm)
    return False, {'ip': None}


def getVmMacAddress(positive, vm, nic='nic1'):
    """
    Function return mac address of vm with specific nic

    Args:
        positive (bool): Expected status.
        vm (str): VM name.
        nic (str): NIC name.

    Returns:
        tuple: True, mac address in dict or False,None
    """
    logger.info("Get VM %s MAC address", vm)
    try:
        nicObj = get_vm_nic(vm, nic)
    except EntityNotFound:
        VM_API.logger.error("Vm %s doesn't have nic '%s'", vm, nic)
        return False, {'macAddress': None}
    return True, {'macAddress': str(nicObj.mac.address)}


def check_vnic_on_vm_nic(vm, nic='nic1', vnic='rhevm'):
    """
    Check for vnic parameter value if this profile resides on the nic
    parameter
    **Author**: gcheresh

    **Parameters**:
        * *vm* - vm name to check for VNIC profile name on
        * *nic* - NIC on VM to check the VNIC profile on
        * *vnic* - vnic name to check on the NIC of VM
    **Returns**: True if VNIC profile with 'vnic' name is located on the nic
    of the vm
    """
    try:
        nic = get_vm_nic(vm, nic)
    except EntityNotFound:
        VM_API.logger.error("Vm %s doesn't have nic '%s'", vm, nic)
        return False
    if nic.get_vnic_profile():
        vnic_obj = VNIC_PROFILE_API.find(nic.get_vnic_profile().get_id(),
                                         attribute='id')
        return vnic_obj.get_name() == vnic
    # for NIC that doesn't have VNIC profile on it
    else:
        return vnic is None


def waitForSystemIsReady(mac, interval=60, timeout=VM_INSTALL_TIMEOUT):
    logger.info(
        "Wait until system %s has status != %s, checking every %s",
        mac, ProvisionContext.STATUS_BUILD, interval,
    )
    try:
        for status in TimeoutingSampler(
            timeout, interval, ProvisionContext.get_system_status, mac,
        ):
            logger.info(
                "Status of system %s is %s", mac, status,
            )
            if status == ProvisionContext.STATUS_ERROR:
                logger.error("Status of system is error, aborting ...")
                return False
            elif status != ProvisionContext.STATUS_BUILD:
                # NOTE: It can happen that guest doesn't provide reports,
                # so can not test on STATUS_READY
                break
    except APITimeout:
        logger.error(
            "System %s doesn't have desired status != %s in timeout %s", mac,
            ProvisionContext.STATUS_BUILD, VM_INSTALL_TIMEOUT,
        )
        return False
    return True


def removeSystem(mac, cobblerAddress=None, cobblerUser=None,
                 cobblerPasswd=None):
    '''
    Description: remove system from provisioning provider:
    Author: imeerovi
    Parameters:
       * mac - mac address of system to remove
       * cobbler* - backward compatibility with cobbler provisioning,
                    should be removed
    Return: True if remove succseeded and False otherwise.
    '''
    return ProvisionProvider.remove_system(mac)


def unattendedInstallation(positive, vm, image, nic='nic1', hostname=None,
                           floppyImage=None, cobblerAddress=None,
                           cobblerUser=None, cobblerPasswd=None):
    '''
    Description: install VM with answer file:
    unattended floppy disk for windows.
    via PXE for rhel.
    Author: imeerovi
    Parameters:
       * vm - VM with clean bootable hard disk.
       * nic- nic name to find out mac address- relevant for rhel only.
       * image- cdrom image for windows or profile for rhel.
       * floppyImage- answer file for windows.
       * cobbler* - backward compatibility with cobbler provisioning,
                    should be removed
    Return: status (True if VM started to insall OS, False otherwise).
    '''
    if re.search('rhel', image, re.I):
        status, mac = getVmMacAddress(positive, vm, nic=nic)
        if not status:
            return False
        if not ProvisionContext.add_system(
            mac=mac['macAddress'],
            os_name=image
        ):
            return False
        if hostname:
            if not ProvisionContext.set_host_name(
                name=mac['macAddress'],
                hostname=hostname
            ):
                return False

        boot_dev = 'hd,network'
        return runVmOnce(positive, vm, boot_dev=boot_dev)
    else:
        boot_dev = 'cdrom'
        return runVmOnce(
            positive, vm, cdrom_image=image, floppy_image=floppyImage,
            boot_dev=boot_dev,
        )


def activateVmDisk(positive, vm, diskAlias=None, diskId=None, wait=True):
    """
    Description: Activates vm's disk
    Author: jlibosva
    Parameters:
        * vm - name of vm which disk belongs to
        * diskAlias - name of the disk
        * diskId - disk's id
        * wait - boolean whether wait till disk is ok
    Return: True if ok, False if something went wrong (or good
            in case positive is False)
    """
    return changeVmDiskState(positive, vm, 'activate', diskAlias, diskId,
                             wait)


def deactivateVmDisk(positive, vm, diskAlias=None, diskId=None, wait=True):
    """
    Description: Deactivates vm's disk
    Author: jlibosva
    Parameters:
        * vm - name of vm which disk belongs to
        * diskAlias - name of the disk
        * diskId - disk's id
        * wait - boolean whether wait till disk is ok
    Return: True if ok, False if something went wrong (or good
            in case positive is False)
    """
    return changeVmDiskState(positive, vm, 'deactivate', diskAlias, diskId,
                             wait)


def changeVmDiskState(positive, vm, action, diskAlias, diskId, wait):
    """
    Description: Change vm's disk active state
    Author: jlibosva
    Parameters:
        * vm - name of vm which disk belongs to
        * action - activate or deactivate
        * diskAlias - name of the disk
        * diskId - disk's id
        * wait - boolean whether wait till disk is ok
    Return: True if ok, False if something went wrong (or good
            in case positive is False)
    """
    if diskAlias is None and diskId is None:
        VM_API.logger.error("Disk must be specified either by alias or ID")
        return False

    if diskId is not None:
        disk = _getVmDiskById(vm, diskId)
    else:
        disk = _getVmFirstDiskByName(vm, diskAlias)

    status = bool(DISKS_API.syncAction(disk, action, positive))
    if status and wait:
        if positive:
            # wait until the disk is really (de)activated
            active = True if action == 'activate' else False
            # always use disk.id
            return waitForVmDiskStatus(
                vm, active, diskId=disk.get_id(), timeout=300) == positive
        else:
            # only wait for the disk to be again in 'ok' state
            return DISKS_API.waitForElemStatus(disk, 'ok', 300)
    return status


def waitForVmDiskStatus(vm, active, diskAlias=None, diskId=None,
                        timeout=VM_ACTION_TIMEOUT, sleep=DEF_SLEEP):
    """
    Description: Waits for desired status of disk within VM (active,
                 deactivated)
    Author: jlibosva
    Parameters:
        * vm - name of vm which disk belongs to
        * active - boolean True if active, False if deactivated
        * diskAlias - name of the disk
        * diskId - disk's id
        * timeout - timeout
        * sleep - polling interval
    Return: True if desired state was reached, False on timeout
    """
    if diskAlias is None and diskId is None:
        VM_API.logger.error("Disk must be specified either by alias or ID")
        return False

    getFunc, diskDesc = (_getVmDiskById, diskId) if diskId is not None else \
        (_getVmFirstDiskByName, diskAlias)

    disk = getFunc(vm, diskDesc)
    cur_state = disk.get_active()

    t_start = time.time()
    while time.time() - t_start < timeout and cur_state != active:
        time.sleep(sleep)
        disk = getFunc(vm, diskDesc)
        cur_state = disk.get_active()

    return cur_state == active


def checkVMConnectivity(
    positive, vm, osType, attempt=1, interval=1, nic='nic1', user=None,
    password=None, ip=False, timeout=1800
):
    """
    Check VM Connectivity
    :param positive: Expected result
    :type positive: bool
    :param vm: vm name
    :type vm: str
    :param osType: os type element rhel/windows.
    :type osType: str
    :param attempt: number of attempts to connect
    :type attempt: int
    :param interval:  interval between attempts
    :type interval: int
    :param nic: NIC to get IP from
    :type nic: str
    :param user: Username
    :type user: str
    :param password: Password for Username
    :type password: str
    :param ip:  if supplied, check VM connectivity by this IP.
    :type ip: str
    :param timeout: timeout to wait for IP
    :type timeout: int
    :return: True if succeed to connect to VM, False otherwise).
    :rtype: bool
    """
    vlan = None
    if re.search('rhel', osType, re.I):
        osType = 'linux'
    elif re.search('win', osType, re.I):
        osType = 'windows'
    else:
        VM_API.logger.error(
            'Wrong value for osType: Should be rhel or windows')
        return False

    if not ip:
        agent_status, ip = waitForIP(vm=vm, timeout=timeout)
        # agent should be installed so convertMacToIpAddress is irrelevant
        if not agent_status:
            status, mac = getVmMacAddress(positive, vm, nic=nic)
            if not status:
                return False
            status, vlan = getVmNicVlanId(vm, nic)
            status, ip = convertMacToIpAddress(
                positive, mac=mac['macAddress'], vlan=vlan['vlan_id']
            )
            if not status:
                return False
        ip = ip['ip']

    status, res = checkHostConnectivity(
        positive, ip,  user=user, password=password, osType=osType,
        attempt=attempt, interval=interval
    )
    VM_API.logger.info(
        "VM: %s TYPE: %s, IP: %s, VLAN: %s, NIC: %s Connectivity Status: %s",
        vm, osType, ip, vlan, nic, status
    )
    return status


def getVmHost(vm):
    """
    Get host name for given running VM

    :param vm: vm name
    :type vm: str
    :return:tuple (True, hostname in dict or False, None)
    :rtype: tuple
    """
    try:
        vm_obj = VM_API.find(vm)
        host_obj = HOST_API.find(vm_obj.get_host().id, "id")
    except EntityNotFound:
        return False, {"vmHoster": None}
    return True, {"vmHoster": host_obj.get_name()}


def getVmNicPortMirroring(positive, vm, nic='nic1'):
    '''
    Get nic port mirror network
    Author: gcheresh
    Parameters:
        * vm - vm name
        * nic - nic name
    Return: True if port_mirroring is enabled on NIC, otherwise False
    '''
    nic_obj = get_vm_nic(vm, nic)
    return bool(nic_obj.get_port_mirroring()) == positive


def get_vm_nic_plugged(vm, nic='nic1', positive=True):
    """
    Get nic plugged parameter value of the NIC

    Args:
        vm (str): VM name
        nic (str): NIC name
        positive (bool): Expected results

    Returns:
        bool: True if NIC is plugged, otherwise False
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Get", obj_type="NIC", obj_name=nic, positive=positive,
        extra_txt="plug state"
    )
    nic_obj = get_vm_nic(vm, nic)
    logger.info(log_info)
    res = nic_obj.get_plugged()
    if res != positive:
        logger.error(log_error)
        return False
    return True


def get_vm_nic_linked(vm, nic='nic1', positive=True):
    """
    Get nic linked parameter value of the NIC

    Args:
        vm (str): VM name
        nic (str): NIC name
        positive (bool): Expected results

    Returns:
        bool: True if NIC is linked, otherwise False
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Get", obj_type="NIC", obj_name=nic, positive=positive,
        extra_txt="link state"
    )
    nic_obj = get_vm_nic(vm, nic)
    logger.info(log_info)
    res = nic_obj.get_linked()
    if res != positive:
        logger.error(log_error)
        return False
    return True


def is_vm_nic_have_profile(vm, nic='nic1'):
    """
    Check if vNIC contains vnic profile

    Args:
        vm (str): VM name
        nic (str): vNIC name

    Returns:
        bool: True if NIC contains non-empty network object or False for
            Empty network object
    """
    nic_obj = get_vm_nic(vm, nic)
    return bool(nic_obj.get_vnic_profile())


def get_vm_nic_vnic_profile(vm, nic):
    """
    Get vNIC vNIC_profile object

    Args:
        vm (str): VM name
        nic (str): vNIC name

    Returns:
        VnicProfile: vVnicProfile object if vNIC have one else None
    """
    nic_obj = get_vm_nic(vm, nic)
    return nic_obj.get_vnic_profile()


def check_vm_nic_profile(vm, vnic_profile_name="", nic='nic1'):
    """
    Check if VNIC profile 'vnic_profile_name' exist on the given VNIC

    Args:
        vm (str): VM name
        vnic_profile_name (str): Name of the vnic_profile to test
        nic (str): NIC name

    Returns:
        bool: True if vnic_profile_name exists on NIC, False otherwise
    """
    logger.info(
        "Check if vNIC profile %s exist on VM %s NIC %s",
        vnic_profile_name, vm, nic
    )
    nic_obj = get_vm_nic(vm=vm, nic=nic)
    if not vnic_profile_name:
        if nic_obj.get_vnic_profile():
            return False
        return True

    all_profiles = VNIC_PROFILE_API.get(absLink=False)
    for profile in all_profiles:
        if profile.get_name() == vnic_profile_name:
            return profile.get_id() == nic_obj.get_vnic_profile().get_id()

    logger.error(
        "vNIC profile %s not found on VM %s NIC %s", vnic_profile_name, vm,
        nic
    )
    return False


def getVmNicVlanId(vm, nic='nic1'):
    '''
    Get nic vlan id if configured
    Author: atal
    Parameters:
        * vm - vm name
        * nic - nic name
    Return: tuple (True and {'vlan_id': id} in case of success
                   False and {'vlan_id': 0} otherwise)
    '''
    try:
        nic_obj = get_vm_nic(vm, nic)
        net_obj = NETWORK_API.find(nic_obj.network.id, 'id')
    except EntityNotFound:
        return False, {'vlan_id': 0}

    try:
        return True, {'vlan_id': int(net_obj.vlan.id)}
    except AttributeError:
        VM_API.logger.warning("%s network doesn't contain vlan id.",
                              net_obj.get_name())
    return False, {'vlan_id': 0}


def validateVmDisks(positive, vm, sparse, format):
    '''
    Description - validate vm disks characteristics (for identical disks)
    TBD - add support for mixed disks
    Author: lustalov
        * vm - vm name
        * sparse - disk allocation type (true/false)
        * format - disk format (COW/RAW)
    Return: status (True/False)
    '''
    vmObj = VM_API.find(vm)
    disks = VM_API.getElemFromLink(vmObj, link_name='disks', attr='disk',
                                   get_href=False)

    for disk in disks:
        if disk.get_sparse() != sparse:
            logger.error(
                "VM disk %s allocation type %s is not as expected: %s",
                disk.id, disk.get_sparse(), sparse)
            return not positive
        if disk.get_format().lower() != format.lower():
            logger.error("VM disk %s format %s is not as expected: %s",
                         disk.id, disk.format, format)
            return not positive
    return positive


def checkVmState(positive, vmName, state, host=None):
    '''
    This method verifies whether vm is in the specified state on the specified
    host
    Parameters:
       * vmName - name of the vm
       * host - name of the host
       * state - expected state
    Return - True if vm is in the specified state on the specified host
             False otherwise
    '''
    vmObj = VM_API.find(vmName)
    general_check = True if vmObj.get_status() == state else False
    if host:
        hostObj = HOST_API.find(host)
        return positive == (vmObj.host.id == hostObj.id and general_check)
    else:
        return positive == general_check


def remove_vm_from_export_domain(
    positive, vm, datacenter, export_storagedomain, timeout=SAMPLER_TIMEOUT,
    sleep=SAMPLER_SLEEP
):
    """
    Remove VM from export domain

    __author__: istein

    Args:
        positive (bool): Expected status
        vm (str): Name of the VM to remove from export domain
        datacenter (str): Name of data center
        export_storagedomain (str): Export domain containing the exported vm
        timeout (int): Timeout to wait for VM removal
        sleep (int): Sleep between sampler iterations

    Returns:
        bool: True if vm was removed properly, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Remove", obj_type="VM", obj_name=vm, positive=positive,
        extra_txt="from export domain %s" % export_storagedomain
    )
    export_storage_domain_obj = STORAGE_DOMAIN_API.find(export_storagedomain)
    vm_obj = VM_API.getElemFromElemColl(export_storage_domain_obj, vm)

    logger.info(log_info)
    status = VM_API.delete(vm_obj, positive)

    if not status:
        logger.error(log_error)
        return False

    sample = TimeoutingSampler(
        timeout=timeout, sleep=sleep, func=export_domain_vm_exist, vm=vm,
        export_domain=export_storagedomain, positive=False
    )
    return sample.waitForFuncStatus(result=True)


def waitForVmsDisks(vm, disks_status=ENUMS['disk_state_ok'], timeout=600,
                    sleep=10):
    """
    Description: Waits until all vm's disks are in given state
    Author: jlibosva
    Parameters:
        * vm_name - name of VM
        * disks_status - desired state of all disks
    Returns: True on success, False on timeout
    """
    vm = VM_API.find(vm)

    start_time = time.time()
    disks_to_wait = [disk for disk in
                     DISKS_API.getElemFromLink(vm, get_href=False)
                     if disk.get_status() != disks_status]
    while disks_to_wait and time.time() - start_time < timeout:
        time.sleep(sleep)
        disks_to_wait = [disk for disk in
                         DISKS_API.getElemFromLink(vm, get_href=False)
                         if disk.get_status() != disks_status]

    return False if disks_to_wait else True


def getVmPayloads(positive, vm, **kwargs):
    '''
    Description: returns the payloads object from certain vm
    Author: talayan
    Parameters:
    * positive = TRUE/FALSE
    * vm - vm name to retreive payloads property from
    Return: status, element obj or None if not found
    '''
    name_query = "name=%s" % vm
    try:
        vm_obj = VM_API.query(name_query, all_content=True)[0]
    except IndexError:
        logger.error('Entity %s not found!' % vm)
        return False, {'property_obj': None}

    property_object = vm_obj.get_payloads()
    if property_object is None:
        logger.error('Property payloads not found in entity %s!' % vm)
        return False, {'property_object': None}

    return True, {'property_object': property_object}


@LookUpVMIpByName('vm_ip', 'name_vm')
def pingVm(vm_ip=None):
    '''
    Ping VM.

    retreives ip for vmName using LookUpVMIpByName and sends
    totally VM_PING_ATTEMPTS_COUNT ICMP Echo requests, expecting at least one
    ICMP Echo reply.

    returns: True iff at least one reply per IP is received,
             False otherwise.
    '''

    ips = [vm_ip]
    return waitUntilPingable(ips)


def migrateVmsSimultaneously(positive, vm_name, range_low, range_high, hosts,
                             useAgent, seed=None):
    '''
    Migrate several VMs between the hosts, taking random one.
    Original Author: jhenner
    Modified Author: bdagan
    Parameters:
       * vms - name of vm
       * hosts    - A comma separated list of hosts hostnames/ip-addreses to
                    migrate vm between.
       * useAgent - Wait for guest_info to appear. Set this to True when
                    you need to ensure an IP address reported by guest agent
                    should be used. Note that after the VM migration, there is
                    some delay until the guest IP reappears.
       * seed     - A seed for pseudo-random generator. If None, the generator
                    will not be seeded, nor the status will be recovered after
                    test finish.
    Return: True if all migrations performed with no error detected.
    '''
    assert positive
    PING_ATTEMPTS = 10

    hostsObjs = [HOST_API.find(host) for host in set(split(hosts))]
    if len(hostsObjs) < 2:
        raise TestCaseError(
            'There is less then 2 hosts. Migrations impossible!')
    all_hosts_ids = set(hostObj.id for hostObj in hostsObjs)

    vmsObjs = [
        VM_API.find(vm) for vm in makeVmList(vm_name, range_low, range_high)]
    if not vmsObjs:
        raise TestCaseError('No vm to migrate on.')

    if useAgent:
        vm_ips = [waitForIP(vmObj.name)[1]['ip'] for vmObj in vmsObjs]
    else:
        vm_ips = [LookUpVMIpByName('ip', 'name').get_ip(vmObj.name)
                  for vmObj in vmsObjs]

    waitUntilPingable(vm_ips)

    # Save the state of the random generator and seed it with the `seed`
    # constant. The state should get recovered before
    # thiLookUpVMIpByName('ip', 'name').get_ip(vmObj.name)s method returns.

    with restoringRandomState(seed):
        for vmObj in vmsObjs:
            # Get the host to migrate the vm on.
            try:
                oldHostId = vmObj.host.id
            except AttributeError as ex:
                MSG = ("The VM {0} is probably not running "
                       "since it has no attribute 'host'. ex: " + str(ex))
                raise TestCaseError(MSG.format(vmObj.name))

            # Pick a new host.
            hostCandidates = all_hosts_ids - set((oldHostId,))
            vmObj.host.id = random.choice(list(hostCandidates))

        # Ping before
        MSG = 'Pinging {0} before the migration.'
        logger.info(MSG.format(sorted(vm_ips)))
        pingResult = pingToVms(vm_ips, PING_ATTEMPTS)
        dead_machines = [ip for ip, alive in pingResult.iteritems()
                         if not alive]
        if dead_machines:
            MSG = "IPs {0} seems to be dead before the migration."
            raise TestCaseError(MSG.format(dead_machines))
            # need to change the error

        # Migrate
        actions_states = [
            bool(
                VM_API.syncAction(vmObj, "migrate", positive, host=vmObj.host)
            )
            for vmObj in vmsObjs
        ]

        for vm, action_succeed in zip(vmsObjs, actions_states):
            # Check migration and VM status.
            if not action_succeed:
                MSG = 'Failed to migrate VM %s from %s to host %s.'
                raise TestCaseError(MSG % (vm.name, oldHostId, vm.host.id))

        # Wait for all migrated VMs are UP.
        def vmsUp(state):
            StateResults = (
                VM_API.find(vm.name).get_status() == state
                for vm in vmsObjs)
            return reduce(and_, StateResults)

        logger.info('Waiting for all migrated machines UP.')
        for state in ['migrating', 'up']:
            sampler = TimeoutingSampler(VM_ACTION_TIMEOUT, 10, vmsUp, state)
            sampler.timeout_exc_args = (
                'Timeouted when waiting for all VMs UP after the migration.',)
            for statusOk in sampler:
                if statusOk:
                    break

        logger.info('Checking whether VMs really migrated.')
        for vm in vmsObjs:
            if vm.href == VM_API.find(vm.name).host.href:
                # need to check if it works on SDK
                MSG = 'VM is on same host as it was before migrating.'
                raise TestCaseError(MSG)
            logger.info('VM {0} migrated.'.format(vm.name))

        # Ping after.
        MSG = 'Pinging {0} after the migration.'
        logger.info(MSG.format(sorted(vm_ips)))
        pingResult = pingToVms(vm_ips, PING_ATTEMPTS)
        dead_machines = [ip for ip, alive in pingResult.iteritems()
                         if not alive]
        if dead_machines:
            MSG = "IPs {0} seems to be dead after the migration."
            raise TestCaseError(MSG.format(dead_machines))

        logger.info('Succeed to migrate all the VMs.')
        return True


def move_vm_disk(
    vm_name, disk_name, target_sd, wait=True, timeout=VM_IMAGE_OPT_TIMEOUT,
    sleep=DEF_SLEEP
):
    """
    Moves disk of vm to another storage domain

    __author__ = "ratamir, libosvar"

    :param vm_name: The VM whose disk will be moved
    :type vm_name: str
    :param disk_name: Name of the disk to be moved
    :type disk_name: str
    :param target_sd: Name of the storage domain into
        which the disk should be moved
    :type target_sd: str
    :param wait: Specifies whether to wait until the disk has moved
    :type wait: bool
    :param timeout: Timeout for waiting
    :type timeout: int
    :param sleep: Polling interval while waiting
    :type sleep: int
    :raises: DiskException if syncAction returns False (syncAction should raise
            exception itself instead of returning False)
    """
    source_domain = get_disk_storage_domain_name(disk_name, vm_name)
    logger.info(
        "Moving disk %s attached to vm %s from storage domain %s to storage "
        "domain %s",
        disk_name, vm_name, source_domain, target_sd)
    sd = STORAGE_DOMAIN_API.find(target_sd)
    disk = getVmDisk(vm_name, disk_name)
    if not DISKS_API.syncAction(
        disk, 'move', storage_domain=sd, positive=True
    ):
        raise exceptions.DiskException(
            "Failed to move disk %s attached to vm %s from storage domain "
            "%s to storage domain %s" %
            (disk_name, vm_name, source_domain, target_sd)
        )
    if wait:
        for disk in TimeoutingSampler(timeout, sleep, getVmDisk, vm_name,
                                      disk_name):
            if disk.get_status() == ENUMS['disk_state_ok']:
                return


def wait_for_vm_states(
    vm_name, states=[ENUMS['vm_state_up']], timeout=VM_WAIT_FOR_IP_TIMEOUT,
    sleep=DEF_SLEEP
):
    """
    Waits by polling API until vm is in desired state

    :param vm_name: Name of the vm
    :type vm_name: str
    :param states: List of desired state
    :type states: list
    :param timeout: Timeout to wait for desire status
    :type timeout: str
    :param sleep: Time to sleep between retries
    :type sleep: int
    :raise: APITimeout when vm won't reach desired state in time
    """
    sampler = TimeoutingSampler(timeout, sleep, VM_API.find, vm_name)
    logger.info("Wait for %s to be in states: %s", vm_name, states)
    for vm in sampler:
        vm_state = vm.get_status()
        logger.info("Current %s state is: %s", vm_name, vm_state)
        if vm_state in states:
            logger.info("%s states is %s", vm_name, vm_state)
            break


def start_vms(
    vm_list, max_workers=2, wait_for_status=ENUMS['vm_state_powering_up'],
    wait_for_ip=True
):
    """
    Starts all vms in vm_list. Throws an exception if it fails

    :param vm_list: list of vm names
    :type vm_list: list
    :param max_workers: In how many threads should vms start
    :type max_workers: int
    :param wait_for_status: from ENUMS, to which state we wait for
    :type wait_for_status: str
    :param wait_for_ip: Boolean, wait to get an ip from the vm
    :type wait_for_ip: bool
    :raises: VMException
    """
    results = list()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for machine in vm_list:
            vm_obj = VM_API.find(machine)
            if vm_obj.get_status() == ENUMS['vm_state_down']:
                logger.info("Starting vm %s", machine)
                results.append(
                    executor.submit(
                        startVm, True, machine, wait_for_status, wait_for_ip
                    )
                )
    for machine, res in zip(vm_list, results):
        if res.exception():
            logger.error(
                "Got exception while starting vm %s: %s",
                machine, res.exception()
            )
            raise res.exception()
        if not res.result():
            raise exceptions.VMException("Cannot start vm %s" % machine)


def wait_for_vm_snapshots(
    vm_name, states, snapshots_description=None, timeout=SNAPSHOT_TIMEOUT,
    sleep=SNAPSHOT_SAMPLING_PERIOD
):
    """
    Description: Wait until snapshots_description are in the given status,
    in case snapshot_descriptions is not provided wait for all the vm's
    snapshots

    __author__ = 'ratamir'
    :param vm_name: name of the vm
    :type vm_name: str
    :param states: list of desired snapshots' state
    :type states: list
    :param snapshots_description: snapshot names in case of specific
    snapshot/s
    :type snapshots_description: str or list
    :param timeout: maximum amount of time this operation can take
    :type timeout: int
    :param sleep: polling period
    :type sleep: int
    """
    def _get_unsatisfying_snapshots(statuses, description):
        """
        Returns True if there are still snapshot not in desired state,
        False otherwise
        """
        snapshots = _getVmSnapshots(vm_name, False)
        if description is not None:
            snapshots = [
                snapshot for snapshot in snapshots
                if snapshot.get_description() in description
            ]
        return bool(
            [
                snap for snap in snapshots if snap.get_snapshot_status() not
                in statuses
            ]
        )

    snapshots = (
        snapshots_description if snapshots_description else "'all snapshots'"
    )
    logger.info(
        "Waiting until snapshots: %s of %s vm are in one of following "
        "states: %s", snapshots, vm_name, states
    )

    for sample in TimeoutingSampler(
        timeout, sleep, _get_unsatisfying_snapshots, states,
        snapshots_description
    ):
        if not sample:
            return


def collect_vm_logs(vm_name, root_passwd='qum5net'):
    """
    Collects /var/log/messages from vm
    and put it in logdir

    Parameters:
        * *vm_name* - name of the vm
        * *root_passwd* - password of root user of the vm

    **Returns**: True/False whether succeed in collecting the logs
    """
    vm = VM_API.find(vm_name)
    os_type = vm.get_os().get_type().lower()
    if not ('linux' in os_type or 'rhel' in os_type):
        # no logs from non-linux machines
        return False

    vm_ip = None

    try:
        vm_ip = LookUpVMIpByName('', '').get_ip(vm_name)
        logger.info('Got ip %s', vm_ip)
    except CanNotFindIP:
        logger.warning(
            "failed to get vm logs from vm %s: No IP found", vm_name)
        return False
    except Exception as e:
        logger.error('Could not get vm logs from vm %s - unexpected exception '
                     'encountered: %s', vm_name, e)
        return False

    m = Machine(vm_ip, 'root', root_passwd).util(LINUX)
    log_dest = os.path.join(opts['logdir'], '{0}-messages.log'.format(vm_name))

    # hack, to be fixed when moving to logging.config
    # logging the error in debug instead of error
    class tempfilter(logging.Filter):
        def filter(self, record):
            if record.msg == '%s: failed copy %s from %s, err: %s':
                logger.warning("failed to copy logs from vm logs from vm %s",
                               vm_name)
                logger.debug(record.getMessage())
                return False
            return True

    tmpfilter = tempfilter()
    util_logger = logging.getLogger('util')
    util_logger.addFilter(tmpfilter)

    success = m.copyFrom('/var/log/messages', log_dest)

    util_logger.removeFilter(tmpfilter)
    if not success:
        logger.warning("failed to copy logs from vm logs from vm %s", vm_name)
        return False
    return True


def restore_snapshot(
    positive, vm, description, ensure_vm_down=False, restore_memory=False
):
    """
    Restore VM state to a particular snapshot

    :param positive: Determines if the operation should be treated as
    positive or negative
    :type positive: bool
    :param vm: VM to restore
    :type vm: str
    :param description: The snapshot description to use
    :type description: str
    :param ensure_vm_down: True if the VM should be powered off before being
    restored, default is False
    :type ensure_vm_down: bool
    :param restore_memory: True if the VM memory should be restored,
    default is False
    :type restore_memory: bool
    :returns: True if snapshot was restored properly, False otherwise
    :rtype: bool
    """
    if ensure_vm_down:
        stop_vms_safely([vm])
        waitForVMState(vm, state=ENUMS['vm_state_down'])
    vmObj = VM_API.find(vm)
    snapshot = _getVmSnapshot(vm, description)
    status = bool(
        SNAPSHOT_API.syncAction(
            snapshot, 'restore', positive, restore_memory=restore_memory
        )
    )
    if status and positive:
        return VM_API.waitForElemStatus(vmObj, ENUMS['vm_state_down'],
                                        VM_ACTION_TIMEOUT)

    return status


def preview_snapshot(positive, vm, description, ensure_vm_down=False,
                     restore_memory=False, disks_lst=None):
    """
    Description: preview vm snapshot
    Author: gickowic
    Parameters:
       * vm - vm where snapshot should be previewed
       * description - snapshot name
       * ensure_vm_down - True if vm should enforce to be down before preview
       * restore_memory - True if should restore vm memory
       * disks_lst - list of disk in case of custom preview
    Return: status (True if snapshot was previewed properly, False otherwise)
    """
    if ensure_vm_down:
        stop_vms_safely([vm])
    return snapshot_action(positive, vm, PREVIEW, description,
                           restore_memory=restore_memory, disks_lst=disks_lst)


def undo_snapshot_preview(positive, vm, ensure_vm_down=False):
    """
    Description: Undo a snapshot preview
    Author: gickowic
    Parameters:
       * vm - vm where snapshot preview should be undone
       * ensure_vm_down - True if vm should enforce to be down before undo
    Return: status (True if snapshot preview was undone, False otherwise)
    """
    if ensure_vm_down:
        stop_vms_safely([vm])
    return snapshot_action(positive, vm, UNDO)


def commit_snapshot(positive, vm, ensure_vm_down=False,
                    restore_memory=False):
    """
    Description: Commit a vm snapshot (must be currently in preview)
    Author: gickowic
    Parameters:
       * vm - vm where snapshot should be commited
       * description - snapshot name that is currently previewed
       * ensure_vm_down - True if vm should enforce to be down before commit
       * restore_memory - True if should restore vm memory
    Return: status (True if snapshot was committed properly, False otherwise)
    """
    if ensure_vm_down:
        stop_vms_safely([vm])
    return snapshot_action(positive, vm, COMMIT,
                           restore_memory=restore_memory)


def snapshot_action(positive, vm, action,
                    description=None, restore_memory='false', disks_lst=None):
    """
    Function that performs snapshot actions
    Author: ratamir
    Parameters:
        * vm - vm name which snapshot belongs to
        * action - snapshot operation to execute (string - 'commit_snapshot',
                   'undo_snapshot', 'undo_snapshot')
        * description - snapshot description (In case of custom preview,
                        this snapshot description is the one the vm
                        configuration is taken from)
        * restore_memory - True if restore memory required
        * disks_lst - in case of custom preview, provide list of
          tuple of desired disks and snapshots
          (i.e. disk_name, snap_description) to be part of the preview
    Return: True if operation succeeded, False otherwise
    """
    vmObj = VM_API.find(vm)
    action_args = {'entity': vmObj,
                   'action': action,
                   'positive': positive}

    if action == PREVIEW:
        snapshot = _getVmSnapshot(vm, description)
        snap = data_st.Snapshot(id=snapshot.get_id())
        action_args['snapshot'] = snap
        action_args['restore_memory'] = restore_memory

        # In case of custom preview
        if disks_lst:
            disks_coll = data_st.Disks()
            for disk, snap_desc in disks_lst:

                new_disk = data_st.Disk()

                if snap_desc == 'Active VM':
                    diskObj = getVmDisk(vm, disk)
                    snap_id = _getVmSnapshot(vm, snap_desc)
                    new_disk.set_snapshot(snap_id)

                else:
                    snap_disks = get_snapshot_disks(vm, snap_desc)
                    diskObj = [d for d in snap_disks if
                               (d.get_alias() == disk)][0]

                    new_disk.set_snapshot(diskObj.get_snapshot())

                new_disk.set_id(diskObj.get_id())
                new_disk.set_image_id(diskObj.get_image_id())

                disks_coll.add_disk(new_disk)

            action_args['disks'] = disks_coll
    status = bool(VM_API.syncAction(**action_args))
    if status and positive:
        return VM_API.waitForElemStatus(vmObj, ENUMS['vm_state_down'],
                                        VM_SNAPSHOT_ACTION)

    return status


def is_snapshot_with_memory_state(vm_name, snapshot):
    """
    Description: Check if snapshot contains memory state (according to the
    snapshot's information)
    Author: gickowic
    Parameters:
        * vm_name - name of the vm
        * snapshot - name of the snapshot to check
    * returns - True iff vm contains the snapshot and it has memory state
    """
    snapshotObj = _getVmSnapshot(vm_name, snapshot)
    return snapshotObj.get_persist_memorystate()


def is_pid_running_on_vm(vm_name, pid, user, password):
    """
    Checks if a process with given pid is running on the vm

    :param vm_name: name of the vm
    :type vm_name: str
    :param pid: pid of the process to search for
    :type pid: str
    :param user: username used to login to vm
    :type user: str
    :param password: password for the user
    :type password: str
    :return: True if pid exists, False otherwise
    :rtype: bool
    """
    status, vm_ip = waitForIP(vm_name)
    if not status:
        raise exceptions.CanNotFindIP("Failed to get IP for vm %s" % vm_name)
    logger.debug('Got ip %s for vm %s', vm_ip['ip'], vm_name)
    vm_machine_object = Machine(vm_ip['ip'], user, password).util(LINUX)
    return vm_machine_object.isProcessExists(pid)


def kill_process_by_pid_on_vm(vm_name, pid, user, password):
    """
    Description: Kills a process with given pid if it is running on the vm
    Author: gickowic
    Parameters:
        * vm_name - name of the vm
        * pid - pid of the process to search for
        * user - username used to login to vm
        * password - password for the user
    Return
    """
    vm_ip = LookUpVMIpByName('', '').get_ip(vm_name)
    vm_machine_object = Machine(vm_ip, user, password).util(LINUX)
    return vm_machine_object.killProcess(pid)


def run_cmd_on_vm(vm_name, cmd, user, password, timeout=15):
    """
    Description: Runs given command on given VM
    Parameters:
        * vm_name - VM name in RHEV-M
        * cmd - command to run - should be a string, not a list of tokens,
                for example 'ps -A', not ['ps', '-A']
        * user - username used to login to vm
        * password - password for the user
    """
    vm_ip = waitForIP(vm_name)[1]['ip']
    rc, out = runMachineCommand(
        True, ip=vm_ip, user=user, password=password, cmd=cmd, timeout=timeout)
    logger.debug("cmd output: %s, exit code: %s", out, rc)
    return rc, out


def check_VM_disk_state(vm_name, disk_alias):
    """
    Description: Check disk state
    Author: ratamir
    Parameters:
        * vm_name - string containing vm name
        * disk_alias - string containing disk name

    Return: True if the disk is active, False otherwise
    """

    disks = getVmDisks(vm_name)
    disks = [disk for disk in disks if disk.get_alias() == disk_alias]
    if not disks:
        raise DiskNotFound('Disk %s not found in vm %s' %
                           (disk_alias, vm_name))
    disk = disks[0]
    return disk.get_active()


def get_vm_state(vm_name):
    """
    Description: Get vm state
    Author: ratamir
    Parameters:
        * vm_name - string containing vm name

    Return: state of vm
    """
    vm_obj = VM_API.find(vm_name)
    return vm_obj.get_status()


def is_vm_run_on_host(vm_name, host_name, **kwargs):
    """
    Check if vm run on given host

    :param vm_name: vm name
    :type vm_name: str
    :param host_name: vm must run on given host
    :type host_name: str
    :param kwargs: timeout: type=int
                   sleep: type=int
    :return: True, if vm run on given host, otherwise False
    """
    query = "name={0} and host={1}".format(vm_name, host_name.lower().strip())
    return VM_API.waitForQuery(query, **kwargs)


def get_snapshot_disks(vm, snapshot):
    """
    Description: Return the disks contained in a snapshot
    Author: ratamir
    Parameters:
        * vm - vm name
        * snapshot - snapshot's description

    Return: list of disks, or raise EntityNotFound exception
    """
    snap_obj = _getVmSnapshot(vm, snapshot)
    disks = DISKS_API.getElemFromLink(snap_obj)
    return disks


def delete_snapshot_disks(vm, snapshot, disk_id=None, wait=True):
    """
    In order to remove a disk that is part of a snapshot, you must
    remove the disk from the snapshot's disk collection using this
    function, and only then remove the disk itself

    __author__ = 'ratamir'
    :param vm: The vm containing the snapshot whose disks are to be deleted
    :type vm: str
    :param snapshot: The snapshot whose disks are to be deleted
    :type snapshot: str
    :param disk_id: The ID of a specific disk to delete in case of deleting
    a specific disk
    :type disk_id: str
    :returns: True in case all relevant disks were deleted, False otherwise
    :rtype: bool
    """
    # Local import to prevent import recursion loop
    from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd
    disks = get_snapshot_disks(vm, snapshot)
    snapshot_disk_ids = [disk.get_id() for disk in disks]
    storage_domain_name = get_disk_storage_domain_name(
        disks[0].get_alias(), vm
    )
    storage_domain_obj = ll_sd.get_storage_domain_obj(
        storage_domain_name
    )
    snapshot_disks = ll_sd.util.getElemFromLink(
        storage_domain_obj,
        link_name='disksnapshots',
        attr='disk_snapshot',
        get_href=False,
    )
    if disk_id:
        snapshot_disks = [
            disk for disk in snapshot_disks if (
                disk.get_disk().get_id() == disk_id
            )
        ]
    else:
        snapshot_disks = [
            disk for disk in snapshot_disks if (
                disk.get_disk().get_id() in snapshot_disk_ids
            )
        ]
    results = []
    for disk_obj in snapshot_disks:
        status = DISKS_API.delete(disk_obj, True)
        if not status:
            logger.error(
                "Failed to delete snapshot's disk %s", disk_obj.get_alias()
            )
        results.append(status)
    if wait:
        wait_for_jobs([ENUMS['job_remove_snapshots_disk']])
        wait_for_disks_status(
            [disk.get_disk().get_id() for disk in snapshot_disks], 'id'
        )
    return all(results)


def get_vm_snapshot_ovf_obj(vm, snapshot):
    """
    Description: Return ovf file of vm
    - The ovf itself is in:
        snaps.get_initialization().get_configuration().get_data()
    Author: ratamir
    Parameters:
        * vm - vm name
        * snapshot - snapshot's description

    Return: ovf configuration object, or raise EntityNotFound exception
    """
    snap_obj = _getVmSnapshot(vm, snapshot, all_content=True)
    return snap_obj.get_initialization()


def get_vm_snapshots(vm, all_content=False):
    """
    Description: Return vm's snapshots
    Author: ratamir
    Parameters:
        * vm - vm name
    Return: list of snapshots, or raise EntityNotFound exception
    """
    snapshots = _getVmSnapshots(vm, get_href=False, all_content=all_content)
    return snapshots


def create_vm_from_ovf(new_vm_name, cluster_name, ovf, compare=False):
    """
    Description: Creates a vm from ovf configuration file
    * The ovf configuration can be retrieved via 'get_vm_ovf_file' method

    Author: ratamir
    Parameters:
        * new_vm_name - name for the restored vm
        * cluster - name of the cluster that the vm should create in
        * ovf - ovf object. can retrieved from 'get_vm_snapshot_ovf_obj'
        * compare - If True, run compareElements, otherwise not.
    Return: True if operation succeeded, or False otherwise
    """
    restored_vm_obj = _prepareVmObject(name=new_vm_name, cluster=cluster_name,
                                       initialization=ovf)
    _, status = VM_API.create(restored_vm_obj, True, compare=compare)
    return status


def stop_vms_safely(vms_list):
    """
    Powers off all vms from vms_list

    __author__ = "ratamir, cmestreg, glazarov"
    :param vms_list: list of vms to power off
    :type vms_list: list
    :return: True if all VMs were powered off successfully, False otherwise
    :rtype: bool
    """
    vms_stop_failed = set()
    vms_action_stop = set()
    logger.info("Powering off VMs: %s", vms_list)
    for vm in vms_list:
        if does_vm_exist(vm):
            if not get_vm_state(vm) == ENUMS['vm_state_down']:
                if not stopVm(True, vm, async='true'):
                    vms_stop_failed.add(vm)
                else:
                    vms_action_stop.add(vm)
        else:
            logger.warning("Vm %s is not exist under engine", vm)
    for vm in vms_action_stop:
        if not waitForVMState(vm, ENUMS['vm_state_down']):
            vms_stop_failed.add(vm)

    if vms_stop_failed:
        logger.error("Failed to stop VMs '%s'", ', '.join(vms_stop_failed))
        return False
    return True


def attach_snapshot_disk_to_vm(disk_obj, vm_name, async=False, activate=True):
    """
    Attaching a snapshot disk to a vm
    Author: ratamir
    Parameters:
        * disk_obj - disk object to attach
        * vm_name - name of the vm that the disk should be attached to
        * async - True if operation should be async
        * activate - True if the disk should be activated after attachment

    Return:
        True if operation succeeded, False otherwise
    """

    new_disk_obj = _prepareDiskObject(id=disk_obj.get_id(),
                                      active=activate,
                                      snapshot=disk_obj.get_snapshot())
    vmDisks = getObjDisks(vm_name)
    diskObj, status = DISKS_API.create(new_disk_obj, True,
                                       collection=vmDisks, async=async)
    return status


def attach_backup_disk_to_vm(src_vm, backup_vm, snapshot_description,
                             async=True, activate=True):
    """
    Attaching a backup disk to a vm
    Author: ratamir
    Parameters:
        * src_vm - name of vm with the disk that should be attached
        * backup_vm - name of the vm that the disk should attach to
        * snapshot_description - snapshot description where the disk
          is located in
        * async - True if operation should be async
    Return:
        True if operation succeeded, False otherwise
    """
    status = True
    disks_objs = get_snapshot_disks(src_vm, snapshot_description)
    for disk_obj in disks_objs:
        logger.info("Attach disk %s of vm %s to vm %s",
                    disk_obj.get_alias(), src_vm, backup_vm)
        status = attach_snapshot_disk_to_vm(disk_obj, backup_vm, async=async,
                                            activate=activate)

        if not status:
            logger.info("Failed to attach disk %s of vm %s to vm %s",
                        disk_obj.get_alias(), src_vm, backup_vm)
            return status
        logger.info("Succeeded to attach disk %s of vm %s to vm %s",
                    disk_obj.get_alias(), src_vm, backup_vm)

    return status


def getVmTemplateId(vm):
    """
    Returns vm's template id
    **Author**: cmestreg

    **Parameters**:
        * *vm* - vm's name
    **Returns**: id of the template, or raise VMException if entity not found
    """
    try:
        vmObj = VM_API.find(vm)
    except EntityNotFound:
        raise exceptions.VMException("Cannot find vm with name %s" % vm)
    return vmObj.get_template().id


def get_vm_boot_sequence(vm_name):
    """
    Get vm boot sequence
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
    **Returns**: list of vm boot devices
    """
    vm_obj = get_vm_obj(vm_name)
    boots = vm_obj.get_os().get_boot()
    return boots.get_devices().get_device()


def remove_all_vms_from_cluster(cluster_name, skip=[], wait=False):
    """
    Stop if need and remove all exists vms from specific cluster

    :param cluster_name: cluster name
    :type cluster_name: str
    :param skip: list of names of vms which should be left
    :type skip: list
    :param wait : If wait is False the remove will be asynchrony
                  else we will wait for each remove VM to finish
    :type wait: bool
    :return: True, if all vms removed from cluster, False otherwise
    :rtype: bool
    """
    logger_message = "Remove VMs in cluster"
    if skip:
        logger_message += " except %s" % ", ".join(skip)
    logger.info(logger_message)
    vms_in_cluster = []
    cluster_name_query = "name=%s" % cluster_name
    cluster_obj = CLUSTER_API.query(cluster_name_query)[0]
    all_vms_obj = VM_API.get(absLink=False)
    for vm_obj in all_vms_obj:
        if vm_obj.get_cluster().get_id() == cluster_obj.get_id():
            if vm_obj.get_name() not in skip:
                vms_in_cluster.append(vm_obj.get_name())
    if vms_in_cluster:
        stop_vms_safely(vms_in_cluster)
        log = "" if wait else "asynchrony"
        logger.info("Remove VMs %s", log)
        for vm in vms_in_cluster:
            logger.info("send delete command to vm: %s", vm)
            removeVm(True, vm, wait=wait)
        return waitForVmsGone(True, vms_in_cluster)
    return True


def get_vm_display_port(vm_name):
    """
    Get vm display port
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
    **Returns**: vm display port or None
    """
    vm_obj = get_vm_obj(vm_name)
    return vm_obj.get_display().get_port()


def get_vm_display_address(vm_name):
    """
    Get vm display address
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
    **Returns**: vm display address or None
    """
    vm_obj = get_vm_obj(vm_name)
    return vm_obj.get_display().get_address()


def get_vm_obj(vm_name, all_content=False):
    """
    Get VM object by using the VM name

    __author__ = "alukiano, glazarov"
    :param vm_name: The VM name from which the VM object should be retrieved
    :type vm_name: str
    :param all_content: Specifies whether the entire content for the VM
    should be retrieved, False is the default
    :type all_content: bool
    :returns: The VM object for the input vm_name
    :rtype: VM object
    """
    vm_name_query = "name=%s" % vm_name
    # Retrieve the entire object content only in the case where this is
    # requested
    if all_content:
        return VM_API.query(vm_name_query, all_content=all_content)[0]
    return VM_API.query(vm_name_query)[0]


# Create this function as duplicate for function removeDisk
# with additional functionality to remove all disks from vm
def remove_vm_disks(vm_name, disk_name=None):
    """
    Remove all disks from given vm, if disk name not specified,
    else remove only given disk from vm
    **Author**: alukiano

    **Parameters**:
        * *vm_name* - vm name
        * *disk_name - disk name to remove,
                       if specified method will remove just this disk
    **Returns**: True, if removed all disks successfully, otherwise False
    """
    vm_disks = [disk.get_name() for disk in getVmDisks(vm_name)]
    if disk_name:
        vm_disks = [disk for disk in vm_disks if disk == disk_name]
    return delete_disks(vm_disks)


def prepare_watchdog_obj(**kwargs):
    """
    Prepare watchdog object for future use

    Keyword Args:
        model (str): Watchdog card model
        action (str): Watchdog action

    Returns:
        WatchDog: New WatchDog instance
    """
    return ll_general.prepare_ds_object("WatchDog", **kwargs)


def get_watchdog_collection(vm_name):
    """
    Get VM watchdog collection

    Args:
        vm_name: VM name

    Returns:
        list: List of watchdog objects
    """
    vm_obj = get_vm_obj(vm_name=vm_name)
    logger.info("Get VM %s watchdog collection", vm_name)
    watchdog_collection = VM_API.getElemFromLink(
        vm_obj, link_name="watchdogs", attr="watchdog", get_href=False
    )
    if not watchdog_collection:
        logging.error("VM %s watchdog collection is empty", vm_name)
    return watchdog_collection


def add_watchdog(vm_name, model, action):
    """
    Add watchdog card to VM

    Args:
        vm_name (str): VM name
        model (str): Watchdog card model
        action (str): Watchdog action

    Returns:
        bool: True, if add watchdog card action succeed, otherwise False
    """
    vm_obj = get_vm_obj(vm_name=vm_name)
    log_info, log_error = ll_general.get_log_msg(
        action="Add",
        obj_type="watchdog",
        obj_name=model,
        extra_txt="to VM %s with action %s" % (vm_name, action),
    )
    vm_watchdog_link = VM_API.getElemFromLink(
        elm=vm_obj, link_name="watchdogs", get_href=True
    )
    watchdog_obj = prepare_watchdog_obj(model=model, action=action)

    logger.info(log_info)
    status = WATCHDOG_API.create(
        watchdog_obj, True, collection=vm_watchdog_link
    )[1]
    if not status:
        logger.error(log_error)
    return status


def update_watchdog(vm_name, **kwargs):
    """
    Update watchdog card on VM

    Args:
        vm_name (str): VM name

    Keyword Args:
        model (str): Watchdog card model
        action (str): Watchdog action

    Returns:
        bool: True, if update watchdog card action succeed, otherwise False
    """
    watchdog_collection = get_watchdog_collection(vm_name=vm_name)
    if not watchdog_collection:
        return False
    old_watchdog_obj = watchdog_collection[0]
    log_info, log_error = ll_general.get_log_msg(
        action="Update",
        obj_type="watchdog",
        obj_name=old_watchdog_obj.get_model(),
        extra_txt="with parameters %s on VM %s" % (kwargs, vm_name)
    )
    new_watchdog_obj = prepare_watchdog_obj(**kwargs)
    logger.info(log_info)
    status = WATCHDOG_API.update(old_watchdog_obj, new_watchdog_obj, True)[1]
    if not status:
        logger.error(log_error)
    return status


def delete_watchdog(vm_name):
    """
    Delete watchdog card from VM

    Args:
        vm_name (str): VM name

    Returns:
        bool: True, if delete watchdog card action succeed, otherwise False
    """
    watchdog_collection = get_watchdog_collection(vm_name=vm_name)
    if not watchdog_collection:
        return False
    watchdog_obj = watchdog_collection[0]
    log_info, log_error = ll_general.get_log_msg(
        action="Delete",
        obj_type="watchdog",
        obj_name=watchdog_obj.get_model(),
        extra_txt="from VM %s" % vm_name
    )
    logger.info(log_info)
    status = WATCHDOG_API.delete(watchdog_obj, True)
    if not status:
        logger.error(log_error)
    return status


def get_vm_machine(vm_name, user, password):
    '''
    Obtain VM machine from vm name for LINUX machine
    Author: lsvaty
    Parameters:
        * vm - vm name
        * user - user of vm
        * password - password for user
    Return value: vm machine
    '''
    status, got_ip = waitForIP(vm_name, timeout=600, sleep=10)
    if not status:
        status, mac = getVmMacAddress(True, vm_name,
                                      nic='nic1')
        if not status:
            return False
        status, vlan = getVmNicVlanId(vm_name, 'nic1')
        status, got_ip = convertMacToIpAddress(True, mac=mac['macAddress'],
                                               vlan=vlan['vlan_id'])
        if not status:
            return False
    return Machine(got_ip['ip'], user, password).util(LINUX)


def reboot_vms(vms):
    """
    Atomic Reboot vms (stop && start)

    :param vms: list of vms
    :return: False if vms failed to start
    :rtype: bool
    """
    stop_vms_safely(vms)
    return startVms(vms)


def extend_vm_disk_size(positive, vm, disk, **kwargs):
    """
    Description: extend already existing vm disk
    Parameters:
      * vm - vm where disk should be updated
      * disk - disk name that should be updated
      * provisioned_size - new disk size in bytes
    Author: ratamir
    Return: Status of the operation's result dependent on positive value
    """
    disk_obj = _getVmFirstDiskByName(vm, disk)
    new_disk = _prepareDiskObject(**kwargs)
    if positive:
        # Expecting to succeed: in this case the validator will verify that
        # the returned object is like the expected one. update() operation is
        # async so the returned object is not the updated one. The returned
        # object in this case is a locked disk with the original size (i.e
        # before the resize).
        # To bypass the object comparison, use compare=False
        disk, status = DISKS_API.update(disk_obj, new_disk, True,
                                        compare=False)
    else:
        # Expecting to fail: in this case the validator is disabled so no
        # further manipulation is needed
        disk, status = DISKS_API.update(disk_obj, new_disk, False)
    return status


def live_migrate_vm_disk(
    vm_name, disk_name, target_sd, timeout=VM_IMAGE_OPT_TIMEOUT*2,
    sleep=SNAPSHOT_SAMPLING_PERIOD, wait=True
):
    """
    Moves vm's disk. Starts disk movement then waits until new
    snapshot appears. Then waits for disk is locked, which means
    migration started. Waits until migration is finished, which is
    when disk is moved to up.

    __author__ = "ratamir"

    :param vm_name: Name of the disk's vm
    :type vm_name: str
    :param disk_name: Name of the disk
    :type disk_name: str
    :param target_sd: Name of storage domain disk should be moved to
    :type target_sd: str
    :param timeout: Timeout for waiting
    :type timeout: int
    :param sleep: Polling interval while waiting
    :type sleep: int
    :param wait: If should wait for operation to finish
    :type wait: bool
    :raises:
        * DiskException if something went wrong
        * APITimeout if waiting for snapshot was longer than 20 seconds
    """
    def _wait_for_new_storage_domain(vm_name, disk_name, new_sd):
        """
        Waits until disk disk_name isn't placed on new_sd
        """
        migrated_disk = getVmDisk(vm_name, disk_name)
        target_domain = STORAGE_DOMAIN_API.find(
            migrated_disk.storage_domains.storage_domain[0].get_id(), 'id')
        return target_domain.name == new_sd
    logger.info("Migrating disk %s of vm %s to domain %s", disk_name, vm_name,
                target_sd)
    move_vm_disk(vm_name, disk_name, target_sd, timeout=timeout, wait=wait)
    if wait:
        sampler = TimeoutingSampler(timeout, sleep,
                                    _wait_for_new_storage_domain,
                                    vm_name, disk_name, target_sd)
        for sample in sampler:
            if sample:
                break
        wait_for_disks_status([disk_name], timeout=timeout)
        wait_for_jobs([ENUMS['job_live_migrate_disk']])
        # Wait for live merge after LSM
        wait_for_jobs([ENUMS['job_remove_snapshot']])
        wait_for_vm_snapshots(vm_name, ENUMS['snapshot_state_ok'])


def live_migrate_vm(vm_name, timeout=VM_IMAGE_OPT_TIMEOUT*2, wait=True,
                    ensure_on=True, same_type=True, target_domain=None):
    """
    Live migrate all vm's disks

    __author__ = "ratamir"

    :param vm_name: Name of the vm
    :type vm_name: str
    :param timeout: Specify how long before an exception should be
        raised (in seconds)
    :type timeout: int
    :param wait: Specifies whether to wait until migration has completed
    :type wait: bool
    :param ensure_on: Specify whether VM should be up before live storage
        migration begins
    :type ensure_on: bool
    :param same_type: If True, return only a storage domain of the same type,
        False will result in a different domain type returned
    :type same_type: bool
    :param target_domain: Name of the target domain to migrate,
        required param in case of specific domain requested
    :type target_domain: str
    :raises:
        * DiskException if something went wrong
        * VMException if vm is not up and ensure_on=False
        * APITimeout if waiting for snapshot was longer than 1800 seconds
    """
    logger.info("Start Live Migrating vm %s disks", vm_name)
    vm_obj = VM_API.find(vm_name)
    if vm_obj.get_status() == ENUMS['vm_state_down']:
        logger.warning("Storage live migrating vm %s is not in up status",
                       vm_name)
        if ensure_on:
            start_vms([vm_name], 1, wait_for_ip=False)
            waitForVMState(vm_name)
        else:
            raise exceptions.VMException("VM must be up to perform live "
                                         "storage migration")

    disk_objecs = getObjDisks(vm_name, get_href=False)
    vm_disks_names = [disk.get_name() for disk in disk_objecs]
    vm_disks_ids = [disk.get_id() for disk in disk_objecs]

    logger.info("Live Storage Migrating vm %s, will migrate following "
                "disks: %s", vm_name, vm_disks_names)

    for disk_id, disk_name in zip(vm_disks_ids, vm_disks_names):
        if target_domain is not None:
            target_sd = target_domain
        else:
            target_sd = get_other_storage_domain(
                disk_id, vm_name, force_type=same_type, key='id'
            )
        live_migrate_vm_disk(
            vm_name, disk_name, target_sd, timeout=timeout, wait=wait
        )
    if wait:
        wait_for_jobs([ENUMS['job_live_migrate_disk']])
        waitForVMState(vm_name, timeout=timeout, sleep=5)


def remove_all_vm_lsm_snapshots(vm_name):
    """
    Removes all snapshots of given VM which were created during
    live storage migration (according to snapshot description)
    Raise: AssertionError if something went wrong

    __author__ = "ratamir"
    :param vm_name: name of the vm that should be cleaned out of snapshots
    created during live migration
    :type vm_name: str
    :raises:
        * VMException if at least one snapshot wasn't removed successfully
        * APITimeout if snapshots are not removed by timeout period
    """
    logger.info("Removing all '%s'", LIVE_SNAPSHOT_DESCRIPTION)
    stop_vms_safely([vm_name])
    waitForDisksStat(vm_name)
    snapshots = _getVmSnapshots(vm_name, False)
    results = []
    for snapshot in snapshots:
        if snapshot.get_description() == LIVE_SNAPSHOT_DESCRIPTION:
            results.append(
                removeSnapshot(
                    True, vm_name, LIVE_SNAPSHOT_DESCRIPTION,
                    VM_REMOVE_SNAPSHOT_TIMEOUT,
                )
            )
        wait_for_jobs([ENUMS['job_remove_snapshot']])
        wait_for_vm_snapshots(vm_name, ENUMS['snapshot_state_ok'])
    if False in results:
        raise exceptions.VMException(
            "At least one snapshot was not removed successfully from VM '%s'" %
            vm_name
        )


# TODO: use 3.5 feature - ability to get device name for vm plugged devices
def get_vm_storage_devices(vm_name, username, password,
                           filter_device=FILTER_DEVICE, ensure_vm_on=False):
    """
    Function that returns vm storage devices
    Author: ratamir
    Parameters:
        * vm_name - name of vm which write operation should occur on
        * username - username for vm
        * password - password for vm
        * filter - filter regex for device (e.g. 'vd*')
        * ensure_on - True if wish to make sure that vm is up
    Return: list of devices (e.g [vdb,vdc,...]) and boot device,
    or raise EntityNotFound if error occurs
    """
    if ensure_vm_on:
        start_vms([vm_name], 1, wait_for_ip=False)
        waitForVMState(vm_name)
    vm_ip = waitForIP(vm_name)[1]['ip']
    vm_machine = Machine(host=vm_ip, user=username,
                         password=password).util(LINUX)
    output = vm_machine.get_boot_storage_device()
    boot_disk = 'vda' if 'vd' in output else 'sda'
    vm_devices = vm_machine.get_storage_devices(filter=filter_device)
    if not vm_devices:
        raise EntityNotFound("Error occurred retrieving vm devices")
    vm_devices = [device for device in vm_devices if device != boot_disk]
    return vm_devices, boot_disk


def verify_vm_disk_moved(vm_name, disk_name, source_sd, target_sd=None):
    """
    Function that checks if disk movement was actually succeeded

    __author__ =  "ratamir"

    :param vm_name: Name of vm which write operation should occur on
    :type vm_name: str
    :param disk_name: The name of the disk that moved
    :type disk_name: str
    :param source_sd: Original storage domain
    :type source_sd: str
    :param target_sd: Destination storage domain
    :type target_sd: str
    :returns: True in case source and target sds are different or actual target
    is equal to target_sd, False otherwise
    :rtype: bool
    """
    actual_sd = get_disk_storage_domain_name(disk_name, vm_name)
    logger.info(
        "Verifying whether disk %s moved from storage domain %s to %s",
        disk_name, source_sd, actual_sd
    )
    if target_sd is not None:
        if source_sd != target_sd:
            if actual_sd == target_sd:
                return True
    elif source_sd != actual_sd:
        return True
    return False


def get_vm_bootable_disk(vm):
    """
    Description: get bootable disk
    Author: ratamir
    Parameters:
      * vm - vm name
    Author: ratamir
    Return: name of the bootable disk or None if no boot disk exist
    """
    vm_disks = getVmDisks(vm)
    boot_disk = [d for d in vm_disks if d.get_bootable()][0].get_alias()
    return boot_disk


def verify_write_operation_to_disk(vm_name, user_name, password,
                                   disk_number=0):
    """
    Function that perform dd command to disk
    Author: ratamir
    Parameters:
        * vm_name - name of vm which write operation should occur on
        * user_name - user name
        * password - password
        * disk_number - disk number from devices list
    Return: ecode and output, or raise EntityNotFound if error occurs
    """
    vm_devices, boot_disk = get_vm_storage_devices(vm_name, user_name,
                                                   password,
                                                   ensure_vm_on=True)

    command = DD_COMMAND % (boot_disk, vm_devices[disk_number])

    ecode, out = run_cmd_on_vm(
        vm_name, shlex.split(command), user_name, password, DD_TIMEOUT)

    return ecode, out


def get_volume_size(hostname, user, password, disk_object, dc_obj):
    """
    Get volume size in GB
    Author: ratamir
    Parameters:
        * hostname - name of host
        * user - user name for host
        * password - password for host
        * disk_object - disk object that need checksum
        * dc_obj - data center that the disk belongs to
    Return:
        Volume size (integer), or raise exception otherwise
    """
    host_machine = Machine(host=hostname, user=user,
                           password=password).util(LINUX)

    vol_id = disk_object.get_image_id()
    sd_id = disk_object.get_storage_domains().get_storage_domain()[0].get_id()
    image_id = disk_object.get_id()
    sp_id = dc_obj.get_id()

    lv_size = host_machine.get_volume_size(sd_id, sp_id, image_id, vol_id)
    logger.info("Volume size of disk %s is %s GB",
                disk_object.get_alias(), lv_size)

    return lv_size


def get_vm_device_size(vm_name, user, password, device_name):
    """
    Get vm device size in GB
    Author: ratamir
    Parameters:
        * vm_name - name of vm
        * user - user name
        * password - password
        * device_name - name of device

    Return:
        VM device size (integer) output, or raise exception otherwise
    """
    vm_machine = get_vm_machine(vm_name, user, password)

    device_size = vm_machine.get_storage_device_size(device_name)
    logger.info("Device %s size: %s GB", device_name, device_size)

    return device_size


def get_vms_from_cluster(cluster):
    """
    Description: Gets all VM added to the given cluster

    Parameters:
        * cluster - cluster name
    """
    logging.info("Getting all vms in cluster %s", cluster)
    cluster_id = CLUSTER_API.find(cluster).get_id()
    all_vms = VM_API.get(absLink=False)
    vms_in_cluster = [
        x.get_name() for x in all_vms
        if x.get_cluster().get_id() == cluster_id]
    logging.info("Vms in cluster: %s", vms_in_cluster)
    return vms_in_cluster


def does_vm_exist(vm_name):
    """
    Description: Checks if vm exists
    Parameters:
        * vm_name: name of the vm
    Retrun:
        True in case vm exists, False otherwise
    """
    try:
        VM_API.find(vm_name)
    except EntityNotFound:
        return False
    return True


def get_vms_disks_storage_domain_name(vm_name, disk_alias=None):
    """
    Desription: get the vm's disks storage domain name. if no disk alias is
                specified take the first one
    Parameters:
        * vm_name: name of the vm
        * disk_alias: alias of specific disk if needed
    Return:
        Storage Domains' name where the disk is located
    """
    disks = getVmDisks(vm_name)
    diskObj = None
    if disk_alias:
        for disk in disks:
            if disk_alias == disk.get_alias():
                diskObj = disk
                break
        if not diskObj:
            raise EntityNotFound("Disk with alias %s is not attached to vm %s"
                                 % (disk_alias, vm_name))
    else:
        diskObj = disks[0]

    sd_id = diskObj.get_storage_domains().get_storage_domain()[0].get_id()
    return STORAGE_DOMAIN_API.find(sd_id, attribute='id').get_name()


def get_vm(vm):
    """
    Description: Get vm object
    Author: ratamir
    Parameters:
        * vm: name of the vm
    Returns vm object, EntityNotFound if a vm doesn't exist
    """
    return VM_API.find(vm)


def get_vm_nics_obj(vm_name):
    """
    Description: get vm's nics objects
    Author: ratamir
    Parameters:
        * vm_name: name of the vm
    Returns: list of nics objects, or raise EntityNotFound
    """
    vm_obj = VM_API.find(vm_name)
    return VM_API.getElemFromLink(vm_obj,
                                  link_name='nics',
                                  attr='nic',
                                  get_href=False)


def get_vm_host(vm_name):
    """
    Return name of host, where vm run

    Args:
        vm_name (str): Name of vm.

    Returns:
        str: Host name if found otherwise None
    """
    try:
        logger.info("Get VM %s host", vm_name)
        vm_obj = VM_API.find(vm_name)
        host_obj = HOST_API.find(vm_obj.host.id, 'id')
    except EntityNotFound:
        logger.error("VM %s not found", vm_name)
        return None

    except AttributeError:
        logger.error("VM %s is not running on any host", vm_name)
        return None
    return host_obj.get_name()


def safely_remove_vms(vms):
    """
    Ensure that all vms passed in are removed

    __author__ = 'cmestreg'
    :param vms: list of vms' names
    :type vms: list
    :returns: False if any of the vms still exist, True otherwise
    :rtype: bool
    """
    if vms:
        logger.debug("Removing vms %s", vms)
        existing_vms = filter(does_vm_exist, vms)
        if existing_vms:
            if not stop_vms_safely(existing_vms):
                return False
            for vm in existing_vms:
                removeVm(True, vm, wait=False)
            return waitForVmsGone(True, existing_vms)
    logger.info("There are no vms to remove")
    return True


def get_vm_disk_logical_name(
    vm_name, disk, wait=True, timeout=GUEST_AGENT_TIMEOUT,
    interval=DEF_SLEEP, parse_logical_name=False, key='name'
):
    """
    Retrieves the logical name of a disk that is attached to a VM
    **** Important note: Guest Agent must be installed in the OS for this
    function to work ****

    __author__ = "glazarov"
    :param vm_name - name of the vm which which contains the disk
    :type: str
    :param disk: The alias/ID of the disk for which the logical volume
    name should be retrieved
    :type disk: str
    :param wait: If the function should wait until the value is set by the
    guest agent
    :type wait: bool
    :param timeout: how long to wait in seconds
    :type timeout: int
    :param interval: sleep interval time in seconds
    :type interval: int
    :param parse_logical_name: Determines whether the logical name (e.g.
    /dev/vdb) is returned in the full format when False is set (this is the
    default), otherwise the logical name will be parsed to remove the /dev/
    (e.g. /dev/vdb -> vdb) when True is set
    :type parse_logical_name: bool
    :param key: key to look for disks by, it can be name or ID
    :type key: str
    :returns: Disk logical name, None in case is not set
    :rtype: str
    """
    def get_logical_name(vm_name, disk_alias=None, disk_id=None):
        if disk_id:
            return getVmDisk(vm_name, disk_id=disk_id).get_logical_name()
        else:
            return getVmDisk(vm_name, disk_alias).get_logical_name()

    if key == 'id':
        disk_alias = None
        disk_id = disk
    else:
        disk_alias = disk
        disk_id = None
    if not wait:
        logical_name = get_logical_name(
            vm_name, disk_alias=disk_alias, disk_id=disk_id
        )
        if parse_logical_name:
            logical_name = logical_name.replace("/dev/", "")
        return logical_name

    logger.debug("Waiting for logical volume name for disk %s", disk)
    for logical_name in TimeoutingSampler(
        timeout, interval, get_logical_name, vm_name, disk_alias, disk_id,
    ):
        if logical_name:
            if parse_logical_name:
                logical_name = logical_name.replace("/dev/", "")
            return logical_name

    return None


def run_vms_once(vms, max_workers=None, **kwargs):
    """
    Starts all vms in vm_list. Throws an exception if it fails

    :param vms: list of vm names
    :type vms: list
    :param max_workers: In how many threads should vms start
    :type max_workers: int
    :param kwargs: vm_name_1: {vm_name_1 run once parameters}
                   vm_name_2: {vm_name_2 run once parameters}
                   ...
    :type kwargs: dict
    :raises: VMException
    """
    results = list()
    max_workers = len(vms) if not max_workers else max_workers
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for vm_name in vms:
            vm_obj = VM_API.find(vm_name)
            if vm_obj.get_status() == ENUMS['vm_state_down']:
                logger.info("Starting vm %s", vm_name)
                results.append(
                    executor.submit(
                        runVmOnce, True, vm_name, **kwargs[vm_name]
                    )
                )
    for vm_name, res in zip(vms, results):
        if res.exception():
            logger.error(
                "Got exception while starting vm %s: %s",
                vm_name, res.exception()
            )
            raise res.exception()
        if not res.result():
            raise exceptions.VMException("Cannot start vm %s" % vm_name)


def get_vm_nic_mac_address(vm, nic='nic1'):
    """
    Get MAC address on specific NIC of given VM

    :param vm: VM to find NIC MAC on
    :type vm: str
    :param nic: NIC of the VM to find MAC on
    :type nic: str
    :return: MAC address on specific NIC of the VM
    :rtype: str
    """
    try:
        nicObj = get_vm_nic(vm, nic)
    except EntityNotFound:
        VM_API.logger.error("Vm %s doesn't have nic '%s'", vm, nic)
        return ""
    return str(nicObj.mac.address)


def get_vm_nic_statistics(vm, nic):
    """
    Get VM NIC statistics collection

    :param vm: VM name
    :type vm: str
    :param nic: NIC name
    :type nic: str
    :return: VM NIC statistics list
    :rtype: list
    """
    vm_nic = get_vm_nic(vm, nic)
    return NIC_API.getElemFromLink(
        vm_nic, link_name="statistics", attr="statistic"
    )


def get_vm_memory(vm_name):
    """
    Get vm memory size from engine

    :param vm_name: name of vm
    :type vm_name: str
    :returns: memory of vm
    :rtype: int
    """
    vm_obj = get_vm_obj(vm_name)
    if not vm_obj:
        logger.error("Vm with name %s not exist under engine", vm_name)
        return 0
    return vm_obj.get_memory()


def get_vm_cores(vm_name):
    """
    Get number of cores on vm from engine

    :param vm_name: name of vm
    :type vm_name: str
    :returns: cores of vm
    :rtype: int
    """
    vm_obj = get_vm_obj(vm_name)
    if not vm_obj:
        logger.error("Vm with name %s not exist under engine", vm_name)
        return 0
    return vm_obj.get_cpu().get_topology().get_cores()


def get_vm_sockets(vm_name):
    """
    Get the VM sockets number

    :param vm_name: host name
    :type vm_name: str
    :return: number of host sockets
    :rtype int
    """
    logger.info("Get VM %s socket", vm_name)
    vm_obj = get_vm_obj(vm_name)
    sockets = vm_obj.cpu.topology.sockets
    if sockets:
        return sockets
    logger.error("Failed to get cpu sockets from %s", vm_name)
    return 0


def get_vm_threads(vm_name):
    """
    Get the VM Threads number

    :param vm_name: host name
    :type vm_name: str
    :return: number of host threads
    :rtype: int
    """
    logger.info("Get VM %s threads", vm_name)
    vm_obj = get_vm_obj(vm_name)
    threads = vm_obj.cpu.topology.threads
    if threads:
        return threads
    logger.error("Failed to get cpu threads from %s", vm_name)
    return 0


def get_vm_processing_units_number(vm_name):
    """
    Get the VM processing units number
    ( sockets * cores * threads )

    :param vm_name: host name
    :type vm_name: str
    :return number of host processing units
    :rtype: int
    """
    logger.info("Get VM %s processing units", vm_name)
    processing_units_number = (
        get_vm_cores(vm_name) *
        get_vm_sockets(vm_name) *
        get_vm_threads(vm_name)
    )
    if processing_units_number:
        return processing_units_number
    logger.error("Failed to get the %s processing units number" % vm_name)
    return 0


def get_vm_numa_nodes(vm_name):
    """
    Get vm numa nodes

    :param vm_name: name of vm
    :type vm_name: str
    :returns: list of numa nodes
    :rtype: list
    """
    vm_obj = get_vm_obj(vm_name)
    return VM_API.getElemFromLink(
        elm=vm_obj, link_name=NUMA_NODE_LINK, attr="vm_numa_node"
    )


def get_vm_numa_node_by_index(vm_name, numa_node_index):
    """
    Get vm numa node by index

    :param vm_name: name of vm
    :type vm_name: str
    :param numa_node_index: index of vm numa node
    :type numa_node_index: int
    :returns: vm numa node with specific index or None
    :rtype: instance of VirtualNumaNode or None
    """
    numa_nodes = get_vm_numa_nodes(vm_name)
    for numa_node in numa_nodes:
        if numa_node.index == numa_node_index:
            return numa_node
    return None


def __prepare_numa_node_object(
    host_name, **kwargs
):
    """
    Prepare virtual numa node obj

    :param host_name: host, where to pin virtual numa node
    :type host_name: str
    :param index: index of virtual numa node
    :type index: int
    :param memory: amount of memory to attach to numa node(MB)
    :type memory: int
    :param cores: list of cores to attach to numa node
    :type cores: list
    :param pin_list: list of host numa nodes to pin virtual numa node
    :type pin_list: list
    :returns: VirtualNumaNode object
    :rtype: VirtualNumaNode instance
    """
    cores = kwargs.pop("cores", None)
    pin_list = kwargs.pop("pin_list", None)
    v_numa_node_obj = ll_general.prepare_ds_object("VirtualNumaNode", **kwargs)

    if pin_list:
        numa_node_pins_obj = data_st.NumaNodePins()
        for h_numa_node_index in pin_list:
            import hosts
            h_numa_node_obj = hosts.get_numa_node_by_index(
                host_name, h_numa_node_index
            )
            if not h_numa_node_obj:
                logger.error(
                    "Numa node with index %d not found on host %s",
                    h_numa_node_index, host_name
                )
                return None
            numa_node_pin_obj = data_st.NumaNodePin(
                pinned=True,
                index=h_numa_node_index,
                host_numa_node=h_numa_node_obj
            )
            numa_node_pins_obj.add_numa_node_pin(numa_node_pin_obj)
        v_numa_node_obj.set_numa_node_pins(numa_node_pins_obj)

    if cores:
        cpu_obj = data_st.Cpu()
        cores_obj = data_st.Cores()
        for core in cores:
            core_obj = data_st.Core(index=core)
            cores_obj.add_core(core_obj)
        cpu_obj.set_cores(cores_obj)
        v_numa_node_obj.set_cpu(cpu_obj)

    return v_numa_node_obj


def add_numa_node_to_vm(
    vm_name, host_name, index, memory, **kwargs
):
    """
    Add numa node to vm

    :param vm_name: vm, where to create new numa node
    :type vm_name: str
    :param host_name: host, where to pin virtual numa node
    :type host_name: str
    :param index: index of virtual numa node
    :type index: int
    :param memory: amount of memory to attach to numa node(MB)
    :type memory: int
    :param cores: list of cores to attach to numa node
    :type cores: list
    :param pin_list: list of host numa nodes to pin virtual numa node
    :type pin_list: list
    :returns: True, if action success, otherwise False
    :rtype: bool
    """
    try:
        numa_node_obj = __prepare_numa_node_object(
            host_name=host_name, index=index, memory=memory, **kwargs
        )
    except exceptions.HostException as ex:
        logger.error("Failed to create virtual numa node object, err: %s", ex)
        return False
    vm_obj = get_vm_obj(vm_name)
    numa_nodes_link = VM_API.getElemFromLink(
        elm=vm_obj, link_name=NUMA_NODE_LINK, get_href=True
    )
    log_info, log_error = ll_general.get_log_msg(
        action="Add",
        obj_type="numa node",
        obj_name=str(index),
        extra_txt="to VM %s" % vm_name,
        **kwargs
    )
    logger.info(log_info)
    status = NUMA_NODE_API.create(
        entity=numa_node_obj, positive=True, collection=numa_nodes_link
    )[1]
    if not status:
        logger.error(log_error)
    return status


def update_numa_node_on_vm(
    vm_name, host_name, old_index, **kwargs
):
    """
    Update vm numa node

    :param vm_name: vm, where to update numa node
    :type vm_name: str
    :param host_name: host, where to pin virtual numa node
    :type host_name: str
    :param old_index: index of vm numa node to update
    :type old_index: int
    :param new_index: new index of virtual numa node
    :type new_index: int
    :param memory: amount of memory to attach to numa node(MB)
    :type memory: int
    :param cores: list of cores to attach to numa node
    :type cores: list
    :param pin_list: list of host numa nodes to pin virtual numa node
    :type pin_list: list
    :returns: True, if action success, otherwise False
    :rtype: bool
    """
    old_numa_node_obj = get_vm_numa_node_by_index(vm_name, old_index)
    if not old_numa_node_obj:
        logger.error(
            "Failed to get numa node with index %d from vm %s",
            old_index, vm_name
        )
        return False
    new_numa_node_obj = __prepare_numa_node_object(
        host_name=host_name, **kwargs
    )
    if not new_numa_node_obj:
        logger.error(
            "Failed to create virtual numa node object with parameters: %s",
            kwargs
        )
        return False
    return NUMA_NODE_API.update(
        old_numa_node_obj, new_numa_node_obj, True
    )[1]


def remove_numa_node_from_vm(vm_name, numa_node_index):
    """
    Remove numa node from vm

    :param vm_name: vm from where to remove numa node
    :type vm_name: str
    :param numa_node_index: index of numa node for remove
    :type numa_node_index: int
    :returns: True, if action success, otherwise False
    :rtype: bool
    """
    numa_node_obj = get_vm_numa_node_by_index(vm_name, numa_node_index)
    if not numa_node_obj:
        logger.error(
            "Failed to get numa node with index %d from vm %s",
            numa_node_index, vm_name
        )
        return False
    log_info, log_error = ll_general.get_log_msg(
        action="Remove",
        obj_type="numa node",
        obj_name=str(numa_node_index),
        extra_txt="from VM %s" % vm_name
    )
    logger.info(log_info)
    status = NUMA_NODE_API.delete(numa_node_obj, True)
    if not status:
        logger.error(log_error)
    return status


def export_domain_vm_exist(vm, export_domain, positive=True):
    """
    __Author__ = slitmano

    Checks if a vm exists in an export domain

    Args:
        vm (str): VM name
        export_domain (str): Export domain name
        positive (bool): Expected status

    Returns:
        bool: True if template exists in export domain False otherwise
    """
    export_domain_object = STORAGE_DOMAIN_API.find(export_domain)
    try:
        VM_API.getElemFromElemColl(export_domain_object, vm)
    except EntityNotFound:
        if positive:
            logger.error(
                "VM %s cannot be found in export domain: %s", vm, export_domain
            )
            return False
        return True
    return True


def add_repo_to_vm(
    vm_host,
    repo_name,
    baseurl,
    path='/etc/yum.repos.d/',
    **kwargs
):
    """
    Add repo to vm

    :param vm_host: vm where repo will be added
    :type vm_host: resources.Host
    :param repo_name: name of the repo
    :type repo_name: str
    :param baseurl: baseurl of the repo
    :type baseurl: str
    :param path: path where repo will be stored
    :type path: str
    :param kwargs: other values of repo configuration
    :type kwargs: dict
    """
    with vm_host.executor().session() as ss:
        with ss.open_file(
            '%s.repo' % os.path.join(path, repo_name),
            'w'
        ) as repo_file:
            repo_file.write((
                '[{repo_name}]\n'
                'name={repo_name}\n'
                'baseurl={baseurl}\n'
                'enabled={enabled}\n'
                'gpgcheck={gpgcheck}\n'
            ).format(
                repo_name=repo_name,
                baseurl=baseurl,
                enabled=kwargs.get('enabled', '1'),
                gpgcheck=kwargs.get('gpgcheck', '0'),
            ))


def reorder_vm_mac_address(vm_name):
    """
    Reorder VM mac addresses

    Args:
        vm_name (str): VM name

    Returns:
        bool: True if reorder MACs on VM succeeded, False otherwise
    """
    vm_obj = VM_API.find(vm_name)
    logger.info("Reorder VM %s vNICs", vm_name)
    res = VM_API.syncAction(vm_obj, "reordermacaddresses", True, "true")
    if not res:
        logger.error("Failed to reorder MACs on VM %s", vm_name)
    return res


def is_disk_attached_to_vm(vm_name, disk_alias):
    """
    Check whether the disk specified is attached to the VM provided

    :param vm_name: The name of the VM where the input disk may be attached
    :type vm_name: str
    :param disk_alias: The alias of the disk that will be checked with the
    input VM
    :type disk_alias: str
    :returns: True if disk is attached to VM, False otherwise
    :rtype: bool
    """
    return disk_alias in [disk.get_alias() for disk in getVmDisks(vm_name)]


def get_vm_applications(vm_name):
    """
    Return list of applications names of vm

    :param vm_name: name of vm to be checked
    :type vm_name: str
    :return: list of vms applications
    :rtype: list of str
    """
    return [
        app.get_name() for app in VM_API.getElemFromLink(
            VM_API.find(vm_name),
            link_name='applications',
            attr='application',
            get_href=False,
        )
        ]


def freeze_vm(positive, vm):
    """
    Freeze vm's filesystems from any write operations

    __author__ = "cmestreg"
    :param positive: True if the freeze action should succeed, False otherwise
    :type positive: bool
    :param vm: Name of vm
    :type vm: str
    :returns: Result of the freeze action
    :rtype: bool
    """

    vmObj = VM_API.find(vm)
    return VM_API.syncAction(vmObj, 'freezefilesystems', positive)


def thaw_vm(positive, vm):
    """
    Thaw vm's filesystems (unfreeze the filesystems)

    __author__ = "cmestreg"
    :param positive: True if the freeze action should succeed, False otherwise
    :type positive: bool
    :param vm: Name of vm
    :type vm: str
    :returns: Result of the thaw action
    :rtype: bool
    """
    vmObj = VM_API.find(vm)
    return VM_API.syncAction(vmObj, 'thawfilesystems', positive)


def reboot_vm(positive, vm):
    """
    Reboot vm

    __author__ = "cmestreg"
    :param positive: True if the reboot action should succeed, False otherwise
    :type positive: bool
    :param vm: Name of vm
    :type vm: str
    :returns: Result of the reboot action
    :rtype: bool
    """
    vmObj = VM_API.find(vm)
    return VM_API.syncAction(vmObj, 'reboot', positive)


def get_cpu_profile_id(vm_name):
    """
    Get VM cpu profile id

    :param vm_name: Name of VM
    :type vm_name: str
    :return: cpu profile id
    :rtype: str
    """
    vm_obj = VM_API.find(vm_name)
    return vm_obj.get_cpu_profile().id


def get_vm_host_devices_link(vm_name):
    """
    Get VM host devices link

    Args:
        vm_name (str): Vm name

    Returns:
        str: Link on host devices collection
    """
    logger.info("Get VM %s host devices link", vm_name)
    vm_obj = get_vm_obj(vm_name=vm_name)
    return VM_API.getElemFromLink(
        elm=vm_obj, link_name=HOST_DEVICE_LINK, get_href=True
    )


def get_vm_host_devices(vm_name):
    """
    Get all VM host devices

    Args:
        vm_name (str): VM name

    Returns:
        list: All host devices
    """
    vm_obj = get_vm_obj(vm_name)
    logger.info("Get all devices from VM %s", vm_name)
    return VM_API.getElemFromLink(
        elm=vm_obj, link_name=HOST_DEVICE_LINK, attr="host_device"
    )


def get_vm_host_device_by_name(vm_name, device_name):
    """
    Get VM host device object by device name

    Args:
        vm_name (str): VM name
        device_name (str): Device name

    Returns:
        HostDevice: Instance of HostDevice
    """
    host_devices = get_vm_host_devices(vm_name=vm_name)
    logger.info(
        "Get host device with name %s from VM %s", device_name, vm_name
    )
    host_devices = filter(
        lambda host_device: host_device.get_name() == device_name, host_devices
    )
    if not host_devices:
        logger.error(
            "Failed to find host device with name %s under VM %s",
            device_name, vm_name
        )
        return None
    return host_devices[0]


def add_vm_host_device(vm_name, host_name, device_name):
    """
    Attach host device to VM

    Args:
        vm_name (str): VM name
        host_name (str): Host name
        device_name (str): Device name

    Returns:
        bool: True, if add host device succeed, otherwise False
    """
    # Local import to prevent import recursion loop
    from art.rhevm_api.tests_lib.low_level.hosts import (
        get_host_device_id_by_name
    )
    host_device_id = get_host_device_id_by_name(
        host_name=host_name, device_name=device_name
    )
    host_device_obj = ll_general.prepare_ds_object(
        "HostDevice", id=host_device_id
    )
    log_info, log_error = ll_general.get_log_msg(
        action="Add", obj_type="host device", obj_name=device_name,
        extra_txt="to VM %s" % vm_name
    )
    host_devices_link = get_vm_host_devices_link(vm_name=vm_name)
    logger.info(log_info)
    status = HOST_DEVICE_API.create(
        entity=host_device_obj, positive=True, collection=host_devices_link
    )[1]
    if not status:
        logger.error(log_error)
    return status


def remove_vm_host_device(vm_name, device_name):
    """
    Remove host device from VM

    Args:
        vm_name (str): VM name
        device_name (str): VM name

    Returns:
        bool: True, if remove host device succeed, otherwise False
    """
    host_device_obj = get_vm_host_device_by_name(
        vm_name=vm_name, device_name=device_name
    )
    log_info, log_error = ll_general.get_log_msg(
        action="Remove", obj_type="host device", obj_name=device_name,
        extra_txt="from VM %s" % vm_name
    )
    logger.info(log_info)
    status = HOST_DEVICE_API.delete(host_device_obj, True)
    if not status:
        logger.error(log_error)
    return status


def get_vm_placement_hosts(vm_name):
    """
    Get VM placement hosts

    Args:
        vm_name (str): VM name

    Returns:
        list: Host names
    """
    vm_obj = get_vm_obj(vm_name=vm_name)
    logger.info("Get VM %s pinned hosts", vm_name)
    vm_hosts_obj = vm_obj.get_placement_policy().get_hosts()
    hosts = [
        HOST_API.find(vm_host_obj.id, 'id').get_name()
        for vm_host_obj in vm_hosts_obj.get_host()
    ]
    return hosts


def get_all_vms():
    """
    Get list of VM objects from API

    Returns:
        list: VM objects
    """
    return VM_API.get(absLink=False)
