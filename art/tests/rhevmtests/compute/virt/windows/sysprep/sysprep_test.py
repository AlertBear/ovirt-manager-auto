#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Virt Windows testing
"""
import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.compute.virt.windows_helper as handler
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier3,
)
from rhevmtests.compute.virt.windows import (
    config as config,
    helper as helper
)
from rhevmtests.compute.virt.windows.fixtures import (  # noqa: F401
    create_windows_vms,
    create_windows_vms_from_sealed_template,
    update_sysprep_with_custom_file,
    update_sysprep_parameters,
    update_cluster,
    set_product_keys,
    remove_seal_templates
)
from rhevmtests.fixtures import (  # noqa: F401
    register_windows_templates,
)


@pytest.fixture(scope='module', autouse=True)  # noqa: F811
def module_setup(request,
                 register_windows_templates):
    """
    This module setup fixture imports a preconfigured
    windows SD with windows templates, attaches it and
    activates it and registers the templates.
    """
    pass


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(create_windows_vms.__name__)
class TestSysprepCase1(VirtTest):
    """
    Seal VM test
    """
    vms_name = config.WINDOWS_SEAL_VMS

    @tier3
    @pytest.mark.parametrize(
        "vm_name",
        [
            polarion("RHEVM-21587")(config.WINDOWS_10),
            polarion("RHEVM-21588")(config.WINDOWS_2012)
        ]
    )
    def test_seal_window_vm(self, vm_name):
        """
        1. Seal VM without floppy
        2. Wait till VM is down (raise APITimeout if not)
        3. Create template from seal vm
        4. Remove VM

        Args:
            vm_name (str): Windows vm name
        """
        vm_ip = hl_vms.get_vm_ip(vm_name=vm_name, start_vm=False)
        windows_vm = handler.WindowsGuest(
            ip=vm_ip, connectivity_check=True
        )
        testflow.step("Seal VM: %s", vm_name)
        windows_vm.seal_vm()
        ll_vms.wait_for_vm_states(
            vm_name=vm_name,
            states=config.VM_DOWN_STATE,
            timeout=config.TIMEOUT_SEAL_VM
        )
        testflow.step("Create template from seal VM: %s", vm_name)
        assert helper.make_template_from_sealed_vm(vm_name)
        testflow.step("Remove VM")
        assert ll_vms.safely_remove_vms([vm_name])


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(
    create_windows_vms_from_sealed_template.__name__,
    update_sysprep_parameters.__name__
)
class TestSysprepCase2(VirtTest):
    """
    Sysprep testing on desktop(windows 10) and server VM (windows 2012 R2)
    """

    @tier3
    @pytest.mark.parametrize(
        ("vm_name", "os_type"),
        [
            polarion("RHEVM-21590")(
                [config.WINDOWS_10, config.WIN_OS_TYPE_DESKTOP]
            ),
            polarion("RHEVM-21589")(
                [config.WINDOWS_2012, config.WIN_OS_TYPE_SERVER]
            )
        ]
    )
    def test_sysprep_parameters(self, vm_name, os_type):
        """
        1. Create and run VM from seal template with sysperp parameters:
        host name, timezone, custom locale.
        2. Check VM configure

        Args:
            vm_name (str): Windows vm name
            os_type (str): Windows OS type (Server/Desktop)
        """
        testflow.step("Check sysprep configuration")
        assert helper.check_syspreped_vm(
            vm_name=vm_name,
            expected_values=config.SYSPREP_EXPECTED_VALUES_BASE,
            os_type=os_type
        )


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@pytest.mark.usefixtures(
    create_windows_vms_from_sealed_template.__name__,
    update_sysprep_with_custom_file.__name__
)
class TestSysprepCase3(VirtTest):
    """
    Sysprep testing on desktop(windows 10) and server VM (windows 2012 R2)
    """

    @tier3
    @pytest.mark.parametrize(
        ("vm_name", "win_version", "os_type"),
        [
            polarion("RHEVM-21591")(
                [config.WINDOWS_10, config.WIN_10_OS,
                 config.WIN_OS_TYPE_DESKTOP]
            ),
            polarion("RHEVM-21592")(
                [config.WINDOWS_2012, config.WIN_2012_R2_64B_OS,
                 config.WIN_OS_TYPE_SERVER]
            )
        ]
    )
    def test_sysprep_with_custom_file(self, vm_name, win_version, os_type):
        """
        1. Create and run VM from seal template with sysperp file
        2. Check VM configure

        Args:
            vm_name (str): Windows vm name
            win_version (str): Windows version (like windows_10_64B)
            os_type (str): Windows OS type (Server/Desktop)
        """
        testflow.step("Check sysprep configuration")
        assert helper.check_syspreped_vm(
            vm_name=vm_name,
            expected_values=config.SYSPREP_EXPECTED_VALUES_BASE,
            os_type=os_type
        )
