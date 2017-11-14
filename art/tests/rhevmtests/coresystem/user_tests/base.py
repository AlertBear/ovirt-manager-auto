import uuid
import logging
import random
import pytest

from functools import partial, wraps

from art.unittest_lib import tier2, testflow, CoreSystemTest
from art.core_api.apis_exceptions import EntityNotFound

from art.rhevm_api.tests_lib.high_level import vmpools as hl_vmpools
from art.rhevm_api.tests_lib.low_level import (
    disks, users, vms,
    vmpools, mla, templates,
    datacenters, clusters, hosts,
    storagedomains, general as ll_general
)
from rhevmtests.coresystem.helpers import EngineCLI

import config

DETACH_TIMEOUT = 5

logger = logging.getLogger(__name__)


def iexs(method, *args, **kwargs):
    """
    Ignore IndexError and EntityNotFound exceptions. We need this function,
    because these tests are so generic, where we don't know if
    action succeeded or not. So in the end we remove all objects
    which could be created or not.

    Args:
        method (function): function to invoke
        *args: arguments of the function

    Kwargs:
        **kwargs: keyword arguments of the function

    Returns:
        None: this function returns nothing as we don't need any result.
    """
    try:
        method(*args, **kwargs)
    except IndexError:
        logger.warning("Index error: %s%s", method.__name__, str(args))
    except EntityNotFound:
        logger.warning("Entity not found: %s%s", method.__name__, str(args))


def skip_if_fails(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AssertionError as err:
            return pytest.skip(
                "Failed on module setup phase with reason: {}".format(err)
            )
    return wrapper


@skip_if_fails
@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Removing vm %s", config.CREATE_VM)
        vms.removeVm(True, config.CREATE_VM)

        testflow.teardown("Removing vm %s", config.RUNNING_VM)
        vms.removeVm(True, config.RUNNING_VM, stopVM='true')

        testflow.teardown("Removing disk %s", config.DELETE_DISK)
        iexs(disks.deleteDisk, True, config.DELETE_DISK, async=False)

        iexs(clusters.removeCluster, True, config.DELETE_CLUSTER)

        testflow.teardown("Removing vm %s", config.DELETE_VM)
        iexs(vms.removeVm, True, config.DELETE_VM)

        testflow.teardown("Removing vmpool %s", config.DELETE_POOL)
        iexs(vmpools.removeVmPool, True, config.DELETE_POOL)

        testflow.teardown("Removing template %s", config.CREATE_TEMPLATE)
        templates.remove_template(True, config.CREATE_TEMPLATE)

        testflow.teardown("Removing template %s", config.DELETE_TEMPLATE)
        iexs(templates.remove_template, True, config.DELETE_TEMPLATE)

        testflow.teardown("Removing datacenter %s", config.DELETE_DC)
        iexs(datacenters.remove_datacenter, True, config.DELETE_DC, force=True)

        with config.ENGINE_HOST.executor().session() as ss:
            user_cli = EngineCLI(
                tool=config.AAA_TOOL, session=ss
            ).setup_module('user')

            for user in config.USERS[:-1]:
                testflow.teardown("Deleting user %s.", user)
                assert user_cli.run("delete", user,)[0]

    request.addfinalizer(finalize)

    with config.ENGINE_HOST.executor().session() as ss:
        user_cli = EngineCLI(
            tool=config.AAA_TOOL, session=ss
        ).setup_module('user')

        for user in config.USERS[:-1]:
            # Workaround if environment is not clean
            try:
                testflow.setup("Deleting user %s.", user)
                user_cli.run("delete", user, )[0]
            except Exception as err:
                raise err

            testflow.setup("Creating user %s.", user)
            user_cli.run(
                "add", user,
                attribute="firstName={0}".format(user),
            )[0]

            testflow.setup("Resetting password of user %s.", user)
            user_cli.run(
                "password-reset", user,
                password="pass:{0}".format(config.USER_PASSWORD),
                password_valid_to='2050-01-01 00:00:00Z',
            )[0]

    testflow.setup("Creating vm %s", config.CREATE_VM)
    assert vms.createVm(
        True, config.CREATE_VM,
        cluster=config.CLUSTER_NAME[0], network=config.MGMT_BRIDGE,
        storageDomainName=config.master_storage, provisioned_size=config.GB
    )

    testflow.setup("Creating vm %s", config.RUNNING_VM)
    assert vms.createVm(
        True, config.RUNNING_VM, cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE, storageDomainName=config.master_storage,
        provisioned_size=config.GB, start="true"
    )

    testflow.setup("Creating template %s", config.CREATE_TEMPLATE)
    assert templates.createTemplate(
        True, vm=config.CREATE_VM, name=config.CREATE_TEMPLATE
    )

    testflow.setup("Creating template's nic %s", config.CREATE_TEMPLATE_NIC1)
    assert templates.addTemplateNic(
        True, config.CREATE_TEMPLATE,
        name=config.CREATE_TEMPLATE_NIC1,
        network=config.MGMT_BRIDGE,
        interface=config.INTERFACE_VIRTIO
    )

    testflow.setup("Adding disk %s", config.DELETE_DISK)
    assert disks.addDisk(
        True, alias=config.DELETE_DISK,
        interface=config.INTERFACE_VIRTIO, format=config.DISK_FORMAT_COW,
        provisioned_size=config.GB, storagedomain=config.master_storage
    )

    testflow.setup("Adding cluster %s", config.DELETE_CLUSTER)
    assert clusters.addCluster(
        True, name=config.DELETE_CLUSTER,
        cpu=config.CPU_NAME,
        data_center=config.DC_NAME[0],
        version=config.COMP_VERSION
    )

    testflow.setup("Creating vm %s", config.DELETE_VM)
    assert vms.createVm(
        True, config.DELETE_VM,
        cluster=config.CLUSTER_NAME[0], network=config.MGMT_BRIDGE,
    )

    testflow.setup("Creating template %s", config.DELETE_TEMPLATE)
    assert templates.createTemplate(
        True, vm=config.CREATE_VM, name=config.DELETE_TEMPLATE
    )

    testflow.setup("Adding vmpool %s", config.DELETE_POOL)
    try:
        hl_vmpools.create_vm_pool(
            True, config.DELETE_POOL, config.VMPOOL_PARAMS
        )
    except Exception:
        raise AssertionError()

    testflow.setup("Adding datacenter %s", config.DELETE_DC)
    assert datacenters.addDataCenter(
        True, name=config.DELETE_DC,
        version=config.COMP_VERSION, local=True
    )

    testflow.setup("Adding permissions to group %s", config.EVERYONE_GROUP)
    assert mla.addTemplatePermissionsToGroup(
        True, config.EVERYONE_GROUP,
        config.CREATE_TEMPLATE, role=config.UserTemplateBasedVm
    )


@ll_general.generate_logs(step=True)
def login_as_user(user, filter_):
    """
    Log into engine as given user.

    Args:
        user (str): User to log in.
        filter_ (bool): Filter API response or not.
    """
    users.loginAsUser(
        user, config.USER_PROFILE,
        config.USER_PASSWORD, filter=filter_
    )
    return True


@ll_general.generate_logs(step=True)
def login_as_admin():
    """
    Log into engine as administrator.
    """
    users.loginAsUser(
        config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
        config.VDC_PASSWORD, filter=False
    )
    return True


def user_case(func=None, login_as=None, cleanup_func=None, **kwargs_glob):
    """
    Perform test case as user. When the method is finished, run cleanup.

    Args:
        login_as (str): user who should perform case
        cleanup_func (function): function which should cleanup case

    Kwargs:
        cleanup_params: parameters of cleanup function

    Returns:
        function: decorator for a test case
    """
    if func is None:
        return partial(
            user_case, login_as=login_as,
            cleanup_func=cleanup_func, **kwargs_glob
        )

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """
        If permit in role permits let's assume positive outcome.
        test_permit[:5] -> permit
        """
        self.positive = func.__name__[5:] in self.perms
        func.__dict__['role'] = kwargs_glob.get('role')

        if self.previous_login != login_as:
            login_as_user(login_as, self.filter_)
            self.previous_login = login_as

        try:
            func(self, *args, **kwargs)
        except EntityNotFound as err:
            if self.positive:
                raise err
            else:
                logger.warning(err)
        except AttributeError as err:
            if self.positive:
                raise err
            else:
                logger.warning(err)
        # Case failed, clean even if not positive.
        except AssertionError as err:
            self.positive = True
            raise err
        finally:
            if self.positive and cleanup_func is not None:
                self.cleanup_functions.append(
                    {
                        'func': cleanup_func,
                        'params': kwargs_glob,
                    }
                )
    return wrapper


@tier2
class CaseRoleActions(CoreSystemTest):
    """
    This class includes all test actions role can have.
    Every test action is the one test case method.
    User is authenticated at the start of the test,
    and never log out during test. Clean up is done
    by admin@internal at the end of test.
    """
    previous_login = ''
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
            login_as_admin()

            for cleanup in cls.cleanup_functions:
                testflow.teardown(
                    "Running cleanup function %s.",
                    cleanup['func'].__name__
                )
                try:
                    cleanup['func'](**cleanup['params'])
                except EntityNotFound as err:
                    logger.warning(err)
                # Continue with execution of all functions.
                except Exception as err:
                    logger.error(err)

            del cls.cleanup_functions[:]

            for vm in [
                    config.DELETE_VM,
                    config.CREATE_VM,
                    config.RUNNING_VM
            ]:
                testflow.teardown("Waiting for vm %s.", vm)
                iexs(
                    vms.wait_for_vm_states,
                    vm, states=[config.VM_UP, config.VM_DOWN]
                )

            testflow.teardown("Removing vmpool %s.", config.CREATE_POOL)
            vmpools.removeVmPool(True, config.CREATE_POOL)

            testflow.teardown(
                "Removing %s user's permissions from cluster %s.",
                config.USER_CLUSTER, config.CLUSTER_NAME[0]
            )
            iexs(
                mla.removeUsersPermissionsFromCluster,
                True, config.CLUSTER_NAME[0], [config.USER_CLUSTER]
            )

            testflow.teardown(
                "Removing %s user's permissions from datacenter %s.",
                config.USER_DC, config.DC_NAME[0]
            )
            iexs(
                mla.removeUsersPermissionsFromDatacenter,
                True, config.DC_NAME[0], [config.USER_DC]
            )

            testflow.teardown(
                "Removing %s user's permissions from storage domain %s.",
                config.USER_STORAGE, config.master_storage
            )
            iexs(
                mla.removeUsersPermissionsFromSD,
                True, config.master_storage, [config.USER_STORAGE]
            )

            for user in config.USERS:
                testflow.teardown(
                    "Removing user %s@%s.", user, config.USER_DOMAIN
                )
                # users.removeUser(True, user, config.USER_DOMAIN)
                users.removeUser(True, user)

            testflow.teardown(
                "Removing user %s@%s.", config.REMOVE_USER, config.USER_DOMAIN
            )
            iexs(users.removeUser, True, config.REMOVE_USER)

            testflow.teardown("Removing role %s.", config.UPDATE_ROLE)
            iexs(mla.removeRole, True, config.UPDATE_ROLE)

        request.addfinalizer(finalize)

        testflow.setup("Adding vmpool %s.", config.CREATE_POOL)
        try:
            hl_vmpools.create_vm_pool(
                True, config.CREATE_POOL, config.VMPOOL_PARAMS
            )
        except Exception as err:
            logger.warning(err)

        for user in config.USERS:
            testflow.setup("Adding user %s@%s.", user, config.USER_DOMAIN)
            assert users.addExternalUser(
                True, user_name=user, domain=config.USER_DOMAIN
            )

        testflow.setup(
            "Adding role %s permissions to %s user.",
            config.UserRole, config.USER_TEST
        )
        assert mla.addVMPermissionsToUser(
            True, config.USER_TEST, config.CREATE_VM, config.UserRole
        )

        testflow.setup("Adding role %s.", config.UPDATE_ROLE)
        assert mla.addRole(
            True, name=config.UPDATE_ROLE, permits=config.PERMIT_LOGIN
        )

        testflow.setup("Adding user %s.", config.REMOVE_USER)
        assert users.addExternalUser(
            True, user_name=config.REMOVE_USER, domain=config.USER_DOMAIN
        )

        testflow.setup(
            "Adding %s role to %s user.", cls.role, config.USER_SYSTEM
        )
        assert users.addRoleToUser(True, config.USER_SYSTEM, cls.role)

        testflow.setup(
            "Adding %s cluster permissions to %s user.",
            config.CLUSTER_NAME[0], config.USER_CLUSTER
        )
        assert mla.addClusterPermissionsToUser(
            True, config.USER_CLUSTER, config.CLUSTER_NAME[0], role=cls.role
        )

        testflow.setup(
            "Adding %s datacenter permission to %s user.",
            config.DC_NAME[0], config.USER_DC
        )
        assert mla.addPermissionsForDataCenter(
            True, config.USER_DC, config.DC_NAME[0], role=cls.role
        )

        testflow.setup(
            "Adding %s storage permissions to %s user.",
            config.master_storage, config.USER_STORAGE
        )
        assert mla.addStoragePermissionsToUser(
            True, config.USER_STORAGE, config.master_storage, role=cls.role
        )

        testflow.setup(
            "Adding %s template permissions to %s user.",
            config.CREATE_TEMPLATE, config.USER_DC
        )
        assert mla.addPermissionsForTemplate(
            True, config.USER_DC, config.CREATE_TEMPLATE, role=cls.role
        )

        testflow.setup(
            "Adding %s vm permissions to %s user.",
            config.CREATE_VM, config.USER_VM
        )
        assert mla.addVMPermissionsToUser(
            True, config.USER_VM, config.CREATE_VM, role=cls.role
        )

        """
        Need to assign permissions for roles which are not supposed to view
        children to avoid EntityNotFound exception and rather test real action
        """

        cls.creator = not mla.allows_view_children(cls.role, config.ENGINE.db)
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
                            True, user,
                            obj_name, role=config.UserTemplateBasedVm
                        )

    # ======================= CREATE ACTIONS ================================

    @user_case(
        login_as=config.USER_SYSTEM,
        cleanup_func=datacenters.remove_datacenter,
        positive=True,
        datacenter=config.USER_SYSTEM,
    )
    def test_create_storage_pool(self):
        """ create_storage_pool """
        testflow.step("Adding datacenter %s.", config.USER_SYSTEM)
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
        vm=config.USER_CLUSTER,
    )
    def test_create_vm(self):
        """ create_vm """
        testflow.step("Creating vm %s.", config.USER_CLUSTER)
        assert vms.createVm(
            self.positive,
            config.USER_CLUSTER,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=templates.remove_template,
        positive=True,
        template=config.USER_DC,
    )
    def test_create_template(self):
        """ create_template """
        testflow.step("Creating template %s.", config.USER_DC)
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
        testflow.step("Creating vm pool %s.", config.USER_DC)
        hl_vmpools.create_vm_pool(
            self.positive, config.USER_DC, config.VMPOOL_PARAMS
        )

    @user_case(
        login_as=config.USER_STORAGE,
        cleanup_func=disks.deleteDisk,
        positive=True,
        alias=config.USER_STORAGE,
    )
    def test_create_disk(self):
        """ create_disk """
        testflow.step("Adding disk %s.", config.USER_STORAGE)
        assert disks.addDisk(
            self.positive,
            alias=config.USER_STORAGE,
            interface=config.INTERFACE_VIRTIO,
            format=config.DISK_FORMAT_COW,
            provisioned_size=config.GB,
            storagedomain=config.master_storage
        )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=clusters.removeCluster,
        positive=True,
        cluster=config.USER_DC,
    )
    def test_create_cluster(self):
        """ create_cluster """
        testflow.step(
            "Adding cluster %s to datacenter %s.",
            config.USER_DC, config.DC_NAME[0]
        )
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
        role=config.CREATE_ROLE,
    )
    def test_manipulate_roles(self):
        """ manipulate_roles """
        testflow.step("Adding role %s.", config.CREATE_ROLE)
        assert mla.addRole(
            self.positive,
            name=config.CREATE_ROLE,
            permits=config.PERMIT_LOGIN
        )

        testflow.step("Updating role %s.", config.UPDATE_ROLE)
        assert mla.updateRole(
            self.positive,
            config.UPDATE_ROLE,
            description=config.CREATE_ROLE
        )

        testflow.step("Removing role %s.", config.UPDATE_ROLE)
        assert mla.removeRole(
            self.positive,
            config.UPDATE_ROLE
        )

    @user_case(
        login_as=config.USER_SYSTEM,
        cleanup_func=users.removeUser,
        positive=True,
        user=config.CREATE_USER,
    )
    def test_manipulate_users(self):
        """ manipulate_users """
        testflow.step("Adding user %s.", config.CREATE_USER)
        assert users.addExternalUser(
            self.positive,
            user_name=config.CREATE_USER,
            domain=config.USER_DOMAIN
        )

    @user_case(
        login_as=config.USER_DC,
    )
    def test_vm_pool_basic_operations(self):
        """ vm_pool_basic_operations """
        testflow.step("Allocating vm from pool %s.", config.CREATE_POOL)
        assert vmpools.allocateVmFromPool(self.positive, config.CREATE_POOL)

        if self.positive:
            testflow.step(
                "Getting list of vms of pool %s.", config.CREATE_POOL
            )
            pool_vms = vmpools.get_vms_in_pool_by_name(config.CREATE_POOL)
            if pool_vms:
                for pool_vm in pool_vms:
                    testflow.step("Waiting for vm %s to up.", pool_vm)
                    vms.wait_for_vm_states(pool_vm, states=[config.VM_UP])

                    testflow.step("Stopping vm %s.", pool_vm)
                    assert vms.stopVm(self.positive, pool_vm)

                    testflow.step("Waiting until vm %s is stopped.", pool_vm)
                    vms.wait_for_vm_states(pool_vm, states=[config.VM_DOWN])

                    testflow.step(
                        "Waiting for all snapshots of vm %s to be ok.", pool_vm
                    )
                    vms.wait_for_vm_snapshots(pool_vm, config.SNAPSHOT_OK)

                    testflow.step(
                        "Waiting for all disks of vm %s to be ok.", pool_vm
                    )
                    assert vms.wait_for_disks_status(
                        [d.get_alias() for d in vms.getVmDisks(pool_vm)]
                    )

    @user_case(
        login_as=config.USER_CLUSTER,
        cleanup_func=vms.restartVm,
        vm=config.RUNNING_VM,
    )
    def test_connect_to_vm(self):
        """ connect_to_vm """
        testflow.step("Connecting to vm %s.", config.RUNNING_VM)
        assert vms.ticketVm(self.positive, vm=config.RUNNING_VM, expiry='120')

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=templates.removeTemplateNic,
        positive=True,
        template=config.CREATE_TEMPLATE,
        nic=config.CREATE_TEMPLATE_NIC2,
    )
    def test_configure_template_network(self):
        """ configure_template_network """
        testflow.step(
            "Adding nic %s to template %s.",
            config.CREATE_TEMPLATE_NIC2, config.CREATE_TEMPLATE
        )
        assert templates.addTemplateNic(
            self.positive,
            config.CREATE_TEMPLATE,
            name=config.CREATE_TEMPLATE_NIC2,
            network=config.MGMT_BRIDGE,
            interface=config.INTERFACE_VIRTIO
        )

        testflow.step(
            "Updating template %s nic %s.",
            config.CREATE_TEMPLATE, config.CREATE_TEMPLATE_NIC2
        )
        assert templates.updateTemplateNic(
            self.positive,
            config.CREATE_TEMPLATE,
            config.CREATE_TEMPLATE_NIC2,
            interface='e1000'
        )

        testflow.step(
            "Removing nic %s from template %s.",
            config.CREATE_TEMPLATE_NIC2, config.CREATE_TEMPLATE
        )
        assert templates.removeTemplateNic(
            self.positive,
            config.CREATE_TEMPLATE,
            config.CREATE_TEMPLATE_NIC2
        )

    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_manipulate_permissions(self):
        """ manipulate_permissions """
        user = "{0}@{1}".format(config.USER_TEST, config.USER_DOMAIN)

        testflow.step(
            "Removing user's %s role from VM %s.", user, config.CREATE_VM
        )
        assert mla.removeUserRoleFromVm(
            self.positive,
            config.CREATE_VM,
            user,
            config.UserRole
        )

        testflow.step(
            "Adding permissions to user %s for VM %s.", user, config.CREATE_VM
        )
        assert mla.addVMPermissionsToUser(
            self.positive,
            config.USER_TEST,
            config.CREATE_VM,
            config.UserRole
        )

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
        testflow.step("Updating vm pool %s.", config.CREATE_POOL)
        assert vmpools.updateVmPool(
            self.positive, config.CREATE_POOL, description=str(uuid.uuid4())
        )

    @user_case(
        login_as=config.USER_DC,
    )
    def test_edit_storage_pool_configuration(self):
        """ edit_storage_pool_configuration """
        testflow.step("Updating datacenter %s.", config.DC_NAME[0])
        assert datacenters.update_datacenter(
            self.positive, config.DC_NAME[0], description=str(uuid.uuid4())
        )

    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_edit_vm_properties(self):
        """ edit_vm_properties """
        testflow.step("Updating VM %s.", config.CREATE_VM)
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
        testflow.step("Updating template %s.", config.CREATE_TEMPLATE)
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
        disk_name = "{0}_Disk1".format(config.CREATE_VM)
        testflow.step("Updating disk %s.", disk_name)
        assert disks.updateDisk(
            self.positive,
            vmName=config.CREATE_VM,
            alias=disk_name,
            description=str(uuid.uuid4())
        )

    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_edit_cluster_configuration(self):
        """ edit_cluster_configuration """
        testflow.step("Updating cluster %s.", config.CLUSTER_NAME[0])
        assert clusters.updateCluster(
            self.positive,
            config.CLUSTER_NAME[0],
            description=str(uuid.uuid4())
        )

    @user_case(
        login_as=config.USER_CLUSTER,
    )
    def test_edit_host_configuration(self):
        """ edit_host_configuration """
        testflow.step("Updating host %s.", config.HOSTS[0])
        assert hosts.update_host(
            self.positive, config.HOSTS[0], spm_priority=random.randint(1, 5)
        )

    @user_case(
        login_as=config.USER_DC,
    )
    def test_edit_storage_domain_configuration(self):
        """ edit_storage_domain_configuration """
        testflow.step("Updating storage domain %s.", config.master_storage)
        assert storagedomains.updateStorageDomain(
            self.positive, config.master_storage, description=str(uuid.uuid4())
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
        testflow.step("Deleting disk %s.", config.DELETE_DISK)
        assert disks.deleteDisk(self.positive, config.DELETE_DISK)

        if self.positive:
            testflow.step("Adding disk %s.", config.DELETE_DISK)
            assert disks.addDisk(
                positive=self.positive,
                alias=config.DELETE_DISK,
                interface=config.INTERFACE_VIRTIO,
                format=config.DISK_FORMAT_COW,
                provisioned_size=config.GB,
                storagedomain=config.master_storage
            )

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=clusters.addCluster,
        positive=True,
        name=config.DELETE_CLUSTER,
        cpu=config.CPU_NAME,
        data_center=config.DC_NAME[0],
        version=config.COMP_VERSION,
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
        network=config.MGMT_BRIDGE,
    )
    def test_delete_vm(self):
        """ delete_vm """
        testflow.step("Removing VM %s.", config.DELETE_VM)
        assert vms.removeVm(self.positive, config.DELETE_VM)

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=templates.createTemplate,
        positive=True,
        vm=config.CREATE_VM,
        name=config.DELETE_TEMPLATE,
    )
    def test_delete_template(self):
        """ delete_template """
        testflow.step("Removing template %s.", config.DELETE_TEMPLATE)
        assert templates.remove_template(
            self.positive, config.DELETE_TEMPLATE
        )

    @user_case(
        login_as=config.USER_SYSTEM,
        cleanup_func=datacenters.addDataCenter,
        positive=True,
        name=config.DELETE_DC,
        version=config.COMP_VERSION,
        local=True,
    )
    def test_delete_storage_pool(self):
        """ delete_storage_pool """
        testflow.step("Removing datacenter %s.", config.DELETE_DC)
        assert datacenters.remove_datacenter(self.positive, config.DELETE_DC)

    @user_case(
        login_as=config.USER_DC,
        cleanup_func=hl_vmpools.create_vm_pool,
        positive=True,
        pool_name=config.DELETE_POOL,
        pool_params=config.VMPOOL_PARAMS,
    )
    def test_delete_vm_pool(self):
        """ delete_vm_pool """
        testflow.step("Removing vm pool %s.", config.DELETE_POOL)
        assert vmpools.removeVmPool(self.positive, config.DELETE_POOL)
