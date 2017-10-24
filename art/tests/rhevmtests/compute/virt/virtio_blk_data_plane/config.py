#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Configuration file for Virtio-blk data plane
"""
from rhevmtests.compute.virt.config import *  # flake8: noqa

VM_IOTHREAD_VIRTIO = "vm_iothread_virtio"
VM_IOTHREAD_SCSI_VIRTIO = "vm_iothread_scsi_virtio"
VM_IOTHREAD_MIXED = "vm_iothread_mixed"
VM_DISK_BUS = "bus"
VM_DISK_BUS_VIRTIO = "virtio"
VM_DISK_BUS_SCSI_VIRTIO = "scsi"

VMS_IOTHREADS_NAMES = {
    VM_IOTHREAD_VIRTIO: {INTERFACE_VIRTIO: 4},
    VM_IOTHREAD_SCSI_VIRTIO: {INTERFACE_VIRTIO_SCSI: 4},
    VM_IOTHREAD_MIXED: {
        INTERFACE_VIRTIO: 2, INTERFACE_VIRTIO_SCSI: 2
    }
}

IOTHREADS_REGEXP = r"<iothreads>(\d+)</iothreads>"
IOTHREADS_CONTROLLERS_REGEXP = (
    r"<controller type='scsi' index='(\d+)' model='virtio-scsi'>"
)
VIRTIO_DISKS_REGEXP = (
    r"<disk type='\w+' device='disk' snapshot='\w+'>\n"
    r"\s*<driver [\w='\s]+ iothread='(\d+)'/>.*?</disk>"
)
VIRTIO_SCSI_DISKS_REGEXP = (
    r"<disk type='\w+' device='disk' snapshot='\w+'>.*?"
    r"<address type='drive' controller='(\d+)' [\s\w\='\d]+/>"
)
BUS_TYPES = {
    VIRTIO_DISKS_REGEXP: VM_DISK_BUS_VIRTIO,
    VIRTIO_SCSI_DISKS_REGEXP: VM_DISK_BUS_SCSI_VIRTIO
}
DISK_IOTHREAD = "iothread"

HOTPLUG_DISK = "hotplug_disk_virtio_blk"
