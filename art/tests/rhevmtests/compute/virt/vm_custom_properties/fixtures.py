#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures for vm custom properties
"""
import pytest
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)


@pytest.fixture()
def clean_vm(request):
    """
    Stop VM and Reset to default values
    """
    vm_name = request.cls.vm_name

    def fin():
        assert ll_vms.stop_vms_safely([vm_name])
        assert ll_vms.updateVm(
            positive=True, vm=vm_name, custom_properties="clear"
        )
    request.addfinalizer(fin)
