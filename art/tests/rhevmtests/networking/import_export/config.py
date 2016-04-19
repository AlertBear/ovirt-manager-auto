#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
config file for import_export networks test
"""
import rhevmtests.networking.config as conf


SD_NAME = None  # Filled in setup_package
VLAN_IDS = [str(i) for i in xrange(2, 5)]
NETS = ["net_%s" % i for i in xrange(1, 4)]

LOCAL_DICT = {
    NETS[0]: {
        "required": "false",
        "nic": 1,
    },
    NETS[1]: {
        "required": "false",
        "mtu": conf.MTU[0],
        "nic": 2
    },
    NETS[2]: {
        "required": "false",
        "vlan_id": VLAN_IDS[0],
        "nic": 3,
    }
}
