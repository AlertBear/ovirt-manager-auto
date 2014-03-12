'''
Testing network permissions feature. Possitive cases.
1 Host, 1 SD, 1 DC, 1 cluster will be created for test.
It will cover scenarios for creating/deleting/viewing networks and vnicprofiles
if user is permittied for it.
'''

__test__ = True

import logging
from user_roles_tests import config as cfg
from user_roles_tests.roles import role
from nose.tools import istest
from art.test_handler.tools import tcms, bz
from art.core_api.apis_exceptions import EntityNotFound
from test_network_permissions_negative import (ignoreAllExceptions,
                                               loginAsUser, loginAsAdmin,
                                               NetworkingNegative)
from art.rhevm_api.tests_lib.low_level import (mla, networks, users, vms,
                                               templates, datacenters)


LOGGER = logging.getLogger(__name__)
VM_NAME = cfg.VM_NAME
TEMPLATE_NAME = cfg.TEMPLATE_NAME
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
    VM_NAME = cfg.VM_NAME
    TEMPLATE_NAME = cfg.TEMPLATE_NAME
    for user in [cfg.USER_NAME, cfg.USER_NAME2, cfg.USER_NAME3]:
        assert users.addUser(True, user_name=user, domain=cfg.USER_DOMAIN)


def tearDownModule():
    loginAsAdmin()
    for user in [cfg.USER_NAME, cfg.USER_NAME2, cfg.USER_NAME3]:
        assert users.removeUser(True, user)


class NetworkingPossitive(NetworkingNegative):
    __test__ = False

    def tearDown(self):
        super(NetworkingPossitive, self).tearDown()
        ignoreAllExceptions(mla.removeRole, positive=True, role=ROLE_NAME)


class PositiveNetworkPermissions231821(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert mla.addPermissionsForDataCenter(
            True, cfg.USER_NAME, cfg.MAIN_DC_NAME, role=role.SuperUser)
        assert mla.addPermissionsForDataCenter(
            True, cfg.USER_NAME2,
            cfg.MAIN_DC_NAME, role=role.DataCenterAdmin)
        assert mla.addPermissionsForDataCenter(
            True, cfg.USER_NAME3,
            cfg.MAIN_DC_NAME, role=role.NetworkAdmin)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231821)
    def createNetworkInDC(self):
        """ CreateNetworkInDc """
        for u in [cfg.USER_NAME, cfg.USER_NAME2, cfg.USER_NAME3]:
            loginAsUser(userName=u, filter_=False)
            assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                       data_center=cfg.MAIN_DC_NAME)
            loginAsAdmin()
            assert networks.removeNetwork(True, network=cfg.NETWORK_NAME1,
                                          data_center=cfg.MAIN_DC_NAME)


class PositiveNetworkPermissions231822(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert mla.addPermissionsForNetwork(
            True, cfg.USER_NAME, cfg.NETWORK_NAME1,
            data_center=cfg.MAIN_DC_NAME, role=role.DataCenterAdmin)
        assert mla.addPermissionsForNetwork(
            True, cfg.USER_NAME2, cfg.NETWORK_NAME1,
            data_center=cfg.MAIN_DC_NAME, role=role.NetworkAdmin)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231822)
    def editNetworkInDC(self):
        """ Edit network in DC """
        mtu = 800
        stp = True
        for uName in [cfg.USER_NAME, cfg.USER_NAME2]:
            loginAsUser(userName=uName, filter_=False)
            assert networks.updateNetwork(True, cfg.NETWORK_NAME1,
                                          data_center=cfg.MAIN_DC_NAME,
                                          mtu=mtu, stp=str(stp).lower())
            mtu += 100
            stp = not stp


class PositiveNetworkPermissions231823(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert mla.addPermissionsForNetwork(
            True, cfg.USER_NAME, cfg.NETWORK_NAME1,
            data_center=cfg.MAIN_DC_NAME, role=role.NetworkAdmin)
        assert mla.addClusterPermissionsToUser(
            True, cfg.USER_NAME2, cluster=cfg.MAIN_CLUSTER_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231823)
    def attachingNetworkToCluster(self):
        """ Attaching network to cluster """
        loginAsUser(cfg.USER_NAME, filter_=False)
        assert networks.addNetworkToCluster(True, cfg.NETWORK_NAME1,
                                            cfg.MAIN_CLUSTER_NAME)
        assert networks.removeNetworkFromCluster(
            True, cfg.NETWORK_NAME1, cfg.MAIN_CLUSTER_NAME)

        loginAsUser(userName=cfg.USER_NAME2, filter_=False)
        assert networks.addNetworkToCluster(False, cfg.NETWORK_NAME1,
                                            cfg.MAIN_CLUSTER_NAME)
        LOGGER.info("ClusterAdmin can't attach network to cluster.")


class TestSwitching(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert mla.addClusterPermissionsToUser(
            True, cfg.USER_NAME, cluster=cfg.MAIN_CLUSTER_NAME)
        assert mla.addPermissionsForNetwork(
            True, cfg.USER_NAME2, cfg.NETWORK_NAME1,
            data_center=cfg.MAIN_DC_NAME, role=role.NetworkAdmin)
        assert networks.addNetworkToCluster(
            True, cfg.NETWORK_NAME1, cfg.MAIN_CLUSTER_NAME)

    def _inverseParams(self, kwargs):
        ''' inverse required or/and display param if exists '''
        if 'required' in kwargs:
            kwargs['required'] = not kwargs['required']
        if 'display' in kwargs:
            kwargs['display'] = not kwargs['display']
        if 'usages' in kwargs:
            kwargs['usages'] = (
                'vm' if kwargs['usages'] == 'display' else 'display')

    def _test_switching_display_and_required(self, **kwargs):
        assert networks.updateClusterNetwork(True, cfg.MAIN_CLUSTER_NAME,
                                             cfg.NETWORK_NAME1, **kwargs)

        for uName in [cfg.USER_NAME, cfg.USER_NAME2]:
            loginAsUser(userName=uName, filter_=False)
            self._inverseParams(kwargs)
            assert networks.updateClusterNetwork(True, cfg.MAIN_CLUSTER_NAME,
                                                 cfg.NETWORK_NAME1, **kwargs)
            self._inverseParams(kwargs)
            assert networks.updateClusterNetwork(True, cfg.MAIN_CLUSTER_NAME,
                                                 cfg.NETWORK_NAME1, **kwargs)


class PositiveNetworkPermissions231824(TestSwitching):
    __test__ = True

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231824)
    def requiredToNonRequiredAndViceVersa(self):
        """ Required to non-required and vice versa """
        self._test_switching_display_and_required(required=True)


class PositiveNetworkPermissions236073(TestSwitching):
    __test__ = True

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236073)
    def displayNetwork(self):
        """ Display network """
        self._test_switching_display_and_required(display=True,
                                                  usages='display')


class PositiveNetworkPermissions231826(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert vms.createVm(True, VM_NAME, '', cluster=cfg.MAIN_CLUSTER_NAME,
                            storageDomainName=cfg.MAIN_STORAGE_NAME,
                            size=cfg.GB, network=cfg.MGMT_BRIDGE)
        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME, VM_NAME)
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert networks.addNetworkToCluster(True, cfg.NETWORK_NAME1,
                                            cfg.MAIN_CLUSTER_NAME)
        assert mla.addPermissionsForVnicProfile(
            True, cfg.USER_NAME, cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
            cfg.MAIN_DC_NAME, role=role.VnicProfileUser)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231826)
    def attachDetachNetworkToVM(self):
        """ Attach/Detach a network to VM  """
        loginAsUser(cfg.USER_NAME)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=cfg.NETWORK_NAME, interface='virtio')
        assert vms.removeNic(True, VM_NAME, NIC_NAME)


class PositiveNetworkPermissions231827(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        # Not possible to create public vnicprofile, just add Everyone perms
        for net in [cfg.NETWORK_NAME1, cfg.NETWORK_NAME2,
                    cfg.NETWORK_NAME3, cfg.NETWORK_NAME4]:
            assert networks.addNetwork(True, name=net,
                                       data_center=cfg.MAIN_DC_NAME)
            assert mla.addVnicProfilePermissionsToGroup(
                True, EVERYONE, net, net, cfg.MAIN_DC_NAME)
            assert networks.addNetworkToCluster(True, net,
                                                cfg.MAIN_CLUSTER_NAME)

        assert vms.createVm(True, VM_NAME, '', cluster=cfg.MAIN_CLUSTER_NAME,
                            network=cfg.MGMT_BRIDGE)
        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME, VM_NAME)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=cfg.NETWORK_NAME1, interface='virtio')

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231827)
    def visibleNetworksAndManipulations(self):
        """ Visible networks and manipulations """
        loginAsUser(cfg.USER_NAME)
        for net in [cfg.NETWORK_NAME1, cfg.NETWORK_NAME2,
                    cfg.NETWORK_NAME3, cfg.NETWORK_NAME4]:
            assert vms.addNic(True, VM_NAME, name=net,
                              network=net, interface='virtio')
            assert vms.updateNic(True, VM_NAME, net, name='%s-x' % net)
        nets = [n.get_name() for n in networks.NET_API.get(absLink=False)]
        LOGGER.info("User can see networks: '%s'" % nets)
        assert len(nets) == 6
        assert vms.removeNic(True, VM_NAME, NIC_NAME)


class PositiveNetworkPermissions231830(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME2,
                                   data_center=cfg.MAIN_DC_NAME)
        for net in [cfg.NETWORK_NAME1, cfg.NETWORK_NAME2]:
            assert networks.addNetworkToCluster(True, net,
                                                cfg.MAIN_CLUSTER_NAME)
        assert vms.createVm(True, VM_NAME, '', cluster=cfg.MAIN_CLUSTER_NAME,
                            network=cfg.MGMT_BRIDGE)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=cfg.NETWORK_NAME1, interface='virtio')
        assert templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME,
                                        cluster=cfg.MAIN_CLUSTER_NAME)

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
        net1 = cfg.NETWORK_NAME1
        net2 = cfg.NETWORK_NAME2
        loginAsUser(cfg.USER_NAME, filter_=filter_)
        self.canSee(self.filterNet(net1, p1, networks.findNetwork),
                    self.filterNet(net2, p2, networks.findNetwork),
                    self.filterNet(net1, p3, networks.VNIC_PROFILE_API.find),
                    self.filterNet(net2, p4, networks.VNIC_PROFILE_API.find))
        loginAsAdmin()

    def _testPermissionsOnVnicProfile(self):
        mla.addPermissionsForVnicProfile(True, cfg.USER_NAME,
                                         cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
                                         cfg.MAIN_DC_NAME,
                                         role=role.VnicProfileUser)
        self._testWrap(True, False, True, False)
        mla.removeUserPermissionsFromVnicProfile(True, cfg.NETWORK_NAME1,
                                                 cfg.NETWORK_NAME1,
                                                 cfg.MAIN_DC_NAME, cfg.USER)

    def _testPermissionsOnVM(self):
        mla.addVMPermissionsToUser(True, cfg.USER_NAME, cfg.VM_NAME)
        self._testWrap(True, False, True, False)
        mla.removeUserPermissionsFromVm(True, cfg.VM_NAME, cfg.USER)

    def _testPermissionsOnTemplate(self):
        mla.addPermissionsForTemplate(True, cfg.USER_NAME, cfg.TEMPLATE_NAME)
        self._testWrap(True, False, True, False)
        mla.removeUserPermissionsFromTemplate(True, cfg.TEMPLATE_NAME,
                                              cfg.USER)

    def _testPermissionsOnDC(self):
        mla.addPermissionsForDataCenter(True, cfg.USER_NAME, cfg.MAIN_DC_NAME)
        self._testWrap(True, True, True, True, False)
        mla.removeUserPermissionsFromDatacenter(True, cfg.MAIN_DC_NAME,
                                                cfg.USER)

    def _testPermissionsOnCluster(self):
        mla.addClusterPermissionsToUser(True, cfg.USER_NAME,
                                        cfg.MAIN_CLUSTER_NAME)
        self._testWrap(True, True, True, True, False)
        mla.removeUserPermissionsFromCluster(True, cfg.MAIN_CLUSTER_NAME,
                                             cfg.USER)

    def _testPermissionsOnSystem(self):
        users.addRoleToUser(True, cfg.USER_NAME, role.UserRole)
        self._testWrap(True, True, True, True)
        users.removeUser(True, cfg.USER_NAME)
        users.addUser(True, user_name=cfg.USER_NAME, domain=cfg.USER_DOMAIN)

    def _testPermissionsOnNetwork(self):
        mla.addPermissionsForNetwork(True, cfg.USER_NAME, cfg.NETWORK_NAME1,
                                     cfg.MAIN_DC_NAME, role.VnicProfileUser)
        self._testWrap(True, False, True, False)
        mla.removeUserPermissionsFromNetwork(True, cfg.NETWORK_NAME1,
                                             cfg.MAIN_DC_NAME, cfg.USER)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231830)
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
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME2,
                                   data_center=cfg.MAIN_DC_NAME)
        assert networks.updateVnicProfile(cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
                                          cluster=cfg.MAIN_CLUSTER_NAME,
                                          data_center=cfg.MAIN_DC_NAME,
                                          port_mirroring=True)
        for user in [{'user': cfg.USER_NAME, 'role': role.NetworkAdmin},
                     {'user': cfg.USER_NAME2, 'role': role.VnicProfileUser}]:
            assert mla.addPermissionsForVnicProfile(
                True, user['user'], cfg.NETWORK_NAME2, cfg.NETWORK_NAME2,
                cfg.MAIN_DC_NAME, role=user['role'])
            assert mla.addPermissionsForVnicProfile(
                True, user['user'], cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
                cfg.MAIN_DC_NAME, role=user['role'])
        assert mla.addPermissionsForDataCenter(True, cfg.USER_NAME2,
                                               cfg.MAIN_DC_NAME, role.UserRole)
        for net in [cfg.NETWORK_NAME1, cfg.NETWORK_NAME2]:
            assert networks.addNetworkToCluster(True, net,
                                                cfg.MAIN_CLUSTER_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 231832)
    def portMirroring(self):
        """ Port mirroring """
        loginAsUser(userName=cfg.USER_NAME2)
        assert not networks.updateVnicProfile(
            cfg.NETWORK_NAME1, cfg.NETWORK_NAME1, port_mirroring=False,
            cluster=cfg.MAIN_CLUSTER_NAME, data_center=cfg.MAIN_DC_NAME)
        assert not networks.updateVnicProfile(
            cfg.NETWORK_NAME2, cfg.NETWORK_NAME2, port_mirroring=True,
            cluster=cfg.MAIN_CLUSTER_NAME, data_center=cfg.MAIN_DC_NAME)
        loginAsUser(cfg.USER_NAME, filter_=False)
        assert networks.updateVnicProfile(cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
                                          cluster=cfg.MAIN_CLUSTER_NAME,
                                          data_center=cfg.MAIN_DC_NAME,
                                          port_mirroring=False)
        assert networks.updateVnicProfile(cfg.NETWORK_NAME2, cfg.NETWORK_NAME2,
                                          cluster=cfg.MAIN_CLUSTER_NAME,
                                          data_center=cfg.MAIN_DC_NAME,
                                          port_mirroring=True)


class PositiveNetworkPermissions236367(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert vms.createVm(True, VM_NAME, '', cluster=cfg.MAIN_CLUSTER_NAME,
                            network=cfg.MGMT_BRIDGE)
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert mla.addPermissionsForVnicProfile(
            True, cfg.USER_NAME, cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
            cfg.MAIN_DC_NAME, role=role.VnicProfileUser)

        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME2, VM_NAME)

        assert networks.addNetworkToCluster(True, cfg.NETWORK_NAME1,
                                            cfg.MAIN_CLUSTER_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236367)
    def addVNICToVM(self):
        """ Add a VNIC to VM  """
        loginAsUser(cfg.USER_NAME)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=None, interface='virtio')
        assert vms.addNic(True, VM_NAME, name=NIC_NAME2,
                          network=cfg.NETWORK_NAME1, interface='virtio')
        loginAsUser(userName=cfg.USER_NAME2)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME3,
                          network=None, interface='virtio')


class PositiveNetworkPermissions236406(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert vms.createVm(True, VM_NAME, '', cluster=cfg.MAIN_CLUSTER_NAME,
                            network=cfg.MGMT_BRIDGE)
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert mla.addPermissionsForVnicProfile(
            True, cfg.USER_NAME, cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
            cfg.MAIN_DC_NAME, role=role.VnicProfileUser)

        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME2, VM_NAME)

        assert networks.addNetworkToCluster(True, cfg.NETWORK_NAME1,
                                            cfg.MAIN_CLUSTER_NAME)

        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=cfg.NETWORK_NAME1, interface='virtio')

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236406)
    def updateVNICOnVM(self):
        """ Update a VNIC on VM """
        loginAsUser(cfg.USER_NAME)
        assert vms.updateNic(True, VM_NAME, NIC_NAME, network=None)
        assert vms.updateNic(True, VM_NAME, NIC_NAME,
                             network=cfg.NETWORK_NAME1)
        loginAsUser(userName=cfg.USER_NAME2)
        assert vms.updateNic(True, VM_NAME, NIC_NAME, network=None)


class PositiveNetworkPermissions236408(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert vms.createVm(True, VM_NAME, '', cluster=cfg.MAIN_CLUSTER_NAME,
                            storageDomainName=cfg.MAIN_STORAGE_NAME,
                            size=cfg.GB, network=cfg.MGMT_BRIDGE)
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert mla.addPermissionsForVnicProfile(
            True, cfg.USER_NAME, cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
            cfg.MAIN_DC_NAME, role=role.VnicProfileUser)
        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME, VM_NAME)
        assert mla.addPermissionsForDataCenter(True, cfg.USER_NAME,
                                               cfg.MAIN_DC_NAME,
                                               role.TemplateCreator)

        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME2, VM_NAME)
        assert mla.addPermissionsForDataCenter(True, cfg.USER_NAME2,
                                               cfg.MAIN_DC_NAME,
                                               role.TemplateOwner)
        assert networks.addNetworkToCluster(True, cfg.NETWORK_NAME1,
                                            cfg.MAIN_CLUSTER_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236408)
    def addVNICToTemplate(self):
        """ Add a VNIC to template """
        loginAsUser(cfg.USER_NAME)
        assert templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME,
                                        cluster=cfg.MAIN_CLUSTER_NAME)
        assert templates.addTemplateNic(True, TEMPLATE_NAME, name=NIC_NAME,
                                        network=None)
        assert templates.addTemplateNic(True, TEMPLATE_NAME, name=NIC_NAME2,
                                        network=cfg.NETWORK_NAME1)

        loginAsUser(userName=cfg.USER_NAME2)
        assert templates.addTemplateNic(True, TEMPLATE_NAME, name=NIC_NAME3,
                                        network=None)


class PositiveNetworkPermissions236409(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert networks.addNetworkToCluster(True, cfg.NETWORK_NAME1,
                                            cfg.MAIN_CLUSTER_NAME)
        assert mla.addPermissionsForVnicProfile(
            True, cfg.USER_NAME, cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
            cfg.MAIN_DC_NAME, role=role.VnicProfileUser)
        assert vms.createVm(True, VM_NAME, '', cluster=cfg.MAIN_CLUSTER_NAME,
                            storageDomainName=cfg.MAIN_STORAGE_NAME,
                            size=cfg.GB, network=cfg.MGMT_BRIDGE)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=cfg.NETWORK_NAME1, interface='virtio')
        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME, VM_NAME)
        assert mla.addVMPermissionsToUser(True, cfg.USER_NAME2, VM_NAME)
        assert templates.createTemplate(True, vm=VM_NAME, name=TEMPLATE_NAME,
                                        cluster=cfg.MAIN_CLUSTER_NAME)
        assert mla.addPermissionsForTemplate(True, cfg.USER_NAME,
                                             TEMPLATE_NAME,
                                             role=role.TemplateOwner)
        assert mla.addPermissionsForTemplate(True, cfg.USER_NAME2,
                                             TEMPLATE_NAME,
                                             role=role.TemplateOwner)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236409)
    def updateVNICOnTemplate(self):
        """ Update a VNIC on the template """
        loginAsUser(cfg.USER_NAME)
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                                           network=None)
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                                           network=cfg.NETWORK_NAME1)
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                                           name='_')
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, '_',
                                           name=NIC_NAME)
        loginAsUser(userName=cfg.USER_NAME2)
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                                           network=None)
        assert templates.updateTemplateNic(True, TEMPLATE_NAME, NIC_NAME,
                                           name='_')


class PositiveNetworkPermissions236577(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert mla.addPermissionsForDataCenter(True, cfg.USER_NAME,
                                               cfg.MAIN_DC_NAME,
                                               role.NetworkAdmin)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236577)
    def removeNetworkFromDC(self):
        """ RemoveNetwokFromDC """
        msg = "NetworkAdmin role wasn't removed after network %s was removed."
        loginAsUser(cfg.USER_NAME, filter_=False)
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert networks.removeNetwork(True, network=cfg.NETWORK_NAME1,
                                      data_center=cfg.MAIN_DC_NAME)

        loginAsAdmin()
        assert mla.removeUserPermissionsFromDatacenter(True, cfg.MAIN_DC_NAME,
                                                       cfg.USER)

        # Check if permissions was removed
        perm_persist = False
        obj = mla.userUtil.find(cfg.USER_NAME)
        objPermits = mla.permisUtil.getElemFromLink(obj, get_href=False)
        roleNAid = users.rlUtil.find(role.NetworkAdmin).get_id()
        for perm in objPermits:
            perm_persist = perm_persist or perm.get_role().get_id() == roleNAid
        assert not perm_persist, msg % cfg.NETWORK_NAME1


class PositiveNetworkPermissions236664(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert mla.addRole(True, name=ROLE_NAME, administrative='true',
                           permits='login create_storage_pool_network')
        assert mla.addPermissionsForDataCenter(True, cfg.USER_NAME,
                                               cfg.MAIN_DC_NAME, ROLE_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 236664)
    def customRole(self):
        """ Custom Role """
        loginAsUser(cfg.USER_NAME, filter_=False)
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME)
        assert networks.updateNetwork(True, cfg.NETWORK_NAME1, mtu=1405,
                                      data_center=cfg.MAIN_DC_NAME)
        assert networks.removeNetwork(True, network=cfg.NETWORK_NAME1,
                                      data_center=cfg.MAIN_DC_NAME)


class PositiveNetworkPermissions317269(NetworkingPossitive):
    __test__ = True
    dc_name = 'rand_dc_name'

    def setUp(self):
        cv = 'compatibility_version'
        assert datacenters.addDataCenter(True, name=self.dc_name,
                                         storage_type=cfg.MAIN_STORAGE_TYPE,
                                         version=cfg.PARAMETERS.get(cv))

    def tearDown(self):
        super(PositiveNetworkPermissions317269, self).tearDown()
        datacenters.removeDataCenter(True, self.dc_name)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 317269)
    def automaticCreateionOfPermissions(self):
        """ Check auto permission creation on new datacenter """
        # newly created dc, vnicprofile has VnicProfileUser role on Everyone
        self.assertTrue(
            mla.hasGroupPermissionsOnObject(
                'Everyone', mla.groupUtil.find('Everyone'),
                role=role.VnicProfileUser),
            "Permission was not created at datacenter for Everyone.")


class PositiveNetworkPermissions317133(NetworkingPossitive):
    __test__ = True
    dc_name = 'rand_dc_name'

    def setUp(self):
        users.addRoleToUser(True, cfg.USER_NAME, role.DataCenterAdmin)
        loginAsUser(cfg.USER_NAME, filter_=False)
        cv = 'compatibility_version'
        assert datacenters.addDataCenter(True, name=self.dc_name,
                                         storage_type=cfg.MAIN_STORAGE_TYPE,
                                         version=cfg.PARAMETERS.get(cv))

    def tearDown(self):
        super(PositiveNetworkPermissions317133, self).tearDown()
        datacenters.removeDataCenter(True, self.dc_name)

    @istest
    @bz(1014985)
    @tcms(TCMS_PLAN_ID_POS, 317133)
    def automaticCreationToUser(self):
        """ Check that networkadmin permissions are added automatically  """
        loginAsAdmin()
        vnic = networks.getVnicProfileObj(networks.MGMT_NETWORK,
                                          networks.MGMT_NETWORK,
                                          cfg.MAIN_CLUSTER_NAME, self.dc_name)
        net = networks.findNetwork(networks.MGMT_NETWORK,
                                   data_center=self.dc_name,
                                   cluster=cfg.MAIN_CLUSTER_NAME)
        self.assertTrue(
            mla.hasUserPermissionsOnObject(cfg.USER1, net,
                                           role=role.NetworkAdmin),
            "Permission was not created at datacenter for network.")
        self.assertTrue(
            mla.hasUserPermissionsOnObject(cfg.USER1, vnic,
                                           role=role.NetworkAdmin),
            "Permission was not created at datacenter for vnicprofile.")


class PositiveNetworkPermissions320610(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                            data_center=cfg.MAIN_DC_NAME)
        networks.addNetworkToCluster(True, cfg.NETWORK_NAME1,
                                     cfg.MAIN_CLUSTER_NAME)
        networks.addVnicProfile(True, cfg.NETWORK_NAME2,
                                cluster=cfg.MAIN_CLUSTER_NAME,
                                data_center=cfg.MAIN_DC_NAME,
                                network=cfg.NETWORK_NAME1)
        mla.addPermissionsForVnicProfile(True, cfg.USER_NAME,
                                         cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
                                         cfg.MAIN_DC_NAME,
                                         role=role.VnicProfileUser)
        mla.addPermissionsForNetwork(True, cfg.USER_NAME, cfg.NETWORK_NAME1,
                                     data_center=cfg.MAIN_DC_NAME,
                                     role=role.VnicProfileUser)
        vms.createVm(True, VM_NAME, '', cluster=cfg.MAIN_CLUSTER_NAME,
                     storageDomainName=cfg.MAIN_STORAGE_NAME, size=cfg.GB,
                     network=cfg.MGMT_BRIDGE)
        mla.addVMPermissionsToUser(True, cfg.USER_NAME, VM_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 320610)
    def vnicPermisAreRestrictedToSpecificProfile(self):
        """
        vnicProfile perms on vNIC profile are restricted to specific profile
        """
        loginAsUser(cfg.USER_NAME)
        self.assertTrue(vms.addNic(True, VM_NAME, name=NIC_NAME,
                                   vnic_profile=cfg.NETWORK_NAME1,
                                   network=cfg.NETWORK_NAME1,
                                   interface='virtio'))
        self.assertRaises(EntityNotFound,
                          lambda: vms.addNic(False, VM_NAME, name=NIC_NAME,
                                             vnic_profile=cfg.NETWORK_NAME2,
                                             network=cfg.NETWORK_NAME1,
                                             interface='virtio'))


class PositiveNetworkPermissions317270(NetworkingPossitive):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(True, name=cfg.NETWORK_NAME1,
                                   data_center=cfg.MAIN_DC_NAME, usages='vm')
        assert mla.addPermissionsForVnicProfile(True, cfg.USER_NAME,
                                                cfg.NETWORK_NAME1,
                                                cfg.NETWORK_NAME1,
                                                cfg.MAIN_DC_NAME,
                                                role=role.UserRole)

    @istest
    @tcms(TCMS_PLAN_ID_POS, 317270)
    def nonVmToVmNetwork(self):
        """ When network is switched to nonvm permissions should be removed """
        vnic = networks.getVnicProfileObj(cfg.NETWORK_NAME1, cfg.NETWORK_NAME1,
                                          cfg.MAIN_CLUSTER_NAME,
                                          cfg.MAIN_DC_NAME)
        self.assertTrue(
            mla.hasUserPermissionsOnObject(cfg.USER1, vnic,
                                           role=role.UserRole))
        self.assertTrue(networks.updateNetwork(True, network=cfg.NETWORK_NAME1,
                                               data_center=cfg.MAIN_DC_NAME,
                                               usages=''))
        self.assertFalse(
            mla.hasUserPermissionsOnObject(cfg.USER1, vnic,
                                           role=role.UserRole),
            "Permission persists on vnicprofile after swtiched to nonvm.")
