'''
Testing if user can access only his objects.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Tests if user can access object which he has permissions for and not see,
if he has not permissions.
'''

__test__ = True

import logging

from rhevmtests.system.user_roles_tests import config, common
from rhevmtests.system.user_roles_tests.roles import role
from nose.tools import istest
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.rhevm_api.tests_lib.low_level import (
    users, vms, templates, mla, clusters, datacenters, hosts,
    storagedomains, networks, events
)
from art.rhevm_api.tests_lib.high_level.datacenters import clean_datacenter

from art.rhevm_api.tests_lib.high_level import (
    storagedomains as h_storagedomains
)
from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.core_api.apis_exceptions import EntityNotFound

TCMS_PLAN_ID = 6283
LOGGER = logging.getLogger(__name__)
ALT_HOST_ID = None


def setUpModule():
    common.addUser(True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)

    if not config.GOLDEN_ENV:
        clusters.addCluster(
            True, name=config.CLUSTER_NAME[1],
            cpu=config.CPU_NAME,
            data_center=config.DC_NAME[0],
            version=config.COMP_VERSION
        )

        datacenters.addDataCenter(
            True, name=config.DC_NAME_B,
            storage_type=config.STORAGE_TYPE,
            version=config.COMP_VERSION
        )
        clusters.addCluster(
            True, name=config.CLUSTER_NAME_B,
            cpu=config.CPU_NAME,
            data_center=config.DC_NAME_B,
            version=config.COMP_VERSION
        )
        hosts.addHost(
            True, config.HOSTS_IP[1],
            root_password=config.HOSTS_PW,
            address=config.HOSTS_IP[1],
            cluster=config.CLUSTER_NAME_B
        )
        h_storagedomains.addNFSDomain(
            config.HOSTS_IP[1], config.STORAGE_NAME[1],
            config.DC_NAME_B, config.ADDRESS[1],
            config.PATH[1]
        )
        global ALT_HOST_ID
        ALT_HOST_ID = hosts.HOST_API.find(config.HOSTS_IP[1]).get_id()


def tearDownModule():
    common.removeUser(True, config.USER_NAME)

    if not config.GOLDEN_ENV:
        clusters.removeCluster(True, config.CLUSTER_NAME[1])
        clean_datacenter(True, config.DC_NAME_B)


def loginAsUser(**kwargs):
    users.loginAsUser(
        config.USER_NAME, config.PROFILE, config.USER_PASSWORD, filter=True
    )


def loginAsAdmin():
    users.loginAsUser(
        config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
        config.VDC_PASSWORD, filter=False
    )


@attr(tier=1, extra_reqs={'datacenters_count': 2})
class VmUserInfoTests(TestCase):
    """ Test if user can see correct events """
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.CLUSTER_NAME_B,
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True, vm=config.VM_NAME2, name=config.TEMPLATE_NAME2,
            cluster=config.CLUSTER_NAME_B
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME1, role.UserRole
        )
        loginAsUser()

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME2)
        vms.removeVm(True, config.VM_NAME1)
        templates.removeTemplate(True, config.TEMPLATE_NAME2)

    @istest
    @polarion("RHEVM3-7642")
    def eventFilter_parentObjectEvents(self):
        """ testEventFilter_parentObjectEvents """
        CHECK_OBJ = {
            'vm': {
                'name': config.VM_NAME2,
                'api': vms.VM_API,
            },
            'cluster': {
                'name': config.CLUSTER_NAME_B,
                'api': clusters.util,
            },
            'data_center': {
                'name': config.DC_NAME_B,
                'api': datacenters.util,
            },
            'template': {
                'name': config.TEMPLATE_NAME2,
                'api': templates.TEMPLATE_API,
            },
            'storage_domain': {
                'name': config.STORAGE_NAME[1],
                'api': storagedomains.util,
            },
        }

        for e in events.util.get(absLink=False):
            if e is None:
                continue

            LOGGER.info(e.get_description())
            for obj_name in [
                'vm', 'storage_domain', 'cluster', 'data_center', 'template'
            ]:
                obj = getattr(e, obj_name)
                if obj:
                    obj_dict = CHECK_OBJ[obj_name]
                    api_obj = obj_dict['api'].find(obj.get_id(), 'id')
                    assert api_obj != obj_dict['name']

            host = e.get_host()
            if host:
                assert host.get_id() != ALT_HOST_ID


@attr(tier=1, extra_reqs={'datacenters_count': 2})
class VmUserInfoTests2(TestCase):
    """ Test if user can see correct objects """
    __test__ = True

    # Accessing to specific id don't working in java/python sdk
    # Cli - RHEVM-1758
    apis = TestCase.apis - set(['java', 'sdk', 'cli'])

    def setUp(self):
        loginAsUser()

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME1, role.UserRole
        )
        mla.addPermissionsForTemplate(
            True, config.USER_NAME, 'Blank', role=role.TemplateOwner
        )

        self.id1 = vms.VM_API.find(config.VM_NAME1).get_id()
        self.id2 = vms.VM_API.find(config.VM_NAME2).get_id()

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        vms.removeVm(True, config.VM_NAME2)

    @istest
    @polarion("RHEVM3-7640")
    def filter_parentObjects(self):
        """ filter_parentObjects """
        # TODO: Extend with /templates, /storagedomains, /users, ...
        # Consulted what should be visible to users
        DC = config.DC_NAME[0]
        CLUSTER = config.CLUSTER_NAME[0]

        msgBlind = "User cannot see %s '%s' where he has permission."
        msgVisible = "User can see %s where he has no permissions. Can see %s"

        dcs = datacenters.util.get(absLink=False)
        cls = clusters.util.get(absLink=False)

        # can user see parent objects of the one with permission?
        dc = datacenters.util.find(DC)
        assert dc is not None, msgBlind % ('datacenter', DC)
        cluster = clusters.util.find(CLUSTER)
        assert cluster is not None, msgBlind % ('cluster', CLUSTER)
        LOGGER.info("User can see object where he has permissions.")

        # is user forbidden to see other objects?
        self.assertRaises(
            EntityNotFound, datacenters.util.find, config.DC_NAME_B
        )
        self.assertRaises(
            EntityNotFound, clusters.util.find, config.CLUSTER_NAME[1]
        )
        LOGGER.info("User can't see object where he has permissions.")

        assert len(dcs) == 1, msgVisible % ('datacenters', dcs)
        assert len(cls) == 1, msgVisible % ('clusters', cls)

    @istest
    @polarion("RHEVM3-7639")
    def filter_vms(self):
        """ testFilter_vms """
        msgBlind = "The user can't see VM '%s' where he has permissions"
        msgVisible = "The user can see a VM he has no permissions for"
        msg_info = "After deleting permissions from VM he can't see it anymore"

        vm1 = vms.VM_API.find(config.VM_NAME1)
        self.assertTrue(vm1 is not None, msgBlind % config.VM_NAME1)
        self.assertRaises(EntityNotFound, vms.VM_API.find, config.VM_NAME2)
        myvms = vms.VM_API.get(absLink=False)
        self.assertEqual(len(myvms), 1, msgVisible)
        LOGGER.info(msgVisible)

        loginAsAdmin()
        mla.removeUserPermissionsFromVm(True, config.VM_NAME1, config.USER1)

        loginAsUser()
        self.assertRaises(EntityNotFound, vms.VM_API.find, config.VM_NAME1)
        LOGGER.info(msg_info)

        loginAsAdmin()
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME1, role.UserRole
        )

    @istest
    @polarion("RHEVM3-7641")
    def eventFilter_vmEvents(self):
        """ testEventFilter_vmEvents """
        msgBlind = "User cannot see VM events where he has permissions"
        msgVissible = "User can see VM events where he's no permissions. %s"

        loginAsAdmin()
        vms.startVm(True, config.VM_NAME1)
        vms.startVm(True, config.VM_NAME2)
        vms.stopVm(True, config.VM_NAME1)
        vms.stopVm(True, config.VM_NAME2)
        LOGGER.info("Events on VMs generated")

        loginAsUser()
        lst_of_vms = set()
        for e in events.util.get(absLink=False):
            if e.get_vm():
                lst_of_vms.add(e.get_vm().get_id())

        assert self.id1 in lst_of_vms, msgBlind
        LOGGER.info(msgVissible % lst_of_vms)

        assert self.id2 in lst_of_vms, msgVissible % lst_of_vms
        LOGGER.info(msgBlind)

    @istest
    @polarion("RHEVM3-7643")
    def specificId(self):
        """ testSpecificId """
        msgBlind = "User cannot see VM where he has permmissions"
        msgVissible = "User can see VM where he's no permission. Can See '%s'"
        vms_api = '/api/vms/%s'

        assert vms.VM_API.get(href=vms_api % self.id1) is not None, msgBlind
        LOGGER.info(msgVissible)

        assert vms.VM_API.get(href=vms_api % self.id2) is None, msgVissible
        LOGGER.info(msgBlind)

    @istest
    @polarion("RHEVM3-7644")
    def accessDenied(self):
        """ testAccessDenied """
        msg = "User can see %s where he has no permissions. Can see %s"

        sds = [s.get_name() for s in storagedomains.util.get(absLink=False)]
        tms = [t.get_name() for t in templates.TEMPLATE_API.get(absLink=False)]
        nets = [n.get_name() for n in networks.NET_API.get(absLink=False)]

        # User should see network, cause every user have NetworkUser perms
        assert len(nets) == 3, msg % ('networks', nets)
        # User should see SD, which is attach to sd, in which is his VM
        assert len(sds) == 1, msg % ('storages', sds)
        # User should se Blank template
        assert len(tms) == 1, msg % ('templates', tms)
        LOGGER.info("User see and don't see resources he can/can't.")

    @istest
    @polarion("RHEVM3-7645")
    def hostInfo(self):
        """ testHostPowerManagementInfo """
        self.assertRaises(
            EntityNotFound, hosts.HOST_API.find, config.HOSTS[0]
        )
        LOGGER.info("User can't see any host info")
        vms.startVm(True, config.VM_NAME1)
        vm = vms.VM_API.find(config.VM_NAME1)
        assert vm.get_host() is None
        LOGGER.info("User can't see any host info in /api/vms")
        assert vm.get_placement_policy() is None
        LOGGER.info("User can't see any placement_policy info in /api/vms")
        vms.stopVm(True, config.VM_NAME1)


@attr(tier=1)
class ViewviewChildrenInfoTests(TestCase):
    """
    Tests if roles that are not able to view childrens,
    really dont view it.
    """
    __test__ = True

    # Could change in the future, probably no way how to get it from API.
    # So should be changed if behaviour will change.
    roles_cant = [
        role.PowerUserRole,
        role.TemplateCreator,
        role.VmCreator,
        role.DiskCreator,
    ]
    roles_can = [
        role.UserRole,
        role.UserVmManager,
        role.DiskOperator,
        role.TemplateOwner,
    ]

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)

    @istest
    @polarion("RHEVM3-7638")
    def canViewChildren(self):
        """ CanViewChildren """
        err_msg = "User can't see vms"
        for role_can in self.roles_can:
            LOGGER.info("Testing role: %s", role_can)
            mla.addClusterPermissionsToUser(
                True, config.USER_NAME, config.CLUSTER_NAME[0], role_can
            )
            loginAsUser()
            assert len(vms.VM_API.get(absLink=False)) > 0, err_msg
            loginAsAdmin()
            mla.removeUserPermissionsFromCluster(
                True, config.CLUSTER_NAME[0], config.USER1
            )
            LOGGER.info("%s can see children", role_can)

    @istest
    @polarion("RHEVM3-7637")
    def cantViewChildren(self):
        """ CantViewChildren """
        for role_can in self.roles_cant:
            LOGGER.info("Testing role: %s", role_can)
            mla.addClusterPermissionsToUser(
                True, config.USER_NAME, config.CLUSTER_NAME[0], role_can
            )
            loginAsUser()
            assert len(vms.VM_API.get(absLink=False)) == 0, "User can see vms"
            loginAsAdmin()
            mla.removeUserPermissionsFromCluster(
                True, config.CLUSTER_NAME[0], config.USER1
            )
            LOGGER.info("%s can see children", role_can)


@attr(tier=1)
class VmCreatorClusterAdminInfoTests(TestCase):
    """ Test for VMcreator and cluster admin role """
    __test__ = True

    @classmethod
    def setUpClass(self):
        mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.CLUSTER_NAME[0], role.UserRole
        )
        mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.CLUSTER_NAME[0], role.VmCreator
        )
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            True, config.VM_NAME3, '', cluster=config.CLUSTER_NAME[1],
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            True, config.VM_NAME4, '', cluster=config.CLUSTER_NAME[1],
            network=config.MGMT_BRIDGE
        )

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        vms.removeVm(True, config.VM_NAME2)
        vms.removeVm(True, config.VM_NAME3)
        vms.removeVm(True, config.VM_NAME4)
        mla.removeUserPermissionsFromCluster(
            True, config.CLUSTER_NAME[0], config.USER1
        )

    @istest
    @polarion("RHEVM3-7647")
    def vmCreatorClusterAdmin_filter_vms(self):
        """ vmCreatorClusterAdmin_filter_vms """
        err_msg_can = "User can see %s"
        err_msg_cant = "User can't see %s"
        loginAsUser()
        LOGGER.info("Checking right permission on vms.")
        myvms = [vm.get_name() for vm in vms.VM_API.get(absLink=False)]
        assert config.VM_NAME1 in myvms, err_msg_cant % config.VM_NAME1
        assert config.VM_NAME2 in myvms, err_msg_cant % config.VM_NAME2
        assert config.VM_NAME3 not in myvms, err_msg_can % config.VM_NAME3
        assert config.VM_NAME4 not in myvms, err_msg_can % config.VM_NAME4


@attr(tier=1)
class VmCreatorInfoTests(TestCase):
    """ Test for VMcreator role """
    __test__ = True

    @classmethod
    def setUpClass(self):
        mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.CLUSTER_NAME[0], role.VmCreator
        )
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        vms.removeVm(True, config.VM_NAME2)
        mla.removeUserPermissionsFromCluster(
            True, config.CLUSTER_NAME[0], config.USER1
        )

    @istest
    @polarion("RHEVM3-7646")
    def vmCreator_filter_vms(self):
        """ vmCreator_filter_vms """
        msg = "User can see vms where he has no permissions. Can see %s"

        loginAsUser()
        myvms = [vm.get_name() for vm in vms.VM_API.get(absLink=False)]
        assert len(myvms) == 0, msg % myvms
        LOGGER.info("User can't see vms where he has not perms. %s" % myvms)

        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        myvms = [vm.get_name() for vm in vms.VM_API.get(absLink=False)]
        assert len(myvms) == 1, msg % myvms
        LOGGER.info("User can see only his vms %s" % myvms)


@attr(tier=1)
class TemplateCreatorInfoTests(TestCase):
    """ Test combination of roles with TemplateCreator role """
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], role.TemplateCreator
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME1, role.UserRole
        )
        templates.createTemplate(
            True, vm=config.VM_NAME2, name=config.TEMPLATE_NAME,
            cluster=config.CLUSTER_NAME[0]
        )
        templates.createTemplate(
            True, vm=config.VM_NAME1, name=config.TEMPLATE_NAME2,
            cluster=config.CLUSTER_NAME[0]
        )

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        vms.removeVm(True, config.VM_NAME2)
        templates.removeTemplate(True, config.TEMPLATE_NAME)
        templates.removeTemplate(True, config.TEMPLATE_NAME2)
        templates.removeTemplate(True, config.TEMPLATE_NAME3)
        mla.removeUserPermissionsFromDatacenter(
            True, config.DC_NAME[0], config.USER1
        )

    @istest
    @polarion("RHEVM3-7648")
    def templateCreator_filter_templatesAndVms(self):
        """ Template creator with user role filter template and vms """
        msgCant = "User can't see %s '%s' which should see"
        msgCan = "User can see %s '%s' which shouldn't see"

        loginAsUser()
        LOGGER.info("Checking right permissions for all vms")

        myvms = [vm.get_name() for vm in vms.VM_API.get(absLink=False)]
        assert config.VM_NAME1 in myvms, msgCant % ('VM', config.VM_NAME1)
        assert config.VM_NAME2 not in myvms, msgCan % ('VM', config.VM_NAME2)
        LOGGER.info("User can see %s" % myvms)

        LOGGER.info("Checking right permissions for all templates")
        tms = [t.get_name() for t in templates.TEMPLATE_API.get(absLink=False)]
        err_msg = msgCan % ('Template', config.TEMPLATE_NAME)
        assert config.TEMPLATE_NAME not in tms, err_msg
        err_msg = msgCan % ('Template', config.TEMPLATE_NAME2)
        assert config.TEMPLATE_NAME2 not in tms, err_msg
        LOGGER.info("User can see %s" % tms)

        templates.createTemplate(
            True, vm=config.VM_NAME1, name=config.TEMPLATE_NAME3,
            cluster=config.CLUSTER_NAME[0]
        )
        LOGGER.info("Checking right permission for %s" % config.TEMPLATE_NAME3)
        tms = [t.get_name() for t in templates.TEMPLATE_API.get(absLink=False)]
        # tms == 2(blank + newly created)
        err_msg = msgCan % ('Templates', tms)
        assert config.TEMPLATE_NAME3 in tms and len(tms) == 2, err_msg
        LOGGER.info("User can see %s" % tms)


# Create some templates in Datacenter1.
# Create user and give him both roles TemplateCreator and DataCenterAdmin for
# Datacenter1
# Create some templates in Datacenter2.
# - Check /api/templates
# Should see all templates in Datacenter1, but none in Datacenter2.
@attr(tier=1, extra_reqs={'datacenters_count': 2})
class TemplateCreatorAndDCAdminInfoTest(TestCase):
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True, vm=config.VM_NAME1, name=config.TEMPLATE_NAME,
            cluster=config.CLUSTER_NAME[0]
        )
        mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], role.TemplateCreator
        )
        mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], role.TemplateOwner
        )
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.CLUSTER_NAME_B,
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True, vm=config.VM_NAME2, name=config.TEMPLATE_NAME2,
            cluster=config.CLUSTER_NAME_B
        )

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME2)
        vms.removeVm(True, config.VM_NAME1)
        templates.removeTemplate(True, config.TEMPLATE_NAME)
        templates.removeTemplate(True, config.TEMPLATE_NAME2)
        mla.removeUserPermissionsFromDatacenter(
            True, config.DC_NAME[0], config.USER1
        )

    @istest
    @polarion("RHEVM3-7649")
    def templateCreatorDataCenterAdmin_filter_templates(self):
        """ Template creator with datacenter admin filter templates """
        loginAsUser()
        templates.TEMPLATE_API.find(config.TEMPLATE_NAME)
        self.assertRaises(
            EntityNotFound, templates.TEMPLATE_API.find, config.TEMPLATE_NAME2
        )


@attr(tier=1, extra_reqs={'datacenters_count': 2})
class ComplexCombinationTest(TestCase):
    """ Test that user can see correct object regargin its permissions """
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True, vm=config.VM_NAME1, name=config.TEMPLATE_NAME,
            cluster=config.CLUSTER_NAME[0]
        )
        templates.createTemplate(
            True, vm=config.VM_NAME2, name=config.TEMPLATE_NAME2,
            cluster=config.CLUSTER_NAME[0]
        )
        vms.createVm(
            True, config.VM_NAME3, '', cluster=config.CLUSTER_NAME_B,
            storageDomainName=config.STORAGE_NAME[1], size=config.GB,
            network=config.MGMT_BRIDGE
        )
        vms.createVm(
            True, config.VM_NAME4, '', cluster=config.CLUSTER_NAME[1],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        templates.createTemplate(
            True, vm=config.VM_NAME3, name=config.TEMPLATE_NAME3,
            cluster=config.CLUSTER_NAME_B
        )
        templates.createTemplate(
            True, vm=config.VM_NAME4, name=config.TEMPLATE_NAME4,
            cluster=config.CLUSTER_NAME[1]
        )
        mla.addVMPermissionsToUser(
            True, config.USER_NAME, config.VM_NAME1, role.UserRole
        )
        mla.addPermissionsForTemplate(
            True, config.USER_NAME, config.TEMPLATE_NAME2
        )
        mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.CLUSTER_NAME_B, role.VmCreator
        )
        mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME_B, role.TemplateCreator
        )
        mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.CLUSTER_NAME[1], role.ClusterAdmin
        )

    # Check BZ 881109 - behaviour could be changed in future.
    @istest
    @polarion("RHEVM3-7650")
    def complexCombination1_filter_templatesAndVms(self):
        """ ComplexCombination filter templatesAndVms """
        # TODO: extend, there could be tested more than this
        loginAsUser()
        vms.VM_API.find(config.VM_NAME1)
        self.assertRaises(EntityNotFound, vms.VM_API.find, config.VM_NAME2)
        self.assertRaises(EntityNotFound, vms.VM_API.find, config.VM_NAME3)
        self.assertRaises(EntityNotFound, vms.VM_API.find, config.VM_NAME4)
        LOGGER.info("User can see %s" % config.VM_NAME1)
        LOGGER.info(
            "User can't see %s, %s, %s" % (
                config.VM_NAME1, config.VM_NAME2, config.VM_NAME3
            )
        )

        self.assertRaises(
            EntityNotFound, templates.TEMPLATE_API.find, config.TEMPLATE_NAME
        )
        self.assertRaises(
            EntityNotFound, templates.TEMPLATE_API.find, config.TEMPLATE_NAME2
        )
        self.assertRaises(
            EntityNotFound, templates.TEMPLATE_API.find, config.TEMPLATE_NAME3
        )
        self.assertRaises(
            EntityNotFound, templates.TEMPLATE_API.find, config.TEMPLATE_NAME4
        )
        LOGGER.info(
            "User can't see %s, %s, %s, %s" % (
                config.TEMPLATE_NAME, config.TEMPLATE_NAME2,
                config.TEMPLATE_NAME3, config.TEMPLATE_NAME4
            )
        )

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        vms.removeVm(True, config.VM_NAME2)
        vms.removeVm(True, config.VM_NAME3)
        vms.removeVm(True, config.VM_NAME4)
        templates.removeTemplate(True, config.TEMPLATE_NAME)
        templates.removeTemplate(True, config.TEMPLATE_NAME2)
        templates.removeTemplate(True, config.TEMPLATE_NAME3)
        templates.removeTemplate(True, config.TEMPLATE_NAME4)
        common.removeUser(True, config.USER_NAME)
        common.addUser(
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
        )
