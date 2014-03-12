'''
Testing network permissions feature. Negative cases.
1 Host, 1 SD, 1 DC, 1 cluster will be created for test.
It will cover scenarios for creating/deleting/viewing networks and vnicprofiles
if user is not permittied for it.
'''

__test__ = True

import logging
from user_roles_tests import config
from user_roles_tests.roles import role
from nose.tools import istest
from art.unittest_lib import BaseTestCase as TestCase
from art.test_handler.tools import tcms
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level import (mla, networks, users, vms,
                                               templates)


LOGGER = logging.getLogger(__name__)
VM_NAME = config.VM_NAME
TEMPLATE_NAME = config.TEMPLATE_NAME
NIC_NAME = 'nic1'
NIC_NAME2 = 'nic2'
NIC_NAME3 = 'nic3'
TCMS_PLAN_ID_NEG = 10640


def loginAsUser(userName, filter_=True):
    users.loginAsUser(userName, config.USER_DOMAIN,
                      config.USER_PASSWORD, filter_)


def loginAsAdmin():
    users.loginAsUser(config.OVIRT_USERNAME, config.OVIRT_DOMAIN,
                      config.OVIRT_PASSWORD, filter=False)


def setUpModule():
    global VM_NAME
    global TEMPLATE_NAME
    VM_NAME = config.VM_NAME
    TEMPLATE_NAME = config.TEMPLATE_NAME
    for user in [config.USER_NAME, config.USER_NAME2, config.USER_NAME3]:
        assert users.addUser(True, user_name=user, domain=config.USER_DOMAIN)


def tearDownModule():
    loginAsAdmin()
    for user in [config.USER_NAME, config.USER_NAME2, config.USER_NAME3]:
        assert users.removeUser(True, user)


def ignoreAllExceptions(method, **kwargs):
    """ Run method and ignore all exceptions. """
    try:
        method(**kwargs)
    except:
        pass


class NetworkingNegative(TestCase):
    __test__ = False

    def tearDown(self):
        loginAsAdmin()
        ignoreAllExceptions(vms.removeVm, positive=True, vm=VM_NAME)
        ignoreAllExceptions(templates.removeTemplate, positive=True,
                            template=TEMPLATE_NAME)

        for network in [config.NETWORK_NAME1, config.NETWORK_NAME2,
                        config.NETWORK_NAME3, config.NETWORK_NAME4]:
            ignoreAllExceptions(networks.removeNetwork,
                                positive=True,
                                network=network,
                                data_center=config.MAIN_DC_NAME)

        mla.removeUsersPermissionsFromDatacenter(
            True, config.MAIN_DC_NAME,
            [config.USER, config.USER2, config.USER3])
        mla.removeUsersPermissionsFromCluster(
            True, config.MAIN_CLUSTER_NAME,
            [config.USER, config.USER2, config.USER3])


class NegativeNetworkPermissions231915(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME, cluster=config.MAIN_CLUSTER_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 231915)
    def createDeleteNetworkinDC(self):
        """ Create/Delete network in DC """
        msg = "User %s with %s can't add/remove network."
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.addNetwork(False, name=config.NETWORK_NAME2,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.removeNetwork(False, network=config.NETWORK_NAME1,
                                      data_center=config.MAIN_DC_NAME)
        LOGGER.info(msg, config.USER, role.ClusterAdmin)


class NegativeNetworkPermissions231916(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME, cluster=config.MAIN_CLUSTER_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 231916)
    def editNetworkInDC(self):
        """  Edit network in DC """
        msg = "User %s with %s can't update network."
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.MAIN_DC_NAME, mtu=1502)
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.MAIN_DC_NAME, vlan_id=3)
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.MAIN_DC_NAME, usages='')
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.MAIN_DC_NAME, usages='VM')
        LOGGER.info(msg, config.USER, role.ClusterAdmin)


class NegativeNetworkPermissions231917(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME2,
                                   data_center=config.MAIN_DC_NAME)

        for net in [config.NETWORK_NAME1, config.NETWORK_NAME2]:
            assert mla.addPermissionsForVnicProfile(
                True, config.USER_NAME, net, net,
                config.MAIN_DC_NAME, role=role.VnicProfileUser)
            assert mla.addPermissionsForVnicProfile(
                True, config.USER_NAME2, net, net,
                config.MAIN_DC_NAME, role=role.VnicProfileUser)
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.MAIN_CLUSTER_NAME)
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME2, config.MAIN_CLUSTER_NAME, role.HostAdmin)

        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                                            config.MAIN_CLUSTER_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 231917)
    def attachingDetachingNetworkToFromCluster(self):
        """ Attaching/Detaching network to/from Cluster """
        for user in [config.USER_NAME, config.USER_NAME2]:
            loginAsUser(userName=user, filter_=False)
            assert networks.removeNetworkFromCluster(
                False, config.NETWORK_NAME1, config.MAIN_CLUSTER_NAME)
            assert networks.addNetworkToCluster(
                False, config.NETWORK_NAME2, config.MAIN_CLUSTER_NAME)


class NegativeNetworkPermissions231918(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.MAIN_DC_NAME, role=role.HostAdmin)
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME2, data_center=config.MAIN_DC_NAME)
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME1, config.NETWORK_NAME1,
            config.MAIN_DC_NAME)
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME2, config.NETWORK_NAME2,
            config.MAIN_DC_NAME)

        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.MAIN_CLUSTER_NAME)
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME2, config.MAIN_CLUSTER_NAME)

        assert networks.updateClusterNetwork(
            True, config.MAIN_CLUSTER_NAME,
            config.NETWORK_NAME1, required=True)
        assert networks.updateClusterNetwork(
            True, config.MAIN_CLUSTER_NAME,
            config.NETWORK_NAME2, required=False)

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 231918)
    def networkRequiredToNonRequiredAndViceVersa(self):
        """ Network required to non-required and vice versa """
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.updateClusterNetwork(
            False, config.MAIN_CLUSTER_NAME,
            config.NETWORK_NAME1, required=False)
        assert networks.updateClusterNetwork(
            False, config.MAIN_CLUSTER_NAME,
            config.NETWORK_NAME1, required=True)


class NegativeNetworkPermissions231919(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME,
                            network=config.MGMT_BRIDGE)
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME,
            config.MAIN_DC_NAME, role=role.HostAdmin)
        assert mla.addVMPermissionsToUser(
            True, config.USER_NAME, VM_NAME, role=role.UserRole)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=config.NETWORK_NAME, interface='virtio')

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 231919)
    def attachingVNICToVM(self):
        """ Attaching VNIC to VM """
        loginAsUser(config.USER_NAME, filter_=False)
        assert vms.addNic(False, VM_NAME, name=NIC_NAME2,
                          network=config.NETWORK_NAME, interface='virtio')
        assert vms.removeNic(False, VM_NAME, NIC_NAME)
        assert vms.updateNic(False, VM_NAME, NIC_NAME, name='newName')


class NegativeNetworkPermissions234215(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.MAIN_DC_NAME, role=role.HostAdmin)
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME,
                            network=config.MGMT_BRIDGE)
        assert templates.createTemplate(
            True, vm=VM_NAME, name=TEMPLATE_NAME,
            cluster=config.MAIN_CLUSTER_NAME)
        assert templates.addTemplateNic(True, TEMPLATE_NAME, name=NIC_NAME,
                                        network=config.NETWORK_NAME)

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 234215)
    def attachVNICToTemplate(self):
        """ Attach VNIC to Template """
        loginAsUser(config.USER_NAME, filter_=False)
        assert templates.addTemplateNic(False, TEMPLATE_NAME, name=NIC_NAME2,
                                        network=config.NETWORK_NAME)
        assert templates.removeTemplateNic(False, TEMPLATE_NAME, NIC_NAME)
        assert templates.updateTemplateNic(False, TEMPLATE_NAME, NIC_NAME,
                                           name='newName')


class NegativeNetworkPermissions236686(NetworkingNegative):
    """ Attach a network to VM """
    __test__ = True

    def setUp(self):
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME,
                            network=config.MGMT_BRIDGE)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME2,
                                   data_center=config.MAIN_DC_NAME)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                                            config.MAIN_CLUSTER_NAME)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME2,
                                            config.MAIN_CLUSTER_NAME)
        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=config.NETWORK_NAME2, interface='virtio')

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 236686)
    def attachNetworkToVM(self):
        """ Attach a network to VM """
        loginAsUser(config.USER_NAME)
        self.assertRaises(EntityNotFound, vms.addNic, False, VM_NAME,
                          name=NIC_NAME3, network=config.NETWORK_NAME1,
                          interface='virtio')
        self.assertRaises(EntityNotFound, vms.updateNic, False, VM_NAME,
                          NIC_NAME, network=config.NETWORK_NAME1)


class NegativeNetworkPermissions236736(NetworkingNegative):
    """ Visible networks and manipulation """
    __test__ = True

    def setUp(self):
        assert vms.createVm(True, VM_NAME, '',
                            cluster=config.MAIN_CLUSTER_NAME,
                            network=config.MGMT_BRIDGE)
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME1,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME2,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME3,
                                   data_center=config.MAIN_DC_NAME)
        assert networks.addNetwork(True, name=config.NETWORK_NAME4,
                                   data_center=config.MAIN_DC_NAME)

        assert networks.addNetworkToCluster(True, config.NETWORK_NAME1,
                                            config.MAIN_CLUSTER_NAME)
        assert networks.addNetworkToCluster(True, config.NETWORK_NAME2,
                                            config.MAIN_CLUSTER_NAME)

        assert vms.addNic(True, VM_NAME, name=NIC_NAME,
                          network=config.NETWORK_NAME1, interface='virtio')
        assert vms.addNic(True, VM_NAME, name=NIC_NAME2,
                          network=config.NETWORK_NAME2, interface='virtio')

    @istest
    @tcms(TCMS_PLAN_ID_NEG, 236736)
    def visibleNetworksAndManipulation(self):
        """ Visible networks and manipulation """
        loginAsUser(config.USER_NAME)
        assert vms.addNic(False, VM_NAME, name=NIC_NAME3,
                          network=config.NETWORK_NAME1, interface='virtio')
        assert vms.updateNic(False, VM_NAME, NIC_NAME2,
                             network=config.NETWORK_NAME1)
        assert vms.removeNic(True, VM_NAME, NIC_NAME)
        self.assertRaises(EntityNotFound, vms.addNic, False, VM_NAME,
                          name=NIC_NAME, network=config.NETWORK_NAME1,
                          interface='virtio')
        nets = [n.get_name() for n in networks.NET_API.get(absLink=False)]
        LOGGER.info("User can see networks: '%s'", nets)
        # User can see network2 and default rhevm network, because has
        # Everyone VnicProfileUser permissons, None network is not count
        # (is not shown in /api/networks) + Default DC
        assert len(nets) == 3
        assert vms.updateNic(True, VM_NAME, NIC_NAME2, network=None)
        self.assertRaises(EntityNotFound, vms.updateNic, False, VM_NAME,
                          NIC_NAME2, network=config.NETWORK_NAME2)
