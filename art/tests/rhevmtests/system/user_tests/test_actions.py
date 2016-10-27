import uuid
import logging
import random
import pytest

from functools import wraps
from art.unittest_lib import attr, testflow
from art.core_api.apis_exceptions import EntityNotFound
from art.unittest_lib import CoreSystemTest as TestCase
from art.rhevm_api.tests_lib.high_level import vmpools as hl_vmpools
from art.rhevm_api.tests_lib.low_level import (
    disks, users, vms, vmpools, mla, templates,
    datacenters, clusters, hosts, storagedomains
)
from rhevmtests.system.user_tests import config


logger = logging.getLogger(__name__)
DETACH_TIMEOUT = 5


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    """ Prepare testing setup """
    def finalize():
        """ Clean testing setup """
        testflow.teardown("Tearing down module %s", __name__)

        testflow.step("Removing vm %s", config.CREATE_VM)
        vms.removeVm(
            True,
            config.CREATE_VM
        )
        testflow.step("Removing vm %s", config.RUNNING_VM)
        vms.removeVm(
            True,
            config.RUNNING_VM,
            stopVM='true'
        )
        testflow.step("Removing vmpool %s", config.CREATE_POOL)
        vmpools.removeVmPool(
            True,
            vmpool=config.CREATE_POOL
        )
        testflow.step("Removing disk %s", config.DELETE_DISK)
        disks.deleteDisk(
            True,
            config.DELETE_DISK,
            async=False
        )
        testflow.step("Removing cluster %s", config.DELETE_CLUSTER)
        clusters.removeCluster(
            True,
            config.DELETE_CLUSTER
        )
        testflow.step("Removing vm %s", config.DELETE_VM)
        vms.removeVm(
            True,
            config.DELETE_VM
        )
        testflow.step("Removing vmpool %s", config.DELETE_POOL)
        vmpools.removeVmPool(
            True,
            vmpool=config.DELETE_POOL,
            wait=True
        )
        testflow.step("Removing template %s", config.CREATE_TEMPLATE)
        templates.removeTemplate(
            True,
            config.CREATE_TEMPLATE
        )
        testflow.step("Removing template %s", config.DELETE_TEMPLATE)
        templates.removeTemplate(
            True,
            config.DELETE_TEMPLATE
        )
        testflow.step("Removing datacenter %s", config.DELETE_DC)
        datacenters.remove_datacenter(
            True,
            config.DELETE_DC,
            force=True
        )

    request.addfinalizer(finalize)

    testflow.setup("Setting up module %s", __name__)

    testflow.step("Creating vm %s", config.CREATE_VM)
    vms.createVm(
        True,
        config.CREATE_VM,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        storageDomainName=config.MASTER_STORAGE,
        provisioned_size=config.GB,
    )
    testflow.step("Creating vm %s", config.RUNNING_VM)
    vms.createVm(
        True,
        config.RUNNING_VM,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        storageDomainName=config.MASTER_STORAGE,
        provisioned_size=config.GB,
        start='true'
    )
    testflow.step("Creating template %s", config.CREATE_TEMPLATE)
    templates.createTemplate(
        True,
        vm=config.CREATE_VM,
        name=config.CREATE_TEMPLATE
    )
    testflow.step("Creating template's nic %s", config.CREATE_TEMPLATE_NIC1)
    templates.addTemplateNic(
        True,
        config.CREATE_TEMPLATE,
        name=config.CREATE_TEMPLATE_NIC1,
        network=config.MGMT_BRIDGE,
        interface='virtio'
    )
    testflow.step("Adding vmpool %s", config.CREATE_POOL)
    vmpools.addVmPool(
        True,
        name=config.CREATE_POOL,
        cluster=config.CLUSTER_NAME[0],
        template=config.CREATE_TEMPLATE,
        size=1
    )
    testflow.step("Adding disk %s", config.DELETE_DISK)
    disks.addDisk(
        True,
        alias=config.DELETE_DISK,
        interface='virtio',
        format='cow',
        provisioned_size=config.GB,
        storagedomain=config.MASTER_STORAGE
    )
    testflow.step("Adding cluster %s", config.DELETE_CLUSTER)
    clusters.addCluster(
        True,
        name=config.DELETE_CLUSTER,
        cpu=config.CPU_NAME,
        data_center=config.DC_NAME[0],
        version=config.COMP_VERSION
    )
    testflow.step("Creating vm %s", config.DELETE_VM)
    vms.createVm(
        True,
        config.DELETE_VM,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
    )
    testflow.step("Creating template %s", config.DELETE_TEMPLATE)
    templates.createTemplate(
        True,
        vm=config.CREATE_VM,
        name=config.DELETE_TEMPLATE
    )
    testflow.step("Adding vmpool %s", config.DELETE_POOL)
    vmpools.addVmPool(
        True,
        name=config.DELETE_POOL,
        cluster=config.CLUSTER_NAME[0],
        template=config.CREATE_TEMPLATE,
        size=1
    )
    testflow.step("Adding datacenter %s", config.DELETE_DC)
    datacenters.addDataCenter(
        True,
        name=config.DELETE_DC,
        version=config.COMP_VERSION,
        local=True
    )
    testflow.step("Adding permissions to group %s", config.EVERYONE_GROUP)
    mla.addTemplatePermissionsToGroup(
        True,
        config.EVERYONE_GROUP,
        config.CREATE_TEMPLATE,
        role=config.UserTemplateBasedVm
    )


def ienf(method, *args, **kwargs):
    """
    Description:
        Ignore EntityNotFound exception. We need this function,
    because these tests are so generic, where we don't know if
    action succeeded or not. So in the end we remove all objects
    which could be created or not.
    Args:
        method (function): function to invoke
        *args: arguments of the function
    Kwargs:
        **kwargs: keyword arguments of the function
    Returns:
        None: this function returns nothing as we don't need any
    result.
    """
    try:
        method(*args, **kwargs)
    except EntityNotFound:
        logger.warn('Entity not found: %s%s', method.__name__, str(args))


def login_as_user(user, filter_):
    users.loginAsUser(
        user,
        config.USER_PROFILE,
        config.USER_PASSWORD,
        filter=filter_
    )


def login_as_admin():
    users.loginAsUser(
        config.VDC_ADMIN_USER,
        config.VDC_ADMIN_DOMAIN,
        config.VDC_PASSWORD, filter=False
    )


def user_case(login_as=None, cleanup_func=None, **kwargs_glob):
    """
    Description:
        Perform test case as user. When the method is finished, run cleanup.
    Args:
        login_as (str): user who should perform case
        cleanup_func (function): function which should cleanup case
    Kwargs:
        cleanup_params: parameters of cleanup function
    Returns:
        function: decorator for a test case
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.positive = func.__name__[5:] in self.perms
            func.__dict__['role'] = kwargs_glob.get('role')
            testflow.step(
                'Running %s %s action',
                'positive' if self.positive else 'negative',
                func.__name__
            )
            if self.last_logged_in != login_as:
                self.last_logged_in = login_as
                login_as_user(login_as, self.filter_)
            try:
                func(self, *args, **kwargs)
            except AssertionError:  # Case failed, clean even if not positive.
                self.positive = True
                raise
            finally:
                if self.positive and cleanup_func is not None:
                    self.cleanup_functions.append(
                        {
                            'func': cleanup_func,
                            'params': kwargs_glob,
                        }
                    )
        return wrapper
    return decorator


@attr(tier=2)
class CaseRoleActions(TestCase):
    """
    This class includes all test actions role can have.
    Every test action is the one test case method.
    User is authenticated at the start of the test,
    and never log out during test. Clean up is done
    by admin@internal at the end of test.
    """
    __test__ = False
    last_logged_in = ''
    cleanup_functions = []  # List of dictionaries of cleanup functions

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """
        Prepare users with roles on objects.
        """
        def finalize():
            """
            Call cleanup functions.
            """
            testflow.teardown("Finalizing class %s", cls.__name__)
            login_as_admin()

            for vm in [
                    config.DELETE_VM,
                    config.CREATE_VM,
                    config.RUNNING_VM
            ]:
                testflow.step("Waiting for vm %s", vm)
                ienf(
                    vms.wait_for_vm_states,
                    vm, states=[
                        config.ENUMS['vm_state_up'],
                        config.ENUMS['vm_state_down']
                    ]
                )
            for user in config.USERS:
                testflow.step(
                    "Removing %s user permissions from %s cluster",
                    user, config.CLUSTER_NAME[0]
                )
                ienf(
                    mla.removeUserPermissionsFromCluster,
                    True, config.CLUSTER_NAME[0], user
                )
                testflow.step(
                    "Removing %s user permissions from %s datacenter",
                    user, config.DC_NAME[0]
                )
                ienf(
                    mla.removeUserPermissionsFromDatacenter,
                    True, config.DC_NAME[0], user
                )
                testflow.step(
                    "Removing %s permissions from %s storage domain",
                    user, config.MASTER_STORAGE
                )
                ienf(
                    mla.removeUserPermissionsFromSD,
                    True, config.MASTER_STORAGE, user
                )
                testflow.step(
                    "Removing all permissions from user %s", user
                )
                ienf(
                    mla.removeAllPermissionsFromUser,
                    True,
                    user
                )
                testflow.step("Removing user %s", user)
                ienf(
                    users.removeUser,
                    True,
                    user,
                    config.USER_DOMAIN
                )

            for cleanup in cls.cleanup_functions:
                testflow.step(
                    "Running %s cleanup function",
                    cleanup['func'].__name__
                )
                try:
                    cleanup['func'](**cleanup['params'])
                except EntityNotFound as e:
                    logger.warn('Entity was not found: %s', str(e))
                # Continue with execution of all functions.
                except Exception as e:
                    logger.error(str(e))

            del cls.cleanup_functions[:]

            testflow.step("Removing role %s", config.UPDATE_ROLE)
            ienf(
                mla.removeRole,
                True,
                config.UPDATE_ROLE
            )
            testflow.step("Removing user %s", config.REMOVE_USER)
            ienf(
                users.removeUser,
                True,
                config.REMOVE_USER
            )
            testflow.step(
                "Adding %s nic to template %s",
                config.CREATE_TEMPLATE_NIC1,
                config.CREATE_TEMPLATE
            )
            ienf(
                templates.addTemplateNic,
                True,
                config.CREATE_TEMPLATE,
                name=config.CREATE_TEMPLATE_NIC1,
                network=config.MGMT_BRIDGE,
                interface='virtio'
            )

        request.addfinalizer(finalize)

        testflow.setup("Setting up class %s", cls.__name__)

        for user in config.USERS:
            testflow.step("Adding user %s", user)
            users.addExternalUser(
                True,
                user_name=user,
                domain=config.USER_DOMAIN
            )
        testflow.step(
            "Adding %s permissions to %s user",
            config.CREATE_VM,
            config.USER_TEST
        )
        mla.addVMPermissionsToUser(
            True,
            config.USER_TEST,
            config.CREATE_VM,
            config.UserRole
        )

        testflow.step("Adding role %s", config.UPDATE_ROLE)
        ienf(
            mla.addRole,
            True,
            name=config.UPDATE_ROLE,
            permits=config.PERMIT_LOGIN
        )
        testflow.step("Adding user %s", config.REMOVE_USER)
        users.addExternalUser(
            True,
            user_name=config.REMOVE_USER,
            domain=config.USER_DOMAIN
        )
        testflow.step(
            "Adding %s role to %s user",
            cls.role,
            config.USER_SYSTEM
        )
        users.addRoleToUser(
            True,
            config.USER_SYSTEM,
            cls.role
        )
        testflow.step(
            "Adding %s cluster permissions to %s user",
            config.CLUSTER_NAME[0],
            config.USER_CLUSTER
        )
        mla.addClusterPermissionsToUser(
            True,
            config.USER_CLUSTER,
            config.CLUSTER_NAME[0],
            cls.role
        )
        testflow.step(
            "Adding %s datacenter permission to %s user",
            config.DC_NAME[0],
            config.USER_DC
        )
        mla.addPermissionsForDataCenter(
            True,
            config.USER_DC,
            config.DC_NAME[0],
            cls.role
        )
        testflow.step(
            "Adding %s storage permissions to %s user",
            config.MASTER_STORAGE,
            config.USER_STORAGE
        )
        mla.addStoragePermissionsToUser(
            True,
            config.USER_STORAGE,
            config.MASTER_STORAGE,
            cls.role
        )
        testflow.step(
            "Adding %s template permissions to %s user",
            config.CREATE_TEMPLATE,
            config.USER_DC
        )
        mla.addPermissionsForTemplate(
            True,
            config.USER_DC,
            config.CREATE_TEMPLATE,
            config.UserTemplateBasedVm
        )
        testflow.step(
            "Adding %s vm permissions to %s user",
            config.CREATE_VM,
            config.USER_VM
        )
        mla.addVMPermissionsToUser(
            True,
            config.USER_VM,
            config.CREATE_VM,
            role=cls.role
        )

        """
        Need to assign permissions for roles which are not supposed to view
        children to avoid EntityNotFound exception and rather test real action
        """
        cls.creator = not mla.allowsViewChildren(cls.role, config.ENGINE.db)
        if cls.creator:
            user_object_perm_map = {
                config.USER_SYSTEM: {
                    mla.addPermissionsForDataCenter: [
                        config.DELETE_DC,
                    ],
                },
                config.USER_DC: {
                    mla.addVMPermissionsToUser: [
                        config.CREATE_VM,
                    ],
                    mla.addVmPoolPermissionToUser: [
                        config.CREATE_POOL, config.DELETE_POOL,
                    ],
                    mla.addPermissionsForTemplate: [
                        config.DELETE_TEMPLATE,
                    ],
                    mla.addClusterPermissionsToUser: [
                        config.DELETE_CLUSTER,
                    ],
                },
                config.USER_CLUSTER: {
                    mla.addVMPermissionsToUser: [
                        config.RUNNING_VM, config.DELETE_VM, config.CREATE_VM,
                    ],
                },
                config.USER_STORAGE: {
                    mla.addPermissionsForDisk: [
                        config.DELETE_DISK,
                    ],
                },
            }
            for user, func_obj_maps, in user_object_perm_map.iteritems():
                for func, obj_names in func_obj_maps.iteritems():
                    for obj_name in obj_names:
                        func(
                            True,
                            user,
                            obj_name,
                            role=config.UserTemplateBasedVm
                        )

    # ======================= CREATE ACTIONS ================================

    @user_case(
        login_as=config.USER_SYSTEM,
        cleanup_func=datacenters.remove_datacenter,
        positive=True,
        datacenter=config.USER_SYSTEM
    )
    def test_create_storage_pool(self):
        """ create_storage_pool """
        assert datacenters.addDataCenter(
            self.positive,
            name=config.USER_SYSTEM,
            version=config.COMP_VERSION,
            local=True
        )

    @user_case(
        login_as=config.USER_CLUSTER,
        cleanup_func=vms.removeVm,
        positive=True,
        vm=config.USER_CLUSTER
    )
    def test_create_vm(self):
        """ create_vm """
        assert vms.createVm(
            self.positive,
            config.USER_CLUSTER,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=templates.removeTemplate,
        positive=True,
        template=config.USER_DC
    )
    def test_create_template(self):
        """ create_template """
        assert templates.createTemplate(
            self.positive,
            vm=config.CREATE_VM,
            name=config.USER_DC
        )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=vmpools.removeVmPool,
        positive=True,
        vmpool=config.USER_DC,
    )
    def test_create_vm_pool(self):
        """ create_vm_pool """
        assert vmpools.addVmPool(
            self.positive,
            name=config.USER_DC,
            cluster=config.CLUSTER_NAME[0],
            template=config.CREATE_TEMPLATE,
            size=1
        )

    @user_case(
        login_as=config.USER_STORAGE,
        cleanup_func=disks.deleteDisk,
        positive=True,
        alias=config.USER_STORAGE
    )
    def test_create_disk(self):
        """ create_disk """
        assert disks.addDisk(
            self.positive,
            alias=config.USER_STORAGE,
            interface='virtio',
            format='cow',
            provisioned_size=config.GB,
            storagedomain=config.MASTER_STORAGE
        )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=clusters.removeCluster,
        positive=True,
        cluster=config.USER_DC
    )
    def test_create_cluster(self):
        """ create_cluster """
        assert clusters.addCluster(
            self.positive,
            name=config.USER_DC,
            cpu=config.CPU_NAME,
            data_center=config.DC_NAME[0],
            version=config.COMP_VERSION
        )

    # TODO
    # create_host - would be tricky
    # create_storage_domain - would be tricky

    # ==================== MANIPULATE ACTIONS ===============================

    @user_case(
        login_as=config.USER_SYSTEM,
        cleanup_func=mla.removeRole,
        positive=True,
        role=config.CREATE_ROLE
    )
    def test_manipulate_roles(self):
        """ manipulate_roles """
        error_stack = []
        if not mla.addRole(
            self.positive,
            name=config.CREATE_ROLE,
            permits=config.PERMIT_LOGIN
        ):
            error_stack.append('Action add role failed.')
        if not mla.updateRole(
            self.positive,
            config.UPDATE_ROLE,
            description=config.CREATE_ROLE
        ):
            error_stack.append('Action update role failed.')
        if not mla.removeRole(
            self.positive,
            config.UPDATE_ROLE
        ):
            error_stack.append('Action remove role failed.')

        if len(error_stack) > 0:
            raise AssertionError(' '.join(error_stack))

    @user_case(
        login_as=config.USER_SYSTEM,
        cleanup_func=users.removeUser,
        positive=True,
        user=config.CREATE_USER
    )
    def test_manipulate_users(self):
        """ manipulate_users """
        error_stack = []
        if not users.addUser(
            self.positive,
            user_name=config.CREATE_USER,
            domain=config.USER_DOMAIN
        ):
            error_stack.append('Action add user failed.')
        try:
            assert users.removeUser(
                True,
                config.REMOVE_USER
            )
        except AssertionError:
            if self.positive:
                error_stack.append('Action remove user failed.')
        except EntityNotFound:
            if self.positive:
                error_stack.append('User was not found.')

        if len(error_stack) > 0:
            raise AssertionError(' '.join(error_stack))

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=hl_vmpools.stop_vm_pool,
        vm_pool=config.CREATE_POOL
    )
    def test_vm_pool_basic_operations(self):
        """ vm_pool_basic_operations """
        assert vmpools.allocateVmFromPool(
            self.positive,
            config.CREATE_POOL
        )

    @user_case(
        login_as=config.USER_CLUSTER,
        cleanup_func=vms.restartVm,
        vm=config.RUNNING_VM,
    )
    def test_connect_to_vm(self):
        """ connect_to_vm """
        assert vms.ticketVm(self.positive, vm=config.RUNNING_VM, expiry='120')

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=templates.removeTemplateNic,
        positive=True,
        template=config.CREATE_TEMPLATE,
        nic=config.CREATE_TEMPLATE_NIC2
    )
    def test_configure_template_network(self):
        """ configure_template_network """
        error_stack = []
        if not templates.addTemplateNic(
            self.positive,
            config.CREATE_TEMPLATE,
            name=config.CREATE_TEMPLATE_NIC2,
            network=config.MGMT_BRIDGE,
            interface='virtio'
        ):
            error_stack.append('Action add template nic failed.')
        if not templates.updateTemplateNic(
            self.positive,
            config.CREATE_TEMPLATE,
            config.CREATE_TEMPLATE_NIC1,
            interface='e1000'
        ):
            error_stack.append('Action update template nic failed.')
        if not templates.removeTemplateNic(
            self.positive,
            config.CREATE_TEMPLATE,
            config.CREATE_TEMPLATE_NIC1
        ):
            error_stack.append('Action remove template nic failed.')

        if len(error_stack) > 0:
            raise AssertionError(' '.join(error_stack))

    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_manipulate_permissions(self):
        """ manipulate_permissions """
        error_stack = []
        try:
            assert mla.removeUserRoleFromVm(
                self.positive,
                config.CREATE_VM,
                '%s@%s' % (config.USER_TEST, config.USER_DOMAIN),
                config.UserRole
            )
        except EntityNotFound:
            if not self.creator and self.positive:
                error_stack.append('User is not visible')
        except AssertionError:
            error_stack.append("Can't/Can remove permissions")
        try:
            assert mla.addVMPermissionsToUser(
                self.positive,
                config.USER_TEST,
                config.CREATE_VM,
                config.UserRole
            )
        except EntityNotFound:
            if not self.creator and self.positive:
                error_stack.append('User is not visible')
        except AssertionError:
            error_stack.append("Can't/Can assign permissions")

        if len(error_stack) > 0:
            raise AssertionError(' '.join(error_stack))

    # vm_basic_operations
    # change_vm_custom_properties
    # change_vm_cd
    # import_export_vm
    # configure_vm_network
    # configure_vm_storage
    # manipulate_vm_snapshots
    # copy_template
    # configure_host_network
    # manipulate_host
    # attach_disk
    # assign_cluster_network
    # manipulate_storage_domain
    # migrate_vm
    # configure_storage_pool_network

    # ======================== EDIT ACTIONS =================================

    @user_case(
        login_as=config.USER_DC,
    )
    def test_edit_vm_pool_configuration(self):
        """ edit_vm_pool_configuration """
        try:
            assert vmpools.updateVmPool(
                self.positive,
                config.CREATE_POOL,
                description=str(uuid.uuid4())
            )
        except AttributeError:
            if self.positive:
                raise

    @user_case(
        login_as=config.USER_DC,
    )
    def test_edit_storage_pool_configuration(self):
        """ edit_storage_pool_configuration """
        assert datacenters.update_datacenter(
            self.positive,
            config.DC_NAME[0],
            description=str(uuid.uuid4())
        )

    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_edit_vm_properties(self):
        """ edit_vm_properties """
        assert vms.updateVm(
            self.positive,
            config.CREATE_VM,
            memory=random.randint(1, 4) * config.GB,
            description=str(uuid.uuid4())
        )

    @user_case(
        login_as=config.USER_DC,
    )
    def test_edit_template_properties(self):
        """ edit_template_properties """
        assert templates.updateTemplate(
            self.positive,
            config.CREATE_TEMPLATE,
            memory=random.randint(1, 4) * config.GB,
            description=str(uuid.uuid4())
        )

    @user_case(
        login_as=config.USER_VM,
    )
    def test_edit_disk_properties(self):
        """ edit_disk_properties """
        assert disks.updateDisk(
            self.positive,
            vmName=config.CREATE_VM,
            alias='%s_Disk1' % config.CREATE_VM,
            description=str(uuid.uuid4())
        )

    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_edit_cluster_configuration(self):
        """ edit_cluster_configuration """
        assert clusters.updateCluster(
            self.positive,
            config.CLUSTER_NAME[0],
            description=str(uuid.uuid4())
        )

    # TODO: https://projects.engineering.redhat.com/browse/RHEVM-1960
    # After ticket is resolved enable case again.
    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_edit_host_configuration(self):
        """ edit_host_configuration """
        try:
            assert hosts.updateHost(
                self.positive,
                config.HOSTS[0],
                spm_priority=random.randint(1, 5),
            )
        except EntityNotFound as e:
            if not self.filter_:
                raise e

    @user_case(
        login_as=config.USER_DC,
    )
    def test_edit_storage_domain_configuration(self):
        """ edit_storage_domain_configuration """
        assert storagedomains.updateStorageDomain(
            self.positive,
            config.MASTER_STORAGE,
            description=str(uuid.uuid4())
        )

    # ======================== DELETE ACTIONS ===============================
    # TODO
    # delete_storage_domain - would be tricky
    # delete_host - would be tricky

    @user_case(
        login_as=config.USER_STORAGE,
    )
    def test_delete_disk(self):
        """ delete_disk """
        assert disks.deleteDisk(
            self.positive,
            config.DELETE_DISK
        )
        if self.positive:
            login_as_admin()
            disks.addDisk(
                positive=True,
                alias=config.DELETE_DISK,
                interface='virtio',
                format='cow',
                provisioned_size=config.GB,
                storagedomain=config.MASTER_STORAGE
            )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=clusters.addCluster,
        positive=True,
        name=config.DELETE_CLUSTER,
        cpu=config.CPU_NAME,
        data_center=config.DC_NAME[0],
        version=config.COMP_VERSION
    )
    def test_delete_cluster(self):
        """ delete_cluster """
        assert clusters.removeCluster(self.positive, config.DELETE_CLUSTER)

    @user_case(
        login_as=config.USER_CLUSTER,
        cleanup_func=vms.createVm,
        positive=True,
        vmName=config.DELETE_VM,
        vmDescription=config.DELETE_VM,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE
    )
    def test_delete_vm(self):
        """ delete_vm """
        assert vms.removeVm(self.positive, config.DELETE_VM, wait=False)

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=templates.createTemplate,
        positive=True,
        vm=config.CREATE_VM,
        name=config.DELETE_TEMPLATE
    )
    def test_delete_template(self):
        """ delete_template """
        assert templates.removeTemplate(self.positive, config.DELETE_TEMPLATE)

    @user_case(
        login_as=config.USER_SYSTEM,
        cleanup_func=datacenters.addDataCenter,
        positive=True,
        name=config.DELETE_DC,
        version=config.COMP_VERSION,
        local=True
    )
    def test_delete_storage_pool(self):
        """ delete_storage_pool """
        assert datacenters.remove_datacenter(self.positive, config.DELETE_DC)

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=vmpools.addVmPool,
        positive=True,
        name=config.DELETE_POOL,
        cluster=config.CLUSTER_NAME[0],
        template=config.CREATE_TEMPLATE,
        size=1
    )
    def test_delete_vm_pool(self):
        """ delete_vm_pool """
        assert vmpools.removeVmPool(
            positive=self.positive, vmpool=config.DELETE_POOL
        )
