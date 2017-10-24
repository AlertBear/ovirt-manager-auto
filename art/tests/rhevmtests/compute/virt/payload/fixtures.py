#! /usr/bin/python
# -*- coding: utf-8 -*-

import os

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
import config
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def create_vm_with_payloads(request):
    """
    Handle two cases:
    1. Create vm with given payload (update_vm flag is false)
    2. Create vm and update vm with payload (update_vm flag is true)
    """

    vm_name = request.node.cls.vm_name
    payload_type = request.node.cls.payload_type
    payload_filename = request.node.cls.payload_filename
    payload_content = request.node.cls.payload_content
    update_vm = getattr(request.node.cls, "update_case", False)
    payloads = [(payload_type, payload_filename, payload_content)]
    dict_vm = {
        'name': vm_name,
        'cluster': config.CLUSTER_NAME[0],
        'template': config.TEMPLATE_NAME[0],
        'os_type': config.VM_OS_TYPE,
        'display_type': config.VM_DISPLAY_TYPE,
        'payloads': payloads if not update_vm else None
    }
    if update_vm:
        assert ll_vms.addVm(positive=True, **dict_vm)
        testflow.setup(
            "Update vm %s with payloads (type=%s, filename=%s,"" content=%s)",
            vm_name, payload_type, payload_filename, payload_content
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=vm_name,
            payloads=payloads
        )
    else:
        testflow.setup(
            "Add new vm %s with payloads (type=%s, filename=%s,"" content=%s)",
            vm_name, payload_type, payload_filename, payload_content
        )
        assert ll_vms.addVm(positive=True, **dict_vm)


@pytest.fixture(scope='class')
def remove_payload_files(request):
    """
    Remove payload file form engine
    """
    payload_filename = request.node.cls.payload_filename

    def fin():
        file_name = os.path.join(config.TMP_DIR, payload_filename)
        testflow.teardown("Remove payload file %s from engine" % file_name)
        if not config.ENGINE_HOST.fs.remove(file_name):
            raise errors.TearDownException(
                "Failed to delete file %s ", file_name
            )
    request.addfinalizer(fin)
