#! /usr/bin/python
# -*- coding: utf-8 -*-

import time

import pytest

import config
import rhevmtests.compute.virt.helper as virt_helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
)
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
    tier2,
)
from fixtures import change_default_tz
from rhevmtests.compute.virt.fixtures import create_vm


class TestVmTz(VirtTest):
    """
    Check VM timezone tests
    """
    vm_parameters = config.VM_PARAMETERS
    vm_name = vm_parameters['name']

    @tier1
    @pytest.mark.parametrize(
        "custom_vm_params",
        config.VM_TZ,
        ids=[
            "linux",
            "windows"
        ]
    )
    @pytest.mark.usefixtures(create_vm.__name__)
    def test_vm_tz(self, custom_vm_params):
        """
        Positive: Add new VM, check that timezone is set correctly
        """
        vm = ll_vms.get_vm(vm=self.vm_name)
        testflow.step('Check that VM timezone is correct')
        assert vm.get_time_zone().get_name() == custom_vm_params['time_zone']

    @tier1
    @pytest.mark.parametrize(
        ("custom_vm_params", "tz_for_upd"), config.UPDATE_VM_TZ,
        ids=[
            "general",
            "windows",
        ]
    )
    @pytest.mark.usefixtures(create_vm.__name__)
    def test_tz_update_vm_tz(self, custom_vm_params, tz_for_upd):
        """
        Positive: Add new VM with custom tz, check that VM has correct tz,
        change its tz, check that tz was changed successfully
        """
        upd_params = {
            'time_zone': tz_for_upd
        }
        testflow.step('Change VM timezone to {tz}'.format(tz=tz_for_upd))
        assert ll_vms.updateVm(True, self.vm_name, **upd_params)
        vm = ll_vms.get_vm(self.vm_name)
        testflow.step('Check that VM timezone is updated')
        assert vm.get_time_zone().get_name() == tz_for_upd

    @tier1
    @pytest.mark.parametrize(
        ("custom_vm_params", "tz_for_upd"), config.UPDATE_RUNNING_VM,
        ids=[
            "general",
            "windows",
        ]
    )
    @pytest.mark.usefixtures(create_vm.__name__)
    def test_tz_update_running_vm_tz(self, custom_vm_params, tz_for_upd):
        """
        Positive: Add new VM with custom tz, check that VM has correct tz
        change its tz, run VM, check that tz was changed successfully
        """
        is_dst = time.localtime().tm_isdst
        upd_params = {
            'time_zone': tz_for_upd
        }
        assert ll_vms.runVmOnce(True, self.vm_name, wait_for_state='up')
        testflow.step('Save old rtc base value')
        rtc_base_old = virt_helper.get_vm_qemu_process_args(
            self.vm_name
        ).get('rtc_base')
        testflow.step('Change VM timezone to {tz}'.format(tz=tz_for_upd))
        assert not ll_vms.updateVm(True, self.vm_name, **upd_params)
        # use startVm and stopVm to avoid race condition, when VM is started
        #  too fast after shutdown, while VmUpdate is in progress
        assert ll_vms.stopVm(positive=True, vm=self.vm_name)
        wait_for_tasks(datacenter=config.DC_NAME[0], engine=config.ENGINE)
        assert ll_vms.startVm(
            positive=True,
            vm=self.vm_name,
            wait_for_status='up'
        )
        rtc_base_new = virt_helper.get_vm_qemu_process_args(
            self.vm_name
        ).get('rtc_base')
        testflow.step(
            'Comparing rtc base - Old value: {old} New value: {new}'.format(
                old=rtc_base_old,
                new=rtc_base_new)
        )
        vm = ll_vms.get_vm(self.vm_name)
        testflow.step('Check that VM timezone is updated')
        assert vm.get_time_zone().get_name() == tz_for_upd
        assert (rtc_base_new - rtc_base_old).seconds / 3600 == 2 + is_dst

    @tier1
    @pytest.mark.parametrize(
        ("tz", 'expected_tz'), config.DEFAULT_TZ_DB,
        ids=[
            "windows",
            "general",
        ]
    )
    def test_default_tz_in_db(self, tz, expected_tz):
        """Check that default TZ value in the DB is correct"""
        testflow.step('Get default timezone values from the DB')
        default_tz = virt_helper.get_default_tz_from_db(config.ENGINE)
        testflow.step('Check that default timezones are correct')
        assert default_tz[tz] == expected_tz


class TestTzCli(VirtTest):
    """
    Tests for CLI part of timezones
    """
    vm_parameters = config.VM_PARAMETERS
    vm_name = vm_parameters['name']

    @tier2
    @pytest.mark.parametrize(
        ('tz', 'tz_val', 'expected_tz'), config.CLI_CHANGE_DB,
        ids=[
            "general",
            "windows",
            "general_wrong",
            "windows_wrong",
        ]
    )
    @pytest.mark.usefixtures(change_default_tz.__name__)
    def test_cli_change_tz(self, tz, tz_val, expected_tz):
        """Change default timezone using engine-config and check that it is
        changed in the DB"""
        default_timezones = virt_helper.get_default_tz_from_db(config.ENGINE)
        testflow.step('Check that default timezone was changed')
        assert default_timezones[tz] == expected_tz
