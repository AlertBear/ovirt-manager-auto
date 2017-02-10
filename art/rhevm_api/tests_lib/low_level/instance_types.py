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
from art.core_api.apis_utils import getDS, data_st
from art.rhevm_api.tests_lib.low_level import general as ll_general
from art.rhevm_api.utils.test_utils import get_api

ELEMENT = 'instance_type'
COLLECTION = 'instancetypes'
INSTANCE_TYPE_API = get_api(ELEMENT, COLLECTION)

INSTANCE = getDS('InstanceType')
CPU = getDS('Cpu')
CPU_TOPOLOGY = getDS('CpuTopology')

logger = logging.getLogger("art.ll_lib.instance_types")


def _prepare_instance_type_object(**kwargs):
    """
    create new instance type object

    Keyword arguments:
        name (str): Name of instance type object
        description (str):Instance type description
        memory (str): Instance type memory size
        cpu_socket (str): Number of cpu sockets
        cpu_cores (str): Number of cpu cores
        cpu_threads (str): Number of cpu threads
        boot (str): Instance type boot device
        type (str): Instance type type
        custom_emulated_machine (str): Custom emulated machine flag name
        custom_cpu_model (str): Custom cpu model name
        virtio_scsi (bool): Enable virtio-scsi
        display_type (str): Type of display (spice/vnc)
        monitors (int): Number of monitors
        disconnect_action (str): Name of action to perform upon condole
            disconnection
        single_qxl_pci (bool): Enable single qxl pci
        smartcard_enabled (bool): Enable smart card
        soundcard_enabled (bool): Enable sound card
        serial_console (bool): Enable serial console
        migration_downtime (int): Custom migration downtime
        auto_converge (str): Auto converge upon migration
        compressed (str): Use XBZRLE compression upon migration
        migration_policy (str): Migration policy id
        usb_type (str): Usb support type (legacy, native)
        io_threads (int): IO threads number
        memory_guaranteed (int): Size of memory guaranteed for instance type
        ballooning (bool): Enable ballooning
        highly_available (bool): Enable high availability
        availability_priority (int): Priority for availability
        max_memory (int): Upper bound for the memory hotplug


    Returns:
        bool: True if instance type was added properly, False otherwise
    """
    instance_type = INSTANCE()

    # name
    name = kwargs.get('name')
    instance_type.set_name(name)

    # description
    description = kwargs.get('description')
    if description:
        instance_type.set_description(description)

    # memory
    memory = kwargs.get('memory')
    if memory:
        instance_type.set_memory(memory)

    type = kwargs.get('type')
    if type:
        instance_type.set_type(type)

    # cpu topology
    cpu_socket = kwargs.get('cpu_sockets')
    cpu_cores = kwargs.get('cpu_cores')
    cpu_threads = kwargs.get('cpu_threads')

    if cpu_socket or cpu_cores or cpu_threads:
        instance_type.set_cpu(
            CPU(
                topology=CPU_TOPOLOGY(
                    sockets=cpu_socket, cores=cpu_cores, threads=cpu_threads
                )
            )
        )

    # custom emulated machine
    custom_emulated_machine = kwargs.get("custom_emulated_machine")
    if custom_emulated_machine:
        instance_type.set_custom_emulated_machine(custom_emulated_machine)

    # custom cpu model
    custom_cpu_model = kwargs.get("custom_cpu_model")
    if custom_cpu_model:
        instance_type.set_custom_cpu_model(custom_cpu_model)

    # virtio-scsi enabled
    virtio_scsi = kwargs.get('virtio_scsi')
    if virtio_scsi is not None:
        virtio_scsi_obj = data_st.VirtioScsi(enabled=virtio_scsi)
        instance_type.set_virtio_scsi(virtio_scsi_obj)

    # display monitors and type
    display_type = kwargs.get("display_type")
    monitors = kwargs.get("monitors")
    disconnect_action = kwargs.get("disconnect_action")
    smartcard_enabled = kwargs.get("smartcard_enabled")
    single_qxl_pci = kwargs.get("single_qxl_pci")
    if monitors or display_type or disconnect_action:
        instance_type.set_display(
            data_st.Display(
                type_=display_type, monitors=monitors,
                disconnect_action=disconnect_action,
                smartcard_enabled=smartcard_enabled,
                single_qxl_pci=single_qxl_pci
            )
        )
    # serial console enabled
    serial_console = kwargs.get('serial_console')
    if serial_console is not None:
        console = data_st.Console(enabled=serial_console)
        instance_type.set_console(console)

    # migration_downtime
    migration_downtime = kwargs.get("migration_downtime")
    if migration_downtime is not None:
        instance_type.set_migration_downtime(migration_downtime)

    # migration options
    auto_converge = kwargs.get("auto_converge")
    compressed = kwargs.get("compressed")
    migration_policy = kwargs.get("migration_policy")
    if migration_policy:
        migration_policy = data_st.MigrationPolicy(id=migration_policy)
    elif migration_policy is not None:
        migration_policy = data_st.MigrationPolicy()
    migration = data_st.MigrationOptions(
        auto_converge=auto_converge, compressed=compressed,
        policy=migration_policy
        )
    instance_type.set_migration(migration)

    # boot sequence
    boot_seq = kwargs.get("boot")
    if boot_seq:
        os = data_st.OperatingSystem()
        if isinstance(boot_seq, basestring):
            boot_seq = boot_seq.split()
        os.set_boot(
            boot=data_st.Boot(
                devices=data_st.devicesType(
                    device=boot_seq
                )
            )
        )
        instance_type.set_os(os)

    # usb_type
    usb_type = kwargs.get("usb_type")
    if usb_type:
        usb = data_st.Usb()
        usb.set_enabled(True)
        usb.set_type(usb_type)
        instance_type.set_usb(usb)

    # soundcard enabled
    soundcard_enabled = kwargs.get("soundcard_enabled")
    if soundcard_enabled is not None:
        instance_type.set_soundcard_enabled(soundcard_enabled)

    # io_threads
    io_threads = kwargs.get("io_threads")
    if io_threads:
        io = data_st.Io()
        io.set_threads(io_threads)
        instance_type.set_io(io)

    # memory policy memory_guaranteed and ballooning
    guaranteed = kwargs.pop("memory_guaranteed", None)
    max_memory = kwargs.pop("max_memory", None)
    ballooning = kwargs.pop('ballooning', None)
    if ballooning is not None or guaranteed or max_memory:
        instance_type.set_memory_policy(
            data_st.MemoryPolicy(
                guaranteed=guaranteed,
                ballooning=ballooning,
                max=max_memory
            )
        )

    # high availablity
    ha = kwargs.get("highly_available")
    ha_priority = kwargs.get("availablity_priority")
    if ha is not None or ha_priority:
        instance_type.set_high_availability(
            data_st.HighAvailability(
                enabled=ha, priority=ha_priority
            )
        )

    return instance_type


@ll_general.generate_logs()
def create_instance_type(instance_type_name, **kwargs):
    """
    create new instance type

    Args:
        instance_type_name (str): Name of the instance type

    Keyword arguments:
        description (str):Instance type description
        memory (str): Instance type memory size
        cpu_socket (str): Number of cpu sockets
        cpu_cores (str): Number of cpu cores
        cpu_threads (str): Number of cpu threads
        boot (str): Instance type boot device
        type (str): Instance type type
        custom_emulated_machine (str): Custom emulated machine flag name
        custom_cpu_model (str): Custom cpu model name
        virtio_scsi (bool): Enable virtio-scsi
        display_type (str): Type of display (spice/vnc)
        monitors (int): Number of monitors
        disconnect_action (str): Name of action to perform upon condole
            disconnection
        single_qxl_pci (bool): Enable single qxl pci
        smartcard_enabled (bool): Enable smart card
        soundcard_enabled (bool): Enable sound card
        serial_console (bool): Enable serial console
        migration_downtime (int): Custom migration downtime
        auto_converge (str): Auto converge upon migration
        compressed (str): Use XBZRLE compression upon migration
        migration_policy (str): Migration policy id
        usb_type (str): Usb support type (legacy, native)
        io_threads (int): IO threads number
        memory_guaranteed (int): Size of memory guaranteed for instance type
        ballooning (bool): Enable ballooning
        highly_available (bool): Enable high availability
        availability_priority (int): Priority for availability
        max_memory (int): Upper bound for the memory hotplug


    Returns:
        bool: True if instance type was added properly, False otherwise
    """
    instance = _prepare_instance_type_object(name=instance_type_name, **kwargs)
    instance, status = INSTANCE_TYPE_API.create(instance, True)
    return status


@ll_general.generate_logs()
def update_instance_type(instance_type_name, **kwargs):
    """
    Update existed instance type

    Args:
        instance_type_name (str): Name of instance type that should be updated

    Keyword arguments:
        name (str): New instance type name
        description (str): New instance type description
        memory (int): New instance type memory size
        cpu_socket (int): New number of cpu sockets
                cpu_socket (str): Number of cpu sockets
        cpu_cores (str): Number of cpu cores
        cpu_threads (str): Number of cpu threads
        boot (str): Instance type boot device
        custom_emulated_machine (str): Custom emulated machine flag name
        custom_cpu_model (str): Custom cpu model name
        virtio_scsi (bool): Enable virtio-scsi
        display_type (str): Type of display (spice/vnc)
        monitors (int): Number of monitors
        disconnect_action (str): Name of action to perform upon condole
            disconnection
        single_qxl_pci (bool): Enable single qxl pci
        smartcard_enabled (bool): Enable smart card
        soundcard_enabled (bool): Enable sound card
        serial_console (bool): Enable serial console
        migration_downtime (int): Custom migration downtime
        auto_converge (str): Auto converge upon migration
        compressed (str): Use XBZRLE compression upon migration
        migration_policy (str): Migration policy id
        usb_type (str): Usb support type (legacy, native)
        io_threads (int): IO threads number
        memory_guaranteed (int): Size of memory guaranteed for instance type
        ballooning (bool): Enable ballooning
        highly_available (bool): Enable high availability
        availability_priority (int): Priority for availability
        max_memory (int): Upper bound for the memory hotplug

    Returns
        bool: True if instance type was updated properly, False otherwise
    """
    instance_obj = get_instance_type_object(instance_type_name)
    if not instance_obj:
        return False
    updated_instance = _prepare_instance_type_object(**kwargs)
    _, status = INSTANCE_TYPE_API.update(instance_obj, updated_instance, True)
    return status


@ll_general.generate_logs()
def remove_instance_type(instance_type_name):
    """
    Remove instance type.

    Args:
        instance_type_name (str): Name of instance type that should be removed

    Returns:
        bool: True if instance type was removed properly, False otherwise
    """
    instance_object = get_instance_type_object(instance_type_name)
    if not instance_object:
        return False
    return INSTANCE_TYPE_API.delete(instance_object, True)


@ll_general.generate_logs(error=False)
def get_instance_type_object(instance_type):
    """
    Get an instance type object by it's name.

    Args:
        instance_type (str): Name of instance type

    Return: The instance type object or None in case there was no instance type
        found in the system with the given name
    """
    instance_type_name_query = "name=%s" % instance_type
    instance_type_objects = INSTANCE_TYPE_API.query(
        instance_type_name_query, all_content=True
    )
    if not instance_type_objects:
        return None
    return instance_type_objects[0]
