"""
Testing if user can access only his objects.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Tests if user can access object which he has permissions for and not see,
if he has not permissions.
"""
import logging
import pytest

from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
    datacenters as hl_dc
)
from art.rhevm_api.tests_lib.low_level import (
    clusters, events, hosts, mla, networks,
    templates, vms, users,
    storagedomains as ll_sd,
    datacenters as ll_dc
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    testflow,
    do_not_run,
)

import common
import config

logger = logging.getLogger(__name__)

alt_host_id = None


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def teardown_module():
        testflow.teardown("Log in as admin.")
        common.login_as_admin()

        testflow.teardown("Removing user %s.", config.USER_NAMES[0])
        users.removeUser(True, config.USER_NAMES[0])

        if not config.GOLDEN_ENV:
            clusters.removeCluster(True, config.CLUSTER_NAME[1])
            hl_dc.clean_datacenter(
                True, config.DC_NAME_B, engine=config.ENGINE
            )

    request.addfinalizer(teardown_module)

    testflow.setup("Log in as admin.")
    common.login_as_admin()

    testflow.setup("Adding user %s.", config.USER_NAMES[0])
    common.add_user(
        True,
        user_name=config.USER_NAMES[0],
        domain=config.USER_DOMAIN
    )

    if not config.GOLDEN_ENV:
        clusters.addCluster(
            True,
            name=config.CLUSTER_NAME[1],
            cpu=config.CPU_NAME,
            data_center=config.DC_NAME[0],
            version=config.COMP_VERSION
        )

        ll_dc.addDataCenter(
            True,
            name=config.DC_NAME_B,
            version=config.COMP_VERSION,
            local=True
        )

        clusters.addCluster(
            True,
            name=config.CLUSTER_NAME_B,
            cpu=config.CPU_NAME,
            data_center=config.DC_NAME_B,
            version=config.COMP_VERSION
        )

        hosts.add_host(
            name=config.HOSTS_IP[1],
            root_password=config.HOSTS_PW,
            address=config.HOSTS_IP[1],
            cluster=config.CLUSTER_NAME_B
        )

        hl_sd.addNFSDomain(
            config.HOSTS_IP[1],
            config.STORAGE_NAME[1],
            config.DC_NAME_B,
            config.ADDRESS[1],
            config.PATH[1]
        )

        global alt_host_id
        alt_host_id = hosts.HOST_API.find(config.HOSTS_IP[1]).get_id()


# extra_reqs={'datacenters_count': 2}
@do_not_run
class TestVmUserInfoTests(common.BaseTestCase):
    """ Test if user can see correct events """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup(cls, request):
        super(TestVmUserInfoTests, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            vms.removeVm(True, config.VM_NAMES[1])
            vms.removeVm(True, config.VM_NAMES[0])
            templates.remove_template(True, config.TEMPLATE_NAMES[1])

        request.addfinalizer(finalize)

        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[1],
            cluster=config.CLUSTER_NAME[1],
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True,
            vm=config.VM_NAMES[1],
            name=config.TEMPLATE_NAMES[1],
            cluster=config.CLUSTER_NAME[1]
        )
        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAMES[0],
            config.role.UserRole
        )
        common.login_as_user()

    @polarion("RHEVM3-7642")
    def test_event_filter_parent_object_events(self):
        """ testEventFilter_parentObjectEvents """
        check_obj = {
            'vm': {
                'name': config.VM_NAMES[1],
                'api': vms.VM_API,
            },
            'cluster': {
                'name': config.CLUSTER_NAME[1],
                'api': clusters.util,
            },
            'data_center': {
                'name': config.DC_NAME[0],
                'api': ll_dc.util,
            },
            'template': {
                'name': config.TEMPLATE_NAMES[1],
                'api': templates.TEMPLATE_API,
            },
            'storage_domain': {
                'name': config.STORAGE_NAME[1],
                'api': ll_sd.util,
            },
        }

        for e in events.util.get(abs_link=False):
            if e is None:
                continue

            logger.info(e.get_description())
            for obj_name in [
                'vm', 'storage_domain', 'cluster', 'data_center', 'template'
            ]:
                obj = getattr(e, obj_name)
                if obj:
                    obj_dict = check_obj[obj_name]
                    api_obj = obj_dict['api'].find(obj.get_id(), 'id')
                    assert api_obj != obj_dict['name']

            host = e.get_host()
            if host:
                assert host.get_id() != alt_host_id


# extra_reqs={'datacenters_count': 2}
@do_not_run
class TestVmUserInfoTests2(common.BaseTestCase):
    """ Test if user can see correct objects """
    # Accessing to specific id don't working in java/python sdk
    # Cli - RHEVM-1758

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestVmUserInfoTests2, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            for vm in config.VM_NAMES[:2]:
                vms.removeVm(True, vm)

        request.addfinalizer(finalize)

        for vm in config.VM_NAMES[:2]:
            vms.createVm(
                positive=True,
                vmName=vm,
                cluster=config.CLUSTER_NAME[0],
                storageDomainName=config.STORAGE_NAME[0],
                provisioned_size=config.GB,
                network=config.MGMT_BRIDGE
            )

        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAMES[0],
            config.role.UserRole
        )
        mla.addPermissionsForTemplate(
            True,
            config.USER_NAMES[0],
            config.BLANK_TEMPLATE,
            role=config.role.TemplateOwner
        )

        cls.vm_ids = [
            vms.VM_API.find(vm).get_id() for vm in config.VM_NAMES[:2]
        ]

    @polarion("RHEVM3-7640")
    def test_filter_parent_objects(self):
        """ filter_parentObjects """
        # TODO: Extend with /templates, /storagedomains, /users, ...
        # Consulted what should be visible to users

        common.login_as_user()

        datacenter = config.DC_NAME[0]
        cluster = config.CLUSTER_NAME[0]

        msg_blind = "User cannot see {0} '{1}' where he has permission."
        msg_visible = (
            "User can see {0} where he has no permissions. Can see {1}"
        )

        dcs = ll_dc.util.get(abs_link=False)
        cls = clusters.util.get(abs_link=False)

        # can user see parent objects of the one with permission?
        dc = ll_dc.util.find(datacenter)
        assert dc is not None, msg_blind.format('datacenter', datacenter)
        cluster = clusters.util.find(cluster)
        assert cluster is not None, msg_blind.format('cluster', cluster)
        logger.info("User can see object where he has permissions.")

        # is user forbidden to see other objects?
        with pytest.raises(EntityNotFound):
            ll_dc.util.find(config.DC_NAME[0])
        with pytest.raises(EntityNotFound):
            clusters.util.find(config.CLUSTER_NAME[1])
        logger.info("User can't see object where he has permissions.")

        assert len(dcs) == 1, msg_visible.format('datacenters', dcs)
        assert len(cls) == 1, msg_visible.format('clusters', cls)

    @polarion("RHEVM3-7639")
    def test_filter_vms(self):
        """ testFilter_vms """
        msg_blind = "The user can't see VM '%s' where he has permissions"
        msg_visible = "The user can see a VM he has no permissions for"
        msg_info = "After deleting permissions from VM he can't see it anymore"

        vm1 = vms.VM_API.find(config.VM_NAMES[0])
        assert vm1 is not None, msg_blind % config.VM_NAMES[0]
        with pytest.raises(EntityNotFound):
            vms.VM_API.find(config.VM_NAMES[1])
        my_vms = vms.VM_API.get(abs_link=False)
        assert len(my_vms) == 1, msg_visible
        logger.info(msg_visible)

        common.login_as_admin()
        mla.removeUserPermissionsFromVm(
            True,
            config.VM_NAMES[0],
            config.USERS[0]
        )

        common.login_as_user()
        with pytest.raises(EntityNotFound):
            vms.VM_API.find(config.VM_NAMES[0])
        logger.info(msg_info)

        common.login_as_admin()
        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAMES[0],
            config.role.UserRole
        )

    @polarion("RHEVM3-7641")
    def test_event_filter_vm_events(self):
        """ testEventFilter_vmEvents """
        msg_blind = "User cannot see VM events where he has permissions"
        msg_visible = "User can see VM events where he's no permissions. {0}"

        common.login_as_admin()
        for vm in config.VM_NAMES[:2]:
            vms.startVm(True, vm)
            vms.stopVm(True, vm)
        logger.info("Events on VMs generated")

        common.login_as_user()

        lst_of_vms = set()
        for e in events.util.get(abs_link=False):
            if e.get_vm():
                lst_of_vms.add(e.get_vm().get_id())

        assert self.vm_ids[0] in lst_of_vms, msg_blind
        logger.info(msg_visible.format(lst_of_vms))

        assert self.vm_ids[1] in lst_of_vms, msg_visible.format(lst_of_vms)
        logger.info(msg_blind)

    @polarion("RHEVM3-7643")
    def test_specific_id(self):
        """ testSpecificId """
        msg_blind = "User cannot see VM where he has permissions"
        msg_visible = "User can see VM where he's no permission. Can See '{0}'"
        vms_api = '/api/vms/{0}'

        common.login_as_user()

        assert vms.VM_API.get(
            href=vms_api.format(self.vm_ids[0])
        ) is not None, msg_blind
        logger.info(msg_visible)

        assert vms.VM_API.get(
            href=vms_api.format(self.vm_ids[1])
        ) is None, msg_visible
        logger.info(msg_blind)

    @polarion("RHEVM3-7644")
    def test_access_denied(self):
        """ testAccessDenied """
        msg = "User can see {0} where he has no permissions. Can see {1}"

        common.login_as_admin()

        def get_storage_domains():
            return [s.get_name() for s in ll_sd.util.get(abs_link=False)]

        def get_templates():
            return [
                t.get_name() for t in templates.TEMPLATE_API.get(
                    abs_link=False
                )
            ]

        def get_networks():
            return [n.get_name() for n in networks.NET_API.get(abs_link=False)]

        admin_storage_domains = get_storage_domains()
        admin_templates = get_templates()
        admin_networks = get_networks()

        common.login_as_user()

        user_storage_domains = get_storage_domains()
        user_templates = get_templates()
        user_networks = get_networks()

        # User should see network, cause every user have NetworkUser perms
        assert len(user_networks) == len(admin_networks), msg.format(
            "networks",
            user_networks
        )
        # User should see SD, which is attach to sd, in which is his VM
        assert len(user_storage_domains) != len(admin_storage_domains), \
            msg.format("storages", user_storage_domains)
        # User should se Blank template
        assert len(user_templates) != len(admin_templates), msg.format(
            "templates",
            user_templates
        )
        logger.info("User see and don't see resources he can/can't.")

    @polarion("RHEVM3-7645")
    def test_host_info(self):
        """ testHostPowerManagementInfo """
        common.login_as_user()

        with pytest.raises(EntityNotFound):
            hosts.HOST_API.find(config.HOSTS[0])
        logger.info("User can't see any host info")
        vms.startVm(True, config.VM_NAMES[0])
        vm = vms.VM_API.find(config.VM_NAMES[0])
        assert vm.get_host() is None
        logger.info("User can't see any host info in /api/vms")
        assert vm.get_placement_policy() is None
        logger.info("User can't see any placement_policy info in /api/vms")
        vms.stopVm(True, config.VM_NAMES[0])


@tier2
class TestViewChildrenInfoTests(common.BaseTestCase):
    """
    Tests if roles that are not able to view children,
    really don't view it.
    """
    # Could change in the future, probably no way how to get it from API.
    # So should be changed if behaviour will change.
    roles_cant = [
        config.role.PowerUserRole,
        config.role.TemplateCreator,
        config.role.VmCreator,
        config.role.DiskCreator,
    ]
    roles_can = [
        config.role.UserRole,
        config.role.UserVmManager,
        config.role.DiskOperator,
        config.role.TemplateOwner,
    ]

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestViewChildrenInfoTests, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Removing VM %s.", config.VM_NAMES[0])
            vms.removeVm(True, config.VM_NAMES[0])

        request.addfinalizer(finalize)

        testflow.setup("Creating VM %s.", config.VM_NAMES[0])
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @polarion("RHEVM3-7638")
    def test_can_view_children(self):
        """ CanViewChildren """
        err_msg = "User can't see vms"
        for role in self.roles_can:
            testflow.step("Testing role: %s", role)
            testflow.step(
                "Adding cluster permissions for user %s.", config.USER_NAMES[0]
            )
            assert mla.addClusterPermissionsToUser(
                True,
                config.USER_NAMES[0],
                config.CLUSTER_NAME[0],
                role
            )

            testflow.step("Log in as user.")
            common.login_as_user()

            testflow.step("Checking if user can see vms.")
            assert len(vms.VM_API.get(abs_link=False)) > 0, err_msg

            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step(
                "Removing cluster permissions from user %s.",
                config.USER_NAMES[0]
            )
            mla.removeUserPermissionsFromCluster(
                True,
                config.CLUSTER_NAME[0],
                config.USERS[0]
            )

    @polarion("RHEVM3-7637")
    def test_cant_view_children(self):
        """ CantViewChildren """
        for role in self.roles_cant:
            testflow.step("Testing role: %s", role)

            testflow.step(
                "Adding cluster permissions for user %s.", config.USER_NAMES[0]
            )
            mla.addClusterPermissionsToUser(
                True,
                config.USER_NAMES[0],
                config.CLUSTER_NAME[0],
                role
            )

            testflow.step("Log in as user.")
            common.login_as_user()

            testflow.step("Checking if user can't see vms.")
            assert len(vms.VM_API.get(abs_link=False)) == 0, "User can see vms"

            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step(
                "Removing cluster permissions from user %s.",
                config.USER_NAMES[0]
            )
            mla.removeUserPermissionsFromCluster(
                True,
                config.CLUSTER_NAME[0],
                config.USERS[0]
            )


# extra_reqs={'clusters_count': 2}
# as ge2 and ge3 have 2 clusters wi will run this test
@do_not_run
class TestVmCreatorClusterAdminInfoTests(common.BaseTestCase):
    """ Test for VM Creator and cluster admin role """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestVmCreatorClusterAdminInfoTests, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            for vm in config.VM_NAMES:
                vms.removeVm(True, vm)
            mla.removeUserPermissionsFromCluster(
                True,
                config.CLUSTER_NAME[0],
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0],
            config.role.UserRole
        )
        mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0],
            config.role.VmCreator
        )

        for idx in range(len(config.VM_NAMES)):
            vms.createVm(
                positive=True,
                vmName=config.VM_NAMES[idx],
                cluster=config.CLUSTER_NAME[0 if idx < 2 else 1],
                network=config.MGMT_BRIDGE
            )

    @polarion("RHEVM3-7647")
    def test_vm_creator_cluster_admin_filter_vms(self):
        """ vmCreatorClusterAdmin_filter_vms """
        err_msg_can = "User can see {0}"
        err_msg_cant = "User can't see {0}"
        common.login_as_user()
        logger.info("Checking right permission on vms.")
        my_vms = [vm.get_name() for vm in vms.VM_API.get(abs_link=False)]
        for idx in range(len(config.VM_NAMES)):
            if idx < 2:
                assert config.VM_NAMES[idx] in my_vms, (
                    err_msg_cant.format(config.VM_NAMES[idx])
                )
            else:
                assert config.VM_NAMES[idx] not in my_vms, (
                    err_msg_can.format(config.VM_NAMES[idx])
                )


@tier2
class TestVmCreatorInfoTests(common.BaseTestCase):
    """ Test for VM Creator role """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestVmCreatorInfoTests, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown(
                "Removing user %s permissions from cluster %s.",
                config.USERS[0], config.CLUSTER_NAME[0]
            )
            mla.removeUserPermissionsFromCluster(
                True, config.CLUSTER_NAME[0], config.USERS[0]
            )

            testflow.teardown(
                "Removing user %s permissions from template %s.",
                config.USERS[0], config.BLANK_TEMPLATE
            )
            mla.removeUserPermissionsFromTemplate(
                True, config.BLANK_TEMPLATE, config.USERS[0]
            )

            for vm in config.VM_NAMES[:2]:
                testflow.teardown("Removing VM %s.", vm)
                vms.removeVm(True, vm)

        request.addfinalizer(finalize)

        testflow.setup(
            "Adding template permissions for user %s.", config.USER_NAMES[0]
        )
        mla.addPermissionsForTemplate(
            True,
            config.USER_NAMES[0],
            config.BLANK_TEMPLATE,
            config.role.UserRole
        )

        testflow.setup(
            "Adding cluster permissions for user %s.", config.USER_NAMES[0]
        )
        mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0],
            config.role.VmCreator
        )

        testflow.setup("Adding VM %s.", config.VM_NAMES[0])
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @polarion("RHEVM3-7646")
    def test_vm_creator_filter_vms(self):
        """ vmCreator_filter_vms """
        msg = "User can see vms where he has no permissions. Can see {0}"

        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step("Checking if user can't see vms.")
        my_vms = [vm.get_name() for vm in vms.VM_API.get(abs_link=False)]
        assert len(my_vms) == 0, msg.format(my_vms)

        testflow.step("Adding VM %s.", config.VM_NAMES[1])
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[1],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        testflow.step("Checking if user can see its VM.")
        my_vms = [vm.get_name() for vm in vms.VM_API.get(abs_link=False)]
        assert len(my_vms) == 1, msg.format(my_vms)


@do_not_run
class TestTemplateCreatorInfoTests(common.BaseTestCase):
    """ Test combination of roles with TemplateCreator role """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestTemplateCreatorInfoTests, cls).setup_class(request)

        def finalize():
            common.login_as_admin()

            for vm in config.VM_NAMES[:2]:
                vms.removeVm(True, vm)

            for template in config.TEMPLATE_NAMES[:3]:
                templates.remove_template(True, template)

            mla.removeUserPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        for vm in config.VM_NAMES[:2]:
            vms.createVm(
                positive=True,
                vmName=vm,
                cluster=config.CLUSTER_NAME[0],
                network=config.MGMT_BRIDGE
            )
        mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            config.role.TemplateCreator
        )
        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAMES[0],
            config.role.UserRole
        )

        for vm, template in zip(
                config.VM_NAMES[:2],
                reversed(config.TEMPLATE_NAMES[:2])
        ):
            templates.createTemplate(
                True,
                vm=vm,
                name=template,
                cluster=config.CLUSTER_NAME[0]
            )

    @polarion("RHEVM3-7648")
    def test_template_creator_filter_templates_and_vms(self):
        """ Template creator with user role filter template and vms """
        msg_cant = "User can't see {0} '{1}' which should see"
        msg_can = "User can see {0} '{1}' which shouldn't see"

        common.login_as_user()
        logger.info("Checking right permissions for all vms")

        user_vms = [vm.get_name() for vm in vms.VM_API.get(abs_link=False)]
        assert config.VM_NAMES[0] in user_vms, msg_cant.format(
            'VM',
            config.VM_NAMES[0]
        )
        assert config.VM_NAMES[1] not in user_vms, msg_can.format(
            'VM',
            config.VM_NAMES[1]
        )
        logger.info("User can see %s", user_vms)

        logger.info("Checking right permissions for all templates")
        tms = [
            t.get_name() for t in templates.TEMPLATE_API.get(abs_link=False)
        ]
        err_msg = msg_can.format('Template', config.TEMPLATE_NAMES[0])
        assert config.TEMPLATE_NAMES[0] not in tms, err_msg
        err_msg = msg_can.format('Template', config.TEMPLATE_NAMES[1])
        assert config.TEMPLATE_NAMES[1] not in tms, err_msg
        logger.info("User can see %s", tms)

        templates.createTemplate(
            True,
            vm=config.VM_NAMES[0],
            name=config.TEMPLATE_NAMES[2],
            cluster=config.CLUSTER_NAME[0]
        )
        logger.info(
            "Checking right permission for %s",
            config.TEMPLATE_NAMES[2]
        )
        tms = [
            t.get_name() for t in templates.TEMPLATE_API.get(abs_link=False)
        ]
        # tms == 2(blank + newly created)
        err_msg = msg_can.format('Templates', tms)
        assert config.TEMPLATE_NAMES[2] in tms and len(tms) == 2, err_msg
        logger.info("User can see %s", tms)


# Create some templates in Datacenter1.
# Create user and give him both roles TemplateCreator and DataCenterAdmin for
# Datacenter1
# Create some templates in Datacenter2.
# - Check /api/templates
# Should see all templates in Datacenter1, but none in Datacenter2.
# extra_reqs={'datacenters_count': 2}
@do_not_run
class TestTemplateCreatorAndDCAdminInfoTest(common.BaseTestCase):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestTemplateCreatorAndDCAdminInfoTest, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            for vm in config.VM_NAMES[:2]:
                vms.removeVm(True, vm)
            for template in config.TEMPLATE_NAMES[:2]:
                templates.remove_template(True, template)
            mla.removeUserPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USERS[0]
            )

        request.addfinalizer(finalize)

        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True,
            vm=config.VM_NAMES[0],
            name=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )
        mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            config.role.TemplateCreator
        )
        mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            config.role.TemplateOwner
        )
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[1],
            cluster=config.CLUSTER_NAME[1],
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True,
            vm=config.VM_NAMES[1],
            name=config.TEMPLATE_NAMES[1],
            cluster=config.CLUSTER_NAME[1]
        )

    @polarion("RHEVM3-7649")
    def test_template_creator_data_center_admin_filter_templates(self):
        """ Template creator with datacenter admin filter templates """
        common.login_as_user()
        templates.TEMPLATE_API.find(config.TEMPLATE_NAMES[0])
        with pytest.raises(EntityNotFound):
            templates.TEMPLATE_API.find(config.TEMPLATE_NAMES[1])


# extra_reqs={'datacenters_count': 2}
@do_not_run
class TestComplexCombinationTest(common.BaseTestCase):
    """ Test that user can see correct object regarding its permissions """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestComplexCombinationTest, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            for vm in config.VM_NAMES:
                vms.removeVm(True, vm)

            for template in config.TEMPLATE_NAMES:
                templates.remove_template(True, template)

            users.removeUser(True, config.USER_NAMES[0])
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
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[1],
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True,
            vm=config.VM_NAMES[0],
            name=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )
        templates.createTemplate(
            True,
            vm=config.VM_NAMES[1],
            name=config.TEMPLATE_NAMES[1],
            cluster=config.CLUSTER_NAME[0]
        )

        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[2],
            cluster=config.CLUSTER_NAME[1],
            storageDomainName=config.STORAGE_NAME[1],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            positive=True,
            vmName=config.VM_NAMES[3],
            cluster=config.CLUSTER_NAME[1],
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True,
            vm=config.VM_NAMES[2],
            name=config.TEMPLATE_NAMES[2],
            cluster=config.CLUSTER_NAME[1]
        )
        templates.createTemplate(
            True,
            vm=config.VM_NAMES[3],
            name=config.TEMPLATE_NAMES[3],
            cluster=config.CLUSTER_NAME[1]
        )
        mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAMES[0],
            config.role.UserRole
        )
        mla.addPermissionsForTemplate(
            True,
            config.USER_NAMES[0],
            config.TEMPLATE_NAMES[1]
        )
        mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[1],
            config.role.VmCreator
        )
        mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            config.role.TemplateCreator
        )
        mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[1],
            config.role.ClusterAdmin
        )

    # Check BZ 881109 - behaviour could be changed in future.
    @polarion("RHEVM3-7650")
    def test_complex_combination_filter_templates_and_vms(self):
        """ ComplexCombination filter templatesAndVms """
        # TODO: extend, there could be tested more than this
        common.login_as_user()
        vms.VM_API.find(config.VM_NAMES[0])
        logger.info("User can see %s", config.VM_NAMES[0])
        logger.info("User can't see:")
        for vm in config.VM_NAMES[1:]:
            with pytest.raises(EntityNotFound):
                vms.VM_API.find(vm)
            logger.info("\t{0}".format(vm))

        logger.info("User can't see:")
        for template in config.TEMPLATE_NAMES:
            with pytest.raises(EntityNotFound):
                templates.TEMPLATE_API.find(template)
            logger.info("\t{0}".format(template))
