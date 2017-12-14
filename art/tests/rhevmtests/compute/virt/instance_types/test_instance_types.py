"""
Virt Instnace types test

https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Compute/
3_5_VIRT_Instance_Type
"""
import time

import pytest

import config
from art.rhevm_api.tests_lib.low_level import (
    instance_types as ll_instance_types,
    vms as ll_vms,
    templates as ll_templates
)
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier1,
)
from fixtures import (
    default_instance_type_teardown, remove_test_vms,
    remove_custom_instance_type, remove_test_templates
)
from rhevmtests.compute.virt.helper import compare_dictionaries


class TestInstanceType(VirtTest):

    __test__ = True

    @tier1
    @polarion("RHEVM3-6487")
    @pytest.mark.usefixtures(remove_custom_instance_type.__name__)
    @pytest.mark.instance_types_created(
        instance_types=[config.INSTANCE_TYPE_NAME, config.NAME_AFTER_UPDATE]
    )
    def test_instance_type_sanity(self):
        """
        1. Create a new instance type.
        2. Update instance type.
        3. Run query to get instnace type.
        4. Remove instance type.
        """
        testflow.step(
            "Create a new instance type: %s", config.INSTANCE_TYPE_NAME
        )
        assert ll_instance_types.create_instance_type(
            instance_type_name=config.INSTANCE_TYPE_NAME,
            **config.INSTANCE_TYPE_PARAMS
        )
        time.sleep(config.OBJ_CREATION_TIMEOUT)
        testflow.step(
            "Update instance type: %s", config.INSTANCE_TYPE_NAME
        )
        assert ll_instance_types.update_instance_type(
            instance_type_name=config.INSTANCE_TYPE_NAME,
            name=config.NAME_AFTER_UPDATE, io_threads=4
        )
        instance_type_object = ll_instance_types.get_instance_type_object(
            instance_type=config.NAME_AFTER_UPDATE
        )
        assert instance_type_object is not None
        testflow.step("Verify instance type was set with the correct values")
        config.INSTANCE_TYPE_SANITY_DICT['name'] = config.NAME_AFTER_UPDATE
        actual_dict = {
            'name': instance_type_object.get_name(),
            'sockets':
                instance_type_object.get_cpu().get_topology().get_sockets(),
            'io_threads': instance_type_object.get_io().get_threads()
        }
        assert compare_dictionaries(
            expected=config.INSTANCE_TYPE_SANITY_DICT, actual=actual_dict
        )
        testflow.step("Removing instance type: %s", config.NAME_AFTER_UPDATE)
        assert ll_instance_types.remove_instance_type(
            instance_type_name=config.NAME_AFTER_UPDATE
        )

    @tier1
    @polarion("RHEVM3-6490")
    @pytest.mark.usefixtures(
        default_instance_type_teardown.__name__, remove_test_vms.__name__
    )
    @pytest.mark.instance_type_name(name=config.TINY_INSTANCE_TYPE)
    def test_edit_tiny_instance_type(self):
        """
        1. Update 'tiny' instance type.
        2. Create a vm from 'tiny' instance type.
        3. Verify vm inherited the updated values from 'tiny' instance type.
        """
        testflow.step("Update %s instance type", config.TINY_INSTANCE_TYPE)
        assert ll_instance_types.update_instance_type(
            instance_type_name=config.TINY_INSTANCE_TYPE, highly_available=True
        )
        testflow.step(
            "Create vm: %s from %s instance type",
            config.INSTANCE_TYPE_VM, config.TINY_INSTANCE_TYPE
        )
        assert ll_vms.addVm(
            positive=True, name=config.INSTANCE_TYPE_VM,
            cluster=config.CLUSTER_NAME[0],
            instance_type=config.TINY_INSTANCE_TYPE
        )
        testflow.step(
            "Verify vm: %s inherited the updated values from %s instance type",
            config.INSTANCE_TYPE_VM, config.TINY_INSTANCE_TYPE
        )
        vm = ll_vms.get_vm_obj(config.INSTANCE_TYPE_VM)
        config.EDIT_TINY_INSTANCE_DICT['instance_type_id'] = (
            config.INSTANCE_TYPE_OBJECT.get_id()
        )
        config.EDIT_TINY_INSTANCE_DICT['memory'] = (
            config.INSTANCE_TYPE_OBJECT.get_memory()
        )
        actual_dict = {
            'instance_type_id': vm.get_instance_type().get_id(),
            'memory': vm.get_memory(),
            'high_availability': vm.get_high_availability().get_enabled()
        }
        assert compare_dictionaries(
            expected=config.EDIT_TINY_INSTANCE_DICT, actual=actual_dict
        )

    @tier1
    @polarion("RHEVM3-6488")
    @pytest.mark.usefixtures(
        default_instance_type_teardown.__name__, remove_test_vms.__name__
    )
    @pytest.mark.instance_type_name(name=config.MEDIUM_INSTANCE_TYPE)
    def test_edit_medium_instance_type(self):
        """
        1. Update 'medium' instance type.
        2. Create a vm from 'medium' instance type.
        3. Verify vm inherited the updated values from 'medium' instance type.
        """
        testflow.step("Update %s instance type", config.MEDIUM_INSTANCE_TYPE)
        assert ll_instance_types.update_instance_type(
            instance_type_name=config.MEDIUM_INSTANCE_TYPE,
            cpu_sockets=4, cpu_cores=2, cpu_threads=2,
            custom_emulated_machine='pc', custom_cpu_model='Conroe'
        )
        testflow.step(
            "Create vm: %s from %s instance type",
            config.INSTANCE_TYPE_VM, config.MEDIUM_INSTANCE_TYPE
        )
        assert ll_vms.addVm(
            positive=True, name=config.INSTANCE_TYPE_VM,
            cluster=config.CLUSTER_NAME[0],
            instance_type=config.MEDIUM_INSTANCE_TYPE
        )
        testflow.step(
            "Verify vm: %s inherited the updated values from %s instance type",
            config.INSTANCE_TYPE_VM, config.MEDIUM_INSTANCE_TYPE
        )
        vm = ll_vms.get_vm_obj(config.INSTANCE_TYPE_VM)
        config.EDIT_MEDIUM_INSTANCE_DICT['instance_type_id'] = (
            config.INSTANCE_TYPE_OBJECT.get_id()
        )
        actual_dict = {
            'instance_type_id': vm.get_instance_type().get_id(),
            'sockets': vm.get_cpu().get_topology().get_sockets(),
            'cores': vm.get_cpu().get_topology().get_cores(),
            'threads': vm.get_cpu().get_topology().get_threads()
        }
        assert compare_dictionaries(
            expected=config.EDIT_MEDIUM_INSTANCE_DICT, actual=actual_dict
        )

    @tier1
    @polarion("RHEVM3-6489")
    @pytest.mark.usefixtures(
        default_instance_type_teardown.__name__, remove_test_vms.__name__
    )
    @pytest.mark.instance_type_name(name=config.SMALL_INSTANCE_TYPE)
    @pytest.mark.skipif(
        condition=config.PPC_ARCH,
        reason=config.PPC_SKIP_MESSAGE
    )
    def test_edit_small_instance_type(self):
        """
        1. Update 'small' instance type.
        2. Create a vm from 'small' instance type.
        3. Verify vm inherited the updated values from 'small' instance type.
        """
        testflow.step("Update %s instance type", config.SMALL_INSTANCE_TYPE)
        assert ll_instance_types.update_instance_type(
            instance_type_name=config.SMALL_INSTANCE_TYPE, display_type='vnc',
            serial_console=True, boot='cdrom',
            smartcard_enabled=config.EDIT_SMALL_INSTANCE_DICT['smartcards'],
            single_qxl_pci=config.EDIT_SMALL_INSTANCE_DICT['single_qxl_pci'],
            soundcard_enabled=config.EDIT_SMALL_INSTANCE_DICT['soundcard'],
        )
        testflow.step(
            "Create vm: %s from %s instance type",
            config.INSTANCE_TYPE_VM, config.SMALL_INSTANCE_TYPE
        )
        assert ll_vms.addVm(
            positive=True, name=config.INSTANCE_TYPE_VM,
            cluster=config.CLUSTER_NAME[0], os_type=config.VM_OS_TYPE,
            instance_type=config.SMALL_INSTANCE_TYPE
        )
        testflow.step(
            "Verify vm: %s inherited the updated values from %s instance type",
            config.INSTANCE_TYPE_VM, config.SMALL_INSTANCE_TYPE
        )
        vm = ll_vms.get_vm_obj(
            vm_name=config.INSTANCE_TYPE_VM, all_content=True
        )
        config.EDIT_SMALL_INSTANCE_DICT['instance_type_id'] = (
            config.INSTANCE_TYPE_OBJECT.get_id()
        )
        actual_dict = {
            'instance_type_id': vm.get_instance_type().get_id(),
            'serial_console': vm.get_console().get_enabled(),
            'display': vm.get_display().get_type(),
            'smartcards': vm.get_display().get_smartcard_enabled(),
            'single_qxl_pci': vm.get_display().get_single_qxl_pci(),
            'soundcard': vm.get_soundcard_enabled(),
            'boot_devices': vm.get_os().get_boot().get_devices().get_device()
        }
        assert compare_dictionaries(
            expected=config.EDIT_SMALL_INSTANCE_DICT, actual=actual_dict
        )

    @tier1
    @polarion("RHEVM3-6493")
    @pytest.mark.usefixtures(
        default_instance_type_teardown.__name__, remove_test_vms.__name__
    )
    @pytest.mark.instance_type_name(name=config.LARGE_INSTANCE_TYPE)
    def test_edit_large_instance_type(self):
        """
        1. Update 'large' instance type.
        2. Create a vm from 'large' instance type.
        3. Verify vm inherited the updated values from 'large' instance type.
        """
        testflow.step("Update %s instance type", config.LARGE_INSTANCE_TYPE)
        assert ll_instance_types.update_instance_type(
            instance_type_name=config.LARGE_INSTANCE_TYPE,
            migration_downtime=100,
            migration_policy='00000000-0000-0000-0000-000000000000',
        )
        testflow.step(
            "Create vm: %s from %s instance type",
            config.INSTANCE_TYPE_VM, config.LARGE_INSTANCE_TYPE
        )
        assert ll_vms.addVm(
            positive=True, name=config.INSTANCE_TYPE_VM,
            cluster=config.CLUSTER_NAME[0],
            instance_type=config.LARGE_INSTANCE_TYPE
        )
        testflow.step(
            "Verify vm: %s inherited the updated values from %s instance type",
            config.INSTANCE_TYPE_VM, config.LARGE_INSTANCE_TYPE
        )
        vm = ll_vms.get_vm_obj(vm_name=config.INSTANCE_TYPE_VM)
        config.EDIT_LARGE_INSTANCE_DICT['instance_type_id'] = (
            config.INSTANCE_TYPE_OBJECT.get_id()
        )
        actual_dict = {
            'instance_type_id': vm.get_instance_type().get_id(),
            'migration_policy': vm.get_migration().get_policy().get_id(),
            'migration_downtime': vm.get_migration_downtime()
        }
        assert compare_dictionaries(
            expected=config.EDIT_LARGE_INSTANCE_DICT, actual=actual_dict
        )

    @tier1
    @polarion("RHEVM3-6491")
    @pytest.mark.usefixtures(
        default_instance_type_teardown.__name__, remove_test_vms.__name__
    )
    @pytest.mark.instance_type_name(name=config.XLARGE_INSTANCE_TYPE)
    def test_edit_xlarge_instance_type(self):
        """
        1. Update 'XLarge' instance type.
        2. Create a vm from 'XLarge' instance type.
        3. Verify vm inherited the updated values from 'XLarge' instance type.
        """
        testflow.step("Update %s instance type", config.XLARGE_INSTANCE_TYPE)
        assert ll_instance_types.update_instance_type(
            instance_type_name=config.XLARGE_INSTANCE_TYPE,
            memory=2 * config.GB, memory_guaranteed=2 * config.GB,
            io_threads=2, ballooning=True, virtio_scsi=True
        )
        testflow.step(
            "Create vm: %s from %s instance type",
            config.INSTANCE_TYPE_VM, config.XLARGE_INSTANCE_TYPE
        )
        assert ll_vms.addVm(
            positive=True, name=config.INSTANCE_TYPE_VM,
            cluster=config.CLUSTER_NAME[0],
            instance_type=config.XLARGE_INSTANCE_TYPE
        )
        testflow.step(
            "Verify vm: %s inherited the updated values from %s instance type",
            config.INSTANCE_TYPE_VM, config.XLARGE_INSTANCE_TYPE
        )
        vm = ll_vms.get_vm_obj(
            vm_name=config.INSTANCE_TYPE_VM, all_content=True
        )
        config.EDIT_XLARGE_INSTANCE_DICT['instance_type_id'] = (
            config.INSTANCE_TYPE_OBJECT.get_id()
        )
        actual_dict = {
            'instance_type_id': vm.get_instance_type().get_id(),
            'io_threads': vm.get_io().get_threads(), 'memory': vm.get_memory(),
            'memory_guaranteed': vm.get_memory_policy().get_guaranteed(),
            'balooning': vm.get_memory_policy().get_ballooning(),
            'virtio_scsi': vm.get_virtio_scsi().get_enabled()
        }
        assert compare_dictionaries(
            expected=config.EDIT_XLARGE_INSTANCE_DICT, actual=actual_dict
        )

    @tier1
    @polarion("RHEVM3-6495")
    @pytest.mark.usefixtures(
        default_instance_type_teardown.__name__, remove_test_vms.__name__
    )
    @pytest.mark.instance_type_name(name=config.SMALL_INSTANCE_TYPE)
    def test_instance_type_mandetory_fields(self):
        """
        1. Create a vm from 'small' instance type
        2. Update a vm value which isn't an instance type mandatory field.
        3. Update a vm value which is an instance type mandatory field.
        4. Repeat step 3 with different arguments.
        """
        testflow.step(
            "Create vm: %s from %s instance type",
            config.INSTANCE_TYPE_VM, config.SMALL_INSTANCE_TYPE
        )
        assert ll_vms.addVm(
            positive=True, name=config.INSTANCE_TYPE_VM,
            cluster=config.CLUSTER_NAME[0],
            instance_type=config.SMALL_INSTANCE_TYPE
        )
        testflow.step("updating non mendatory fieleds on the vm")
        assert ll_vms.updateVm(
            positive=True, vm=config.INSTANCE_TYPE_VM,
            virtio_scsi=True, display_type='vnc'
        )
        testflow.step("Updating instance type's mandatory fields on the vm")
        assert ll_vms.updateVm(
            positive=True, vm=config.INSTANCE_TYPE_VM, memory=8 * config.GB,
            memory_guaranteed=8 * config.GB, compare=False
        )
        testflow.step(
            "Verifying that the update was ignored and instance type mandatory"
            "fields values persist in the vm"
        )
        vm_object = ll_vms.get_vm_obj(vm_name=config.INSTANCE_TYPE_VM)
        assert vm_object.get_memory() == 2 * config.GB
        assert ll_vms.updateVm(
            positive=True, vm=config.INSTANCE_TYPE_VM, cpu_threads=2,
            cpu_sockets=2, cpu_cores=2, compare=False
        )
        vm_object = ll_vms.get_vm_obj(vm_name=config.INSTANCE_TYPE_VM)
        assert vm_object.get_cpu().get_topology().get_sockets() == 1
        assert ll_vms.updateVm(
            positive=True, vm=config.INSTANCE_TYPE_VM, high_available=True,
            compare=False
        )
        vm_object = ll_vms.get_vm_obj(vm_name=config.INSTANCE_TYPE_VM)
        assert vm_object.get_high_availability().get_enabled() is False

    @tier1
    @polarion("RHEVM3-15089")
    @pytest.mark.usefixtures(
        remove_test_templates.__name__, remove_test_vms.__name__,
        remove_custom_instance_type.__name__,
    )
    @pytest.mark.instance_types_created(
        instance_types=[config.INSTANCE_TYPE_NAME]
    )
    def test_create_vm_with_instance_type_and_template(self):
        """
        1. Create a new instance type with some values.
        2. Create a new vm with all the values different from the new instance
            type create on step 1.
        3. Create a template from the vm from step 2.
        4. Create a new vm using both the instance type from step 1 and the
            template from step 3.
        5. Verify that the vm's HW parameters values are inherited from the
            instance type and not from the template.
        """
        testflow.step(
            "Create a new instance type: %s", config.INSTANCE_TYPE_NAME
        )
        assert ll_instance_types.create_instance_type(
            instance_type_name=config.INSTANCE_TYPE_NAME,
            **config.INSTANCE_TYPE_PARAMS
        )
        testflow.step(
            "Create vm: %s in order to create a new template from it",
            config.TEMPLATE_VM
        )
        assert ll_vms.addVm(
            positive=True, name=config.TEMPLATE_VM,
            cluster=config.CLUSTER_NAME[0],
            os_type=config.VM_OS_TYPE, **config.TEMPLATE_PARAMS
        )
        testflow.step(
            "Create template: %s from vm: %s", config.NEW_TEMPLATE_NAME,
            config.TEMPLATE_VM
        )
        assert ll_templates.createTemplate(
            positive=True, name=config.NEW_TEMPLATE_NAME, vm=config.TEMPLATE_VM
        )
        testflow.step(
            "Creating vm: %s using both instance type: %s and template: %s",
            config.INSTANCE_TYPE_VM, config.INSTANCE_TYPE_NAME,
            config.NEW_TEMPLATE_NAME
        )
        assert ll_vms.addVm(
            positive=True, name=config.INSTANCE_TYPE_VM,
            cluster=config.CLUSTER_NAME[0],
            instance_type=config.INSTANCE_TYPE_NAME,
            template=config.NEW_TEMPLATE_NAME
        )
        testflow.step(
            "Verify that the vm inherited the values from the instance type"
        )
        vm = ll_vms.get_vm_obj(
            vm_name=config.INSTANCE_TYPE_VM, all_content=True
        )
        actual_dict = {
            'io_threads': vm.get_io().get_threads(),
            'sockets': vm.get_cpu().get_topology().get_sockets(),
            'cores': vm.get_cpu().get_topology().get_cores(),
            'threads': vm.get_cpu().get_topology().get_threads(),
            'memory': vm.get_memory(),
            'memory_guaranteed': vm.get_memory_policy().get_guaranteed(),
            'high_availability': vm.get_high_availability().get_enabled()
        }
        assert compare_dictionaries(
            expected=config.INSTANCE_TYPE_AND_TEMPLATE_DICT, actual=actual_dict
        )
