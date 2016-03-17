#!/usr/bin/env python

import copy
import uuid
import logging
import random

from functools import wraps
from art.unittest_lib import attr
from art.core_api.apis_exceptions import EntityNotFound
from art.unittest_lib import CoreSystemTest as TestCase
from rhevmtests.system.user_tests import config
from art.rhevm_api.tests_lib.high_level import vmpools as hl_vmpools
from art.rhevm_api.tests_lib.low_level import (
    disks, users, vms, vmpools, mla, templates,
    datacenters, clusters, hosts, storagedomains
)


LOGGER = logging.getLogger(__name__)
DETACH_TIMEOUT = 5


def setup_module():
    """ Prepare testing setup """
    assert vms.createVm(
        True,
        config.CREATE_VM, '',
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        storageDomainName=config.MASTER_STORAGE,
        size=config.GB,
    )
    assert vms.createVm(
        True,
        config.RUNNING_VM, '',
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        storageDomainName=config.MASTER_STORAGE,
        size=config.GB,
        start='true'
    )
    assert templates.createTemplate(
        True,
        vm=config.CREATE_VM,
        name=config.CREATE_TEMPLATE
    )
    assert templates.addTemplateNic(
        True,
        config.CREATE_TEMPLATE,
        name=config.CREATE_TEMPLATE_NIC1,
        network=config.MGMT_BRIDGE,
        interface='virtio'
    )
    assert vmpools.addVmPool(
        True,
        name=config.CREATE_POOL,
        cluster=config.CLUSTER_NAME[0],
        template=config.CREATE_TEMPLATE,
        size=1
    )
    assert disks.addDisk(
        True,
        alias=config.DELETE_DISK,
        interface='virtio',
        format='cow',
        provisioned_size=config.GB,
        storagedomain=config.MASTER_STORAGE
    )
    assert clusters.addCluster(
        True,
        name=config.DELETE_CLUSTER,
        cpu=config.CPU_NAME,
        data_center=config.DC_NAME[0],
        version=config.COMP_VERSION
    )
    assert vms.createVm(
        True,
        config.DELETE_VM, '',
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
    )
    assert templates.createTemplate(
        True,
        vm=config.CREATE_VM,
        name=config.DELETE_TEMPLATE
    )
    assert vmpools.addVmPool(
        True,
        name=config.DELETE_POOL,
        cluster=config.CLUSTER_NAME[0],
        template=config.CREATE_TEMPLATE,
        size=1
    )
    assert datacenters.addDataCenter(
        True,
        name=config.DELETE_DC,
        storage_type='nfs',
        version=config.COMP_VERSION
    )
    assert mla.addTemplatePermissionsToGroup(
        True,
        config.EVERYONE_GROUP,
        config.CREATE_TEMPLATE,
        role=config.UserTemplateBasedVm
    )


def teardown_module():
    """ Clean testing setup """
    vms.removeVm(
        True,
        config.CREATE_VM
    )
    vms.removeVm(
        True,
        config.RUNNING_VM,
        stopVM='true'
    )
    vmpools.removeVmPool(
        True,
        vmpool=config.CREATE_POOL
    )
    disks.deleteDisk(
        True,
        config.DELETE_DISK
    )
    clusters.removeCluster(
        True,
        config.DELETE_CLUSTER
    )
    vms.removeVm(
        True,
        config.DELETE_VM
    )
    vmpools.removeVmPool(
        True,
        vmpool=config.DELETE_POOL,
    )
    templates.removeTemplate(
        True,
        config.CREATE_TEMPLATE
    )
    templates.removeTemplate(
        True,
        config.DELETE_TEMPLATE
    )
    datacenters.remove_datacenter(
        True,
        config.DELETE_DC
    )


def ienf(method, *args, **kwargs):
    """
    Ignore EntityNotFound exception I need this function,
    because I have generic test, where I don't know if action succedd or not.
    So at the end I remove all objects which could be created or not.
    """
    try:
        method(*args, **kwargs)
    except EntityNotFound:
        LOGGER.warn('Entity not found: %s%s', method.__name__, args)


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
    Perform test case as user. When method finished, run cleanup.
    :param login_as: user who should perform case
    :param cleanup_func: function which should cleanup case
    :param cleanup_params: parameters of cleanup function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.positive = func.__name__[5:] in self.perms
            LOGGER.info('Running %s %s action',
                        'positive' if self.positive else 'negative',
                        func.__name__)
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
                    self.cleanup_functions.append({
                        'func': cleanup_func,
                        'params': kwargs_glob,
                        })
        return wrapper
    return decorator


@attr(tier=2)
class CaseRoleActions(TestCase):
    """
    This class include all test actions, which role can have.
    Every test action is one test case method.
    User is authenticated at the start of the test,
    and never log out during test. Clean up is done
    by admin@internal at the end of test.
    """
    __test__ = False
    last_logged_in = ''
    cleanup_functions = []  # List of dictionaries of cleanup functions

    def __init__(self, *args, **kwargs):
        """ Assign bz to specific cases """
        super(CaseRoleActions, self).__init__(*args, **kwargs)
        bzs = {
            '1209505': {
                'DiskCreator': ['create_disk'],
                'DiskOperator': ['create_disk'],
                'InstanceCreator': ['create_disk'],
                'PowerUserRole': ['create_disk', 'create_template'],
                'TemplateCreator': ['create_template'],
                'UserInstanceManager': ['create_disk'],
                'UserVmManager': ['create_disk'],
                'UserVmRunTimeManager': ['create_disk'],
                'VmCreator': ['create_disk'],
                'TemplateAdmin': ['create_template'],
                'ClusterAdmin': [
                    'create_vm_pool',
                    'edit_vm_pool_configuration',
                ],
                'DataCenterAdmin': [
                    'create_template',
                    'create_vm_pool',
                    'edit_vm_pool_configuration',
                ],
                'VmPoolAdmin': [
                    'create_vm_pool',
                    'edit_vm_pool_configuration',
                ],
            },
        }
        for bzid, role in bzs.iteritems():
            for perm in role.get(self.role, ()):
                method_name = 'test_%s' % perm
                m = getattr(self, method_name)

                @wraps(m)
                def wrapper(*args, **kwargs):
                    return m(*args, **kwargs)
                wrapper.__dict__ = copy.copy(m.__dict__)
                wrapper.__dict__['bz'] = {
                    bzid: {},
                }
                setattr(self, method_name, wrapper)

    @classmethod
    def setup_class(cls):
        """
        Prepare users with roles on objects.
        """
        for user in config.USERS:
            assert users.addUser(
                True,
                user_name=user,
                domain=config.USER_DOMAIN
            )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_TEST,
            config.CREATE_VM,
            config.UserRole
        )
        assert mla.addRole(
            True,
            name=config.UPDATE_ROLE,
            permits=config.PERMIT_LOGIN
        )
        assert users.addUser(
            True,
            user_name=config.REMOVE_USER,
            domain=config.USER_DOMAIN
        )
        assert users.addRoleToUser(
            True,
            config.USER_SYSTEM,
            cls.role
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_CLUSTER,
            config.CLUSTER_NAME[0],
            cls.role
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_DC,
            config.DC_NAME[0],
            cls.role
        )
        assert mla.addStoragePermissionsToUser(
            True,
            config.USER_STORAGE,
            config.MASTER_STORAGE,
            cls.role
        )
        assert mla.addPermissionsForTemplate(
            True,
            config.USER_DC,
            config.CREATE_TEMPLATE,
            config.UserTemplateBasedVm
        )
        assert mla.addVMPermissionsToUser(
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
                        assert func(
                            True,
                            user,
                            obj_name,
                            role=config.UserTemplateBasedVm
                        )

    @classmethod
    def teardown_class(cls):
        """
        Call cleanup functions.
        """
        login_as_admin()
        for user in config.USERS:
            assert users.removeUser(True, user, config.USER_DOMAIN)

        LOGGER.info('Running cleanup functions: %s', cls.cleanup_functions)
        for cleanup in cls.cleanup_functions:
            try:
                cleanup['func'](**cleanup['params'])
            except EntityNotFound as e:
                LOGGER.warn('Entity was not found: %s', e)
            except Exception as e:  # Continue with execution all functions.
                LOGGER.error(e)

        del cls.cleanup_functions[:]

        ienf(
            mla.removeRole,
            True,
            config.UPDATE_ROLE
        )
        ienf(
            users.removeUser,
            True,
            config.REMOVE_USER
        )
        templates.addTemplateNic(
            True,
            config.CREATE_TEMPLATE,
            name=config.CREATE_TEMPLATE_NIC1,
            network=config.MGMT_BRIDGE,
            interface='virtio'
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
        self.assertTrue(
            datacenters.addDataCenter(
                self.positive,
                name=config.USER_SYSTEM,
                storage_type='nfs',
                version=config.COMP_VERSION
            )
        )

    @user_case(
        login_as=config.USER_CLUSTER,
        cleanup_func=vms.removeVm,
        positive=True,
        vm=config.USER_CLUSTER
    )
    def test_create_vm(self):
        """ create_vm """
        self.assertTrue(
            vms.createVm(
                self.positive,
                config.USER_CLUSTER,
                vmDescription='',
                cluster=config.CLUSTER_NAME[0],
                network=config.MGMT_BRIDGE
            )
        )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=templates.removeTemplate,
        positive=True,
        template=config.USER_DC
    )
    def test_create_template(self):
        """ create_template """
        self.assertTrue(
            templates.createTemplate(
                self.positive,
                vm=config.CREATE_VM,
                name=config.USER_DC
            )
        )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=vmpools.removeVmPool,
        positive=True,
        vmpool=config.USER_DC,
    )
    def test_create_vm_pool(self):
        """ create_vm_pool """
        self.assertTrue(
            vmpools.addVmPool(
                self.positive,
                name=config.USER_DC,
                cluster=config.CLUSTER_NAME[0],
                template=config.CREATE_TEMPLATE,
                size=1
            )
        )

    @user_case(
        login_as=config.USER_STORAGE,
        cleanup_func=disks.deleteDisk,
        positive=True,
        alias=config.USER_STORAGE
    )
    def test_create_disk(self):
        """ create_disk """
        self.assertTrue(
            disks.addDisk(
                self.positive,
                alias=config.USER_STORAGE,
                interface='virtio',
                format='cow',
                provisioned_size=config.GB,
                storagedomain=config.MASTER_STORAGE
            )
        )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=clusters.removeCluster,
        positive=True,
        cluster=config.USER_DC
    )
    def test_create_cluster(self):
        """ create_cluster """
        self.assertTrue(
            clusters.addCluster(
                self.positive,
                name=config.USER_DC,
                cpu=config.CPU_NAME,
                data_center=config.DC_NAME[0],
                version=config.COMP_VERSION
            )
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
        self.assertTrue(
            vmpools.allocateVmFromPool(
                self.positive,
                config.CREATE_POOL
            )
        )

    @user_case(
        login_as=config.USER_CLUSTER,
        cleanup_func=vms.restartVm,
        vm=config.RUNNING_VM,
    )
    def test_connect_to_vm(self):
        """ connect_to_vm """
        self.assertTrue(
            vms.ticketVm(
                self.positive,
                vm=config.RUNNING_VM,
                expiry='120'
            )
        )

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
            self.assertTrue(
                mla.removeUserRoleFromVm(
                    self.positive,
                    config.CREATE_VM,
                    '%s@%s' % (config.USER_TEST, config.USER_DOMAIN),
                    config.UserRole
                )
            )
        except EntityNotFound:
            if not self.creator and self.positive:
                error_stack.append('User is not visible')
        except AssertionError:
            error_stack.append("Can't/Can remove permissions")
        try:
            self.assertTrue(
                mla.addVMPermissionsToUser(
                    self.positive,
                    config.USER_TEST,
                    config.CREATE_VM,
                    config.UserRole
                )
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
            self.assertTrue(
                vmpools.updateVmPool(
                    self.positive,
                    config.CREATE_POOL,
                    description=str(uuid.uuid4())
                )
            )
        except AttributeError:
            if self.positive:
                raise

    @user_case(
        login_as=config.USER_DC,
    )
    def test_edit_storage_pool_configuration(self):
        """ edit_storage_pool_configuration """
        self.assertTrue(
            datacenters.update_datacenter(
                self.positive,
                config.DC_NAME[0],
                description=str(uuid.uuid4())
            )
        )

    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_edit_vm_properties(self):
        """ edit_vm_properties """
        self.assertTrue(
            vms.updateVm(
                self.positive,
                config.CREATE_VM,
                memory=random.randint(1, 4) * config.GB,
                description=str(uuid.uuid4())
            )
        )

    @user_case(
        login_as=config.USER_DC,
    )
    def test_edit_template_properties(self):
        """ edit_template_properties """
        self.assertTrue(
            templates.updateTemplate(
                self.positive,
                config.CREATE_TEMPLATE,
                memory=random.randint(1, 4) * config.GB,
                description=str(uuid.uuid4())
            )
        )

    @user_case(
        login_as=config.USER_VM,
    )
    def test_edit_disk_properties(self):
        """ edit_disk_properties """
        self.assertTrue(
            vms.updateVmDisk(
                self.positive,
                config.CREATE_VM,
                '%s_Disk1' % config.CREATE_VM,
                description=str(uuid.uuid4())
            )
        )

    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_edit_cluster_configuration(self):
        """ edit_cluster_configuration """
        self.assertTrue(
            clusters.updateCluster(
                self.positive,
                config.CLUSTER_NAME[0],
                description=str(uuid.uuid4())
            )
        )

    # TODO: https://projects.engineering.redhat.com/browse/RHEVM-1960
    # After ticket is resolved enable case again.
    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_edit_host_configuration(self):
        """ edit_host_configuration """
        try:
            self.assertTrue(
                hosts.updateHost(
                    self.positive,
                    config.HOSTS[0],
                    storage_manager_priority=random.randint(1, 5),
                )
            )
        except EntityNotFound as e:
            if not self.filter_:
                raise e

    @user_case(
        login_as=config.USER_DC,
    )
    def test_edit_storage_domain_configuration(self):
        """ edit_storage_domain_configuration """
        self.assertTrue(
            storagedomains.updateStorageDomain(
                self.positive,
                config.MASTER_STORAGE,
                description=str(uuid.uuid4())
            )
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
        self.assertTrue(
            disks.deleteDisk(
                self.positive,
                config.DELETE_DISK
            )
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
        self.assertTrue(
            clusters.removeCluster(
                self.positive,
                config.DELETE_CLUSTER
            )
        )

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
        self.assertTrue(
            vms.removeVm(
                self.positive,
                config.DELETE_VM,
                wait=False
            )
        )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=templates.createTemplate,
        positive=True,
        vm=config.CREATE_VM,
        name=config.DELETE_TEMPLATE
    )
    def test_delete_template(self):
        """ delete_template """
        self.assertTrue(
            templates.removeTemplate(
                self.positive,
                config.DELETE_TEMPLATE
            )
        )

    @user_case(
        login_as=config.USER_SYSTEM,
        cleanup_func=datacenters.addDataCenter,
        positive=True,
        name=config.DELETE_DC,
        storage_type='nfs',
        version=config.COMP_VERSION
    )
    def test_delete_storage_pool(self):
        """ delete_storage_pool """
        self.assertTrue(
            datacenters.remove_datacenter(
                self.positive,
                config.DELETE_DC
            )
        )

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
        self.assertTrue(
            vmpools.removeVmPool(
                positive=self.positive,
                vmpool=config.DELETE_POOL,
            )
        )
