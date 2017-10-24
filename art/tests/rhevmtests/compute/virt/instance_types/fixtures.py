#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures for instance types test module
"""
import pytest

import config
from art.rhevm_api.tests_lib.low_level import (
    templates as ll_templates,
    vms as ll_vms,
    instance_types as ll_instance_types
)
from art.unittest_lib import testflow


@pytest.fixture()
def default_instance_type_teardown(request):
    """
    Stores the case's instance type object as global parameter.
    Reverts the system's default instance types to their default configuration
    after changes made in the test
    """
    marker = request.node.get_marker("instance_type_name")
    name = marker.kwargs.get("name")

    def fin():
        """
        Revert instance type to it's default values.
        """
        kwargs = config.DEFAULT_INSTANCES_PARAMS[name]
        testflow.teardown("Reverting instance type %s to default values", name)
        ll_instance_types.update_instance_type(
            instance_type_name=name, **kwargs
        )
        config.INSTANCE_TYPE_OBJECT = None

    request.addfinalizer(fin)
    config.INSTANCE_TYPE_OBJECT = ll_instance_types.get_instance_type_object(
        name
    )


@pytest.fixture()
def remove_custom_instance_type(request):
    """
    Removes the instance type that was created in the test
    """

    marker = request.node.get_marker("instance_types_created")
    instance_types = marker.kwargs.get("instance_types")

    def fin():
        for instance_type in instance_types:
            if ll_instance_types.get_instance_type_object(instance_type):
                testflow.teardown(
                    "Removing instance type: %s", instance_type
                )
                ll_instance_types.remove_instance_type(
                    instance_type)

    request.addfinalizer(fin)


@pytest.fixture()
def remove_test_vms(request):
    """
    Removes the vms that were created in the test
    """
    def fin():
        testflow.teardown(
            "Removing vms: %s", [config.INSTANCE_TYPE_VM, config.TEMPLATE_VM]
        )
        ll_vms.safely_remove_vms([config.INSTANCE_TYPE_VM, config.TEMPLATE_VM])
    request.addfinalizer(fin)


@pytest.fixture()
def remove_test_templates(request):
    """
    Removes the templates which were created in the test
    """
    def fin():
        testflow.teardown("Removing template: %s", config.NEW_TEMPLATE_NAME)
        ll_templates.remove_template(True, config.NEW_TEMPLATE_NAME)
    request.addfinalizer(fin)
