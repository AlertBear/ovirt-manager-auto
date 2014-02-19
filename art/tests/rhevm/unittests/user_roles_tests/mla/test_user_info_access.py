'''
Testing if user can access only his objects.
1 Host, 1 DC, 1 Cluster, 1 SD will be created.
Tests if user can access object which he has permissions for and not see,
if he has not permissions.
'''

__test__ = True

from user_roles_tests import config
from user_roles_tests.roles import role
from nose.tools import istest
import logging
from art.test_handler.tools import bz, tcms
from art.rhevm_api.tests_lib.low_level import \
    users, vms, templates, mla, clusters, datacenters, hosts,\
    storagedomains, networks, events
from art.rhevm_api.tests_lib.high_level import storagedomains as \
    h_storagedomains
from unittest import TestCase

from art.core_api.apis_exceptions import EntityNotFound

TCMS_PLAN_ID = 6283
LOGGER = logging.getLogger(__name__)
ALT_HOST_ID = None


def setUpModule():
    users.addUser(True, user_name=config.USER_NAME, domain=config.USER_DOMAIN)
    clusters.addCluster(
        True, name=config.ALT_CLUSTER_NAME,
        cpu=config.PARAMETERS.get('cpu_name'),
        data_center=config.MAIN_DC_NAME,
        version=config.PARAMETERS.get('compatibility_version'))

    datacenters.addDataCenter(
        True, name=config.DC_NAME_B, storage_type=config.MAIN_STORAGE_TYPE,
        version=config.PARAMETERS.get('compatibility_version'))
    clusters.addCluster(
        True, name=config.CLUSTER_NAME_B,
        cpu=config.PARAMETERS.get('cpu_name'), data_center=config.DC_NAME_B,
        version=config.PARAMETERS.get('compatibility_version'))
    hosts.addHost(
        True, config.ALT1_HOST_ADDRESS,
        root_password=config.ALT1_HOST_ROOT_PASSWORD,
        address=config.ALT1_HOST_ADDRESS, cluster=config.CLUSTER_NAME_B)
    h_storagedomains.addNFSDomain(
        config.ALT1_HOST_ADDRESS, config.ALT1_STORAGE_NAME,
        config.DC_NAME_B, config.ALT1_STORAGE_ADDRESS,
        config.ALT1_STORAGE_PATH)
    global ALT_HOST_ID
    ALT_HOST_ID = hosts.HOST_API.find(config.ALT1_HOST_ADDRESS).get_id()


def tearDownModule():
    users.removeUser(True, config.USER_NAME)
    clusters.removeCluster(True, config.ALT_CLUSTER_NAME)
    storagedomains.cleanDataCenter(True, config.DC_NAME_B)


def loginAsUser(**kwargs):
    users.loginAsUser(
        config.USER_NAME, config.USER_DOMAIN, config.USER_PASSWORD,
        filter=True)


def loginAsAdmin():
    users.loginAsUser(
        config.OVIRT_USERNAME, config.OVIRT_DOMAIN,
        config.OVIRT_PASSWORD, filter=False)


class VmUserInfoTests(TestCase):
    """ Test if user can see correct events """
    __test__ = True

    vms_api = '/api/vms/%s'
    sd_api = '/api/storagedomains/%s'
    cl_api = '/api/clusters/%s'
    dc_api = '/api/datacenters/%s'
    host_api = '/api/hosts/%s'
    tmp_api = '/api/templates/%s'

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME,
            storageDomainName=config.MAIN_STORAGE_NAME, size=config.GB,
            network=config.MGMT_BRIDGE)
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.CLUSTER_NAME_B,
            network=config.MGMT_BRIDGE)
        templates.createTemplate(
            True, vm=config.VM_NAME2, name=config.TEMPLATE_NAME2,
            cluster=config.CLUSTER_NAME_B)
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME1,
                                   role.UserRole)
        loginAsUser()

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME2)
        vms.removeVm(True, config.VM_NAME1)
        templates.removeTemplate(True, config.TEMPLATE_NAME2)

    @istest
    @tcms(TCMS_PLAN_ID, 171856)
    def eventFilter_parentObjectEvents(self):
        """ testEventFilter_parentObjectEvents """
        for e in events.util.get(absLink=False):
            if e is None:
                continue
            LOGGER.info(e.get_description())
            vm = e.get_vm()
            sd = e.get_storage_domain()
            cl = e.get_cluster()
            dc = e.get_data_center()
            host = e.get_host()
            tmp = e.get_template()
            if vm:
                vm_obj = vms.VM_API.get(href=self.vms_api % vm.get_id())
                assert vm_obj.get_name() != config.VM_NAME2
            if sd:
                sd_href = self.sd_api % sd.get_id()
                sd_obj = storagedomains.util.get(href=sd_href)
                assert sd_obj.get_name() != config.ALT1_STORAGE_NAME
            if cl:
                cl_obj = clusters.util.get(self.cl_api % cl.get_id())
                assert cl_obj.get_name() != config.CLUSTER_NAME_B
            if dc:
                dc_obj = datacenters.util.get(self.dc_api % dc.get_id())
                assert dc_obj.get_name() != config.DC_NAME_B
            if tmp:
                tmp_href = self.tmp_api % tmp.get_id()
                tmp_obj = templates.TEMPLATE_API.get(href=tmp_href)
                assert tmp_obj.get_name() != config.TEMPLATE_NAME2
            if host:
                assert host.get_id() != ALT_HOST_ID


class VmUserInfoTests2(TestCase):
    """ Test if user can see correct objects """
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME,
            storageDomainName=config.MAIN_STORAGE_NAME, size=config.GB,
            network=config.MGMT_BRIDGE)
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.MAIN_CLUSTER_NAME,
            storageDomainName=config.MAIN_STORAGE_NAME, size=config.GB,
            network=config.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME1,
                                   role.UserRole)

        self.id1 = vms.VM_API.find(config.VM_NAME1).get_id()
        self.id2 = vms.VM_API.find(config.VM_NAME2).get_id()

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        vms.removeVm(True, config.VM_NAME2)

    def setUp(self):
        loginAsUser()

    @istest
    @tcms(TCMS_PLAN_ID, 171878)
    def filter_parentObjects(self):
        """ filter_parentObjects """
        # TODO: Extend with /templates, /storagedomains, /users, ...
        # Consulted what should be visible to users
        DC = config.MAIN_DC_NAME
        CLUSTER = config.MAIN_CLUSTER_NAME

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
        self.assertRaises(EntityNotFound, datacenters.util.find,
                          config.DC_NAME_B)
        self.assertRaises(EntityNotFound, clusters.util.find,
                          config.ALT_CLUSTER_NAME)
        LOGGER.info("User can't see object where he has permissions.")

        assert len(dcs) == 1, \
            msgVisible % ('datacenters', dcs)
        assert len(cls) == 1, msgVisible % ('clusters', cls)

    @istest
    @tcms(TCMS_PLAN_ID, 171076)
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
        myvms = vms.VM_API.get(absLink=False)
        self.assertRaises(EntityNotFound, vms.VM_API.find, config.VM_NAME1)
        self.assertEqual(myvms, None, msgVisible)
        LOGGER.info(msg_info)

        loginAsAdmin()
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME1,
                                   role.UserRole)

    @istest
    @bz(968961)
    @tcms(TCMS_PLAN_ID, 171077)
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

        assert self.id2 not in lst_of_vms, msgVissible % lst_of_vms
        LOGGER.info(msgBlind)

    @istest
    @tcms(TCMS_PLAN_ID, 171079)
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
    @tcms(TCMS_PLAN_ID, 168714)
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
    @tcms(TCMS_PLAN_ID, 175445)
    def hostInfo(self):
        """ testHostPowerManagementInfo """
        self.assertRaises(EntityNotFound, hosts.HOST_API.find,
                          config.MAIN_HOST_NAME)
        LOGGER.info("User can't see any host info")
        vms.startVm(True, config.VM_NAME1)
        vm = vms.VM_API.find(config.VM_NAME1)
        assert vm.get_host() is None
        LOGGER.info("User can't see any host info in /api/vms")
        assert vm.get_placement_policy() is None
        LOGGER.info("User can't see any placement_policy info in /api/vms")
        vms.stopVm(True, config.VM_NAME1)


class ViewviewChildrenInfoTests(TestCase):
    """
    Tests if roles that are not able to view childrens,
    really dont view it.
    """
    __test__ = True

    # Could change in the future, probably no way how to get it from API.
    # So should be changed if behaviour will change.
    roles_cant = [role.PowerUserRole,
                  role.TemplateCreator,
                  role.VmCreator,
                  role.DiskCreator]
    roles_can = [role.UserRole,
                 role.UserVmManager,
                 role.DiskOperator,
                 role.TemplateOwner]

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)

    @istest
    @tcms(TCMS_PLAN_ID, 230017)
    def canViewChildren(self):
        """ CanViewChildren """
        err_msg = "User can't see vms"
        for role in self.roles_can:
            LOGGER.info("Testing role: %s", role)
            mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                            config.MAIN_CLUSTER_NAME,
                                            role)
            loginAsUser()
            assert len(vms.VM_API.get(absLink=False)) == 1, err_msg
            loginAsAdmin()
            mla.removeUserPermissionsFromCluster(
                True, config.MAIN_CLUSTER_NAME, config.USER1)
            LOGGER.info("%s can see children", role)

    @istest
    @tcms(TCMS_PLAN_ID, 230018)
    def cantViewChildren(self):
        """ CantViewChildren """
        for role in self.roles_cant:
            LOGGER.info("Testing role: %s", role)
            mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                            config.MAIN_CLUSTER_NAME,
                                            role)
            loginAsUser()
            assert len(vms.VM_API.get(absLink=False)) == 0, "User can see vms"
            loginAsAdmin()
            mla.removeUserPermissionsFromCluster(
                True, config.MAIN_CLUSTER_NAME, config.USER1)
            LOGGER.info("%s can see children", role)


class VmCreatorClusterAdminInfoTests(TestCase):
    """ Test for VMcreator and cluster admin role """
    __test__ = True

    @classmethod
    def setUpClass(self):
        mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                        config.MAIN_CLUSTER_NAME,
                                        role.UserRole)
        mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                        config.MAIN_CLUSTER_NAME,
                                        role.VmCreator)
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.MAIN_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)
        vms.createVm(
            True, config.VM_NAME3, '', cluster=config.ALT_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)
        vms.createVm(
            True, config.VM_NAME4, '', cluster=config.ALT_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        vms.removeVm(True, config.VM_NAME2)
        vms.removeVm(True, config.VM_NAME3)
        vms.removeVm(True, config.VM_NAME4)
        mla.removeUserPermissionsFromCluster(True, config.MAIN_CLUSTER_NAME,
                                             config.USER1)

    @istest
    @tcms(TCMS_PLAN_ID, 174404)
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


class VmCreatorInfoTests(TestCase):
    """ Test for VMcreator role """
    __test__ = True

    @classmethod
    def setUpClass(self):
        mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                        config.MAIN_CLUSTER_NAME,
                                        role.VmCreator)
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        vms.removeVm(True, config.VM_NAME2)
        mla.removeUserPermissionsFromCluster(True, config.MAIN_CLUSTER_NAME,
                                             config.USER1)

    @istest
    @tcms(TCMS_PLAN_ID, 171080)
    def vmCreator_filter_vms(self):
        """ vmCreator_filter_vms """
        msg = "User can see vms where he has no permissions. Can see %s"

        loginAsUser()
        myvms = [vm.get_name() for vm in vms.VM_API.get(absLink=False)]
        assert len(myvms) == 0, msg % myvms
        LOGGER.info("User can't see vms where he has not perms. %s" % myvms)

        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.MAIN_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)
        myvms = [vm.get_name() for vm in vms.VM_API.get(absLink=False)]
        assert len(myvms) == 1, msg % myvms
        LOGGER.info("User can see only his vms %s" % myvms)


class TemplateCreatorInfoTests(TestCase):
    """ Test combination of roles with TemplateCreator role """
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.MAIN_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)
        mla.addPermissionsForDataCenter(True, config.USER_NAME,
                                        config.MAIN_DC_NAME,
                                        role.TemplateCreator)
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME1,
                                   role.UserRole)
        templates.createTemplate(
            True, vm=config.VM_NAME2, name=config.TEMPLATE_NAME,
            cluster=config.MAIN_CLUSTER_NAME)
        templates.createTemplate(
            True, vm=config.VM_NAME1, name=config.TEMPLATE_NAME2,
            cluster=config.MAIN_CLUSTER_NAME)

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME1)
        vms.removeVm(True, config.VM_NAME2)
        templates.removeTemplate(True, config.TEMPLATE_NAME)
        templates.removeTemplate(True, config.TEMPLATE_NAME2)
        templates.removeTemplate(True, config.TEMPLATE_NAME3)
        mla.removeUserPermissionsFromDatacenter(
            True, config.MAIN_DC_NAME, config.USER1)

    @istest
    @tcms(TCMS_PLAN_ID, 174403)
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
            cluster=config.MAIN_CLUSTER_NAME)
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
class TemplateCreatorAndDCAdminInfoTest(TestCase):
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME,
            network=config.MGMT_BRIDGE)
        templates.createTemplate(
            True, vm=config.VM_NAME1, name=config.TEMPLATE_NAME,
            cluster=config.MAIN_CLUSTER_NAME)
        mla.addPermissionsForDataCenter(True, config.USER_NAME,
                                        config.MAIN_DC_NAME,
                                        role.TemplateCreator)
        mla.addPermissionsForDataCenter(True, config.USER_NAME,
                                        config.MAIN_DC_NAME,
                                        role.TemplateOwner)
        vms.createVm(True, config.VM_NAME2, '', cluster=config.CLUSTER_NAME_B,
                     network=config.MGMT_BRIDGE)
        templates.createTemplate(
            True, vm=config.VM_NAME2, name=config.TEMPLATE_NAME2,
            cluster=config.CLUSTER_NAME_B)

    @classmethod
    def tearDownClass(self):
        loginAsAdmin()
        vms.removeVm(True, config.VM_NAME2)
        vms.removeVm(True, config.VM_NAME1)
        templates.removeTemplate(True, config.TEMPLATE_NAME)
        templates.removeTemplate(True, config.TEMPLATE_NAME2)
        mla.removeUserPermissionsFromDatacenter(
            True, config.MAIN_DC_NAME, config.USER1)

    @istest
    @tcms(TCMS_PLAN_ID, 174405)
    def templateCreatorDataCenterAdmin_filter_templates(self):
        """ Template creator with datacenter admin filter templates """
        loginAsUser()
        templates.TEMPLATE_API.find(config.TEMPLATE_NAME)
        self.assertRaises(EntityNotFound, templates.TEMPLATE_API.find,
                          config.TEMPLATE_NAME2)


class ComplexCombinationTest(TestCase):
    """ Test that user can see correct object regargin its permissions """
    __test__ = True

    @classmethod
    def setUpClass(self):
        vms.createVm(
            True, config.VM_NAME1, '', cluster=config.MAIN_CLUSTER_NAME,
            storageDomainName=config.MAIN_STORAGE_NAME, size=config.GB,
            network=config.MGMT_BRIDGE)
        vms.createVm(
            True, config.VM_NAME2, '', cluster=config.MAIN_CLUSTER_NAME,
            storageDomainName=config.MAIN_STORAGE_NAME, size=config.GB,
            network=config.MGMT_BRIDGE)
        templates.createTemplate(
            True, vm=config.VM_NAME1, name=config.TEMPLATE_NAME,
            cluster=config.MAIN_CLUSTER_NAME)
        templates.createTemplate(
            True, vm=config.VM_NAME2, name=config.TEMPLATE_NAME2,
            cluster=config.MAIN_CLUSTER_NAME)
        vms.createVm(
            True, config.VM_NAME3, '', cluster=config.CLUSTER_NAME_B,
            storageDomainName=config.ALT1_STORAGE_NAME, size=config.GB,
            network=config.MGMT_BRIDGE)
        vms.createVm(
            True, config.VM_NAME4, '', cluster=config.ALT_CLUSTER_NAME,
            storageDomainName=config.MAIN_STORAGE_NAME, size=config.GB,
            network=config.MGMT_BRIDGE)
        templates.createTemplate(
            True, vm=config.VM_NAME3, name=config.TEMPLATE_NAME3,
            cluster=config.CLUSTER_NAME_B)
        templates.createTemplate(
            True, vm=config.VM_NAME4, name=config.TEMPLATE_NAME4,
            cluster=config.ALT_CLUSTER_NAME)

        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME1,
                                   role.UserRole)
        mla.addPermissionsForTemplate(True, config.USER_NAME,
                                      config.TEMPLATE_NAME2)
        mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                        config.CLUSTER_NAME_B, role.VmCreator)
        mla.addPermissionsForDataCenter(True, config.USER_NAME,
                                        config.DC_NAME_B, role.TemplateCreator)
        mla.addClusterPermissionsToUser(True, config.USER_NAME,
                                        config.ALT_CLUSTER_NAME,
                                        role.ClusterAdmin)

    # Check BZ 881109 - behaviour could be changed in future.
    @istest
    @tcms(TCMS_PLAN_ID, 174406)
    def complexCombination1_filter_templatesAndVms(self):
        """ ComplexCombination filter templatesAndVms """
        # TODO: extend, there could be tested more than this
        loginAsUser()
        vms.VM_API.find(config.VM_NAME1)
        self.assertRaises(EntityNotFound, vms.VM_API.find, config.VM_NAME2)
        self.assertRaises(EntityNotFound, vms.VM_API.find, config.VM_NAME3)
        self.assertRaises(EntityNotFound, vms.VM_API.find, config.VM_NAME4)
        LOGGER.info("User can see %s" % config.VM_NAME1)
        LOGGER.info("User can't see %s, %s, %s" % (config.VM_NAME1,
                    config.VM_NAME2, config.VM_NAME3))

        self.assertRaises(EntityNotFound, templates.TEMPLATE_API.find,
                          config.TEMPLATE_NAME)
        self.assertRaises(EntityNotFound, templates.TEMPLATE_API.find,
                          config.TEMPLATE_NAME2)
        self.assertRaises(EntityNotFound, templates.TEMPLATE_API.find,
                          config.TEMPLATE_NAME3)
        self.assertRaises(EntityNotFound, templates.TEMPLATE_API.find,
                          config.TEMPLATE_NAME4)
        LOGGER.info("User can't see %s, %s, %s, %s" % (config.TEMPLATE_NAME,
                    config.TEMPLATE_NAME2, config.TEMPLATE_NAME3,
                    config.TEMPLATE_NAME4))

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
        users.removeUser(True, config.USER_NAME)
        users.addUser(True, user_name=config.USER_NAME,
                      domain=config.USER_DOMAIN)
