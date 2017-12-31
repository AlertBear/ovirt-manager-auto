#! /usr/bin/python
# -*- coding: utf-8 -*-
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
from Queue import Queue
from threading import Thread

from concurrent.futures import ThreadPoolExecutor
from art.rhevm_api.utils.jobs import Job, JobsSet
from utilities.machine import Machine, LINUX

import art.rhevm_api.tests_lib.low_level.general as ll_general
from art.core_api.apis_exceptions import (APITimeout, EntityNotFound)
from art.core_api.apis_utils import data_st, TimeoutingSampler, getDS
from art.rhevm_api import resources
from art.rhevm_api.tests_lib.low_level.disks import (
    _prepareDiskObject, getVmDisk, getObjDisks, get_other_storage_domain,
    wait_for_disks_status, get_disk_storage_domain_name,
    prepare_disk_attachment_object, updateDisk, get_disk_attachments,
    get_disk_attachment, get_disk_obj, get_disk_list_from_disk_attachments,
    get_snapshot_disks_by_snapshot_obj
)
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.low_level.networks import get_vnic_profile_obj
from art.rhevm_api.utils.name2ip import LookUpVMIpByName
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.rhevm_api.utils.test_utils import (
    searchForObj, update_vm_status_in_database, get_api, waitUntilGone,
)
from art.test_handler import exceptions
from art.test_handler.exceptions import CanNotFindIP
from art.test_handler.settings import ART_CONFIG

ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
RHEVM_UTILS_ENUMS = ART_CONFIG['elements_conf']['RHEVM Utilities']
Migration_Options = getDS('MigrationOptions')
Migration_Policy = getDS('MigrationPolicy')

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
    'size', 'type', 'format', 'sparse',
    'wipe_after_delete', 'propagate_errors', 'alias', 'read_only'
]
VM_WAIT_FOR_IP_TIMEOUT = 600
SNAPSHOT_TIMEOUT = 15 * 60
PREVIEW = ENUMS['preview_snapshot']
UNDO = ENUMS['undo_snapshot']
COMMIT = ENUMS['commit_snapshot']
LIVE_SNAPSHOT_DESCRIPTION = ENUMS['live_snapshot_description']

SNAPSHOT_STATE_OK = ENUMS['snapshot_state_ok']

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
DISK_ATTACHMENTS_API = get_api("disk_attachment", "diskattachments")
INSTANCE_TYPE_API = get_api("instance_type", "instancetypes")

Snapshots = getDS('Snapshots')
NUMA_NODE_LINK = "numanodes"
HOST_DEVICE_LINK = "hostdevices"
SAMPLER_TIMEOUT = 120
SAMPLER_SLEEP = 5
VM = "VM"
MIGRATION_TIMEOUT = 300
VM_PASSWORD = "qum5net"
NETWORK_FILTER_PARAMETER = "network_filter_parameter"
NETWORK_FILTER_PARAMETERS = "networkfilterparameters"
NETWORK_FILTER_API = get_api(
    NETWORK_FILTER_PARAMETER, NETWORK_FILTER_PARAMETERS
)

logger = logging.getLogger("art.ll_lib.vms")


class DiskNotFound(Exception):
    pass


def _prepare_vm_object(**kwargs):
    """
    Prepare vm object

    Args:
        name (str): vm name
        description (str): new vm description
        cluster (str): new vm cluster
        memory (int): vm memory size in bytes
        cpu_socket (int): number of cpu sockets
        cpu_cores (int): number of cpu cores
        cpu_threads (int): number of threads per core
        cpu_mode (str): mode of cpu
        os_type (str): OS type of new vm
        boot (str): type of boot
        template (str): name of template that should be used
        type (str): vm type (SERVER or DESKTOP)
        monitors (int): number of display monitors
        display_type (str): type of vm display (VNC or SPICE)
        kernel (str): kernel path
        initrd (str): initrd path
        cmdline (str): kernel parameters
        vcpu_pinning (dict): vcpu pinning affinity
        serial_console (bool): set 'Enable VirtIO serial console' flag for vm
        single_qxl_pci (bool): set Console -> 'Single PCI' flag.
        highly_available (str): set high-availability for vm ('true'/'false')
        placement_affinity (str): vm to host affinity
        placement_host (str): host that the affinity holds for
        placement_hosts (list): multiple hosts for vm placement
        availablity_priority (int): priority for high-availability (an integer
                                    in range 0-100 where 0 - Low, 50 - Medium,
                                    100 - High priority)
        custom_properties (str): custom properties set to the vm
        stateless (bool): if vm stateless or not
        memory_guaranteed (int): size of guaranteed memory in bytes
        ballooning (bool): True of False - enable ballooning on vm
        quota (str): vm quota id
        protected (bool): true if vm is delete protected
        templateUuid (str): id of template to be used
        clusterUuid (str): uuid of cluster
        storagedomain (str): name of storagedomain
        disk_clone (str): defines whether disk should be cloned from template
        domainName (str): sys.prep domain name
        snapshot (str): description of snapshot to use. Causes error if not
                        unique
        cpu_profile_id (str): cpu profile id
        numa_mode (str): numa mode for vm(strict, preferred, interleave)
        cpu_shares (int): cpu shares
        serial_number (str): serial number to use
        start_in_pause (bool): start vm in pause
        comment (str): vm comment
        usb_type (str): usb type to use (can work only with spice display type)
        custom_emulated_machine (str): add custom emulated machine value for vm
        custom_cpu_model (str): overried cluster cpu model and set any cpu type
        disconnect_action (str): disconnect action for display console
        soundcard_enabled (bool): enable sound card for display console
        virtio_scsi (bool): enable virtIO scsi
        migration_downtime (int): migration_downtime allowed (in miliseconds)
        io_threads (int): number of io threads
        boot_menu (bool): enable boot menu on vm startup
        start_paused (bool): enable start in pause mode
        file_transfer_enabled (bool): enable file transfer via spice
        time_zone (str): set specific time zone for vm
        time_zone_offset (str): time zone offset (from GMT)
        template_version (int): template version of the specified template
        migration_policy (str): Migration policy name
        auto_converge (bool): Enable auto converge (only with Legacy policy)
        compressed (bool): Enable compressed (only with Legacy policy)
        instance_type (str): name of instance_type to be used for the vm
        max_memory (int): Upper bound for the memory hotplug
        rng_device (bool): Enable rng device
        rng_bytes (int): Bytes per period
        rng_period (int): Period duration (ms)
        lease (str): Storage domain name for the lease or ''(empty string) to
            remove the lease

    Returns:
        instance of VM: vm object
    """
    add = kwargs.pop("add", False)
    vm_name = kwargs.pop("name", None)
    uuid = kwargs.pop("uuid", None)
    description = kwargs.pop("description", None)
    vm = data_st.Vm(name=vm_name, description=description, id=uuid)

    # snapshot
    snapshot_name = kwargs.pop("snapshot", None)
    if snapshot_name:
        add = False
        vms = VM_API.get(abs_link=False)
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
    template_version = kwargs.pop("template_version", 1)
    template = None
    if template_id:
        template = TEMPLATE_API.find(template_id, ID_ATTR)
    elif template_name:
        from art.rhevm_api.tests_lib.low_level.templates import (
            get_template_obj
        )
        template = get_template_obj(template_name, version=template_version)
    if template:
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

    # instance type
    instance_type_name = kwargs.get("instance_type")
    if instance_type_name:
        instance_type = INSTANCE_TYPE_API.find(instance_type_name)
        vm.set_instance_type(instance_type)

    # memory
    vm.memory = kwargs.pop("memory", None)

    # cpu topology & cpu pinning
    cpu_socket = kwargs.pop("cpu_socket", None)
    cpu_cores = kwargs.pop("cpu_cores", None)
    cpu_threads = kwargs.pop("cpu_threads", None)
    vcpu_pinning = kwargs.pop("vcpu_pinning", None)
    cpu_mode = kwargs.pop("cpu_mode", None)
    if (
        cpu_socket or
        cpu_cores or
        cpu_threads or
        vcpu_pinning is not None or
        cpu_mode is not None
    ):
        cpu = data_st.Cpu()
        if cpu_socket or cpu_cores or cpu_threads:
            cpu.set_topology(
                topology=data_st.CpuTopology(
                    sockets=cpu_socket, cores=cpu_cores, threads=cpu_threads
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
                                vcpu=int(elm.keys()[0]),
                                cpu_set=elm.values()[0]
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
        if opt_val is not None:
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
    monitors = kwargs.pop("monitors", None)
    disconnect_action = kwargs.pop("disconnect_action", None)
    file_transfer_enabled = kwargs.pop("file_transfer_enabled", None)
    single_qxl_pci = kwargs.pop('single_qxl_pci', None)
    if monitors or display_type or disconnect_action or single_qxl_pci:
        vm.set_display(
            data_st.Display(
                type_=display_type, monitors=monitors,
                disconnect_action=disconnect_action,
                file_transfer_enabled=file_transfer_enabled,
                single_qxl_pci=single_qxl_pci
            )
        )

    # stateless
    vm.set_stateless(kwargs.pop("stateless", None))

    # serial console
    serial_console = kwargs.pop("serial_console", None)
    if serial_console is not None:
        vm.set_console(
            data_st.Console(
                enabled=serial_console
            )
        )

    # high availablity
    ha = kwargs.pop("highly_available", None)
    ha_priority = kwargs.pop("availablity_priority", None)
    if ha is not None or ha_priority:
        vm.set_high_availability(
            data_st.HighAvailability(
                enabled=ha, priority=ha_priority
            )
        )

    from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd
    lease = kwargs.pop("lease", None)
    if lease is not None:
        if lease:
            storage_domain_obj = ll_sd.get_storage_domain_obj(lease)
            lease_st = data_st.StorageDomainLease(
                storage_domain=data_st.StorageDomain(
                    id=storage_domain_obj.get_id()
                )
            )
        else:
            lease_st = data_st.StorageDomainLease()
        vm.set_lease(lease_st)

    # custom properties
    custom_prop = kwargs.pop("custom_properties", None)
    if custom_prop:
        vm.set_custom_properties(createCustomPropertiesFromArg(custom_prop))

    # memory policy memory_guaranteed and ballooning
    guaranteed = kwargs.pop("memory_guaranteed", None)
    max_memory = kwargs.pop("max_memory", None)
    ballooning = kwargs.pop('ballooning', None)
    if ballooning is not None or guaranteed or max_memory:
        vm.set_memory_policy(
            data_st.MemoryPolicy(
                guaranteed=guaranteed,
                ballooning=ballooning,
                max=max_memory
            )
        )

    # placement policy: placement_affinity & placement_host
    affinity = kwargs.pop("placement_affinity", None)
    placement_host = kwargs.pop("placement_host", None)
    placement_hosts = kwargs.pop("placement_hosts", None) or []
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
            payload = data_st.Payload(files=payload_files, type_=payload_type)
            payload_array.append(payload)
        payloads = data_st.Payloads(payload_array)
        vm.set_payloads(payloads)

    # delete protection
    protected = kwargs.pop("protected", None)
    if protected is not None:
        vm.set_delete_protected(protected)

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

    # usb_type
    usb_type = kwargs.pop("usb_type", None)
    if usb_type:
        usb = data_st.Usb()
        usb.set_enabled(True)
        usb.set_type(usb_type)
        vm.set_usb(usb)

    # custom emulated machine
    custom_emulated_machine = kwargs.pop("custom_emulated_machine", None)
    if custom_emulated_machine is not None:
        vm.set_custom_emulated_machine(custom_emulated_machine)

    # custom cpu model
    custom_cpu_model = kwargs.pop("custom_cpu_model", None)
    if custom_cpu_model is not None:
        vm.set_custom_cpu_model(custom_cpu_model)

    # soundcard enabled
    soundcard_enabled = kwargs.pop("soundcard_enabled", None)
    if soundcard_enabled is not None:
        vm.set_soundcard_enabled(soundcard_enabled)

    # migration_downtime
    migration_downtime = kwargs.pop("migration_downtime", None)
    if migration_downtime:
        vm.set_migration_downtime(migration_downtime)

    # io_threads
    io_threads = kwargs.pop("io_threads", None)
    if io_threads:
        io = data_st.Io()
        io.set_threads(io_threads)
        vm.set_io(io)

    # boot_menu
    boot_menu = kwargs.pop("boot_menu", None)
    if boot_menu:
        bios = data_st.Bios()
        boot = data_st.BootMenu(enabled=boot_menu)
        bios.set_boot_menu(boot)
        vm.set_bios(bios)

    # start_paused
    start_paused = kwargs.pop("start_paused", None)
    if start_paused:
        vm.set_start_paused(start_paused)

    # migration policy
    if 'migration_policy_id' in kwargs:
        migration_policy_id = kwargs.pop('migration_policy_id')
        if migration_policy_id == 'inherit':
            logger.info("setting empty policy (restore default)")
            migration_policy = Migration_Policy()
        else:
            migration_policy = Migration_Policy(id=migration_policy_id)
        auto_converge = str(kwargs.pop("auto_converge", "inherit")).lower()
        compressed = str(kwargs.pop("compressed", "inherit")).lower()
        migration_options = Migration_Options(
            policy=migration_policy,
            auto_converge=auto_converge,
            compressed=compressed
        )
        vm.set_migration(migration_options)

    # RNG policy
    rng_device = kwargs.pop("rng_device", None)
    if rng_device:
        rng_bytes = kwargs.pop("rng_bytes", None)
        rng_period = kwargs.pop("rng_period", None)
        rng = data_st.RngDevice(
            source=rng_device,
            rate=data_st.Rate(bytes=rng_bytes, period=rng_period)
        )
        vm.set_rng_device(rng)

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


@ll_general.generate_logs(step=True)
def addVm(positive, wait=True, **kwargs):
    """
    Description: add new vm (without starting it)

    :param positive: True if action is positive, Flase if negative
    :type positive: bool
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
    :param cpu_threads: number of cpu threads
    :type cpu_threads: int
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
    :param monitors: number of display monitors
    :type monitors: int
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
    :param template_version: template version of the specified template
    :type template_version: int
    :param migration_policy: Migration policy name
    :type migration_policy: str
    :param auto_converge: Enable auto converge (only with Legacy policy)
    :type auto_converge: bool
    :param compressed: Enable compressed (only with Legacy policy)
    :type compressed: bool
    :param instance_type: name of instance_type to be used for the vm
    :type instance_type: str
    :param max_memory: Upper bound for the memory hotplug
    :type max_memory: int
    :param rng_device: Enable rng device
    :type rng_device: bool
    :param rng_bytes: Bytes per period
    :type rng_bytes: int
    :param rng_period: Period duration (ms)
    :type  rng_period: int
    :returns: True, if add vm success, otherwise False
    :rtype: bool
    """
    kwargs.update(add=True)
    vm_obj = _prepare_vm_object(**kwargs)
    expected_vm = _prepare_vm_object(**kwargs)
    operations = []
    # disk_clone
    disk_clone = kwargs.pop("disk_clone", None)
    if disk_clone and disk_clone.lower() == "true":
        operations.append('clone=true')
    # copy_permissions
    copy_permissions = kwargs.pop("copy_permissions", None)
    if copy_permissions:
        operations.append('clone_permissions')

    if False in [positive, wait]:
        vm_obj, status = VM_API.create(
            vm_obj, positive, expected_entity=expected_vm,
            operations=operations
        )
        return status

    wait_timeout = kwargs.pop('timeout', VM_ACTION_TIMEOUT)

    if disk_clone and disk_clone.lower() == 'true':
        expected_vm.set_template(data_st.Template(id=BLANK_TEMPLATE))
        wait_timeout = VM_DISK_CLONE_TIMEOUT

    vm_obj, status = VM_API.create(
        vm_obj, positive, expected_entity=expected_vm, operations=operations
    )

    if status:
        status = VM_API.waitForElemStatus(vm_obj, "DOWN", wait_timeout)
    return status


@ll_general.generate_logs(step=True)
def updateVm(positive, vm, **kwargs):
    """
    Update existed vm

    Args:
        vm (str): Name of vm
        name (str): New vm name
        description (str): New vm description
        data_center (str): New vm data center
        cluster (str): New vm cluster
        memory (int): VM memory size in bytes
        cpu_socket (int): Number of cpu sockets
        cpu_cores (int): Number of cpu cores
        cpu_threads (int): Number of cpu threads
        cpu_mode (str): Mode of cpu
        os_type (str): OS type of new vm
        boot (str): Type of boot
        template (str): Name of template that should be used
        type (str): VM type (SERVER or DESKTOP)
        monitors (int): Number of display monitors
        display_type (str): Type of vm display (VNC or SPICE)
        kernel (str): Kernel path
        initrd (str): Initrd path
        cmdline (str): Kernel parameters
        highly_available(str): Set high-availability for vm ('true' or 'false')
        availablity_priority(int) : Priority for high-availability
            (an integer in range 0-100: 0 - Low,
            50 - Medium, 100 - High priority)
        custom_properties (str) : Custom properties set to the vm
        stateless(bool): If vm stateless or not
        memory_guaranteed (int): Size of guaranteed memory in bytes
        ballooning (bool): Memory ballooning device enable or disable
        domainName (str):  Sys.prep domain name
        placement_affinity (str): VM to host affinity
        placement_host (str): Host that the affinity holds for
        placement_hosts (list): Multiple hosts for vm placement
        quota (str): VM quota id
        protected (bool) : True if vm is delete protected
        watchdog_model (str): Model of watchdog card (ib6300)
        watchdog_action (str): Action of watchdog card
        time_zone (str): Set to timezone out of product possible timezones
        time_zone_offset (str): Set to utc_offset out of product
            possible offsets
        compare (bool): Disable or enable validation for update
        cpu_profile_id (str): Cpu profile id
        numa_mode (str): Numa mode for vm (strict, preferred, interleave)
        initialization (Initialization): Initialization obj for cloud init
        cpu_shares (int): Cpu shares
        start_in_pause (bool): Start vm in pause mode
        comment (str): VM comment
        migration_policy (str): Migration policy name
        auto_converge (bool): Enable auto converge (only with Legacy policy)
        compressed (bool): Enable compressed (only with Legacy policy)
        instance_type (str): Name of instance_type to be used for the vm
        max_memory (int): Upper bound for the memory hotplug
        virtio_scsi (bool): Enable/Disable virtIO scsi
        rng_device (bool): Enable rng device
        rng_bytes (int): Bytes per period
        rng_period (int): Period duration (ms)
        custom_properties (str): custom properties set to the vm

    Returns:
        bool: True, if update success, otherwise False
    """
    vm_obj = VM_API.find(vm)
    vm_new_obj = _prepare_vm_object(**kwargs)
    compare = kwargs.get("compare", True)
    vm_new_obj, status = VM_API.update(
        vm_obj, vm_new_obj, positive, compare=compare
    )
    return status


@ll_general.generate_logs(step=True)
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
    vm_obj = VM_API.find(vm)
    force = kwargs.pop('force', None)
    href_params = []
    if force:
        href_params.append('force=true')
    vm_status = vm_obj.get_status().lower()
    stop_vm = kwargs.pop('stopVM', 'false')
    if str(stop_vm).lower() == 'true' and vm_status != ENUMS['vm_state_down']:
        if not stopVm(positive, vm):
            return False
    status = VM_API.delete(vm_obj, positive, operations=href_params)

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
        vmsList = vms.replace(',', ' ').split()
    else:
        vmsList = vms
    if not vmsList:
        raise ValueError("vms cannot be empty")

    if str(stop).lower() == 'true':
        stop_vms(vmsList)

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
        names = names.replace(',', ' ').split()
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


@ll_general.generate_logs()
def changeVMStatus(positive, vm, action, expectedStatus, async='true'):
    """
    Change vm status

    Args:
        positive (bool): indicates positive/negative test's flow
        vm (str): name of vm
        action (str): action that should be run on vm -
            (start/stop/suspend/shutdown/detach)
        expectedStatus (str): status of vm in case the action succeeded
        async (str): don't wait for VM status if 'true' ('false' by default)

    Returns:
        bool: True if vm status is changed properly, False otherwise
    """
    vm_object = get_vm(vm=vm)
    async_mode = async.lower() == 'true'
    status = bool(VM_API.syncAction(vm_object, action, positive, async=async))
    if status and positive and not async_mode:
        return VM_API.waitForElemStatus(
            vm_object, expectedStatus, VM_ACTION_TIMEOUT,
            ignoreFinalStates=True
        )
    return status


@ll_general.generate_logs(step=True)
def restartVm(
    vm, wait_for_ip=False, timeout=VM_ACTION_TIMEOUT, async='false',
    wait_for_status=ENUMS['vm_state_up'], placement_host=None
):
    """
    Restart vm

    Args:
        vm (str): Name of vm
        wait_for_ip (bool): True/False wait for ip
        timeout (int): Timeout of wait for vm
        async (str): Stop VM asynchronously if 'true' ('false' by default)
        wait_for_status (str): Status which should have vm after starting it
        placement_host (str): host where the vm should be started

    Returns:
        bool: True if vm restarted successfully, False otherwise
    """
    if not checkVmState(True, vm, ENUMS['vm_state_down']):
        if not stopVm(True, vm, async=async):
            return False
    return startVm(
        True, vm, wait_for_status=wait_for_status, wait_for_ip=wait_for_ip,
        timeout=timeout, placement_host=placement_host
    )


@ll_general.generate_logs(step=True)
def startVm(
    positive, vm, wait_for_status=ENUMS['vm_state_powering_up'],
    wait_for_ip=False, timeout=VM_ACTION_TIMEOUT, placement_host=None,
    use_cloud_init=False, pause=False, **kwargs
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
    if pause:
        wait_for_status = ENUMS['vm_state_paused']
        action_params["pause"] = pause
    action_params.update(kwargs)
    log_info, log_error = ll_general.get_log_msg(
        log_action="start", obj_type=VM, obj_name=vm, positive=positive,
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
        started = wait_for_vm_ip(vm)[0]
        if started != positive:
            VM_API.logger.error(
                "wait_for_vm_ip returned %s, positive is set to %s",
                started, positive
            )

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
        vms = vms.replace(',', ' ').split()
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


@ll_general.generate_logs(step=True)
def stopVm(positive, vm, async='false'):
    """
    Stop vm

    Args:
        positive (bool): Expected status
        vm (str): Name of vm
        async (str): Stop VM asynchronously if 'true' ('false' by default)

    Returns:
        bool: True if vm was stopped properly, False otherwise
    """
    return changeVMStatus(positive, vm, 'stop', 'DOWN', async)


@ll_general.generate_logs(step=True)
def stop_vms(vms, async='true'):
    """
    Stop vms

    Args:
        vms (list or str): list of vm names OR
            string of VM names comma separated, to be stopped
        async (str): stop VMs asynchronously ('true' by default)

    Returns:
        bool: True if all VMs were stopped properly, False otherwise
    """
    if isinstance(vms, basestring):
        vms = vms.replace(',', ' ').split()
    results = list()
    for vm in vms:
        results.append(stopVm(positive=True, vm=vm, async=async))

    return all(results)


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
        log_action="detach", obj_type=VM, obj_name=vm, positive=positive
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

    disk_attachments = VM_API.getElemFromLink(
        vm_obj, link_name='diskattachments', attr='disk_attachment',
        get_href=False
    )
    disks = get_disk_list_from_disk_attachments(disk_attachments)
    disks.sort(key=lambda disk: disk.get_alias())
    return disks


def get_storage_domain_disks(storage_domain):
    """
    Returns a list of the storage domain's disks formatted as data structured
    objects

    Args:
        storage_domain (str): name of the storage domain which the disks will
            be retrieved

    Returns:
        list : list of disks objects under the storage domain or None if
        storage_domain does not exist
    """
    # Local import to prevent import recursion loop
    from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd

    try:
        storage_domain_obj = ll_sd.get_storage_domain_obj(
            storage_domain
        )
        storage_domain_disks_objects = ll_sd.getObjList(
            storage_domain_obj, 'disks'
        )

    except EntityNotFound:
        storage_domain_disks_objects = list()

    return storage_domain_disks_objects


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
    # TODO: This function shouldn't contain pre-define values like format or
    # interface as helpers, because testing a negative case cannot be possible.
    # pre-define values should be used in other helper functions or generated
    # dictionaries. Remove the pre-define values and check all instances of
    # this function
    disk = data_st.Disk(provisioned_size=provisioned_size,
                        format=ENUMS['format_cow'],
                        sparse=True,
                        alias=kwargs.pop('alias', None),
                        description=kwargs.pop('description', None))

    log_info, log_error = ll_general.get_log_msg(
        log_action="Add", obj_type="disk", obj_name=disk, positive=positive,
        extra_txt="provisioned size: %d" % provisioned_size, **kwargs
    )
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

    interface = kwargs.pop('interface', ENUMS['interface_virtio'])
    bootable = kwargs.pop('bootable', None)
    active = kwargs.pop('active', True)
    # Report the unknown arguments that remains.
    if 0 < len(kwargs):
        E = "addDisk() got an unexpected keyword arguments %s"
        raise TypeError(E % kwargs)

    if storagedomain:
        sd = STORAGE_DOMAIN_API.find(storagedomain)
        diskSds = data_st.StorageDomains()
        diskSds.add_storage_domain(sd)
        disk.set_storage_domains(diskSds)

    disk_attachment_obj = prepare_disk_attachment_object(
        interface=interface, bootable=bootable, disk=disk, active=active
    )

    disks = get_disk_attachments(vm, get_href=True)
    logger.info(log_info)
    new_disk, status = DISK_ATTACHMENTS_API.create(
        disk_attachment_obj, positive, collection=disks
    )
    if status and positive and wait:
        disk = DISKS_API.find(new_disk.get_id(), attribute='id')
        return DISKS_API.waitForElemStatus(disk, "OK", timeout)
    if not status:
        logger.error(log_error)
    return status


def removeDisk(positive, vm, disk=None, wait=True, disk_id=None):
    """
    Removes a disk from the system (that is attached to a vm)

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
    :return: True if disk was detached and removed successfully,
    False otherwise
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
        log_info, log_error = ll_general.get_log_msg(
            log_action="Remove", obj_type="disk", obj_name=disk,
            positive=positive, extra_txt="disk id %s" % disk_obj.get_id()
        )
        logger.info(log_info)
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
    if not status:
        logger.error(log_error)
    return status


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
    """
    Prepare Nic object

    Keyword Args:
        name (str): NIC name
        network (str): Network name
        vnic_profile (str): The VNIC profile that will be selected for the NIC
        interface (str): NIC type. (virtio, rtl8139, e1000 and passthrough)
        mac_address (str): NIC mac address
        plugged (bool): Add the NIC with plugged/unplugged state
        linked (bool): Add the NIC with linked/unlinked state
        vm (str): VM name where nic should be added
        network_filter (dict): Network filter params, nf = {
            name: filter name,
            value: filter value
            }

    Returns:
        Nic: Nic object
    """
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

    if "network_filter" in kwargs:
        network_filter = kwargs.get("network_filter")
        network_filter_parameters = data_st.NetworkFilterParameters()
        network_filter_object = prepare_vnic_network_filter_parameters(
            name=network_filter.get("name"), value=network_filter.get("value")
        )
        network_filter_parameters.add_network_filter_parameter(
            network_filter_object
        )
        nic_obj.set_network_filter_parameters(network_filter_parameters)

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

    Raises:
        EntityNotFound: If VM NIC object not found

    """
    vm_obj = VM_API.find(vm)
    logger.info("Get %s vNIC object from %s", nic, vm)
    return VM_API.getElemFromElemColl(vm_obj, nic, 'nics', 'nic')


@ll_general.generate_logs(step=True)
def addNic(positive, vm, **kwargs):
    """
    Add vNIC name to VM

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
        network_filter (dict): Network filter params, nf = {
            name: filter name,
            value: filter value
            }

    Returns:
        bool: True if NIC was added properly, False otherwise
    """
    vm_obj = VM_API.find(vm)
    expected_status = vm_obj.get_status()

    nic_obj = _prepareNicObj(vm=vm, **kwargs)
    nics_coll = get_vm_nics(vm)
    res, status = NIC_API.create(nic_obj, positive, collection=nics_coll)
    if not status:
        return False

    # TODO: remove wait section. func need to be atomic. wait can be done
    # externally!
    if positive and status:
        return VM_API.waitForElemStatus(
            vm_obj, expected_status, VM_ACTION_TIMEOUT
        )
    return status


@ll_general.generate_logs(step=True)
def updateNic(positive, vm, nic, **kwargs):  # noqa: N802
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
        interface (str): NIC type. (virtio, rtl8139, e1000 and pci_passthrough)
        mac_address (str): NIC mac address
        plugged (bool): Update the NIC with plugged/unplugged state
        linked (bool): Update the NIC with linked/unlinked state

    Returns:
        bool: status (True if NIC was updated properly, False otherwise)
    """
    nic_new = _prepareNicObj(vm=vm, **kwargs)
    nic_obj = get_vm_nic(vm, nic)
    return NIC_API.update(nic_obj, nic_new, positive)[1]


@ll_general.generate_logs(step=True)
def removeNic(positive, vm, nic):  # noqa: N802
    """
    Remove nic from VM

    Args:
        positive (bool): Expected status
        vm (str): VM where nic should be removed from
        nic (str): NIC name that should be removed

    Returns:
        bool: True if nic was removed properly, False otherwise
    """
    vm_obj = VM_API.find(vm)
    nic_obj = get_vm_nic(vm, nic)
    expected_status = vm_obj.get_status()

    status = NIC_API.delete(nic_obj, positive)
    if not status:
        return False

    # TODO: remove wait section. func need to be atomic. wait can be done
    # externally!
    if positive and status:
        return VM_API.waitForElemStatus(
            vm_obj, expected_status, VM_ACTION_TIMEOUT
        )
    return status


def remove_locked_vm(vm_name, engine):
    """
    Remove locked vm with flag force=true
    Make sure that vm no longer exists, otherwise set it's status to down,
    and remove it
    Author: jvorcak

    Args:
        vm_name (str): VM name to remove
        engine (Engine): engine - instance of resources.Engine

    Returns:
        bool: True if VM was removed properly, False otherwise
    """

    if removeVm(positive=True, vm=vm_name, force='true'):
        return True

    # clean if vm has not been removed
    logger.error('Locked vm has not been removed with force flag')

    if update_vm_status_in_database(vm_name=vm_name, status=0, engine=engine):
        return removeVm(positive=True, vm=vm_name)
    else:
        logger.error('Could not update locked VM status')
        return False


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


@ll_general.generate_logs(step=True)
def addSnapshot(
    positive, vm, description, wait=True, persist_memory=None, disks_lst=None
):
    """
    Add snapshot to VM

    __author__ = "ratamir"

    Args:
        positive (bool): True if operation should succeed, False otherwise
        vm (str): Name of the VM for which a snapshot will be created
        description (str): Snapshot name
        wait (bool): Specifies whether to wait until the snapshot operation
                     has been completed waiting when False
        persist_memory (bool): True when memory state should be saved with the
                              snapshot, False when the memory state
                              doesn't need to be saved with the snapshot.
                              The default is False
        disks_lst (list): If not None, this list of disks names will be
                          included in snapshot's disks (Single disk snapshot)

    Returns:
         bool: True if snapshot was added properly, False otherwise
    """

    snapshot = data_st.Snapshot()
    snapshot.set_description(description)
    snapshot.set_persist_memorystate(persist_memory)

    if disks_lst:
        disks_coll = data_st.DiskAttachments()
        for disk in disks_lst:

            diskObj = get_disk_obj(disk)
            disk = data_st.DiskAttachment()
            disk.set_id(diskObj.get_id())
            disk.set_disk(data_st.Disk(id=diskObj.get_id()))

            disks_coll.add_disk_attachment(disk)

        snapshot.set_disk_attachments(disks_coll)

    vmSnapshots = _getVmSnapshots(vm)

    snapshot, status = SNAPSHOT_API.create(snapshot, positive,
                                           collection=vmSnapshots,
                                           compare=wait)

    if wait:
        wait_for_jobs([ENUMS['job_create_snapshot']])

    try:
        snapshot = _getVmSnapshot(vm, description)
    except EntityNotFound:
        return positive is False

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


@ll_general.generate_logs(step=True)
def runVmOnce(
    positive, vm, wait_for_state=ENUMS['vm_state_powering_up_or_up'],
    pause=False, use_cloud_init=False, use_sysprep=False, **kwargs
):
    """
    Run VM once

    Args:
        positive (bool): True if test is positive (VM needs to start), or False
            if negative (VM doesn't need to start)
        vm (str): VM name to run
        wait_for_state (str): Wait for specific VM state after run
        pause (bool): True to start VM in 'pause' state
        use_cloud_init (bool): True to use cloud, False otherwise
        use_sysprep (bool): True to use Sysprep, False otherwise

    Keyword arguments:
        display_type (str): Display type of vm
        kernel (str): Kernel path
        initrd (str): Initrd path
        cmdline (str): Kernel parameters
        stateless (bool): True if VM should be stateless
        cdrom_image (str): CD-ROM image to attach
        floppy_image (str): Floppy image to attach
        boot_dev (str): Boot vm from device
        host (str): Host name to run the VM on
        domainName (str): VM domain
        user_name (str): Domain user name
        password (str): Domain user password
        initialization (Initialization): Initialization obj for cloud init
        custom_cpu_model (str): Name of custom cpu model to start vm with
        custom_emulated_machine (str): Name of custom emulated machine type to
            start vm with


    Returns
        bool: True, if positive and action succeed or negative and action
        failed, otherwise False
    """
    vm_obj = get_vm(vm=vm)
    action_params = {}
    vm_for_action = data_st.Vm()
    display_type = kwargs.get("display_type")
    if display_type:
        vm_for_action.set_display(data_st.Display(type_=display_type))
    stateless = kwargs.get("stateless")
    if stateless is not None:
        vm_for_action.set_stateless(stateless)
    initialization = kwargs.get("initialization")
    if initialization:
        vm_for_action.set_initialization(initialization)
    cdrom_image = kwargs.get("cdrom_image")
    if cdrom_image:
        cdrom = data_st.Cdrom()
        vm_cdroms = data_st.Cdroms()
        cdrom.set_file(data_st.File(id=cdrom_image))
        vm_cdroms.add_cdrom(cdrom)
        vm_for_action.set_cdroms(vm_cdroms)
    floppy_image = kwargs.get("floppy_image")
    if floppy_image:
        floppy = data_st.Floppy()
        floppies = data_st.Floppies()
        floppy.set_file(data_st.File(id=floppy_image))
        floppies.add_floppy(floppy)
        vm_for_action.set_floppies(floppies)

    os_type = data_st.OperatingSystem()
    boot_dev = kwargs.get("boot_dev")
    if boot_dev:
        os_type.set_boot(
            boot=data_st.Boot(
                devices=data_st.devicesType(
                    device=boot_dev.split(",")
                )
            )
        )

    for opt_name in "kernel", "initrd", "cmdline":
        opt_val = kwargs.pop(opt_name, None)
        if opt_val is not None:
            setattr(os_type, opt_name, opt_val)
    vm_for_action.set_os(os_type)
    host = kwargs.get("host")
    if host:
        vm_policy = data_st.VmPlacementPolicy()
        vm_hosts = data_st.Hosts()
        vm_hosts.add_host(HOST_API.find(host))
        vm_policy.set_hosts(vm_hosts)
        vm_for_action.set_placement_policy(vm_policy)

    custom_cpu_model = kwargs.get("custom_cpu_model")
    if custom_cpu_model is not None:
        vm_for_action.set_custom_cpu_model(custom_cpu_model)

    custom_emulated_machine = kwargs.get("custom_emulated_machine")
    if custom_emulated_machine is not None:
        vm_for_action.set_custom_emulated_machine(custom_emulated_machine)

    action_params["vm"] = vm_for_action
    action_params['use_sysprep'] = use_sysprep
    action_params['use_cloud_init'] = use_cloud_init
    if pause:
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


@ll_general.generate_logs(step=True)
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
        log_action="suspend", obj_type="vm", obj_name=vm, positive=positive,
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


@ll_general.generate_logs(step=True)
def migrateVm(
        positive,
        vm,
        host=None,
        wait=True,
        force=False,
        timeout=MIGRATION_TIMEOUT,
        wait_for_status='up'
):
    """
    Migrate the VM.

    If the host was specified, after the migrate action was performed,
    the method is checking whether the VM status is as expected and whether
    the VM runs on required destination host.

    If the host was not specified, after the migrate action was performed, the
    method is checking whether the VM is UP and whether the VM runs
    on host different to the source host.


    Args:
        positive(bool): Expected result
        vm(str): name of vm
        host(str): Name of the destination host to migrate VM on, or
         None for RHEVM destination host autodetect.
        wait(bool): When True wait until end of action, False return without
         waiting.
        wait_for_status(str): VM status after migrate done. (up, paused)
        force(bool): Force action
        timeout(int): Timeout to check if vm is update after migration is done

    Returns:
         True if vm was migrated and test is positive, False otherwise.
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
        log_action="Migrate", obj_type=VM, obj_name=vm, positive=positive,
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
    if not VM_API.waitForElemStatus(vm_obj, wait_for_status, timeout):
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
        VM_API.syncAction(
            vm_obj, "export", positive, async=async, **action_params
        )
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
        'async': async,
        'operations': [],
    }

    action_name = 'import'

    new_vm = data_st.Vm()
    if name:
        new_vm.set_name(name)
        clone = True
        expected_name = name

    if clone:
        action_params['clone'] = True
        collapse = True

    if collapse:
        action_params['operations'].append('collapse_snapshots')
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


def _createVmForClone(
    name, template=None, cluster=None, vol_sparse=None,
    vol_format=None, storagedomain=None, snapshot=None, vm_name=None,
    interface=ENUMS['interface_virtio'], bootable='True', **kwargs
):
    """
    Description: helper function - creates VM objects for VM_API.create call
                 when VM is created from template, sets all required attributes
    Author: kjachim
    Parameters:
       * template - template name
       * name - vm name
       * cluster - cluster name
       * vol_sparse - true/false - convert VM disk to sparse/preallocated
       * vol_format - COW/RAW - convert VM disk format
       * storagedomain - storage domain to clone the VM disk
       * snapshot - description of the snapshot to clone
       * vm_name - name of the snapshot's vm
       * interface - disk interface
       * bootable - if disk should be bootable
    Returns: VM object
    """
    # TODO: Probaly better split this since the disk parameter is not that
    # similar for template and snapshots
    # Create the vm object
    vm = _prepare_vm_object(name=name, cluster=cluster, **kwargs)
    if template:
        templObj = TEMPLATE_API.find(template)
        vm.set_template(templObj)
        disks = get_disk_attachments(name=template, object_type='template')
    elif snapshot and vm_name:
        # better pass both elements and don't search in all vms
        snapshotObj = _getVmSnapshot(vm_name, snapshot)
        snapshots = Snapshots()
        snapshots.add_snapshot(snapshotObj)
        vm.set_snapshots(snapshots)
        disks_from = snapshotObj
        disks = DISKS_API.getElemFromLink(
            disks_from, link_name='disks', attr='disk',
            get_href=False
        )
    else:
        raise ValueError("Either template or snapshot and vm parameters "
                         "must be set")

    diskArray = data_st.Disks()
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
            disk_obj = get_disk_obj(dsk.get_id(), attribute='id')
            for elem in disk_obj.get_storage_domains().get_storage_domain():
                sd.append(
                    STORAGE_DOMAIN_API.find(
                        elem.get_id(), attribute="id")
                )
        for elem in sd:
            storage_domains.add_storage_domain(elem)
        disk.storage_domains = storage_domains
        diskArray.add_disk(disk)

    disk_attachments = data_st.DiskAttachments()

    for _disk in diskArray.get_disk():
        disk_attachments.add_disk_attachment(
            prepare_disk_attachment_object(
                _disk.get_id(),
                interface=interface,
                bootable=bootable,
                disk=_disk,
            )
        )
    vm.set_disk_attachments(disk_attachments)

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
       * clone - True/False - if True, template disk will be copied
       * vol_sparse - True/False - convert VM disk to sparse/preallocated
       * vol_format - COW/RAW - convert VM disk format
    Return: status (True if vm was cloned properly, False otherwise)
    '''
    expectedVm = _createVmForClone(name, template, cluster, vol_sparse,
                                   vol_format, storagedomain,
                                   **kwargs)
    newVm = _createVmForClone(name, template, cluster, vol_sparse,
                              vol_format, storagedomain,
                              **kwargs)
    operations = []
    if clone:
        operations = ['clone=true']
        expectedVm.set_template(data_st.Template(id=BLANK_TEMPLATE))
    vm, status = VM_API.create(
        newVm, positive, expected_entity=expectedVm, async=(not wait),
        compare=wait, operations=operations
    )
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
    expectedVm = _createVmForClone(
        name, cluster=cluster, vol_sparse=sparse,
        vol_format=vol_format, storagedomain=storagedomain, snapshot=snapshot,
        vm_name=vm, **kwargs)
    newVm = _createVmForClone(
        name, cluster=cluster, vol_sparse=sparse,
        vol_format=vol_format, storagedomain=storagedomain, snapshot=snapshot,
        vm_name=vm, **kwargs)

    operations = ['clone=true']
    expectedVm.set_snapshots(None)
    expectedVm.set_template(data_st.Template(id=BLANK_TEMPLATE))
    logger.info("Cloning vm %s from snapshot %s", name, snapshot)
    vm, status = VM_API.create(newVm, positive, expected_entity=expectedVm,
                               compare=compare, operations=operations)
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
    initialization=None, cpu_shares=None, serial_number=None,
    max_memory=None, lease=None, **kwargs
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
    :param max_memory: Upper bound for the memory hotplug
    :type max_memory: int
    :param lease: Storage domain name for the lease or '' to remove the
        lease
    :type lease: str
    :param kwargs: additional params supported by addVm method.
    :type kwargs: dict
    :returns: True, if create vm success, otherwise False
    :rtype: bool
    """
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
        serial_number=serial_number, placement_hosts=placement_hosts,
        max_memory=max_memory, **kwargs
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
        logger.warning("Installation OS is not supported at the moment")
    else:
        if start.lower() == "true":
            return startVm(positive, vmName)

        return True


def wait_for_vm_ip(
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
    vm_host = get_vm_host(vm_name=vm)
    if not vm_host:
        logger.error("VM %s is not running", vm)
        return False, {'ip': None}

    host_ip = ll_hosts.get_host_ip_from_engine(host=vm_host)
    vds_resource = resources.VDS(ip=host_ip, root_password=vm_password)

    def _get_ip(vm, vds_resource):
        """
        Get VM IP using vdsClient command on VDSM

        Args:
            vm (str): VM name
            vds_resource (VDS): VDSM resource

        Returns:
            str or list: IP or list of IPs depend on get_all_ips param
        """
        vms_info = vds_resource.vds_client(cmd="Host.getVMFullList")
        vm_id = [i.get("vmId") for i in vms_info if i.get("vmName") == vm]
        if not vm_id:
            logger.error("No VMs found in host %s", vds_resource)
            return ""

        vm_ips = list()
        vm_info = vds_resource.vds_client(
            cmd="VM.getStats", args={"vmID": vm_id[0]}
        )
        if not vm_info:
            logger.error("VDS didn't return getStats for VM %s", vm_id)
            return ""

        vm_info = vm_info[0]
        vm_name = vm_info.get("vmName")
        if vm_name == vm:
            vm_interfaces = vm_info.get("netIfaces")
            if not vm_interfaces:
                logger.error("No interfaces found for VM %s", vm_name)
                return ""

            for vm_interface in vm_interfaces:
                vm_ips.extend(vm_interface.get("inet"))

        if not vm_ips:
            logger.error("No IP was found for VM %s", vm)
            return ""

        if get_all_ips:
            return vm_ips

        vm_ip = None
        for ip_ in vm_ips:
            logger.info("Send ICMP to %s", ip_)
            if vds_resource.network.send_icmp(dst=ip_):
                vm_ip = ip_
                break

        return vm_ip

    logger.info("Waiting for IP from %s", vm)
    try:
        for ip in TimeoutingSampler(
            timeout, sleep, _get_ip, vm, vds_resource
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
    logger.info(
        "Activating disk %s of VM %s", diskAlias if diskAlias else diskId, vm)
    return changeVmDiskState(
        positive, vm, 'activate', diskAlias, diskId, wait
    )


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
    logger.info(
        "Deactivating disk %s of VM %s",
        diskAlias if diskAlias else diskId, vm
    )
    return changeVmDiskState(
        positive, vm, 'deactivate', diskAlias, diskId, wait
    )


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

    active = True if action == 'activate' else False
    status = updateDisk(
        positive, id=disk.get_id(), vmName=vm, active=active
    )
    if status and wait:
        if positive:
            # always use disk.id
            return wait_for_vm_disk_active_status(
                vm, active, diskId=disk.get_id(), timeout=300) == positive
        else:
            # only wait for the disk to be again in 'ok' state
            return DISKS_API.waitForElemStatus(disk, 'ok', 300)
    return status


def wait_for_vm_disk_active_status(
    vm, active, diskAlias=None, diskId=None, timeout=VM_ACTION_TIMEOUT,
    sleep=DEF_SLEEP
):
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
    if diskAlias:
        disk = diskAlias
        attr = 'name'
    elif diskId:
        disk = diskId
        attr = 'id'
    else:
        VM_API.logger.error("Disk must be specified either by alias or ID")
        return False

    def check_active_status():
        disk_attachment_obj = get_disk_attachment(vm, disk, attr=attr)
        return disk_attachment_obj.get_active() == active

    sampler = TimeoutingSampler(timeout, sleep, check_active_status)
    return sampler.waitForFuncStatus(result=True)


def check_vm_connectivity(vm, interval=1, password=None, timeout=1800):
    """
    Check VM Connectivity

    Args:
        vm (str): vm name
        interval (int):  interval between attempts
        password (str): Password for Username
        timeout (int): timeout to wait for IP

    Returns:
        bool: True if succeed to connect to VM, False otherwise).
    """
    ip = wait_for_vm_ip(vm=vm, timeout=timeout)[1].get("ip")
    if not ip:
        return False

    vds_resource = resources.VDS(ip=ip, root_password=password)
    return vds_resource.executor().wait_for_connectivity_state(
        positive=True, timeout=timeout, sample_time=interval
    )


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
        log_action="Get", obj_type="NIC", obj_name=nic, positive=positive,
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
        log_action="Get", obj_type="NIC", obj_name=nic, positive=positive,
        extra_txt="link state"
    )
    nic_obj = get_vm_nic(vm, nic)
    logger.info(log_info)
    res = nic_obj.get_linked()
    if res != positive:
        logger.error(log_error)
        return False
    return True


@ll_general.generate_logs()
def check_vm_nic_profile(vm, vnic_profile_name="", nic='nic1'):
    """
    Check if VNIC profile vnic_profile_name exist on the given VNIC on VM.

    To check if vNIC have empty profile send vnic_profile_name=""

    Args:
        vm (str): VM name
        vnic_profile_name (str): Name of the vnic_profile to test
        nic (str): vNIC name

    Returns:
        bool: True if vnic_profile_name exists on vNIC, False otherwise
    """

    nic_obj = get_vm_nic(vm=vm, nic=nic)
    if not vnic_profile_name:
        return not bool(nic_obj.get_vnic_profile())

    all_profiles = VNIC_PROFILE_API.get(abs_link=False)
    for profile in all_profiles:
        if profile.get_name() == vnic_profile_name:
            return profile.get_id() == nic_obj.get_vnic_profile().get_id()
    return False


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
    disks = get_disk_list_from_disk_attachments(get_disk_attachments(vm))

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


@ll_general.generate_logs()
def remove_vm_from_export_domain(
    positive, vm, datacenter, export_storagedomain, timeout=SAMPLER_TIMEOUT,
    sleep=SAMPLER_SLEEP
):
    """
    Remove VM from export_storagedomain

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
    export_storage_domain_obj = STORAGE_DOMAIN_API.find(export_storagedomain)
    vm_obj = VM_API.getElemFromElemColl(export_storage_domain_obj, vm)
    status = VM_API.delete(vm_obj, positive)
    if not status:
        return False

    sample = TimeoutingSampler(
        timeout=timeout, sleep=sleep, func=is_vm_exists_in_export_domain,
        vm=vm, export_domain=export_storagedomain, positive=False
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
    def all_disks_status():
        disks = [
            d for d in getVmDisks(vm) if
            d.get_storage_type() != ENUMS['storage_type_lun']
        ]
        return all([d.get_status() == disks_status for d in disks])
    sampler = TimeoutingSampler(timeout, sleep, all_disks_status)
    return sampler.waitForFuncStatus(result=True)


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


def move_vm_disk(
    vm_name, disk_name, target_sd, wait=True, timeout=VM_IMAGE_OPT_TIMEOUT,
    sleep=DEF_SLEEP, verify_no_snapshot_operation_occur=False
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
    :param verify_no_snapshot_operation_occur: True if wait for all the
        VM snapshots to be in 'ok' state, False otherwise
    :type verify_no_snapshot_operation_occur: bool
    :raises: DiskException if syncAction returns False (syncAction should raise
            exception itself instead of returning False)
    """
    source_domain = get_disk_storage_domain_name(disk_name, vm_name)

    logger.info(
        "Moving disk %s attached to vm %s from storage domain %s to storage "
        "domain %s",
        disk_name, vm_name, source_domain, target_sd
    )
    sd = STORAGE_DOMAIN_API.find(target_sd)
    disk = getVmDisk(vm_name, disk_name)

    # in case of live migrating multiple disks at the same time, a removal of
    # auto-generated snapshot of previous disk can occur
    if verify_no_snapshot_operation_occur:
        wait_for_vm_snapshots(vm_name, SNAPSHOT_STATE_OK)

    if not DISKS_API.syncAction(
        disk, 'move', storage_domain=sd, positive=True
    ):
        raise exceptions.DiskException(
            "Failed to move disk %s attached to vm %s from storage domain "
            "%s to storage domain %s" %
            (disk_name, vm_name, source_domain, target_sd)
        )
    if wait:
        wait_for_vm_disk_active_status(
            vm_name, True, disk_name, timeout=timeout, sleep=sleep
        )


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
    log_dest = os.path.join(
        ART_CONFIG['PARAMETERS']['logdir'],
        '{0}-messages.log'.format(vm_name)
    )

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
    logger.info("Previewing vm's %s snapshot '%s'", vm, description)
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
    logger.info("Undoing snapshot preview of vm %s", vm)
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
        return VM_API.waitForElemStatus(
            vmObj, ENUMS['vm_state_down'], VM_SNAPSHOT_ACTION
        )
    return status or not positive


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
    status, vm_ip = wait_for_vm_ip(vm_name)
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
    vm_ip = wait_for_vm_ip(vm_name)[1]['ip']
    rc, out = runMachineCommand(
        True, ip=vm_ip, user=user, password=password, cmd=cmd, timeout=timeout)
    logger.debug("cmd output: %s, exit code: %s", out, rc)
    return rc, out


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


def wait_for_snapshot_creation(
    vm_name, snapshot_description, timeout=VM_IMAGE_OPT_TIMEOUT,
    sleep=SNAPSHOT_SAMPLING_PERIOD, wait_for_status=None,
    include_disk_alias=None
):
    """
    Wait until snapshot creation initiated

    Args:
        vm_name(str): Name of the VM
        snapshot_description(str): Name of the VM
        timeout(int): Timeout for waiting
        sleep(float): Polling interval while waiting
        wait_for_status(str): Desired snapshot state
        include_disk_alias (str): Alias of the disk that should be include on
            the snapshot disks

    Returns:
        bool: True if snapshot has been created, False otherwise
    """
    logger.info(
        "Waiting until snapshot: %s of VM %s creation will start",
        snapshot_description, vm_name
    )
    sampler = TimeoutingSampler(timeout, sleep, get_vm_snapshots, vm_name)
    for sample in sampler:
        for snapshot in sample:
            if snapshot.get_description() == snapshot_description:
                #  check if snapshot contain the disk alias
                if include_disk_alias:
                    disks = get_snapshot_disks_by_snapshot_obj(
                        snapshot=snapshot
                    )
                    for disk in disks:
                        if include_disk_alias == disk.get_alias():
                            if wait_for_status:
                                wait_for_vm_snapshots(
                                    vm_name=vm_name, states=wait_for_status,
                                    snapshots_description=snapshot_description
                                )
                            return True
                    continue

                if wait_for_status:
                    wait_for_vm_snapshots(
                        vm_name=vm_name, states=wait_for_status,
                        snapshots_description=snapshot_description
                    )
                return True
    return False


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
    restored_vm_obj = _prepare_vm_object(
        name=new_vm_name, cluster=cluster_name, initialization=ovf
    )
    logger.debug("Restoring vm %s from ovf file %s", new_vm_name, ovf)
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
            logger.warning("Vm %s does not exist under engine", vm)
    for vm in vms_action_stop:
        if not waitForVMState(vm, ENUMS['vm_state_down']):
            vms_stop_failed.add(vm)

    if vms_stop_failed:
        logger.error("Failed to stop VMs '%s'", ', '.join(vms_stop_failed))
        return False
    return True


def attach_snapshot_disk_to_vm(
    disk_obj, vm_name, async=False, activate=True,
    interface=ENUMS['interface_virtio']
):
    """
    Attaching a snapshot disk to a vm
    Author: ratamir
    Parameters:
        * disk_obj - disk object to attach
        * vm_name - name of the vm that the disk should be attached to
        * async - True if operation should be async
        * activate - True if the disk should be activated after attachment
        * interface - Interface to attach the disk to the vm

    Return:
        True if operation succeeded, False otherwise
    """
    new_disk_obj = _prepareDiskObject(
        id=disk_obj.get_id(), snapshot=disk_obj.get_snapshot()
    )
    new_disk_attachment_obj = prepare_disk_attachment_object(
        id=disk_obj.get_id(), interface=interface, active=activate,
        disk=new_disk_obj,
    )
    vmDisks = getObjDisks(vm_name)
    diskObj, status = DISK_ATTACHMENTS_API.create(
        new_disk_attachment_obj, True, collection=vmDisks, async=async
    )
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
        status = attach_snapshot_disk_to_vm(
            disk_obj, backup_vm, async=async, activate=activate
        )

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


def prepare_watchdog_obj(**kwargs):
    """
    Prepare watchdog object for future use

    Keyword Args:
        model (str): Watchdog card model
        action (str): Watchdog action

    Returns:
        WatchDog: New WatchDog instance
    """
    return ll_general.prepare_ds_object("Watchdog", **kwargs)


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
        log_action="Add",
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
        log_action="Update",
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
        log_action="Delete",
        obj_type="watchdog",
        obj_name=watchdog_obj.get_model(),
        extra_txt="from VM %s" % vm_name
    )
    logger.info(log_info)
    status = WATCHDOG_API.delete(watchdog_obj, True)
    if not status:
        logger.error(log_error)
    return status


def reboot_vms(vms):
    """
    Atomic Reboot vms (stop && start)

    :param vms: list of vms
    :return: False if vms failed to start
    :rtype: bool
    """
    stop_vms_safely(vms)
    return startVms(vms)


def extend_vm_disk_size(positive, vm, disk, provisioned_size):
    """
    Description: extend already existing vm disk
    Parameters:
      * vm - vm where disk should be updated
      * disk - disk name that should be updated
      * provisioned_size - new disk size in bytes
    Author: ratamir
    Return: Status of the operation's result dependent on positive value
    """
    return updateDisk(
        positive, vmName=vm, alias=disk, provisioned_size=provisioned_size
    )


def migrate_vm_disk(
    vm_name, disk_name, target_sd, timeout=VM_IMAGE_OPT_TIMEOUT*2,
    sleep=SNAPSHOT_SAMPLING_PERIOD, wait=True,
    verify_no_snapshot_operation_occur=False
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
    :param verify_no_snapshot_operation_occur: True if wait for all the
        VM snapshots to be in 'ok' state, False otherwise
    :type verify_no_snapshot_operation_occur: bool
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
    move_vm_disk(
        vm_name, disk_name, target_sd, timeout=timeout, wait=wait,
        verify_no_snapshot_operation_occur=verify_no_snapshot_operation_occur
    )
    if wait:
        sampler = TimeoutingSampler(
            timeout, sleep, _wait_for_new_storage_domain, vm_name, disk_name,
            target_sd
        )
        for sample in sampler:
            if sample:
                break
        wait_for_disks_status([disk_name], timeout=timeout)
        wait_for_jobs([ENUMS['job_live_migrate_disk']])
        # Wait for live merge after LSM
        wait_for_jobs([ENUMS['job_remove_snapshot']])
        wait_for_vm_snapshots(vm_name, ENUMS['snapshot_state_ok'])


def migrate_vm_disks(
    vm_name, timeout=VM_IMAGE_OPT_TIMEOUT*2, wait=True, ensure_on=True,
    same_type=True, target_domain=None
):
    """
    Migrate all VM's disks

    __author__ = "ratamir"

    Args:
        vm_name (str): Name of the VM
        timeout (int): Specify how long before an exception should be
        raised (in seconds)
        wait (bool): Specifies whether to wait until migration has completed
        ensure_on (bool): Specify whether VM should be up before live storage
        migration begins
        same_type (bool): If True, return only a storage domain of the same
        type, False will result in a different domain type returned
        target_domain (str): Name of the target domain to migrate, required
        param in case of specific domain requested

    Raises:
        DiskException: If failed to migrate disk
        APITimeout: If waiting for snapshot was longer than 1800 seconds
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
            logger.warning("Performing cold move for VM %s", vm_name)

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
        migrate_vm_disk(
            vm_name, disk_name, target_sd, timeout=timeout, wait=wait
        )
    if wait:
        wait_for_jobs([ENUMS['job_live_migrate_disk']])


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
    vm_ip = wait_for_vm_ip(vm_name)[1]['ip']
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


def get_vm_bootable_disk_object(vm):
    """
    Get bootable disk object of the VM

    Args:
        vm (str): VM name

    Returns:
        obj: bootable disk object of selected VM
    """

    vm_disks = getVmDisks(vm)
    boot_disk = [d for d in vm_disks if is_bootable_disk(vm, d.get_id())][0]

    return boot_disk


def get_vm_bootable_disk(vm):
    """
    Description: get bootable disk
    Author: ratamir
    Parameters:
      * vm - vm name
    Author: ratamir
    Return: name of the bootable disk or None if no boot disk exist
    """
    boot_disk_obj = get_vm_bootable_disk_object(vm)
    if boot_disk_obj:
        return boot_disk_obj.get_alias()
    return None


def get_vm_bootable_disk_id(vm):
    """
    Get bootable disk id

    Args:
        vm (str): vm name

    Returns:
        str: id of the bootable disk or None if no boot disk exist
    """
    boot_disk_obj = get_vm_bootable_disk_object(vm)
    if boot_disk_obj:
        return boot_disk_obj.get_id()
    return None


def get_vms_from_cluster(cluster):
    """
    Description: Gets all VM added to the given cluster

    Parameters:
        * cluster - cluster name
    """
    logging.info("Getting all vms in cluster %s", cluster)
    cluster_id = CLUSTER_API.find(cluster).get_id()
    all_vms = VM_API.get(abs_link=False)
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


@ll_general.generate_logs()
def get_vm(vm):
    """
    Get VM object

    Args:
        vm (str): VM name

    Returns:
        Vm: VM object

    Raises:
        EntityNotFound: If VM object not found
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
            return get_disk_attachment(vm_name, disk_id).get_logical_name()
        else:
            return get_disk_attachment(
                vm_name, disk_alias, attr='name'
            ).get_logical_name()

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


def get_vm_stateless_status(vm_name):
    """
    Get VM stateless status.

    Args:
        vm_name (str): VM name.

    Returns:
        bool: True if VM is stateless, otherwise - False.

    Raises:
        EntityNotFound: In case of non-existing VM name entered.
    """
    vm_obj = get_vm_obj(vm_name)
    return vm_obj.get_stateless()


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
                    "Numa node with index %s not found on host %s",
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


@ll_general.generate_logs(step=True)
def add_numa_node_to_vm(
    vm_name, host_name, index, memory, **kwargs
):
    """
    Add NUMA node to VM

    Args:
        vm_name (str): VM name
        host_name (str): Host name
        index (int): NUMA node index
        memory (int): NUMA node memory

    Keyword Args:
        cores (list): NUMA node cores
        pin_list (list): Pinning between VM numa node to the host NUMA node

    Returns:
        bool: True, if the creation succeeds, otherwise False
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
    return NUMA_NODE_API.create(
        entity=numa_node_obj, positive=True, collection=numa_nodes_link
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
        log_action="Remove",
        obj_type="numa node",
        obj_name=str(numa_node_index),
        extra_txt="from VM %s" % vm_name
    )
    logger.info(log_info)
    status = NUMA_NODE_API.delete(numa_node_obj, True)
    if not status:
        logger.error(log_error)
    return status


def is_vm_exists_in_export_domain(vm, export_domain, positive=True):
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
    res = VM_API.syncAction(vm_obj, "reordermacaddresses", True, async=True)
    if not res:
        logger.error("Failed to reorder MACs on VM %s", vm_name)
    return res


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


@ll_general.generate_logs(step=True)
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
        log_action="Add", obj_type="host device", obj_name=device_name,
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


@ll_general.generate_logs()
def remove_vm_host_device(vm_name, device_name):
    """
    Remove host device from VM

    Args:
        vm_name (str): VM name
        device_name (str): VM name

    Returns:
        bool: True, if remove host device succeed, otherwise False
    """
    host_device = get_vm_host_device_by_name(
        vm_name=vm_name, device_name=device_name
    )
    if not host_device:
        return False
    vm_host_device_col_href = get_vm_host_devices_link(vm_name=vm_name)
    new_host_device_obj = ll_general.prepare_ds_object(
        object_name="HostDevice",
        href="{0}/{1}".format(vm_host_device_col_href, host_device.get_id())
    )
    return HOST_DEVICE_API.delete(new_host_device_obj, True)


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
    return VM_API.get(abs_link=False)


def get_all_vms_names():
    """
    Get list of all VMs names from API

    Returns:
        list: all VMs names
    """
    return [vm.get_name() for vm in get_all_vms()]


def is_bootable_disk(vm, disk, attr='id'):
    """
    Gets the disk bootable flag

    :param vm: Name of vm
    :type : str
    :param disk: Disk name or ID
    :type : str
    :param attr: Attribute to identify the disk, 'id' or 'name'
    :type: str
    :return: True in case the disk is bootable, False otherwise
    :rtype: bool
    """
    return get_disk_attachment(vm, disk, attr).get_bootable()


def is_active_disk(vm, disk, attr='id'):
    """
    Gets the disk active flag

    :param vm: Name of vm
    :type : str
    :param disk: Disk name or ID
    :type : str
    :param attr: Attribute to identify the disk, 'id' or 'name'
    :type: str
    :return: True in case the disk is active, False otherwise
    :rtype: bool
    """
    return get_disk_attachment(vm, disk, attr).get_active()


def create_vms(vms_params, max_workers=None):
    """
    Create VM's simultaneously

    Args:
        vms_params (dict): VM's parameters to create
            {
                vm_name_1: {
                    cluster: ...,
                    vmDescription: ...,
                    nic: ...,
                    storageDomainName: ...,
                    provisioned_size: ...,
                    memory: ...,
                    template: ...,
                    ...
                },
                vm_name_2: {
                    ...
                }
            }
        max_workers (int): Number of threads to use

    Returns:
        bool: True, if succeed to create all VM's, otherwise False
    """
    max_workers = max_workers if max_workers else len(vms_params)
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for vm_name, vm_params in vms_params.iteritems():
            results.append(
                executor.submit(
                    fn=createVm, positive=True, vmName=vm_name, **vm_params
                )
            )
    for result in results:
        if result.exception() or not result.result():
            return False
    return True


def add_affinity_label(vm_name, affinity_label_name):
    """
    Add affinity label to the VM

    Args:
        vm_name (str): VM name
        affinity_label_name (str): Affinity label name

    Returns:
        bool: True, if add action succeed, otherwise False
    """
    from art.rhevm_api.tests_lib.low_level.affinitylabels import (
        add_affinity_label_to_element
    )
    vm_obj = get_vm_obj(vm_name=vm_name)
    return add_affinity_label_to_element(
        element_obj=vm_obj,
        element_api=VM_API,
        element_type="VM",
        affinity_label_name=affinity_label_name
    )


def remove_affinity_label(vm_name, affinity_label_name):
    """
    Remove affinity label from the VM

    Args:
        vm_name (str): VM name
        affinity_label_name (str): Affinity label name

    Returns:
        bool: True, if remove action succeed, otherwise False
    """
    from art.rhevm_api.tests_lib.low_level.affinitylabels import (
        remove_affinity_label_from_element
    )
    vm_obj = get_vm_obj(vm_name=vm_name)
    return remove_affinity_label_from_element(
        element_obj=vm_obj,
        element_api=VM_API,
        element_type="VM",
        affinity_label_name=affinity_label_name
    )


@ll_general.generate_logs()
def get_vms_objects_from_storage_domain(storage_domain_name):
    """
    Get list of vm objects in a given storage domain

    Args:
        storage_domain_name (str): Name of storage domain

    Returns:
        list: of vm objects in storage domain, empty list if no vms are found
    """
    from art.rhevm_api.tests_lib.low_level.storagedomains import (
        get_storage_domain_obj
    )
    try:
        storage_domain_object = get_storage_domain_obj(storage_domain_name)
    except EntityNotFound:
        return list()
    return VM_API.getElemFromLink(
        storage_domain_object, link_name='vms', attr='vm', get_href=False,
    )


def get_vms_from_storage_domain(storage_domain_name):
    """
    Get list of vms in a given storage domain

    Args:
        storage_domain_name (str): Name of storage domain

    Returns:
        list: of vm names in storage domain, empty list if no vms are found
    """
    storage_domain_vms = get_vms_objects_from_storage_domain(
        storage_domain_name
    )
    if storage_domain_vms:
        storage_domain_vms = [vm.get_name() for vm in storage_domain_vms]
        logger.info(
            "Vms found in storage domain: %s: %s",
            storage_domain_name, storage_domain_vms
        )
    return storage_domain_vms


@ll_general.generate_logs()
def get_vm_vnic_profile_obj(nic):
    """
    Get vm NIC vNIC profile object.

    Args:
        nic (object): Nic object.

    Returns:
        VnicProfile or None: VnicProfile object if found else None.
    """
    vnic_profile_obj = nic.get_vnic_profile()

    return None if not vnic_profile_obj else VNIC_PROFILE_API.find(
        val=vnic_profile_obj.get_id(), attribute='id'
    )


@ll_general.generate_logs()
def get_snapshot_description_in_preview(vm_name):
    """
    Get the description of the snapshot that is in preview

    Args:
        vm_name: Name of the vm

    Returns:
        str: description of the snapshot in preview, empty string ('') in case
        the vm is not in preview status
    """
    for snapshot in _getVmSnapshots(vm_name, get_href=False):
        if (
            snapshot.get_snapshot_status() ==
            ENUMS['snapshot_state_in_preview']
        ):
            return snapshot.get_description()
    return ''


@ll_general.generate_logs()
def get_vm_disks_ids(vm):
    """
    Returns disks ids for given vm

    Args:
        vm: vm name

    Returns:
        list: List of disk ids, if no disk found return empty list
    """
    disk_objs = getObjDisks(name=vm, get_href=False)
    if disk_objs:
        return [disk_obj.id for disk_obj in disk_objs]
    else:
        return []
    pass


def get_qcow_version_disks_snapshot(vm, snapshot):
    """
       Returns a list of qcow verion of each snapshot disk in a specific
       snapshot

       Args:
           vm (str): Name of the VM
           snapshot (str): Snapshot name/description

       Returns:
           list: List of qcow version of each snapshot disk in a specific
                snapshot
    """

    return [
        snapshot_disk.get_qcow_version() for snapshot_disk in
        get_snapshot_disks(vm, snapshot)
    ]


@ll_general.generate_logs(step=True)
def set_he_global_maintenance(vm_name, enabled):
    """
    Set hosted engine global maintenance

    Args:
        vm_name (str): Hosted engine VM name
        enabled (bool): Enable/Disable global maintenance

    Returns:
        bool: True, if the action succeeded, otherwise False
    """
    vm_obj = get_vm(vm=vm_name)
    return bool(
        VM_API.syncAction(
            entity=vm_obj,
            action="maintenance",
            positive=True,
            maintenance_enabled=enabled
        )
    )


def init_initialization_obj(params):
    """
    Returns Initialization object to set sysperp

    Args:
        params (dict): Dict with initialization parameters

    Returns:
        obj: Initialization obj
    """
    logger.info("Initialization params: %s", params)
    return data_st.Initialization(**params)


@ll_general.generate_logs(step=True)
def get_vnic_network_filter_parameters(vm, nic):
    """
    Get VM NIC network filter parameters

    Args:
        vm (str): VM name
        nic (str): NIC name

    Returns:
        list: List of NetworkFilterParameter objects
    """
    vm_nic = get_vm_nic(vm=vm, nic=nic)
    return NIC_API.getElemFromLink(
        elm=vm_nic, link_name=NETWORK_FILTER_PARAMETERS,
        attr=NETWORK_FILTER_PARAMETER
    )


@ll_general.generate_logs(step=True)
def delete_vnic_network_filter_parameters(nf_object):
    """
    Delete VM NIC network filter parameters

    Args:
        nf_object (NetworkFilterParameter): Network filter parameter object

    Returns:
        bool: True if the action succeeded, otherwise False
    """
    return NETWORK_FILTER_API.delete(entity=nf_object, positive=True)


@ll_general.generate_logs(step=True)
def add_vnic_network_filter_parameters(vm, nic, param_name, param_value):
    """
    Add VM NIC network filter parameters

    Args:
        vm (str): VM name
        nic (str): NIC name
        param_name (str): Filter param name
        param_value (str): Filter param value

    Returns:
        bool: True if the action succeeded, otherwise False
    """
    vm_nic = get_vm_nic(vm=vm, nic=nic)
    filter_object = prepare_vnic_network_filter_parameters(
        name=param_name, value=param_value
    )

    parameters_href = "{vnic_href}/{filter_parameters}".format(
        vnic_href=vm_nic.href, filter_parameters=NETWORK_FILTER_PARAMETERS
    )
    return NETWORK_FILTER_API.create(
        entity=filter_object, positive=True, collection=parameters_href,
        coll_elm_name=NETWORK_FILTER_PARAMETER
    )[0]


@ll_general.generate_logs(step=True)
def update_vnic_network_filter_parameters(nf_object, param_name, param_value):
    """
    Update VM NIC network filter parameters

    Args:
        nf_object (NetworkFilterParameter): Network filter parameter object
        param_name (str): Filter param name
        param_value (str): Filter param value

    Returns:
        bool: True if the action succeeded, otherwise False
    """
    new_filter_object = prepare_vnic_network_filter_parameters(
        name=param_name, value=param_value
    )
    return NETWORK_FILTER_API.update(
        origEntity=nf_object, newEntity=new_filter_object, positive=True
    )[0]


@ll_general.generate_logs()
def prepare_vnic_network_filter_parameters(name, value):
    """
    Prepare VM NIC network filter parameters

    Args:
        name (str): Filter param name
        value (str): Filter param value

    Returns:
        NetworkFilterParameter: NetworkFilterParameter object
    """
    return ll_general.prepare_ds_object(
        object_name="NetworkFilterParameter", name=name, value=value
    )


@ll_general.generate_logs(step=True)
def set_sso_ticket(vm_name, value='test', expiry=VM_ACTION_TIMEOUT):
    """
    Create SSO ticket for a VM

    Args:
        vm_name (str): name of a VM
        value (str): value for SSO token
        expiry (int): token expire time in seconds

    Returns:
        bool: True, if the action succeeded, otherwise False
    """
    vm_obj = get_vm(vm=vm_name)
    return bool(
        VM_API.syncAction(
            entity=vm_obj,
            action='ticket',
            positive=True,
            value=value,
            expiry=expiry
        )
    )


@ll_general.generate_logs(step=True)
def logon_vm(vm_name):
    """
    Log on a VM

    Args:
        vm_name (str): name of a VM

    Returns:
        bool: True, if the action succeeded, otherwise False
    """
    vm_obj = get_vm(vm=vm_name)
    return bool(
        VM_API.syncAction(
            entity=vm_obj,
            action='logon',
            positive=True
        )
    )


@ll_general.generate_logs(step=True)
def get_vm_sessions(vm_name):
    """
    Get all sessions on a VM

    Args:
        vm_name (str): name of a VM

    Returns:
        list: list of all sessions connected to a VM
    """
    vm_obj = get_vm(vm=vm_name)
    return VM_API.getElemFromLink(
        vm_obj, link_name='sessions', attr='session', get_href=False
    ) or []


@ll_general.generate_logs(step=True)
def get_vm_uuid(vm_name):
    """
    Get VM uuid.

    Args:
        vm_name (str): VM name

    Returns:
        vm_uuid (str): VM uuid
    """
    return get_vm(vm_name).get_id()


@ll_general.generate_logs()
def get_vm_type(vm_name):
    """
    Get VM type

    Args:
        vm_name (str): VM name

    Returns:
        str: VM type
    """
    return get_vm(vm_name).get_type()
