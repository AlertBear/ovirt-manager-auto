'''
Testing network permissions feature. Possitive cases.
1 Host, 1 SD, 1 DC, 1 cluster will be created for test.
It will cover scenarios for creating/deleting/viewing networks and vnicprofiles
if user is permittied for it.
'''

__test__ = True

import logging
from rhevmtests.system.user_roles_tests import config, common
from rhevmtests.system.user_roles_tests.roles import role
from nose.tools import istest
from art.unittest_lib import attr
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.core_api.apis_exceptions import EntityNotFound
from test_network_permissions_negative import (
    ignoreAllExceptions, loginAsUser, loginAsAdmin, NetworkingNegative
)
from art.rhevm_api.tests_lib.low_level import (
    mla, networks, users, vms, templates, datacenters
)


LOGGER = logging.getLogger(__name__)
VM_NAME = config.VM_NAME
TEMPLATE_NAME = config.TEMPLATE_NAME
NIC_NAME = 'nic1'
NIC_NAME2 = 'nic2'
NIC_NAME3 = 'nic3'
NIC_NAME4 = 'nic4'
ROLE_NAME = '_NetworkCreator'
TCMS_PLAN_ID_POS = 10639
EVERYONE = 'Everyone'


def setUpModule():
    global VM_NAME
    global TEMPLATE_NAME
    VM_NAME = config.VM_NAME
    TEMPLATE_NAME = config.TEMPLATE_NAME
    for user in [config.USER_NAME, config.USER_NAME2, config.USER_NAME3]:
        assert common.addUser(True, user_name=user, domain=config.USER_DOMAIN)


def tearDownModule():
    loginAsAdmin()
    for user in [config.USER_NAME, config.USER_NAME2, config.USER_NAME3]:
        assert common.removeUser(True, user)


@attr(tier=1)
class NetworkingPossitive(NetworkingNegative):
    __test__ = False

    def tearDown(self):
        super(NetworkingPossitive, self).tearDown()
        ignoreAllExceptions(mla.removeRole, positive=True, role=ROLE_NAME)


class PositiveNetworkPermissions231821(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], role=role.SuperUser
        )
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME2,
            config.DC_NAME[0], role=role.DataCenterAdmin
        )
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME3,
            config.DC_NAME[0], role=role.NetworkAdmin
        )

    @istest
    @polarion("RHEVM3-8369")
    def createNetworkInDC(self):
        """ CreateNetworkInDc """
        for u in [config.USER_NAME, config.USER_NAME2, config.USER_NAME3]:
            loginAsUser(userName=u, filter_=False)
            assert networks.addNetwork(
                True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
            )
            loginAsAdmin()
            assert networks.removeNetwork(
                True,
                network=config.NETWORK_NAME1,
                data_center=config.DC_NAME[0]
            )


class PositiveNetworkPermissions231822(NetworkingPossitive):
    __test__ = True

    apis = NetworkingPossitive.apis - set(['java'])

    def setUp(self):
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert mla.addPermissionsForNetwork(
            True, config.USER_NAME, config.NETWORK_NAME1,
            data_center=config.DC_NAME[0], role=role.DataCenterAdmin
        )
        assert mla.addPermissionsForNetwork(
            True, config.USER_NAME2, config.NETWORK_NAME1,
            data_center=config.DC_NAME[0], role=role.NetworkAdmin
        )

    @istest
    @polarion("RHEVM3-8384")
    def editNetworkInDC(self):
        """ Edit network in DC """
        mtu = 800
        stp = True
        for uName in [config.USER_NAME, config.USER_NAME2]:
            loginAsUser(userName=uName, filter_=False)
            assert networks.updateNetwork(
                True, config.NETWORK_NAME1,
                data_center=config.DC_NAME[0],
                mtu=mtu, stp=str(stp).lower()
            )
            mtu += 100
            stp = not stp


class PositiveNetworkPermissions231823(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert mla.addPermissionsForNetwork(
            True, config.USER_NAME, config.NETWORK_NAME1,
            data_center=config.DC_NAME[0], role=role.NetworkAdmin
        )
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME2, cluster=config.CLUSTER_NAME[0]
        )

    @istest
    @polarion("RHEVM3-8383")
    def attachingNetworkToCluster(self):
        """ Attaching network to cluster """
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        assert networks.removeNetworkFromCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        loginAsUser(userName=config.USER_NAME2, filter_=False)
        assert networks.addNetworkToCluster(
            False, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        LOGGER.info("ClusterAdmin can't attach network to cluster.")


class TestSwitching(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME, cluster=config.CLUSTER_NAME[0]
        )
        assert mla.addPermissionsForNetwork(
            True, config.USER_NAME2, config.NETWORK_NAME1,
            data_center=config.DC_NAME[0], role=role.NetworkAdmin
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )

    def _inverseParams(self, kwargs):
        ''' inverse required or/and display param if exists '''
        if 'required' in kwargs:
            kwargs['required'] = not kwargs['required']
        if 'display' in kwargs:
            kwargs['display'] = not kwargs['display']
        if 'usages' in kwargs:
            kwargs['usages'] = (
                'vm' if kwargs['usages'] == 'display' else 'display'
            )

    def _test_switching_display_and_required(self, **kwargs):
        assert networks.updateClusterNetwork(
            True, config.CLUSTER_NAME[0], config.NETWORK_NAME1, **kwargs
        )
        for uName in [config.USER_NAME, config.USER_NAME2]:
            loginAsUser(userName=uName, filter_=False)
            self._inverseParams(kwargs)
            assert networks.updateClusterNetwork(
                True, config.CLUSTER_NAME[0], config.NETWORK_NAME1, **kwargs
            )
            self._inverseParams(kwargs)
            assert networks.updateClusterNetwork(
                True, config.CLUSTER_NAME[0], config.NETWORK_NAME1, **kwargs
            )


class PositiveNetworkPermissions231824(TestSwitching):
    __test__ = True

    @istest
    @polarion("RHEVM3-8382")
    def requiredToNonRequiredAndViceVersa(self):
        """ Required to non-required and vice versa """
        self._test_switching_display_and_required(required=True)


class PositiveNetworkPermissions236073(TestSwitching):
    __test__ = True

    @istest
    @polarion("RHEVM3-8377")
    def displayNetwork(self):
        """ Display network """
        self._test_switching_display_and_required(
            display=True, usages='display'
        )


class PositiveNetworkPermissions231826(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            size=config.GB, network=config.MGMT_BRIDGE
        )
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME1, config.NETWORK_NAME1,
            config.DC_NAME[0], role=role.VnicProfileUser
        )

    @istest
    @polarion("RHEVM3-8381")
    def attachDetachNetworkToVM(self):
        """ Attach/Detach a network to VM  """
        loginAsUser(config.USER_NAME)
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME,
            network=config.NETWORK_NAME, interface='virtio'
        )
        assert vms.removeNic(True, VM_NAME, NIC_NAME)


class PositiveNetworkPermissions231827(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        # Not possible to create public vnicprofile, just add Everyone perms
        for net in [config.NETWORK_NAME1, config.NETWORK_NAME2,
                    config.NETWORK_NAME3, config.NETWORK_NAME4]:
            assert networks.addNetwork(
                True, name=net, data_center=config.DC_NAME[0]
            )
            assert mla.addVnicProfilePermissionsToGroup(
                True, EVERYONE, net, net, config.DC_NAME[0]
            )
            assert networks.addNetworkToCluster(
                True, net, config.CLUSTER_NAME[0]
            )

        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME, network=config.NETWORK_NAME1,
            interface='virtio'
        )

    @istest
    @polarion("RHEVM3-8380")
    def visibleNetworksAndManipulations(self):
        """ Visible networks and manipulations """
        loginAsUser(config.USER_NAME)
        for net in [
            config.NETWORK_NAME1,
            config.NETWORK_NAME2,
            config.NETWORK_NAME3,
            config.NETWORK_NAME4
        ]:
            assert vms.addNic(
                True, VM_NAME, name=net, network=net, interface='virtio'
            )
            assert vms.updateNic(True, VM_NAME, net, name='%s-x' % net)
        nets = [n.get_name() for n in networks.NET_API.get(absLink=False)]
        LOGGER.info("User can see networks: '%s'" % nets)
        if not config.GOLDEN_ENV:
            assert len(nets) == 6
        assert vms.removeNic(True, VM_NAME, NIC_NAME)


class PositiveNetworkPermissions231830(NetworkingPossitive):
    __test__ = True

    apis = set(['rest'])

    def setUp(self):
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME2, data_center=config.DC_NAME[0]
        )
        for net in [config.NETWORK_NAME1, config.NETWORK_NAME2]:
            assert networks.addNetworkToCluster(
                True, net, config.CLUSTER_NAME[0]
            )
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME, network=config.NETWORK_NAME1,
            interface='virtio'
        )
        assert templates.createTemplate(
            True, vm=VM_NAME, name=TEMPLATE_NAME,
            cluster=config.CLUSTER_NAME[0]
        )

    def canSee(self, net1, net2, vnic1, vnic2):
        for net in [net1, net2, vnic1, vnic2]:
            if net['filt']:
                self.assertTrue(net['func'](net['name']) is not None)
            else:
                self.assertRaises(EntityNotFound, net['func'], net['name'])

    def filterNet(self, name, filt, func):
        return {'name': name, 'filt': filt, 'func': func}

    def _testWrap(self, p1, p2, p3, p4, filter_=True):
        """ wrap assert """
        net1 = config.NETWORK_NAME1
        net2 = config.NETWORK_NAME2
        loginAsUser(config.USER_NAME, filter_=filter_)
        self.canSee(
            self.filterNet(net1, p1, networks.findNetwork),
            self.filterNet(net2, p2, networks.findNetwork),
            self.filterNet(net1, p3, networks.VNIC_PROFILE_API.find),
            self.filterNet(net2, p4, networks.VNIC_PROFILE_API.find)
        )
        loginAsAdmin()

    def _testPermissionsOnVnicProfile(self):
        mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAME,
            config.NETWORK_NAME1,
            config.NETWORK_NAME1,
            config.DC_NAME[0],
            role=role.VnicProfileUser
        )
        self._testWrap(True, False, True, False)
        mla.removeUserPermissionsFromVnicProfile(
            True,
            config.NETWORK_NAME1,
            config.NETWORK_NAME1,
            config.DC_NAME[0],
            config.USER
        )

    def _testPermissionsOnVM(self):
        mla.addVMPermissionsToUser(True, config.USER_NAME, config.VM_NAME)
        self._testWrap(True, False, True, False)
        mla.removeUserPermissionsFromVm(True, config.VM_NAME, config.USER)

    def _testPermissionsOnTemplate(self):
        mla.addPermissionsForTemplate(
            True, config.USER_NAME, config.TEMPLATE_NAME
        )
        self._testWrap(True, False, True, False)
        mla.removeUserPermissionsFromTemplate(
            True, config.TEMPLATE_NAME, config.USER
        )

    def _testPermissionsOnDC(self):
        mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0]
        )
        self._testWrap(True, True, True, True, False)
        mla.removeUserPermissionsFromDatacenter(
            True, config.DC_NAME[0], config.USER
        )

    def _testPermissionsOnCluster(self):
        mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.CLUSTER_NAME[0]
        )
        self._testWrap(True, True, True, True, False)
        mla.removeUserPermissionsFromCluster(
            True, config.CLUSTER_NAME[0], config.USER
        )

    def _testPermissionsOnSystem(self):
        users.addRoleToUser(True, config.USER_NAME, role.UserRole)
        self._testWrap(True, True, True, True)
        common.removeUser(True, config.USER_NAME)
        common.addUser(
            True, user_name=config.USER_NAME, domain=config.USER_DOMAIN
        )

    def _testPermissionsOnNetwork(self):
        mla.addPermissionsForNetwork(
            True,
            config.USER_NAME,
            config.NETWORK_NAME1,
            config.DC_NAME[0],
            role.VnicProfileUser
        )
        self._testWrap(True, False, True, False)
        mla.removeUserPermissionsFromNetwork(
            True, config.NETWORK_NAME1, config.DC_NAME[0], config.USER
        )

    @istest
    @polarion("RHEVM3-8379")
    def networkVisibilityInAPI(self):
        """ Network visibility in RestAPI """
        self._testPermissionsOnVnicProfile()
        self._testPermissionsOnVM()
        self._testPermissionsOnTemplate()
        self._testPermissionsOnDC()
        self._testPermissionsOnCluster()
        self._testPermissionsOnNetwork()
        self._testPermissionsOnSystem()


class PositiveNetworkPermissions231832(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME2, data_center=config.DC_NAME[0]
        )
        assert networks.updateVnicProfile(
            config.NETWORK_NAME1,
            config.NETWORK_NAME1,
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            port_mirroring=True
        )
        for user in [
            {
                'user': config.USER_NAME,
                'role': role.NetworkAdmin
            },
            {
                'user': config.USER_NAME2,
                'role': role.VnicProfileUser
            }
        ]:
            assert mla.addPermissionsForVnicProfile(
                True, user['user'], config.NETWORK_NAME2, config.NETWORK_NAME2,
                config.DC_NAME[0], role=user['role']
            )
            assert mla.addPermissionsForVnicProfile(
                True, user['user'], config.NETWORK_NAME1, config.NETWORK_NAME1,
                config.DC_NAME[0], role=user['role']
            )
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME2, config.DC_NAME[0], role.UserRole
        )
        for net in [config.NETWORK_NAME1, config.NETWORK_NAME2]:
            assert networks.addNetworkToCluster(
                True, net, config.CLUSTER_NAME[0]
            )

    @istest
    @polarion("RHEVM3-8378")
    def portMirroring(self):
        """ Port mirroring """
        loginAsUser(userName=config.USER_NAME2)
        assert not networks.updateVnicProfile(
            config.NETWORK_NAME1, config.NETWORK_NAME1, port_mirroring=False,
            cluster=config.CLUSTER_NAME[0], data_center=config.DC_NAME[0]
        )
        assert not networks.updateVnicProfile(
            config.NETWORK_NAME2, config.NETWORK_NAME2, port_mirroring=True,
            cluster=config.CLUSTER_NAME[0], data_center=config.DC_NAME[0]
        )
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.updateVnicProfile(
            config.NETWORK_NAME1,
            config.NETWORK_NAME1,
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            port_mirroring=False
        )
        assert networks.updateVnicProfile(
            config.NETWORK_NAME2,
            config.NETWORK_NAME2,
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            port_mirroring=True
        )


class PositiveNetworkPermissions236367(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME1, config.NETWORK_NAME1,
            config.DC_NAME[0], role=role.VnicProfileUser
        )
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME2, VM_NAME)
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )

    @istest
    @polarion("RHEVM3-8376")
    def addVNICToVM(self):
        """ Add a VNIC to VM  """
        loginAsUser(config.USER_NAME)
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME, network=None, interface='virtio'
        )
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME2, network=config.NETWORK_NAME1,
            interface='virtio'
        )
        loginAsUser(userName=config.USER_NAME2)
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME3, network=None, interface='virtio'
        )


class PositiveNetworkPermissions236406(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME1, config.NETWORK_NAME1,
            config.DC_NAME[0], role=role.VnicProfileUser
        )
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME2, VM_NAME)

        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME, network=config.NETWORK_NAME1,
            interface='virtio'
        )

    @istest
    @polarion("RHEVM3-8375")
    def updateVNICOnVM(self):
        """ Update a VNIC on VM """
        loginAsUser(config.USER_NAME)
        assert vms.updateNic(True, VM_NAME, NIC_NAME, network=None)
        assert vms.updateNic(
            True, VM_NAME, NIC_NAME, network=config.NETWORK_NAME1
        )
        loginAsUser(userName=config.USER_NAME2)
        assert vms.updateNic(True, VM_NAME, NIC_NAME, network=None)


class PositiveNetworkPermissions236408(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            size=config.GB, network=config.MGMT_BRIDGE
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME1, config.NETWORK_NAME1,
            config.DC_NAME[0], role=role.VnicProfileUser
        )
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], role.TemplateCreator
        )
        assert mla.addVMPermissionsToUser(True, config.USER_NAME2, VM_NAME)
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME2, config.DC_NAME[0], role.TemplateOwner
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )

    @istest
    @polarion("RHEVM3-8374")
    @bz({'1209505': {'engine': None, 'version': ['3.6']}})
    def addVNICToTemplate(self):
        """ Add a VNIC to template """
        loginAsUser(config.USER_NAME)
        assert templates.createTemplate(
            True, vm=VM_NAME, name=TEMPLATE_NAME,
            cluster=config.CLUSTER_NAME[0]
        )
        assert templates.addTemplateNic(
            True, TEMPLATE_NAME, name=NIC_NAME, network=None
        )
        assert templates.addTemplateNic(
            True, TEMPLATE_NAME, name=NIC_NAME2, network=config.NETWORK_NAME1
        )
        loginAsUser(userName=config.USER_NAME2)
        assert templates.addTemplateNic(
            True, TEMPLATE_NAME, name=NIC_NAME3, network=None
        )


class PositiveNetworkPermissions236409(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME1, config.NETWORK_NAME1,
            config.DC_NAME[0], role=role.VnicProfileUser
        )
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            size=config.GB, network=config.MGMT_BRIDGE
        )
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME, network=config.NETWORK_NAME1,
            interface='virtio'
        )
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME2, VM_NAME)
        assert templates.createTemplate(
            True, vm=VM_NAME, name=TEMPLATE_NAME,
            cluster=config.CLUSTER_NAME[0]
        )
        assert mla.addPermissionsForTemplate(
            True, config.USER_NAME, TEMPLATE_NAME, role=role.TemplateOwner
        )
        assert mla.addPermissionsForTemplate(
            True, config.USER_NAME2, TEMPLATE_NAME, role=role.TemplateOwner
        )

    @istest
    @polarion("RHEVM3-8373")
    def updateVNICOnTemplate(self):
        """ Update a VNIC on the template """
        loginAsUser(config.USER_NAME)
        assert templates.updateTemplateNic(
            True, TEMPLATE_NAME, NIC_NAME, network=None
        )
        assert templates.updateTemplateNic(
            True, TEMPLATE_NAME, NIC_NAME, network=config.NETWORK_NAME1
        )
        assert templates.updateTemplateNic(
            True, TEMPLATE_NAME, NIC_NAME, name='_'
        )
        assert templates.updateTemplateNic(
            True, TEMPLATE_NAME, '_', name=NIC_NAME
        )
        loginAsUser(userName=config.USER_NAME2)
        assert templates.updateTemplateNic(
            True, TEMPLATE_NAME, NIC_NAME, network=None
        )
        assert templates.updateTemplateNic(
            True, TEMPLATE_NAME, NIC_NAME, name='_'
        )


class PositiveNetworkPermissions236577(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], role.NetworkAdmin
        )

    @istest
    @polarion("RHEVM3-8372")
    def removeNetworkFromDC(self):
        """ RemoveNetwokFromDC """
        msg = "NetworkAdmin role wasn't removed after network %s was removed."
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert networks.removeNetwork(
            True, network=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        loginAsAdmin()
        assert mla.removeUserPermissionsFromDatacenter(
            True, config.DC_NAME[0], config.USER
        )
        # Check if permissions was removed
        perm_persist = False
        obj = mla.userUtil.find(config.USER_NAME)
        objPermits = mla.permisUtil.getElemFromLink(obj, get_href=False)
        roleNAid = users.rlUtil.find(role.NetworkAdmin).get_id()
        for perm in objPermits:
            perm_persist = perm_persist or perm.get_role().get_id() == roleNAid
        assert not perm_persist, msg % config.NETWORK_NAME1


class PositiveNetworkPermissions236664(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert mla.addRole(
            True, name=ROLE_NAME, administrative='true',
            permits='login create_storage_pool_network'
        )
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], ROLE_NAME
        )

    @istest
    @polarion("RHEVM3-8371")
    def customRole(self):
        """ Custom Role """
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert networks.updateNetwork(
            True, config.NETWORK_NAME1, mtu=1405, data_center=config.DC_NAME[0]
        )
        assert networks.removeNetwork(
            True, network=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )


class PositiveNetworkPermissions317269(NetworkingPossitive):
    __test__ = True
    dc_name = 'rand_dc_name'

    def setUp(self):
        assert datacenters.addDataCenter(
            True, name=self.dc_name, storage_type=config.STORAGE_TYPE_NFS,
            version=config.COMP_VERSION
        )

    def tearDown(self):
        super(PositiveNetworkPermissions317269, self).tearDown()
        datacenters.removeDataCenter(True, self.dc_name)

    @istest
    @polarion("RHEVM3-4031")
    def automaticCreateionOfPermissions(self):
        """ Check auto permission creation on new datacenter """
        # newly created dc, vnicprofile has VnicProfileUser role on Everyone
        self.assertTrue(
            mla.hasGroupPermissionsOnObject(
                'Everyone', mla.groupUtil.find('Everyone'),
                role=role.VnicProfileUser
            ),
            "Permission was not created at datacenter for Everyone."
        )


class PositiveNetworkPermissions317133(NetworkingPossitive):
    __test__ = True
    dc_name = 'rand_dc_name'
    bz = {'1214805': {'engine': None, 'version': ['3.6']}}

    def setUp(self):
        users.addRoleToUser(True, config.USER_NAME, role.DataCenterAdmin)
        loginAsUser(config.USER_NAME, filter_=False)
        assert datacenters.addDataCenter(
            True, name=self.dc_name, storage_type=config.STORAGE_TYPE_NFS,
            version=config.COMP_VERSION
        )

    def tearDown(self):
        super(PositiveNetworkPermissions317133, self).tearDown()
        datacenters.removeDataCenter(True, self.dc_name)

    @istest
    @polarion("RHEVM3-4030")
    def automaticCreationToUser(self):
        """ Check that networkadmin permissions are added automatically  """
        loginAsAdmin()
        vnic = networks.getVnicProfileObj(
            networks.MGMT_NETWORK,
            networks.MGMT_NETWORK,
            config.CLUSTER_NAME[0],
            self.dc_name
        )
        net = networks.findNetwork(
            networks.MGMT_NETWORK,
            data_center=self.dc_name,
            cluster=config.CLUSTER_NAME[0]
        )
        self.assertTrue(
            mla.hasUserPermissionsOnObject(
                config.USER1, net, role=role.NetworkAdmin
            ),
            "Permission was not created at datacenter for network."
        )
        self.assertTrue(
            mla.hasUserPermissionsOnObject(
                config.USER1, vnic, role=role.NetworkAdmin
            ),
            "Permission was not created at datacenter for vnicprofile."
        )


class PositiveNetworkPermissions320610(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        networks.addVnicProfile(
            True, config.NETWORK_NAME2, cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0], network=config.NETWORK_NAME1
        )
        mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME1,
            config.NETWORK_NAME1, config.DC_NAME[0], role=role.VnicProfileUser
        )
        mla.addPermissionsForNetwork(
            True, config.USER_NAME, config.NETWORK_NAME1,
            data_center=config.DC_NAME[0], role=role.VnicProfileUser
        )
        vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE, size=config.GB,
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)

    @istest
    @polarion("RHEVM3-4044")
    def vnicPermisAreRestrictedToSpecificProfile(self):
        """
        vnicProfile perms on vNIC profile are restricted to specific profile
        """
        loginAsUser(config.USER_NAME)
        self.assertTrue(
            vms.addNic(
                True, VM_NAME, name=NIC_NAME,
                vnic_profile=config.NETWORK_NAME1,
                network=config.NETWORK_NAME1,
                interface='virtio'
            )
        )
        self.assertRaises(
            EntityNotFound,
            lambda: vms.addNic(
                False, VM_NAME, name=NIC_NAME,
                vnic_profile=config.NETWORK_NAME2,
                network=config.NETWORK_NAME1,
                interface='virtio'
            )
        )


class PositiveNetworkPermissions317270(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(
            True,
            name=config.NETWORK_NAME1,
            data_center=config.DC_NAME[0],
            usages='vm'
        )
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME1, config.NETWORK_NAME1,
            config.DC_NAME[0], role=role.UserRole
        )

    @istest
    @polarion("RHEVM3-4032")
    def nonVmToVmNetwork(self):
        """ When network is switched to nonvm permissions should be removed """
        vnic = networks.getVnicProfileObj(
            config.NETWORK_NAME1,
            config.NETWORK_NAME1,
            config.CLUSTER_NAME[0],
            config.DC_NAME[0]
        )
        self.assertTrue(
            mla.hasUserPermissionsOnObject(
                config.USER1, vnic, role=role.UserRole
            )
        )
        self.assertTrue(
            networks.updateNetwork(
                True,
                network=config.NETWORK_NAME1,
                data_center=config.DC_NAME[0],
                usages=''
            )
        )
        self.assertFalse(
            mla.hasUserPermissionsOnObject(
                config.USER1, vnic, role=role.UserRole
            ),
            "Permission persists on vnicprofile after swtiched to nonvm."
        )
