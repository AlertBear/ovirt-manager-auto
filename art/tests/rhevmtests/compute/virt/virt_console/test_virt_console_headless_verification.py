import pytest

import config as vcons_conf
import fixtures
import helper
from art.rhevm_api.tests_lib.high_level import vms as hl_vms
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier2,
    tier3,
    VirtTest,
    testflow,
)


class TestVirtConsoleHeadlessInheritanceClass(VirtTest):

    @tier3
    @pytest.mark.usefixtures(
        fixtures.setup_vm_adv.__name__
    )
    @pytest.mark.parametrize(
        "obj_type",
        [
            polarion("RHEVM-19609")("template"),
            polarion("RHEVM-19608")(bz({"1406394": {}})("instance_type")),
            polarion("RHEVM-19607")("template_and_instance_type")
        ]
    )
    def test_boot_vm_from_headless_resource(self, obj_type):
        """
        Verify if VM booted from headless resource template/instance_type is
        headless.
        """

        for k, v in vcons_conf.VIRT_CONSOLE_VM_DICT_ADV.iteritems():
            if obj_type == v:
                vm_name = k

                testflow.step(
                    "Verify {vm} VM is in headless state".format(vm=vm_name)
                )
                assert helper.verify_object_headless(
                    object_name=vm_name, object_type="vm"
                ), (
                    "VM did not boot headless from a headless "
                    "{resource}".format(resource=obj_type)
                )


class TestVirtConsoleHeadlessClass(VirtTest):

    @tier2
    @pytest.mark.usefixtures(
        fixtures.setup_vm.__name__
    )
    @pytest.mark.parametrize(
        vcons_conf.HEADLESS_STATE_ARGS,
        vcons_conf.HEADLESS_STATE_PARAMS
    )
    def test_1_headless_verification(
            self, console_protocol, obj_name, obj_type
    ):
        """
        Test to verify VM/Template/Instance_type go headless when consoles are
        deleted.
        """
        testflow.step(
            "Set console type to {console}.".format(console=console_protocol)
        )

        helper.set_console_type(
            console_type=console_protocol,
            object_name=obj_name,
            obj=obj_type
        )

        testflow.step(
            "Remove all consoles from {object_type}.".format(
                object_type=obj_type.upper()
            )
        )
        helper.del_consoles(
            object_name=obj_name,
            obj_type=obj_type
        )

        testflow.step(
            "Verify {obj} is headless".format(obj=obj_type)
        )
        assert helper.verify_object_headless(
            object_name=obj_name, object_type=obj_type
        ), (
            "{obj_type} was not transferred to headless mode after consoles "
            "were deleted.".format(obj_type=obj_type)
        )

        testflow.step(
            "Set console type to {console}.".format(console=console_protocol)
        )

        helper.set_console_type(
            console_type=console_protocol,
            object_name=obj_name,
            obj=obj_type
        )
        testflow.step(
            "Verify {obj} is not headless".format(obj=obj_name)
        )
        assert not helper.verify_object_headless(
            object_name=obj_name, object_type=obj_type
        ), (
            "{obj_type} was not transferred to normal mode from headless "
            "after consoles were added.".format(obj_type=obj_type)
        )

    @tier2
    @polarion("RHEVM-19428")
    @pytest.mark.usefixtures(
        fixtures.setup_vm.__name__,
        fixtures.shutdown_vm.__name__
    )
    def test_2_set_headless_on_active_vm(self):
        """
        Test set headless on Active VM.
        """
        testflow.setup("Activate test VM.")
        assert ll_vms.startVms(
            vms=[vcons_conf.VIRT_CONSOLE_VM_SYSTEM],
            wait_for_status=vcons_conf.VM_UP
        ), "Failed to start test VMs."

        testflow.step("Remove graphics consoles.")
        helper.del_consoles(vcons_conf.VIRT_CONSOLE_VM_SYSTEM, "vm")
        testflow.step("Verify VM is not headless.")
        assert not helper.verify_object_headless(
            object_name=vcons_conf.VIRT_CONSOLE_VM_SYSTEM, object_type="vm"
        ), (
            "VM became headless without restarting it for changes to take "
            "effect."
        )
        testflow.step("Reboot VM.")
        assert ll_vms.reboot_vms(
            vms=[vcons_conf.VIRT_CONSOLE_VM_SYSTEM]
        ), "Failed to reboot VM."
        testflow.step("Verify VM is headless.")
        assert helper.verify_object_headless(
            object_name=vcons_conf.VIRT_CONSOLE_VM_SYSTEM, object_type="vm"
        ), (
            "VM was not transferred to headless state, meaning that changes "
            "did not take effect after reboot."
        )

    @tier2
    @polarion("RHEVM-19530")
    @pytest.mark.usefixtures(
        fixtures.setup_vm.__name__,
        fixtures.shutdown_vm.__name__
    )
    def test_3_set_non_headless_on_active_vm(self):
        """
        Test set non-headless on Active VM.
        """
        testflow.setup("Remove graphics consoles.")
        helper.del_consoles(vcons_conf.VIRT_CONSOLE_VM_SYSTEM, "vm")
        testflow.setup("Activate test VM.")
        assert ll_vms.startVms(
            vms=[vcons_conf.VIRT_CONSOLE_VM_SYSTEM],
            wait_for_status=vcons_conf.VM_UP
        ), "Failed to start test VMs."

        testflow.step("Verify VM is headless.")
        assert helper.verify_object_headless(
            object_name=vcons_conf.VIRT_CONSOLE_VM_SYSTEM, object_type="vm"
        ), (
            "VM booted up not headless."
        )

        testflow.step(
            "Add a %s graphics console to a VM", vcons_conf.DISPLAY_TYPE
        )
        helper.set_console_type(
            vcons_conf.DISPLAY_TYPE,
            vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
            'vm'
        )

        testflow.step("Reboot VM")
        assert ll_vms.reboot_vms(
            vms=[vcons_conf.VIRT_CONSOLE_VM_SYSTEM]
        ), "Failed to reboot VM."

        testflow.step("Verify VM is not headless.")
        assert not helper.verify_object_headless(
            object_name=vcons_conf.VIRT_CONSOLE_VM_SYSTEM, object_type="vm"
        ), (
            "VM was not transferred to non headless state, meaning that "
            "changes did not take effect after reboot."
        )

    @tier2
    @polarion("RHEVM-19426")
    @pytest.mark.usefixtures(
        fixtures.setup_vm.__name__,
        fixtures.shutdown_vm.__name__
    )
    def test_4_migrate_headless_vm(self):
        """
        Test set migrate headless VM.
        """
        testflow.setup("Remove graphics consoles.")
        helper.del_consoles(vcons_conf.VIRT_CONSOLE_VM_SYSTEM, "vm")
        testflow.setup("Activate test VM.")
        assert ll_vms.startVms(
            vms=[vcons_conf.VIRT_CONSOLE_VM_SYSTEM],
            wait_for_status=vcons_conf.VM_UP
        ), "Failed to start test VMs."

        testflow.step("Verify VM is headless.")
        assert helper.verify_object_headless(
            object_name=vcons_conf.VIRT_CONSOLE_VM_SYSTEM, object_type="vm"
        ), (
            "VM booted up not headless."
        )
        testflow.step("Migrate VM.")
        assert ll_vms.migrateVm(
            positive=True, vm=vcons_conf.VIRT_CONSOLE_VM_SYSTEM
        )
        testflow.step("Verify VM is headless after migration procedure.")
        assert helper.verify_object_headless(
            object_name=vcons_conf.VIRT_CONSOLE_VM_SYSTEM, object_type="vm"
        ), (
            "VM did not save its headless state during Migration."
        )

    @tier3
    @polarion("RHEVM-19606")
    @pytest.mark.usefixtures(
        fixtures.setup_vm.__name__,
        fixtures.shutdown_vm.__name__
    )
    def test_5_clone_headless_vm(self):
        """
        Test set clone headless VM.
        """
        testflow.setup("Remove graphics consoles.")
        helper.del_consoles(vcons_conf.VIRT_CONSOLE_VM_SYSTEM, "vm")
        testflow.step("Clone VM.")
        hl_vms.clone_vm(
            positive=True,
            vm=vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
            clone_vm_name=vcons_conf.VIRT_CONSOLE_CLONE_VM_NAME
        )
        testflow.step("Start cloned VM.")
        assert ll_vms.startVms(
            vms=[vcons_conf.VIRT_CONSOLE_CLONE_VM_NAME],
            wait_for_status=vcons_conf.VM_UP
        ), "Failed to start VM."

        testflow.step("Verify cloned VM booted headless.")
        assert helper.verify_object_headless(
            object_name=vcons_conf.VIRT_CONSOLE_CLONE_VM_NAME, object_type="vm"
        ), (
            "Cloned VM was did not boot headless as it should."
        )

    @tier3
    @pytest.mark.usefixtures(
        fixtures.setup_vm.__name__,
        fixtures.shutdown_vm.__name__
    )
    @pytest.mark.parametrize(
        vcons_conf.IMPORT_EXPORT_HEADLESS_ARGS,
        vcons_conf.IMPORT_EXPORT_HEADLESS_VAL

    )
    def test_6_import_export_headless_resource(
            self, obj_type, obj_name
    ):
        """
        Verify resource preserves its headless state after import/export cycle.
        """
        testflow.step("Remove graphics consoles.")
        helper.del_consoles(obj_name, obj_type)

        testflow.step(
            "Export {resource_name} {resource}".format(
                resource_name=obj_name,
                resource=obj_type
            )
        )

        assert helper.export_object(obj_name, obj_type), (
            "Failed to export {resource}".format(resource=obj_type)
        )

        testflow.step(
            "Import {resource_name} {resource}".format(
                resource_name=obj_name,
                resource=obj_type
            )
        )

        assert helper.import_object(obj_name, obj_type), (
            "Failed to import {resource}".format(resource=obj_name)
        )

        testflow.step(
            "Verify imported {resource} is headless.".format(resource=obj_type)
        )

        if obj_type == "vm":
            obj_name_new = vcons_conf.VIRT_CONSOLE_VM_IMPORT_NEW
        else:
            obj_name_new = vcons_conf.VIRT_CONSOLE_TEMPLATE_IMPORT_NEW

        assert helper.verify_object_headless(
            object_name=obj_name_new,
            object_type=obj_type
        ), (
            "Imported {resource} is not headless as it should.".format(
                resource=obj_type
            )
        )
