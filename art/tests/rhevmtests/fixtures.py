#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Global fixtures
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def start_vm(request):
    """
    Run VM once.
    """
    vms_dict = getattr(request.node.cls, "start_vms_dict", dict())
    vms_to_stop = getattr(request.node.cls, 'vms_to_stop', vms_dict.keys())

    def fin():
        """
        Stop VM(s).
        """
        testflow.teardown("Stop VMs %s", vms_to_stop)
        assert ll_vms.stop_vms_safely(vms_list=vms_to_stop)
    request.addfinalizer(fin)

    for vm, val in vms_dict.iteritems():
        host_index = val.get("host")
        wait_for_status = val.get("wait_for_status", conf.VM_UP)
        host_name = conf.HOSTS[host_index] if host_index is not None else None
        log = "on host %s" % host_name if host_name else ""
        testflow.setup("Start VM %s %s", vm, log)
        assert ll_vms.runVmOnce(
            positive=True, vm=vm, host=host_name,
            wait_for_state=wait_for_status
        )
