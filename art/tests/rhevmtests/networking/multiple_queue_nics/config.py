#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file for Multiple Queue NICs test
"""

NUM_QUEUES = [5, 6]
PROP_QUEUES = ["=".join(["queues", str(i)]) for i in NUM_QUEUES]
VM_FROM_TEMPLATE = "vm_from_queues_template"
VM_NIC = "multiple_queues_nic"
