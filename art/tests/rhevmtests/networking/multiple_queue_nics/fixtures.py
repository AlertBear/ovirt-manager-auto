#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for Multiple Queue NICs
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def create_vm(request):
    """
    Create VM.
    """
    vm_name = request.node.cls.vm_name
    template = conf.TEMPLATE_NAME[0]

    def fin():
        """
        Remove vm
        """
        assert ll_vms.removeVm(
            positive=True, vm=vm_name, stopVM="True", wait=True
        )
    request.addfinalizer(fin)

    testflow.setup("Creating VM: %s from template: %s", vm_name, template)
    assert ll_vms.createVm(
        positive=True, vmName=vm_name, cluster=conf.CL_0,
        vmDescription="from_template", template=template
    )
