"""
Testing copy permissions feauture.
Every case create vm/template and check if permissions from it are/aren't
copied, when copy_permissions flag is/isn't provided.
"""
import pytest

from art.rhevm_api.tests_lib.low_level import mla, templates, vms
from art.test_handler.tools import polarion
from art.unittest_lib import attr, testflow

import common
import config


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        for user_name in config.USER_NAMES[:2]:
            testflow.teardown(
                "Removing user %s@%s.", user_name, config.USER_DOMAIN
            )
            common.remove_user(True, user_name)

        testflow.teardown("Removing VM %s.", config.VM_NAME)
        vms.removeVm(True, config.VM_NAME)

        testflow.teardown("Removing template %s.", config.TEMPLATE_NAMES[0])
        templates.remove_template(True, config.TEMPLATE_NAMES[0])

    request.addfinalizer(finalize)

    for user_name in config.USER_NAMES[:2]:
        testflow.setup(
            "Adding user %s@%s.", user_name, config.USER_DOMAIN
        )
        common.add_user(True, user_name, config.USER_DOMAIN)

    testflow.setup("Adding VM %s.", config.VM_NAME)
    vms.createVm(
        positive=True,
        vmName=config.VM_NAME,
        cluster=config.CLUSTER_NAME[0],
        storageDomainName=config.MASTER_STORAGE,
        provisioned_size=config.GB,
        network=config.MGMT_BRIDGE
    )

    testflow.setup("Creating template %s.", config.TEMPLATE_NAMES[0])
    templates.createTemplate(
        True,
        vm=config.VM_NAME,
        name=config.TEMPLATE_NAMES[0],
        cluster=config.CLUSTER_NAME[0]
    )

    testflow.setup(
        "Adding cluster %s permissions for user %s@%s.",
        config.CLUSTER_NAME[0], config.USER_NAMES[0], config.USER_DOMAIN
    )
    mla.addClusterPermissionsToUser(
        True,
        config.USER_NAMES[0],
        config.CLUSTER_NAME[0]
    )

    testflow.setup(
        "Adding cluster %s permissions for user %s@%s.",
        config.CLUSTER_NAME[0], config.USER_NAMES[1], config.USER_DOMAIN
    )
    mla.addClusterPermissionsToUser(
        True,
        config.USER_NAMES[1],
        config.CLUSTER_NAME[0],
    )

    testflow.setup(
        "Adding vm permission role %s to user %s@%s.",
        config.role.UserRole, config.USER_NAMES[0], config.USER_DOMAIN
    )
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[0],
        config.VM_NAME,
        role=config.role.UserRole
    )

    testflow.setup(
        "Adding vm permission role %s to user %s@%s.",
        config.role.UserTemplateBasedVm,
        config.USER_NAMES[0], config.USER_DOMAIN
    )
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[0],
        config.VM_NAME,
        role=config.role.UserTemplateBasedVm
    )

    testflow.setup(
        "Adding vm permission role %s to user %s@%s.",
        config.role.TemplateAdmin,
        config.USER_NAMES[0], config.USER_DOMAIN
    )
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[0],
        config.VM_NAME,
        role=config.role.TemplateAdmin
    )

    testflow.setup(
        "Adding vm permission role %s to user %s@%s.",
        config.role.TemplateAdmin,
        config.USER_NAMES[1], config.USER_DOMAIN
    )
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[1],
        config.VM_NAME,
        role=config.role.TemplateAdmin
    )

    testflow.setup(
        "Adding vm permission role %s to user %s@%s.",
        config.role.DiskCreator,
        config.USER_NAMES[1], config.USER_DOMAIN
    )
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[1],
        config.VM_NAME,
        role=config.role.DiskCreator
    )

    testflow.setup(
        "Adding template permission role %s to user %s@%s",
        config.role.PowerUserRole,
        config.USER_NAMES[0], config.USER_DOMAIN
    )
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[0],
        config.TEMPLATE_NAMES[0],
        role=config.role.PowerUserRole
    )

    testflow.setup(
        "Adding template permission role %s to user %s@%s.",
        config.role.UserRole,
        config.USER_NAMES[0], config.USER_DOMAIN
    )
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[0],
        config.TEMPLATE_NAMES[0],
        role=config.role.UserRole
    )

    testflow.setup(
        "Adding template permission role %s to user %s@%s.",
        config.role.TemplateAdmin,
        config.USER_NAMES[1], config.USER_DOMAIN
    )
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[1],
        config.TEMPLATE_NAMES[0],
        role=config.role.TemplateAdmin
    )

    testflow.setup(
        "Adding template permission role %s to user %s@%s.",
        config.role.UserTemplateBasedVm,
        config.USER_NAMES[0], config.USER_DOMAIN
    )
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[0],
        config.TEMPLATE_NAMES[0],
        role=config.role.UserTemplateBasedVm
    )

    testflow.setup(
        "Adding template permission role %s to user %s@%s.",
        config.role.TemplateOwner,
        config.USER_NAMES[1], config.USER_DOMAIN
    )
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[1],
        config.TEMPLATE_NAMES[0],
        role=config.role.TemplateOwner
    )

    testflow.setup(
        "Adding datacenter permission role %s to user %s@%s.",
        config.role.DataCenterAdmin,
        config.USER_NAMES[1], config.USER_DOMAIN
    )
    mla.addPermissionsForDataCenter(
        True,
        config.USER_NAMES[1],
        config.DC_NAME[0],
        role=config.role.DataCenterAdmin
    )


@attr(tier=2)
class CopyPermissions299326(common.BaseTestCase):
    """ Check if permissions are copied to vm when enabled """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(CopyPermissions299326, cls).setup_class(request)

        def finalize():
            testflow.teardown("Removing VM %s.", config.VM_NAMES[0])
            vms.removeVm(True, config.VM_NAMES[0])

        request.addfinalizer(finalize)

        testflow.setup("Creating VM %s.", config.VM_NAMES[0])
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            template=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            copy_permissions=True,
            network=config.MGMT_BRIDGE,
        )

    @polarion("RHEVM3-7367")
    def test_create_vm_with_copy_permissions_option(self):
        """ create vm with copy permissions option """
        testflow.step("Checking for copied permissions.")
        common.check_for_vm_permissions(
            True,
            config.USER1_VM_ROLES,
            config.USER2_VM_ROLES
        )


@attr(tier=2)
class CopyPermissions299330(common.BaseTestCase):
    """ Check if permissions are copied to vm when disabled """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(CopyPermissions299330, cls).setup_class(request)

        def finalize():
            testflow.teardown("Removing VM %s.", config.VM_NAMES[0])
            vms.removeVm(True, config.VM_NAMES[0])

        request.addfinalizer(finalize)

        testflow.setup("Creating VM %s.", config.VM_NAMES[0])
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            template=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @polarion("RHEVM3-7371")
    def test_create_vm_without_copy_permissions_option(self):
        """ create vm without copy permissions option """
        testflow.step("Checking for copied permissions.")
        common.check_for_vm_permissions(
            False,
            config.USER1_VM_ROLES,
            config.USER2_VM_ROLES
        )


@attr(tier=2)
class CopyPermissions299328(common.BaseTestCase):
    """ Check if permissions are copied to template when enabled """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(CopyPermissions299328, cls).setup_class(request)

        def finalize():
            testflow.teardown(
                "Removing template %s.", config.TEMPLATE_NAMES[1]
            )
            templates.remove_template(True, config.TEMPLATE_NAMES[1])

        request.addfinalizer(finalize)

        testflow.setup("Creating template %s.", config.TEMPLATE_NAMES[1])
        templates.createTemplate(
            True,
            vm=config.VM_NAME,
            name=config.TEMPLATE_NAMES[1],
            cluster=config.CLUSTER_NAME[0],
            copy_permissions=True
        )

    @polarion("RHEVM3-7369")
    def test_make_template_with_copy_permissions_option(self):
        """ make template with copy permissions option """
        testflow.step("Checking for copied permissions.")
        common.check_for_template_permissions(
            True,
            config.USER1_TEMPLATE_ROLES,
            config.USER2_TEMPLATE_ROLES
        )


@attr(tier=2)
class CopyPermissions299331(common.BaseTestCase):
    """ Check if permissions are not copied to template when disabled """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(CopyPermissions299331, cls).setup_class(request)

        def finalize():
            testflow.teardown(
                "Removing template %s.", config.TEMPLATE_NAMES[1]
            )
            templates.remove_template(True, config.TEMPLATE_NAMES[1])

        request.addfinalizer(finalize)

        testflow.setup("Creating template %s.", config.TEMPLATE_NAMES[1])
        templates.createTemplate(
            True,
            vm=config.VM_NAME,
            name=config.TEMPLATE_NAMES[1],
            cluster=config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-7372")
    def test_make_template_without_copy_permissions_option(self):
        """ make template without copy permissions option """
        testflow.step("Checking for copied permissions.")
        common.check_for_template_permissions(
            False,
            config.USER1_TEMPLATE_ROLES,
            config.USER2_TEMPLATE_ROLES
        )
