import copy

import pytest

import config
import helper
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.test_handler.tools import polarion, bz
from art.unittest_lib import VirtTest, tier1, tier3
from art.unittest_lib import testflow
from rhevmtests import helpers
from rhevmtests.compute.virt.fixtures import (
    create_vm, start_vms_function_scope
)


class TestSMBiOSCustomData(VirtTest):
    """
    SMBiOS customize data test suite.
    """

    custom_uuid_value = config.custom_uuid
    invalid_uuid_value = config.incorrect_uuid
    default_uuid_value = None
    vm_parameters = config.SMBIOS_VM_DEFAULTS
    vm_name = vm_parameters["name"]

    @tier1
    @polarion("RHEVM3-10622")
    @bz({"1466270": {}})
    def test_negative_smbios_incorrect_uuid(self):
        """
        Create vm with incorrect UUID
        """
        vm_params = copy.deepcopy(config.SMBIOS_VM_DEFAULTS)
        vm_params.update(
            **{
                "name": "smbios_negative_test",
                "positive": False,
                "uuid": self.invalid_uuid_value
            }
        )
        assert ll_vms.addVm(**vm_params), (
            "Was able to create VM with incorrect UUID value."
        )

    @tier3
    @pytest.mark.usefixtures(
        create_vm.__name__,
        start_vms_function_scope.__name__
    )
    @pytest.mark.parametrize(
        "custom_vm_params",
        [
            polarion("RHEVM-11265")({"uuid": custom_uuid_value}),
            polarion("RHEVM-11266")({"uuid": default_uuid_value})
        ]
    )
    def test_create_vm_with_uuid(self, custom_vm_params):
        """
        Create vm with custom/default UUID.
        """
        vm_resource = helpers.get_vm_resource(config.SMBIOS_VM)
        _, uuid_via_cmd, _ = vm_resource.run_command(config.CMD)
        uuid_via_resource = ll_vms.get_vm_uuid(config.SMBIOS_VM)
        testflow.step("Verify VM uuid is set as expected.")
        helper.verify_uuid(
            custom_vm_params['uuid'],
            uuid_via_cmd.strip().lower(),
            uuid_via_resource
        )

        assert ll_vms.migrateVm(positive=True, vm=config.SMBIOS_VM), (
            "Failed to migrate SMBiOS VM."
        )

        _, uuid_via_cmd, _ = vm_resource.run_command(config.CMD)
        testflow.step("Verify VM uuid is set as expected.")
        helper.verify_uuid(
            custom_vm_params['uuid'],
            uuid_via_cmd.strip().lower(),
            uuid_via_resource
        )
