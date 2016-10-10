"""
Testing working with permissions.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Tests if permissions are correctly inherited/viewed/assigned/removed.
"""
import logging

import pytest

from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
    vmpools as hl_vmpools
)
from art.rhevm_api.tests_lib.low_level import (
    disks, hosts, mla, storagedomains, templates,
    users, vms,
    vmpools as ll_vmpools,
    datacenters as ll_dc,
    clusters as ll_cluster
)
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import (
    bz, polarion
)
from art.unittest_lib import attr
from rhevmtests.system.user_tests.mla import common, config

# Predefined role for creation of VM as non-admin user
VM_PREDEFINED = config.role.UserVmManager
# Predefined role for creation of Disk as non-admin user
DISK_PREDEFINED = config.role.DiskOperator
# Predefined role for creation of Template as non-admin user
TEMPLATE_PREDEFINED = config.role.TemplateOwner

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        common.login_as_admin()

        for user_name in config.USER_NAMES[:3]:
            common.remove_user(True, user_name)

        vms.removeVm(True, config.VM_NAME, wait=True)

        disks.deleteDisk(True, config.DISK_NAME, async=False)
        disks.waitForDisksGone(True, config.DISK_NAME)

        hl_vmpools.detach_vms_from_pool(config.VMPOOL_NAME)

        vm_name = "{}-1".format(config.VMPOOL_NAME)

        vms.wait_for_vm_states(
            vm_name,
            states=[common.ENUMS["vm_state_down"]]
        )
        vms.removeVm(True, vm_name, wait=True)

        ll_vmpools.removeVmPool(True, config.VMPOOL_NAME)

        templates.removeTemplate(True, config.TEMPLATE_NAMES[0])

        test_utils.wait_for_tasks(
            config.VDC_HOST,
            config.VDC_ROOT_PASSWORD,
            config.DC_NAME[0]
        )

    request.addfinalizer(finalize)

    common.login_as_admin()

    for user_name in config.USER_NAMES[:3]:
        common.add_user(
            True,
            user_name=user_name,
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
    ll_vmpools.addVmPool(
        True,
        name=config.VMPOOL_NAME,
        size=1,
        cluster=config.CLUSTER_NAME[0],
        template=config.TEMPLATE_NAMES[0]
    )
    vms.wait_for_vm_states(
        "{0}-{1}".format(config.VMPOOL_NAME, 1),
        states=[
            common.ENUMS["vm_state_down"]
        ]
    )

    disks.addDisk(
        True,
        alias=config.DISK_NAME,
        interface='virtio',
        format='cow',
        provisioned_size=config.GB,
        storagedomain=config.MASTER_STORAGE
    )
    disks.wait_for_disks_status(config.DISK_NAME)


@attr(tier=1)
class PermissionsCase54408(common.BaseTestCase):
    """ objects and user permissions """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PermissionsCase54408, cls).setup_class(request)

        # Test these object for adding/removing/viewing perms on it
        cls.objects = {
            config.VM_NAME: vms.VM_API,
            config.TEMPLATE_NAMES[0]: templates.TEMPLATE_API,
            config.DISK_NAME: disks.DISKS_API,
            config.VMPOOL_NAME: ll_vmpools.UTIL,
            config.CLUSTER_NAME[0]: ll_cluster.util,
            config.DC_NAME[0]: ll_dc.util,
            config.HOSTS[0]: hosts.HOST_API,
            config.MASTER_STORAGE: storagedomains.util
        }

    # Check that there are two types of Permissions sub-tabs in the system:
    # for objects on which you can define permissions and for users.
    @polarion("RHEVM3-7168")
    def test_objects_and_user_permissions(self):
        """ objects and user permissions """
        msg = '%s has permissions subcollection.'

        for k in self.objects.keys():
            obj = self.objects[k].find(k)
            href = "{}/permissions".format(obj.get_href())
            assert self.objects[k].get(href=href) is not None
            logger.info(msg, obj.get_name())


@attr(tier=1)
class PermissionsCase54409(common.BaseTestCase):
    """" permissions inheritance """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PermissionsCase54409, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            common.remove_user(True, config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

        users.addRoleToUser(
            True,
            config.USER_NAMES[0],
            config.role.ClusterAdmin
        )

    @polarion("RHEVM3-7185")
    def test_permissions_inheritance(self):
        """ permissions inheritance """
        common.login_as_user(filter_=False)

        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert vms.removeVm(True, config.VM_NAMES[0])
        logger.info("User can create/remove vm with vm permissions.")

        common.login_as_admin()
        common.remove_user(True, config.USER_NAMES[0])
        common.add_user(
            True,
            user_name=config.USER_NAMES[0],
            domain=config.USER_DOMAIN
        )
        # To be able login
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0],
            config.role.UserRole
        )

        common.login_as_user()
        assert vms.createVm(
            positive=False,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        logger.info("User can't create/remove vm without vm permissions.")


# Check that in the object Permissions sub tab you will see all permissions
# that were associated with the selected object in the main grid or one of
# its ancestors.
@attr(tier=1)
class PermissionsCase5441054414(common.BaseTestCase):
    """" permissions subtab """
    __test__ = True

    @polarion("RHEVM3-7186")  # Also RHEVM3-7187, can not have multiple IDs
    def test_permissions_sub_tab(self):
        """ permissions subtab """
        # Try to add UserRole and AdminRole to object, then
        # check if both roles are visible via /api/objects/objectid/permissions
        msg = "There are visible all permissions which were associated."

        user_ids = [users.util.find(u).get_id() for u in config.USER_NAMES[:2]]

        logger.info("Testing object %s", config.VM_NAME)
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME,
            role=config.role.UserRole
        )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[1],
            config.VM_NAME,
            role=config.role.UserRole
        )
        vm = vms.VM_API.find(config.VM_NAME)
        role_permits = mla.permisUtil.getElemFromLink(vm, get_href=False)
        users_id = [perm.user.get_id() for perm in role_permits if perm.user]
        for user_id in user_ids:
            assert user_id in users_id
        logger.info(msg)

        for user_name in config.USERS[:2]:
            mla.removeUserPermissionsFromVm(
                True,
                config.VM_NAME,
                user_name
            )


# Assuming that there is always Super-Admin user on RHEV-M.
# Try to remove last permission on certain object.
# This also tests 54410
# It should be impossible to remove last Super-admin user with permission on
# system object.
# Try to remove last super-admin user with permission on system object.
# Try to remove super-admin + system permission from the user.
@attr(tier=2)
class PermissionsCase5441854419(common.BaseTestCase):
    """ last permission on object and test removal of SuperUser """
    __test__ = True

    @polarion("RHEVM3-7188")
    def test_last_permission_on_object(self):
        """ last permission on object """
        common.login_as_admin()

        mla.addVMPermissionsToUser(True, config.USER_NAMES[0], config.VM_NAME)
        mla.removeUserPermissionsFromVm(True, config.VM_NAME, config.USERS[0])

    @polarion("RHEVM3-7189")
    def test_removal_of_super_user(self):
        """ test removal of SuperUser """
        assert users.removeUser(False, 'admin@internal', 'internal')
        assert mla.removeUserRoleFromDataCenter(
            False,
            config.DC_NAME[0],
            'admin@internal',
            config.role.SuperUser
        )
        logger.info(
            'Unable to remove admin@internal or his SuperUser permissions.'
        )


# Try to add a permission associated with an
# administrator Role (i.e. "Administrator Permission") to another user when
# you don't have "Super-Admin" permission on the "System" object". - FAILED
# When you're user/super user ,try to delegate permission to another
# user/super user. - SUCCESS
@attr(tier=2)
class PermissionsCase54425(common.BaseTestCase):
    """ test delegate perms """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PermissionsCase54425, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            vms.removeVm(True, config.VM_NAMES[0])
            common.remove_user(True, config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

        request.addfinalizer(finalize)

        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @polarion("RHEVM3-7191")
    def test_delegate_permissions(self):
        """ delegate permissions """
        # Test SuperUser that he can add permissions
        for role_obj in mla.util.get(absLink=False):
            role_name = role_obj.get_name()

            logger.info("Testing role - %s", role_name)
            # Get roles perms, to check for manipulate_permissions
            role_obj = mla.util.find(role_name)  # multi user switching hack
            role_permits = mla.util.getElemFromLink(
                role_obj,
                link_name='permits',
                attr='permit',
                get_href=False
            )
            perms = [p.get_name() for p in role_permits]
            if 'login' not in perms:
                logger.info("User not tested, because don't have login perms.")
                continue

            users.addRoleToUser(True, config.USER_NAMES[0], role_name)
            mla.addVMPermissionsToUser(
                True,
                config.USER_NAMES[0],
                config.VM_NAMES[0], role_name
            )

            # For know if login as User/Admin
            _filter = not role_obj.administrative
            # login as user with role
            common.login_as_user(filter_=_filter)
            # Test if user with role can/can't manipulate perms
            if 'manipulate_permissions' in perms:
                if _filter or config.role.SuperUser != role_name:
                    try:
                        mla.addVMPermissionsToUser(
                            False,
                            config.USER_NAMES[0],
                            config.VM_NAMES[0],
                            config.role.TemplateAdmin
                        )
                    except:  # Ignore, user should not add perms
                        pass
                    logger.info("'%s' can't add admin permissions.", role_name)
                    assert mla.addVMPermissionsToUser(
                        True,
                        config.USER_NAMES[0],
                        config.VM_NAMES[0]
                    )
                    logger.info("'%s' can add user permissions.", role_name)
                else:
                    assert mla.addVMPermissionsToUser(
                        True,
                        config.USER_NAMES[0],
                        config.VM_NAMES[0],
                        config.role.UserRole
                    )
                    logger.info("'%s' can add user permissions.", role_name)
                    assert mla.addVMPermissionsToUser(
                        True,
                        config.USER_NAMES[0],
                        config.VM_NAMES[0],
                        config.role.TemplateAdmin
                    )
                    logger.info("'%s' can add admin permissions.", role_name)
            else:
                try:
                    mla.addVMPermissionsToUser(
                        False,
                        config.USER_NAMES[0],
                        config.VM_NAMES[0],
                        config.role.UserRole
                    )
                except:  # Ignore, user should not add perms
                    pass
                logger.info("'%s' can't manipulate permissions.", role_name)

            common.login_as_admin()
            common.remove_user(True, config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )

    # in order ro add new object you will need the appropriate permission on
    # the ancestor (e.g. to create a new storage domain you'll need a "add
    # storage domain" permission on the "system" object,to create a new Host/VM
    # you will need appropriate permission on the relevant cluster.
    @polarion("RHEVM3-7192")
    def test_new_object_check_permissions(self):
        """ Adding new business entity/new object. """
        msg = "This functionality tests modules admin_tests and user_tests"
        logger.info(msg)


# Check if user is under some Group if it has permissions of its group
@attr(tier=2)
class PermissionsCase54446(common.BaseTestCase):
    """ Check if user is under some Group if has permissions of its group """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PermissionsCase54446, cls).setup_class(request)

        def finalize():
            common.login_as_admin()

            vms.removeVm(True, config.VM_NAMES[0])

            common.remove_user(True, config.GROUP_USER)
            users.deleteGroup(True, config.GROUP_NAME)

        request.addfinalizer(finalize)

        users.addGroup(
            True,
            config.GROUP_NAME,
            config.USER_DOMAIN
        )

        mla.addClusterPermissionsToGroup(
            True,
            config.GROUP_NAME,
            config.CLUSTER_NAME[0],
            config.role.UserVmManager
        )

    @polarion("RHEVM3-7193")
    def test_users_permissions(self):
        """ users permissions """
        common.login_as_user(user_name=config.GROUP_USER_NAME)

        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        assert templates.createTemplate(
            False,
            vm=config.VM_NAMES[0],
            name=config.TEMPLATE_NAMES[1],
            cluster=config.CLUSTER_NAME[0]
        )


# user API - createVm - should add perms UserVmManager on VM
# https://bugzilla.redhat.com/show_bug.cgi?id=881145
@attr(tier=2)
class PermissionsCase54420(common.BaseTestCase):
    """ Object creating from User and Admin portal """
    __test__ = True

    @bz({'1209505': {}})
    @polarion("RHEVM3-7190")
    def test_object_admin_user(self):
        """ Object creating from User portal """
        b = False

        for rr in [config.role.VmCreator, config.role.TemplateCreator]:
            common.login_as_admin()
            role_obj = users.rlUtil.find(rr)
            role_permits = mla.util.getElemFromLink(
                role_obj,
                link_name='permits',
                attr='permit',
                get_href=False
            )
            r_permits = [p.get_name() for p in role_permits]

            users.addRoleToUser(True, config.USER_NAMES[0], rr)
            mla.addClusterPermissionsToUser(
                True,
                config.USER_NAMES[0],
                config.CLUSTER_NAME[0],
                config.role.UserRole
            )
            common.login_as_user(filter_=not role_obj.administrative)

            logger.info("Testing role - %s", role_obj.get_name())

            # Create vm,template, disk and check permissions of it
            if 'create_vm' in r_permits:
                logger.info("Testing create_vm.")
                vms.createVm(
                    positive=True,
                    vmName=config.VM_NAMES[0],
                    cluster=config.CLUSTER_NAME[0],
                    network=config.MGMT_BRIDGE
                )
                b = b or common.check_if_object_has_role(
                    vms.VM_API.find(config.VM_NAMES[0]),
                    VM_PREDEFINED,
                    role_obj.administrative
                )
                common.login_as_admin()
                vms.removeVm(True, config.VM_NAMES[0])

            if 'create_template' in r_permits:
                logger.info("Testing create_template.")
                templates.createTemplate(
                    True,
                    vm=config.VM_NAME,
                    name=config.TEMPLATE_NAMES[1],
                    cluster=config.CLUSTER_NAME[0]
                )
                b = b or common.check_if_object_has_role(
                    templates.TEMPLATE_API.find(config.TEMPLATE_NAMES[1]),
                    TEMPLATE_PREDEFINED,
                    role_obj.administrative
                )
                common.login_as_admin()
                templates.removeTemplate(True, config.TEMPLATE_NAMES[1])

            if 'create_disk' in r_permits:
                logger.info("Testing createDisk.")
                disks.addDisk(
                    True,
                    alias=config.DISK_NAME1,
                    interface='virtio',
                    format='cow',
                    provisioned_size=config.GB,
                    storagedomain=config.MASTER_STORAGE
                )
                disks.wait_for_disks_status(config.DISK_NAME1)
                b = b or common.check_if_object_has_role(
                    disks.DISKS_API.find(config.DISK_NAME1),
                    DISK_PREDEFINED,
                    role_obj.administrative
                )

                common.login_as_admin()
                disks.deleteDisk(True, config.DISK_NAME1)
                disks.waitForDisksGone(True, config.DISK_NAME1)

            common.remove_user(True, config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )
        if not b:
            raise AssertionError


# add a group of users from AD to the system (give it some admin permission)
# login as user from group, remove the user
# Check that group still exist in the Configure-->System.
# Check that group's permissions still exist
@attr(tier=2)
class PermissionsCase108233(common.BaseTestCase):
    """ Removing user that part of the group. """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PermissionsCase108233, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            common.remove_user(True, config.GROUP_USER_NAME)
            users.deleteGroup(True, config.GROUP_NAME)

        request.addfinalizer(finalize)

        users.addGroup(
            True,
            config.GROUP_NAME,
            config.USER_DOMAIN
        )
        mla.addClusterPermissionsToGroup(
            True,
            config.GROUP_NAME,
            config.CLUSTER_NAME[0]
        )
        common.add_user(
            True,
            user_name=config.GROUP_USER_NAME,
            domain=config.USER_DOMAIN
        )

    @polarion("RHEVM3-7169")
    def test_remove_user_from_group(self):
        """ Removing user that part of the group. """
        common.login_as_user(
            user_name=config.GROUP_USER_NAME,
            filter_=False
        )
        assert vms.VM_API.find(config.VM_NAME)

        common.login_as_admin()
        assert users.util.find(config.GROUP_USER_NAME)
        logger.info("User was added.")


# Check that data-center has a user with UserRole permission
# Create new desktop pool
# Check that permission was inherited from data-center
# Ensure that user can take a machine from created pool
@attr(tier=2)
class PermissionsCase109086(common.BaseTestCase):
    """ Permission inheritance for desktop pool """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PermissionsCase109086, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            mla.removeUserPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            config.role.UserRole
        )

    @polarion("RHEVM3-7170")
    def test_permissions_inheritance_for_vm_pools(self):
        """ Permission inheritance for desktop pools """
        common.login_as_user()
        assert ll_vmpools.allocateVmFromPool(True, config.VMPOOL_NAME)

        common.login_as_admin()
        vms.wait_for_vm_states(
            "{0}-{1}".format(config.VMPOOL_NAME, 1)
        )

        common.login_as_user()
        assert hl_vmpools.stop_vm_pool(config.VMPOOL_NAME)

        common.login_as_admin()
        vms.wait_for_vm_states(
            "{0}-{1}".format(config.VMPOOL_NAME, 1),
            states=[common.ENUMS["vm_state_down"]]
        )


# create a StorageDomain with templates and VMs
# grant permissions for user X to some VMs & templates on that SD
# destroy the SD take a look in the user under permission tab
# extra_reqs={'datacenters_count': 2}
@attr(tier=config.DO_NOT_RUN)
class PermissionsCase111082(common.BaseTestCase):
    """ Test if perms removed after object is removed """
    __test__ = True

    apis = set(['rest'])

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PermissionsCase111082, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            common.remove_user(True, config.USER_NAMES[0])
            common.add_user(
                True,
                user_name=config.USER_NAMES[0],
                domain=config.USER_DOMAIN
            )
            storagedomains.removeStorageDomain(
                config.STORAGE_NAME[1],
                config.DC_NAME[0],
                config.HOSTS[0]
            )

        request.addfinalizer(finalize)
        hl_sd.addNFSDomain(
            config.HOSTS[0],
            config.STORAGE_NAME[1],
            config.DC_NAME[0],
            config.ADDRESS[1],
            config.PATH[1]
        )
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[1],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True,
            vm=config.VM_NAMES[0],
            name=config.TEMPLATE_NAMES[1],
            cluster=config.CLUSTER_NAME[0]
        )
        disks.addDisk(
            True,
            alias=config.DISK_NAME1,
            interface='virtio',
            format='cow',
            provisioned_size=config.GB,
            storagedomain=config.STORAGE_NAME[1]
        )
        disks.wait_for_disks_status(config.DISK_NAME1)
        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAMES[0]
        )
        mla.addPermissionsForTemplate(
            True,
            config.USER_NAMES[0],
            config.TEMPLATE_NAMES[1],
            config.role.TemplateOwner
        )
        mla.addPermissionsForDisk(
            True,
            config.USER_NAMES[0],
            config.DISK_NAME1
        )

    @polarion("RHEVM3-7171")
    def test_permissions_removed_after_object_remove(self):
        """ permissions removed after object is removed """
        storagedomains.deactivateStorageDomain(
            True,
            config.DC_NAME[0],
            config.STORAGE_NAME[1]
        )
        storagedomains.removeStorageDomain(
            True,
            config.STORAGE_NAME[1],
            config.HOSTS[0],
            destroy=True
        )

        # When destroying SD, then also vm is destroyed
        # vms.removeVm(True, config.VM_NAMES[0])
        user_vm_manager_id = users.rlUtil.find(
            config.role.UserVmManager
        ).get_id()
        template_owner_id = users.rlUtil.find(
            config.role.TemplateOwner
        ).get_id()
        disk_operator_id = users.rlUtil.find(
            config.role.DiskOperator
        ).get_id()

        obj = users.util.find(config.USER_NAMES[0])
        permits = mla.permisUtil.getElemFromLink(obj, get_href=False)

        permits_id = [p.get_role().get_id() for p in permits]
        assert user_vm_manager_id not in permits_id
        assert template_owner_id not in permits_id
        assert disk_operator_id not in permits_id


@attr(tier=1)
class AdminPropertiesOfTemplate(common.BaseTestCase):
    """
    Test create of vm as PowerUserRole from template which has set
    administrator properties. He should be able to create such vm.
    """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(AdminPropertiesOfTemplate, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            templates.updateTemplate(
                True,
                config.TEMPLATE_NAME[0],
                custom_properties='clear',
            )
            mla.removeUserPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USERS[0],
            )
            mla.removeUserPermissionsFromTemplate(
                True,
                config.TEMPLATE_NAME[0],
                config.USERS[0],
            )

        request.addfinalizer(finalize)

        assert templates.updateTemplate(
            True,
            config.TEMPLATE_NAME[0],
            custom_properties='sndbuf=10',
        )
        assert mla.addPermissionsForDataCenter(
            positive=True,
            user=config.USER_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.PowerUserRole,
        )
        assert mla.addPermissionsForTemplate(
            positive=True,
            user=config.USER_NAMES[0],
            template=config.TEMPLATE_NAME[0],
            role=config.role.UserTemplateBasedVm,
        )

    @bz({'1284472': {}})
    @polarion('RHEVM3-14560')
    def test_create_vm_from_template_with_admin_props(self):
        """ Test create vm from template with admin properties set """
        common.login_as_user()
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0],
        )
        assert vms.removeVm(True, config.VM_NAMES[0])
