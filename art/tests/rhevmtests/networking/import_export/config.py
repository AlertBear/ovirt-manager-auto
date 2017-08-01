#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for import_export networks test
"""
from random import randint

import rhevmtests.networking.config as conf
from rhevmtests.config import ENUMS

SD_NAME = None  # Filled in setup_package
NETS = ["ie_net_%s" % i for i in xrange(1, 4)]
VNICS = ["import_export_vnic_%s" % i for i in xrange(5)]
NAME_INT = randint(1, 100)
IE_VM = "IE_VM_%s" % NAME_INT
IE_VM_2 = "IE_VM_2_%s" % NAME_INT
IE_TEMPLATE = "IE_TEMPLATE_%s" % NAME_INT
IMP_MORE_THAN_ONCE_VM = "MoreThanOnceVM_%s" % NAME_INT
IMP_MORE_THAN_ONCE_TEMP = "MoreThanOnceTEMPLATE_%s" % NAME_INT
IE_VM_NAME = IE_VM
IE_VM_2_NAME = IE_VM_2
IE_TEMPLATE_NAME = IE_TEMPLATE
IMP_MORE_THAN_ONCE_VM_NAME = IMP_MORE_THAN_ONCE_VM
IMP_MORE_THAN_ONCE_TEMP_NAME = IMP_MORE_THAN_ONCE_TEMP
EXPORT_TYPE = ENUMS['storage_dom_type_export']

LOCAL_DICT = {
    NETS[0]: {
        "required": "false",
    },
    NETS[1]: {
        "required": "false",
        "mtu": conf.MTU[0],
    },
    NETS[2]: {
        "required": "false",
        "vlan_id": conf.DUMMY_VLANS.pop(0),
    }
}
