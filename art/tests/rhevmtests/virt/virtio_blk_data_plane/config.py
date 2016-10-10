#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - Test configuration module
"""
from rhevmtests.virt.config import *  # flake8: noqa

VM_VIRTIO_DATA_PLANE_NAME = 'virtio_data_plane'
DISK_NAME = "".join((VM_VIRTIO_DATA_PLANE_NAME, '_disk_'))
HOTPLUG_DISK_NAME = "virtio_data_plane_hotplug_disk"
