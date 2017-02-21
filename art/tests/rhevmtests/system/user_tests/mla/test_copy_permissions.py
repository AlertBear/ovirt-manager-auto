"""
Testing copy permissions feauture.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Every case create vm/template and check if permissions from it are/aren't
copied, when copy_permissions flag is/isn't provided.
"""
import pytest

from art.rhevm_api.tests_lib.low_level import mla, templates, vms
from art.test_handler.tools import polarion
from art.unittest_lib import attr

from rhevmtests.system.user_tests.mla import common, config


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        for user_name in config.USER_NAMES[:2]:
            common.remove_user(True, user_name)
        vms.removeVm(True, config.VM_NAME)
        templates.remove_template(True, config.TEMPLATE_NAMES[0])

    request.addfinalizer(finalize)

    common.add_user(
        True,
        user_name=config.USER_NAMES[0],
        domain=config.USER_DOMAIN
    )
    common.add_user(
        True,
        user_name=config.USER_NAMES[1],
        domain=config.USER_DOMAIN
    )
    vms.createVm(
        positive=True,
        vmName=config.VM_NAME,
        cluster=config.CLUSTER_NAME[0],
        storageDomainName=config.MASTER_STORAGE,
        provisioned_size=config.GB,
        network=config.MGMT_BRIDGE
    )

    templates.createTemplate(
        True,
        vm=config.VM_NAME,
        name=config.TEMPLATE_NAMES[0],
        cluster=config.CLUSTER_NAME[0]
    )

    # ## Add permissions to vm ##
    # ClusterAdmin role on cluster to user1 (should no be copied)
    mla.addClusterPermissionsToUser(
        True,
        config.USER_NAMES[0],
        config.CLUSTER_NAME[0]
    )
    # ClusterAdmin role on cluster to user2 (should no be copied)
    mla.addClusterPermissionsToUser(
        True,
        config.USER_NAMES[1],
        config.CLUSTER_NAME[0],
        role=config.role.UserRole
    )
    # Add UserRole on vm to user1 (should be copied)
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[0],
        config.VM_NAME,
        role=config.role.UserRole
    )
    # Add UserTemplateBasedVm on vm to user1 (should be copied)
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[0],
        config.VM_NAME,
        role=config.role.UserTemplateBasedVm
    )
    # Add TemplateAdmin on vm to user1 (should be copied)
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[0],
        config.VM_NAME,
        role=config.role.TemplateAdmin
    )
    # Add TemplateAdmin on vm to user2 (should be copied)
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[1],
        config.VM_NAME,
        role=config.role.TemplateOwner
    )
    # Add DiskCreator on vm to user2 (should be copied)
    mla.addVMPermissionsToUser(
        True,
        config.USER_NAMES[1],
        config.VM_NAME,
        role=config.role.DiskCreator
    )

    # ## Add permissions to template ##
    # PowerUserRole on template to user1 (should be copied)
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[0],
        config.TEMPLATE_NAMES[0],
        role=config.role.PowerUserRole
    )
    # UserRole on template to user1 (should be copied)
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[0],
        config.TEMPLATE_NAMES[0],
        role=config.role.UserRole
    )
    # TemplateAdmin on template to user2 (should be copied)
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[1],
        config.TEMPLATE_NAMES[0],
        role=config.role.TemplateAdmin
    )
    # UserTemplateBasedVm on template to user1 (should not be copied)
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[0],
        config.TEMPLATE_NAMES[0],
        role=config.role.UserTemplateBasedVm
    )
    # TemplateOwner on template to user2 (should not be copied)
    mla.addPermissionsForTemplate(
        True,
        config.USER_NAMES[1],
        config.TEMPLATE_NAMES[0],
        role=config.role.TemplateOwner
    )
    # DataCenterAdmin on template to user2 (should not be copied)
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
            vms.removeVm(True, config.VM_NAMES[0])

        request.addfinalizer(finalize)

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
            vms.removeVm(True, config.VM_NAMES[0])

        request.addfinalizer(finalize)

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
            templates.remove_template(True, config.TEMPLATE_NAMES[1])

        request.addfinalizer(finalize)

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
            templates.remove_template(True, config.TEMPLATE_NAMES[1])

        request.addfinalizer(finalize)

        templates.createTemplate(
            True,
            vm=config.VM_NAME,
            name=config.TEMPLATE_NAMES[1],
            cluster=config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-7372")
    def test_make_template_without_copy_permissions_option(self):
        """ make template without copy permissions option """
        common.check_for_template_permissions(
            False,
            config.USER1_TEMPLATE_ROLES,
            config.USER2_TEMPLATE_ROLES
        )
