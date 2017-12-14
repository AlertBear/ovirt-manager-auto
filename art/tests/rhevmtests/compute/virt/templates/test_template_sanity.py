"""
Expension of template test suite.
The following test cases test template version feature
"""
import logging
import pytest
import config as conf
from fixtures import (
    remove_existing_templates, supply_base_templates, supply_vm, init_module,
    add_user_role_permission_for_base_vm, restore_base_template_configurations,
    add_user_role_permission_for_template, remove_vm, supply_dummy_template,
    supply_dummy_dc_cluster, remove_dummy_template,
    remove_template_admin_role_from_group
)
import art.core_api.validator as validator
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    mla as ll_mla,
    templates as ll_templates
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier1,
)
from art.unittest_lib import testflow, VirtTest

logger = logging.getLogger('virt.templates.test_template_sanity')


class TestTemplateSanity(VirtTest):

    __test__ = True

    @tier1
    @pytest.mark.usefixtures(
        init_module.__name__, remove_existing_templates.__name__
    )
    @polarion("RHEVM-15177")
    def test_01_create_template(self):
        """
        1. Create template from VM
        """
        testflow.step(
            "Create template: %s from vm: %s",
            conf.TEMPLATE_LIST[0], conf.BASE_VM_1
        )
        assert ll_templates.createTemplate(
            True, vm=conf.BASE_VM_1, name=conf.TEMPLATE_LIST[0]
        )

    @tier1
    @pytest.mark.usefixtures(add_user_role_permission_for_base_vm.__name__)
    @polarion("RHEVM-15179")
    def test_02_create_template_copy_vm_permission(self):
        """
        1. Create template from VM + copy vm's permissions
        2. Verify that template got vm's permissions
        """
        testflow.step(
            "Create template: %s from vm: %s, copy vm's permissions.",
            conf.TEMPLATE_LIST[0], conf.BASE_VM_1
        )
        assert ll_templates.createTemplate(
            True, vm=conf.BASE_VM_1, name=conf.TEMPLATE_LIST[0],
            copy_permissions=True
        )
        template_object = ll_templates.get_template_obj(
            template_name=conf.TEMPLATE_LIST[0]
        )
        user_name = '%s@%s' % (conf.USER, conf.USER_DOMAIN)
        testflow.step(
            "Verify that template: %s got %s permissions for user: %s",
            conf.TEMPLATE_LIST[0], conf.USER_ROLE, user_name
        )
        assert ll_mla.has_user_or_group_permissions_on_object(
            user_name, template_object, conf.USER_ROLE
        )

    @tier1
    @pytest.mark.usefixtures(
        supply_base_templates.__name__,
        restore_base_template_configurations.__name__
    )
    @pytest.mark.template_marker(template_versions=[1])
    @polarion("RHEVM3-12280")
    def test_03_edit_template(self):
        """
        Edit template - add description
        """
        testflow.step(
            "Adding description to template: %s", conf.TEMPLATE_LIST[0]
        )
        assert ll_templates.updateTemplate(
            True, conf.TEMPLATE_LIST[0], description='test'

        )

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.template_marker(template_versions=[1])
    @polarion("RHEVM-15182")
    def test_04_remove_template(self):
        """
        1. Template is delete protected - created as such in setup
        2. Negative - remove template - fails due to delete protection
        3. Update template - disable delete protection
        4. Positive - remove template
        """
        testflow.step(
            "Negative: Attempting to remove template: "
            "%s, template is delete protected, "
            "expecting action to fail", conf.TEMPLATE_LIST[0]
        )
        assert not ll_templates.remove_template(True, conf.TEMPLATE_LIST[0])
        testflow.step(
            "updating template: %s, disabling delete protection",
            conf.TEMPLATE_LIST[0]
        )
        assert ll_templates.updateTemplate(
            True, conf.TEMPLATE_LIST[0], protected=not conf.DELETE_PROTECTED
        )
        testflow.step(
            "Remove template: %s, expecting action to succeed",
            conf.TEMPLATE_LIST[0]
        )
        assert ll_templates.remove_template(True, conf.TEMPLATE_LIST[0])

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.template_marker(template_versions=[1])
    @polarion("RHEVM3-5373")
    def test_05_create_template_version(self):
        """
        1. Create a new template version of an existing template
        """
        testflow.step(
            "Creating a new template version of template: %s from vm: %s",
            conf.TEMPLATE_LIST[0], conf.BASE_VM_2
        )
        assert ll_templates.createTemplate(
            positive=True, name=conf.TEMPLATE_LIST[0],
            new_version=True, vm=conf.BASE_VM_2
        )

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.template_marker(template_versions=[1])
    @polarion("RHEVM-15183")
    def test_06_template_inheritance(self):
        """
        1. Verify that the template has inherited all the parameters values
        from the vm.
        """
        vm_object = ll_vms.get_vm(conf.BASE_VM_1)
        template_object = ll_templates.get_template_obj(
            conf.TEMPLATE_LIST[0]
        )
        testflow.step(
            "Verifying that template: %s (version %s) inherited the following"
            "parameters values from vm: %s: %s",
            conf.TEMPLATE_LIST[0], 1, conf.BASE_VM_1, conf.BASE_VM_1_PARAMETERS
        )
        assert validator.compareElements(
            vm_object, template_object, logger=logger, root='Comparator',
            ignore=conf.TEMPLATE_VALIDATOR_IGNORE_LIST
        )

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.template_marker(template_versions=[1, 2])
    @polarion("RHEVM-15186")
    def test_07_template_version_inheritance(self):
        """
        1. Verify that the template version (2) has inherited all the
        parameters values from the vm.
        """
        vm_object = ll_vms.get_vm(conf.BASE_VM_2)
        template_object = ll_templates.get_template_obj(
            conf.TEMPLATE_LIST[0], version=2
        )
        testflow.step(
            "Verifying that template: %s (version %s) inherited the following"
            "parameters values from vm: %s: %s",
            conf.TEMPLATE_LIST[0], 2, conf.BASE_VM_2, conf.BASE_VM_2_PARAMETERS
        )
        assert validator.compareElements(
            vm_object, template_object, logger=logger, root='Comparator',
            ignore=conf.TEMPLATE_VALIDATOR_IGNORE_LIST
        )

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.template_marker(template_versions=[1])
    @polarion("RHEVM3-5369")
    def test_08_create_vm_from_base_template(self):
        """
        1. Create a vm from template base version
        """
        testflow.step(
            "Create vm: %s from template: %s version: %s",
            conf.VM_NO_DISK_1, conf.TEMPLATE_LIST[0], 1
        )
        assert ll_vms.addVm(
            True, name=conf.VM_NO_DISK_1, template=conf.TEMPLATE_LIST[0],
            template_version=1, cluster=conf.CLUSTER_NAME[0]
        )

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.template_marker(template_versions=[2])
    @polarion("RHEVM3-5371")
    def test_09_create_vm_from_template_version(self):
        """
        1. Create a vm from template version (2)
        """
        testflow.step(
            "Create vm: %s from template: %s version: %s",
            conf.VM_NO_DISK_2, conf.TEMPLATE_LIST[0], 2
        )
        assert ll_vms.addVm(
            True, name=conf.VM_NO_DISK_2, template=conf.TEMPLATE_LIST[0],
            template_version=2, cluster=conf.CLUSTER_NAME[0]
        )

    @tier1
    @pytest.mark.usefixtures(
        supply_base_templates.__name__, supply_vm.__name__
    )
    @pytest.mark.template_marker(template_versions=[1])
    @pytest.mark.vm_marker(vm_name=conf.VM_NO_DISK_1, template_version=1)
    @polarion("RHEVM-15188")
    def test_10_vm_inheritance_from_template(self):
        """
        1. Verify that the vm has inherited all the parameters values from
        the template base version it was created from
        """
        template_object = ll_templates.get_template_obj(
            conf.TEMPLATE_LIST[0]
        )
        vm_object = ll_vms.get_vm(conf.VM_NO_DISK_1)
        testflow.step(
            "Verifying that vm: %s inherited the following"
            "parameters values from template: %s (version %s): %s",
            conf.VM_NO_DISK_1, conf.TEMPLATE_LIST[0], 1,
            conf.BASE_VM_1_PARAMETERS
        )
        assert validator.compareElements(
            template_object, vm_object, logger=logger, root='Comparator',
            ignore=conf.TEMPLATE_VALIDATOR_IGNORE_LIST
        )

    @tier1
    @pytest.mark.usefixtures(
        supply_base_templates.__name__, supply_vm.__name__
    )
    @pytest.mark.template_marker(template_versions=[2])
    @pytest.mark.vm_marker(vm_name=conf.VM_NO_DISK_2, template_version=2)
    @polarion("RHEVM-15189")
    def test_11_vm_inheritance_from_template_version(self):
        """
        1. Verify that the vm has inherited all the parameters values from
        the template sub-version (2) it was created from
        """
        template_object = ll_templates.get_template_obj(
            conf.TEMPLATE_LIST[0], version=2
        )
        vm_object = ll_vms.get_vm(conf.VM_NO_DISK_2)
        testflow.step(
            "Verifying that vm: %s inherited the following"
            "parameters values from template: %s (version %s): %s",
            conf.VM_NO_DISK_2, conf.TEMPLATE_LIST[0], 2,
            conf.BASE_VM_2_PARAMETERS
        )
        assert validator.compareElements(
            template_object, vm_object, logger=logger, root='Comparator',
            ignore=conf.TEMPLATE_VALIDATOR_IGNORE_LIST
        )

    @tier1
    @pytest.mark.usefixtures(
        supply_base_templates.__name__, supply_vm.__name__
    )
    @pytest.mark.template_marker(template_versions=[2])
    @pytest.mark.vm_marker(vm_name=conf.VM_NO_DISK_2, template_version=2)
    @polarion("RHEVM-15190")
    def test_12_negative_remove_template_used_by_vm(self):
        """
        Attempt to remove a template that is being used by a vm
        """
        testflow.step(
            "Negative: Attempt to remove template: %s version: %s that is "
            "being used "
            "by a vm: %s", conf.TEMPLATE_LIST[0], 2, conf.VM_NO_DISK_2
        )
        assert not ll_templates.remove_template(
            True, conf.TEMPLATE_LIST[0], version_number=2
        )

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.template_marker(template_versions=[1, 2])
    @polarion("RHEVM3-13966")
    def test_13_query_template(self):
        """
        1. Run query - search for templates by name
        """
        testflow.step(
            "Using API query to get templates named: %s", conf.TEMPLATE_LIST[0]
        )
        assert ll_templates.searchForTemplate(
            True,
            expected_count=2,
            query_key='name',
            query_val=conf.TEMPLATE_LIST[0],
            key_name='name',
        )

    @tier1
    @pytest.mark.usefixtures(
        supply_base_templates.__name__,
        add_user_role_permission_for_template.__name__, remove_vm.__name__
    )
    @pytest.mark.template_marker(template_versions=[2])
    @pytest.mark.vm_marker(vm_name=conf.VM_NO_DISK_2)
    @polarion("RHEVM-15191")
    def test_14_create_vm_copy_template_permission(self):
        """
        1. Create vm from template - copy template permissions.
        2. Verify vm got template's permission
        """
        testflow.step(
            "Creating vm: %s from template: %s version: %s, Copying template's"
            "permissions", conf.VM_NO_DISK_2, conf.TEMPLATE_LIST[0], 2
        )
        assert ll_vms.addVm(
            True, name=conf.VM_NO_DISK_2, template=conf.TEMPLATE_LIST[0],
            template_version=2, cluster=conf.CLUSTER_NAME[0],
            copy_permissions=True
        )
        vm_object = ll_vms.get_vm(conf.VM_NO_DISK_2)
        user_name = '%s@%s' % (conf.USER, conf.USER_DOMAIN)
        testflow.step(
            "Verify that vm: %s got %s permissions for user: %s",
            conf.VM_NO_DISK_2, conf.USER_ROLE, user_name
        )
        assert ll_mla.has_user_or_group_permissions_on_object(
            user_name, vm_object, conf.USER_ROLE
        )

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.template_marker(template_versions=[1])
    @polarion("RHEVM3-12276")
    def test_15_create_template_with_existing_name_in_dc(self):
        """
        1. Negative - Attempt to create a template with a name existing in dc
        """
        testflow.step(
            "Negative - Attempt to create a template with a name that exists "
            "in dc"
        )
        assert ll_templates.createTemplate(
            False, vm=conf.BASE_VM_2, name=conf.TEMPLATE_LIST[0]
        )

    @tier1
    @pytest.mark.usefixtures(supply_dummy_template.__name__)
    @polarion("RHEVM3-12277")
    def test_16_update_template_with_existing_name_in_dc(self):
        """
        1. Negative - Attempt to update a template to a name that exists in dc
        """
        testflow.step(
            "Negative - Attempt to update a template to a name that exists "
            "in dc"
        )
        assert ll_templates.updateTemplate(
            False, conf.TEMPLATE_LIST[1], name=conf.TEMPLATE_LIST[0]
        )

    @tier1
    @pytest.mark.usefixtures(supply_dummy_dc_cluster.__name__)
    @polarion("RHEVM3-12278")
    def test_17_create_template_with_wrong_dc(self):
        """
        1. Negative - Attempt to create a template on a different dc/cluster
        """
        testflow.step(
            "Negative - Attempt to create a template on a different dc/cluster"
        )
        assert ll_templates.createTemplate(
            positive=False, vm=conf.BASE_VM_2, name=conf.TEMPLATE_LIST[1],
            cluster=conf.DUMMY_CLUSTER
        )

    @tier1
    @pytest.mark.usefixtures(remove_dummy_template.__name__)
    @polarion("RHEVM3-12279")
    def test_18_create_template_on_specific_sd(self):
        """
        1. Create template - specify storage domain
        """
        testflow.step("Create template - specify storage domain")
        assert ll_templates.createTemplate(
            positive=True, vm=conf.BASE_VM_2, name=conf.TEMPLATE_LIST[1],
            storagedomain=conf.NON_MASTER_DOMAIN
        )

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.usefixtures(remove_template_admin_role_from_group.__name__)
    @pytest.mark.template_marker(template_versions=[1])
    @polarion("RHEVM3-12282")
    def test_19_add_template_permissions_to_group(self):
        """
        1. Add templateAdminRole to group 'Everyone'
        """
        template_object = ll_templates.get_template_obj(
            conf.TEMPLATE_LIST[0]
        )
        testflow.step("Add templateAdminRole to group 'Everyone'")
        assert ll_mla.addUserPermitsForObj(
            True, conf.GROUP_EVERYONE, conf.TEMPLATE_ROLE, template_object,
            True
        )

    @tier1
    @pytest.mark.usefixtures(supply_dummy_template.__name__)
    @polarion("RHEVM3-12283")
    def test_20_export_import_template_sanity(self):
        """
        1. Export template.
        2. Export template again - override.
        3. Remove template from SD.
        4. Import template from export domain back to SD.
        """
        testflow.step("Export template: %s", conf.TEMPLATE_LIST[1])
        assert ll_templates.exportTemplate(
            True, conf.TEMPLATE_LIST[1], conf.EXPORT_DOMAIN_NAME
        )
        testflow.step("Export template: %s - override", conf.TEMPLATE_LIST[1])
        assert ll_templates.exportTemplate(
            True, conf.TEMPLATE_LIST[1], conf.EXPORT_DOMAIN_NAME,
            exclusive='true'
        )
        testflow.step("Remove template: %s", conf.TEMPLATE_LIST[1])
        assert ll_templates.remove_template(True, conf.TEMPLATE_LIST[1])
        testflow.step(
            "Import template: %s from export domain back to SD",
            conf.TEMPLATE_LIST[1]
        )
        assert ll_templates.import_template(
            True, conf.TEMPLATE_LIST[1], conf.EXPORT_DOMAIN_NAME,
            conf.STORAGE_NAME[0], conf.CLUSTER_NAME[0]
        )

    @tier1
    @pytest.mark.usefixtures(supply_base_templates.__name__)
    @pytest.mark.template_marker(template_versions=[1])
    @polarion("RHEVM3-12284")
    def test_21_crud_template_nic(self):
        """
        1. Add nic to template.
        2. Update template's nic - change name.
        3. Remove template's nic.
        """
        testflow.step(
            "Add nic: %s to template: %s", conf.TEMPLATE_NIC,
            conf.TEMPLATE_LIST[0]
        )
        assert ll_templates.addTemplateNic(
            True, conf.TEMPLATE_LIST[0], name=conf.TEMPLATE_NIC,
            network=conf.MGMT_BRIDGE
        )
        testflow.step(
            "Update nic: %s from template: %s. Change name to: %s",
            conf.TEMPLATE_NIC, conf.TEMPLATE_LIST[0], conf.UPDATED_NIC
        )
        assert ll_templates.updateTemplateNic(
            True, conf.TEMPLATE_LIST[0], conf.TEMPLATE_NIC,
            name=conf.UPDATED_NIC
        )
        testflow.step(
            "Remove nic: %s from template: %s",
            conf.TEMPLATE_NIC, conf.TEMPLATE_LIST[0]
        )
        assert ll_templates.removeTemplateNic(
            True, conf.TEMPLATE_LIST[0], conf.UPDATED_NIC
        )
