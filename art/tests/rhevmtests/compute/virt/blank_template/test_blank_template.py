import pytest
import config
import fixtures

from art.unittest_lib import testflow
from art.unittest_lib import VirtTest, tier1, tier2
from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import templates as ll_templ
from rhevmtests.compute.virt.fixtures import remove_created_vms


class TestsBlankTemplate(VirtTest):

    reg_vms = [config.BLANK_TEMPLATE_VM]

    @tier2
    @polarion("RHEVM3-10822")
    @pytest.mark.usefixtures(
        fixtures.restore_template_name.__name__
    )
    def test_change_name(self):
        """
        Verify possibility of changing blank template name.
        """
        testflow.step("Update blank template name.")
        assert ll_templ.updateTemplate(
            positive=True,
            template=config.BLANK_TEMPLATE,
            name=config.NEW_NAME
        ), "Failed to rename blank template."
        testflow.step("Verify blank template name was actually changed.")
        assert config.NEW_NAME in ll_templ.get_all_template_objects_names()

    @tier2
    @pytest.mark.usefixtures(
        remove_created_vms.__name__,
        fixtures.restore_template_params.__name__
    )
    @pytest.mark.parametrize(
        ("memory", "stateless", "boot_device"),
        [
            polarion("RHEVM3-10817")(
                [
                    3*config.GB,
                    None,
                    None
                ]
            ),
            polarion("RHEVM3-10819")(
                [
                    None,
                    True,
                    None
                ]
            ),
            polarion("RHEVM3-10820")(
                [
                    None,
                    None,
                    ["hd"]
                ]
            )
        ],
        ids=[
            "verify_memory_inheritance",
            "verify_stateless_inheritance",
            "verify_boot_sequesnce_inheritance"
        ]
    )
    def test_parameters_inheritance(self, memory, stateless, boot_device):
        """
        Verify Blank template parameters are inherited by VM.
        """
        testflow.step("Update blank template.")
        assert ll_templ.updateTemplate(
            positive=True,
            template=config.BLANK_TEMPLATE,
            memory=memory,
            stateless=stateless,
            boot=boot_device
        ), "Failed to update blank template."
        assert ll_vms.addVm(
            positive=True, **config.BLANK_TEMPLATE_VM_DEFAULTS
        ), "Failed to create VM from blank template."
        if memory:
            testflow.step("Verify VM inherited memory size.")
            current_vm_memory = ll_vms.get_vm_memory(config.BLANK_TEMPLATE_VM)
            assert current_vm_memory == config.GB * 3, (
                "VM did not inherit memory size from blank template."
            )
        if stateless:
            testflow.step("Verify VM inherited stateless status.")
            current_vm_stateless = ll_vms.get_vm_stateless_status(
                config.BLANK_TEMPLATE_VM
            )
            assert current_vm_stateless, (
                "VM did not inherit stateless status from blank template."
            )
        if boot_device:
            current_vm_boot_seq = ll_vms.get_vm_boot_sequence(
                config.BLANK_TEMPLATE_VM
            )
            assert current_vm_boot_seq == ["hd"], (
                "VM did not inherit boot sequence from blank template."
            )

    @tier2
    @polarion("RHEVM3-11228")
    @pytest.mark.usefixtures(
        remove_created_vms.__name__
    )
    def test_mem_size_change_on_vm(self):
        """
        Verify it is possible to change memory size of VM created from blank
        template.
        """
        assert ll_vms.addVm(
            positive=True, **config.BLANK_TEMPLATE_VM_DEFAULTS
        ), "Failed to create VM from blank template."
        mem_val_before_update = ll_vms.get_vm_memory(config.BLANK_TEMPLATE_VM)
        assert ll_vms.updateVm(
            positive=True,
            vm=config.BLANK_TEMPLATE_VM,
            memory=mem_val_before_update*2
        )
        testflow.step("Verify new memory value was set correctly.")
        mem_val_after_update = ll_vms.get_vm_memory(config.BLANK_TEMPLATE_VM)
        assert mem_val_after_update == mem_val_before_update * 2, (
            "VM memory was not changed successfully."
        )

    @tier1
    @polarion("RHEVM3-12347")
    def test_remove_blank_template(self):
        """
        Verify it is not allowed to remove blank template.
        """
        testflow.step("Try to remove blank template, operation should fail.")
        assert ll_templ.remove_template(
            positive=False,
            template=config.BLANK_TEMPLATE
        )
