#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - payload config
"""
from rhevmtests.compute.virt.config import *  # flake8: noqa

PAYLOADS_TYPE = [ENUMS['payload_type_cdrom'], ENUMS['payload_type_floppy']]
PAYLOADS_DEVICES = ['/dev/sr1', '/dev/fd0']
PAYLOADS_FILENAME = ['payload.cdrom', 'payload.floppy']
PAYLOADS_CONTENT = [
    'cdrom payload via create',
    'cdrom payload via update',
    'floppy payload via create',
    'floppy payload via update',
    'complex\npayload\nfor\nuse'
]
TMP_DIR = '/tmp'
