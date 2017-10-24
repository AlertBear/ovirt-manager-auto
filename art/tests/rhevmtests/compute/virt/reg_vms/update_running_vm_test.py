#! /usr/bin/python
# -*- coding: utf-8 -*-

# Virt VMs: RHEVM3/wiki/Compute/3_5_VIRT_Edit_Running_VM

import logging

import pytest

import config
import rhevmtests.helpers as helper
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    vms as ll_vms
)
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
)
from fixtures import (
    add_vm_fixture, start_stop_fixture
)

logger = logging.getLogger("update_vm_cases")


class TestUpdateRunningVm(VirtTest):
    """
    Update parameters of a running VM.
    """
    __test__ = True
    vm_name = 'update_running_vm_test'
    add_disk = True
    affinity = config.ENUMS['vm_affinity_user_migratable']

    def _check_vm_parameter(
        self,
        parameter_name,
        actual_value,
        expected_value
    ):
        """
        Checking vm value parameters

        :param parameter_name: parameter name
        :type parameter_name: str
        :param actual_value: actual value on vm
        :type actual_value: str
        :param expected_value: expected value
        :type expected_value: str
        :return: True expected value equals to actual value else False
        :rtype: bool
        """
        logger.info(
            "Checking vm value: %s, actual_value: %s, expected_value: %s",
            parameter_name, actual_value, expected_value
        )
        assert actual_value == expected_value, (
            "parameter %s value is not as expected" % parameter_name
        )

    @tier1
    @polarion("RHEVM3-6295")
    @pytest.mark.usefixtures(
        add_vm_fixture.__name__, start_stop_fixture.__name__
    )
    def test_update_fields_applied_immediately(self):
        """
        Expect the fields be applied immediately.
        """
        parameters = {
            'description': 'new description',
            'comment': 'update test',
            'highly_available': 'true'
        }
        testflow.step("Update vm fields and check them without reboot")
        assert ll_vms.updateVm(
            positive=True, vm=self.vm_name, **parameters
        ), "Failed to update immediate fields"
        vm_obj = ll_vms.get_vm_obj(self.vm_name, all_content=True)
        logger.info("Checking vm after update")
        assert vm_obj.get_high_availability().get_enabled(), (
            "VM did not set to high availability"
        )
        self._check_vm_parameter(
            'description',
            vm_obj.get_description(),
            parameters['description'],
        )
        self._check_vm_parameter(
            'comment',
            vm_obj.get_comment(),
            parameters['comment'],
        )

    @tier1
    @polarion("RHEVM3-6295")
    @pytest.mark.usefixtures(
        add_vm_fixture.__name__, start_stop_fixture.__name__
    )
    def test_update_field_applied_after_reboot_case_1(self):
        """
        Expect the fields be after next boot.
        VM fields:
        memory, memory_guaranteed, monitors,
        placement_affinity, placement_host
        """

        parameters = {
            'memory': config.TWO_GB,
            'max_memory': helper.get_gb(4),
            'memory_guaranteed': config.TWO_GB,
            'monitors': 2,
            'placement_affinity': self.affinity,
            'placement_host': config.HOSTS[0],
        }
        if config.PPC_ARCH:
            del parameters['monitors']

        testflow.step("Update vm fields and check them after reboot")
        host_id = ll_hosts.get_host_object(config.HOSTS[0]).get_id()
        assert ll_vms.updateVm(
            positive=True, vm=self.vm_name, compare=False, **parameters
        ), "Failed to update immediate fields"
        logger.info("Finish update vm fields, reboot vm")
        ll_vms.reboot_vms([self.vm_name])
        vm_obj = ll_vms.get_vm_obj(self.vm_name, all_content=True)

        logger.info("Checking vm fields after reboot")
        self._check_vm_parameter(
            'memory',
            str(vm_obj.get_memory()),
            str(parameters['memory']),
        )
        self._check_vm_parameter(
            'memory_guaranteed',
            str(vm_obj.get_memory_policy().get_guaranteed()),
            str(parameters['memory_guaranteed'])
        )
        self._check_vm_parameter(
            'placement_affinity',
            vm_obj.get_placement_policy().get_affinity(),
            parameters['placement_affinity']
        )
        host_obj = vm_obj.get_placement_policy().get_hosts().get_host()[0]
        self._check_vm_parameter(
            'placement_host',
            str(host_obj.get_id()),
            str(host_id)
        )
        if not config.PPC_ARCH:
            self._check_vm_parameter(
                'monitors',
                str(vm_obj.get_display().get_monitors()),
                str(parameters['monitors'])
            )
