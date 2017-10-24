#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
VM custom properties test plan:
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Compute/VM%20custom%20properties
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.compute.virt.config as config
import rhevmtests.compute.virt.virt_executor as executor
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    tier2,
    testflow
)
from fixtures import clean_vm
from rhevmtests.compute.virt.fixtures import create_vm_class


@pytest.mark.usefixtures(create_vm_class.__name__)
class TestVMCustomProperties(VirtTest):
    """
    Testing VM custom properties
    """
    vm_name = "vm_custom_properties"
    vm_parameters = {
        'name': vm_name,
        'template': config.TEMPLATE_NAME[0],
        'os_type': config.OS_TYPE,
        'cluster': config.CLUSTER_NAME[0]
    }

    @tier2
    @pytest.mark.parametrize(
        (
            "actions", "property_name", "property_value"
        ),
        [
            pytest.param(
                [
                    (config.START_ACTION, None),
                    (config.MIGRATION_ACTION, None),
                    (config.STOP_ACTION, None)
                ],
                "vhost", "ovirtmgmt:true",
                marks=(polarion("RHEVM-22259"))
            ),
            pytest.param(
                [
                    (config.START_ACTION, None),
                    (config.MIGRATION_ACTION, None),
                    (config.STOP_ACTION, None)
                ],
                "sap_agent", "true",
                marks=(polarion("RHEVM-22225"))
            ),
            pytest.param(
                [
                    (config.START_ACTION, None),
                    (config.MIGRATION_ACTION, None),
                    (config.STOP_ACTION, None)

                ],
                "sap_agent", "false",
                marks=(polarion("RHEVM-22224"))
            ),
            pytest.param(
                [
                    (config.START_ACTION, None),
                    (config.MIGRATION_ACTION, None),
                    (config.STOP_ACTION, None),
                ],
                "sndbuf", "1",
                marks=(polarion("RHEVM-22263"))
            ),
            pytest.param(
                [
                    (config.START_ACTION, None),
                    (config.STOP_ACTION, None),
                ],
                "viodiskcache", "writethrough",
                marks=(polarion("RHEVM-22257"))
            ),
            pytest.param(
                [
                    (config.START_ACTION, None),
                    (config.STOP_ACTION, None),
                ],
                "viodiskcache", "writeback",
                marks=(polarion("RHEVM-22256"))
            )
        ]
    )
    @pytest.mark.usefixtures(
        clean_vm.__name__
    )
    def test_vm_custom_properties(
        self, actions, property_name, property_value
    ):
        """
        Update vm with custom property and test the given actions

        Args:
            actions (list): List of action to invoke on vm
            property_name (str): VM Property name
            property_value (str): Property value
        """
        testflow.step(
            "Test custom property: %s with value: %s ",
            property_name, property_value
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=self.vm_name,
            custom_properties='%s=%s' % (property_name, property_value)
        )
        for action in actions:
            assert executor.vm_life_cycle_action(
                vm_name=self.vm_name,
                action_name=action[0],
                func_args=action[1]
            )
