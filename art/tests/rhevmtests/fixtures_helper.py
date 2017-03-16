#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Helper functions for fixture.py
"""
import operator
from _pytest.fixtures import FixtureLookupError
from concurrent.futures import ThreadPoolExecutor

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


def get_attr_helper(attribute, obj, default=None):
    """
    Helper to get attribute value from any object, works with nested
    attributes like obj.attr1.attr2.attr3

    Args:
        attribute (str): path to the attribute
        obj (object): object to get attribute from
        default: default value is attribute is not found

    Returns:
        any: attr value if present, default otherwise
    """
    try:
        return operator.attrgetter(attribute)(obj)
    except AttributeError:
        return default


def start_vm_helper(vms_dict):
    """
    Start VM(s) helper for start_vms fixtures

    Args:
        vms_dict (dict): VMs dict to start
    """
    results = list()
    with ThreadPoolExecutor(max_workers=len(vms_dict.keys())) as executor:
        for vm, val in vms_dict.iteritems():
            vm_obj = ll_vms.get_vm(vm)
            if vm_obj.get_status() == conf.ENUMS['vm_state_down']:
                host_index = val.get("host")
                wait_for_status = val.get("wait_for_status", conf.VM_UP)
                host_name = (
                    conf.HOSTS[host_index] if host_index is not None else None
                )
                log = "on host %s" % host_name if host_name else ""
                testflow.setup("Start VM %s %s", vm, log)
                results.append(
                    executor.submit(
                        ll_vms.runVmOnce, positive=True, vm=vm,
                        host=host_name, wait_for_state=wait_for_status
                    )
                )
    for result in results:
        assert result.result(), result.exception()


def get_fixture_val(request, attr_name, default_value=None):
    """
    Get request.getfixturevalue()

    Args:
        request (Request): request fixture object
        attr_name (str): Attribute name to get
        default_value (any): Default value if attribute not found

    Returns:
        any: fixturevalue if found else default value
    """
    try:
        return request.getfixturevalue(attr_name)
    except FixtureLookupError:
        return default_value
