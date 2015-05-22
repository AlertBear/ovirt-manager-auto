'''
Testing network permissions feature. Negative cases.
1 Host, 1 SD, 1 DC, 1 cluster will be created for test.
It will cover scenarios for creating/deleting/viewing networks and vnicprofiles
if user is not permittied for it.
'''

__test__ = True

import logging
from rhevmtests.system.user_roles_tests import config, common
from rhevmtests.system.user_roles_tests.roles import role
from nose.tools import istest
from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
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
    users.loginAsUser(
        userName, config.PROFILE, config.USER_PASSWORD, filter_
    )


def loginAsAdmin():
    users.loginAsUser(
        config.VDC_ADMIN_USER,
        config.VDC_ADMIN_DOMAIN,
        config.VDC_PASSWORD,
        filter=False
    )


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


def ignoreAllExceptions(method, **kwargs):
    """ Run method and ignore all exceptions. """
    try:
        method(**kwargs)
    except:
        pass


@attr(tier=1)
class NetworkingNegative(TestCase):
    __test__ = False

    # Network is not supported in CLI
    apis = set(['rest', 'sdk', 'java'])

    def tearDown(self):
        loginAsAdmin()
        ignoreAllExceptions(vms.removeVm, positive=True, vm=VM_NAME)
        ignoreAllExceptions(
            templates.removeTemplate, positive=True, template=TEMPLATE_NAME
        )

        for network in [
            config.NETWORK_NAME1,
            config.NETWORK_NAME2,
            config.NETWORK_NAME3,
            config.NETWORK_NAME4,
        ]:
            ignoreAllExceptions(
                networks.removeNetwork,
                positive=True,
                network=network,
                data_center=config.DC_NAME[0]
            )

        mla.removeUsersPermissionsFromDatacenter(
            True, config.DC_NAME[0],
            [config.USER, config.USER2, config.USER3]
        )
        mla.removeUsersPermissionsFromCluster(
            True, config.CLUSTER_NAME[0],
            [config.USER, config.USER2, config.USER3]
        )


class NegativeNetworkPermissions231915(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME, cluster=config.CLUSTER_NAME[0]
        )

    @istest
    @polarion("RHEVM3-8676")
    def createDeleteNetworkinDC(self):
        """ Create/Delete network in DC """
        msg = "User %s with %s can't add/remove network."
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.addNetwork(
            False, name=config.NETWORK_NAME2, data_center=config.DC_NAME[0]
        )
        assert networks.removeNetwork(
            False, network=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        LOGGER.info(msg, config.USER, role.ClusterAdmin)


class NegativeNetworkPermissions231916(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME, cluster=config.CLUSTER_NAME[0]
        )

    @istest
    @polarion("RHEVM3-8677")
    def editNetworkInDC(self):
        """  Edit network in DC """
        msg = "User %s with %s can't update network."
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.DC_NAME[0], mtu=1502
        )
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.DC_NAME[0], vlan_id=3
        )
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.DC_NAME[0], usages=''
        )
        assert networks.updateNetwork(
            False, network=config.NETWORK_NAME1,
            data_center=config.DC_NAME[0], usages='VM'
        )
        LOGGER.info(msg, config.USER, role.ClusterAdmin)


class NegativeNetworkPermissions231917(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1,
            data_center=config.DC_NAME[0]
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME2, data_center=config.DC_NAME[0]
        )

        for net in [config.NETWORK_NAME1, config.NETWORK_NAME2]:
            assert mla.addPermissionsForVnicProfile(
                True, config.USER_NAME, net, net,
                config.DC_NAME[0], role=role.VnicProfileUser
            )
            assert mla.addPermissionsForVnicProfile(
                True, config.USER_NAME2, net, net,
                config.DC_NAME[0], role=role.VnicProfileUser
            )
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME, config.CLUSTER_NAME[0]
        )
        assert mla.addClusterPermissionsToUser(
            True, config.USER_NAME2, config.CLUSTER_NAME[0], role.HostAdmin
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )

    @istest
    @polarion("RHEVM3-8678")
    def attachingDetachingNetworkToFromCluster(self):
        """ Attaching/Detaching network to/from Cluster """
        for user in [config.USER_NAME, config.USER_NAME2]:
            loginAsUser(userName=user, filter_=False)
            assert networks.removeNetworkFromCluster(
                False, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
            )
            assert networks.addNetworkToCluster(
                False, config.NETWORK_NAME2, config.CLUSTER_NAME[0]
            )


class NegativeNetworkPermissions231918(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], role=role.HostAdmin
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME2, data_center=config.DC_NAME[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME1,
            config.NETWORK_NAME1, config.DC_NAME[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True, config.USER_NAME, config.NETWORK_NAME2,
            config.NETWORK_NAME2, config.DC_NAME[0]
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME2, config.CLUSTER_NAME[0]
        )
        assert networks.updateClusterNetwork(
            True, config.CLUSTER_NAME[0],
            config.NETWORK_NAME1, required=True
        )
        assert networks.updateClusterNetwork(
            True, config.CLUSTER_NAME[0],
            config.NETWORK_NAME2, required=False
        )

    @istest
    @polarion("RHEVM3-8679")
    def networkRequiredToNonRequiredAndViceVersa(self):
        """ Network required to non-required and vice versa """
        loginAsUser(config.USER_NAME, filter_=False)
        assert networks.updateClusterNetwork(
            False, config.CLUSTER_NAME[0],
            config.NETWORK_NAME1, required=False
        )
        assert networks.updateClusterNetwork(
            False, config.CLUSTER_NAME[0],
            config.NETWORK_NAME1, required=True
        )


class NegativeNetworkPermissions231919(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME,
            config.DC_NAME[0], role=role.HostAdmin
        )
        assert mla.addVMPermissionsToUser(
            True, config.USER_NAME, VM_NAME, role=role.UserRole
        )
        assert vms.addNic(
            True,
            VM_NAME,
            name=NIC_NAME,
            network=config.NETWORK_NAME,
            interface='virtio'
        )

    @istest
    @polarion("RHEVM3-8680")
    def attachingVNICToVM(self):
        """ Attaching VNIC to VM """
        loginAsUser(config.USER_NAME, filter_=False)
        assert vms.addNic(
            False, VM_NAME, name=NIC_NAME2,
            network=config.NETWORK_NAME, interface='virtio'
        )
        assert vms.removeNic(False, VM_NAME, NIC_NAME)
        assert vms.updateNic(False, VM_NAME, NIC_NAME, name='newName')


class NegativeNetworkPermissions234215(NetworkingNegative):
    __test__ = True

    def setUp(self):
        assert mla.addPermissionsForDataCenter(
            True, config.USER_NAME, config.DC_NAME[0], role=role.HostAdmin
        )
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert templates.createTemplate(
            True, vm=VM_NAME, name=TEMPLATE_NAME,
            cluster=config.CLUSTER_NAME[0]
        )
        assert templates.addTemplateNic(
            True, TEMPLATE_NAME, name=NIC_NAME, network=config.NETWORK_NAME
        )

    @istest
    @polarion("RHEVM3-8682")
    def attachVNICToTemplate(self):
        """ Attach VNIC to Template """
        loginAsUser(config.USER_NAME, filter_=False)
        assert templates.addTemplateNic(
            False, TEMPLATE_NAME, name=NIC_NAME2, network=config.NETWORK_NAME
        )
        assert templates.removeTemplateNic(False, TEMPLATE_NAME, NIC_NAME)
        assert templates.updateTemplateNic(
            False, TEMPLATE_NAME, NIC_NAME, name='newName'
        )


class NegativeNetworkPermissions236686(NetworkingNegative):
    """ Attach a network to VM """
    __test__ = True

    def setUp(self):
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME2, data_center=config.DC_NAME[0]
        )
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME2, config.CLUSTER_NAME[0]
        )
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME, network=config.NETWORK_NAME2,
            interface='virtio'
        )

    @istest
    @polarion("RHEVM3-8683")
    def attachNetworkToVM(self):
        """ Attach a network to VM """
        loginAsUser(config.USER_NAME)
        self.assertRaises(
            EntityNotFound, vms.addNic, False, VM_NAME, name=NIC_NAME3,
            network=config.NETWORK_NAME1, interface='virtio'
        )
        self.assertRaises(
            EntityNotFound, vms.updateNic, False, VM_NAME,
            NIC_NAME, network=config.NETWORK_NAME1
        )


class NegativeNetworkPermissions236736(NetworkingNegative):
    """ Visible networks and manipulation """
    __test__ = True

    def setUp(self):
        assert vms.createVm(
            True, VM_NAME, '', cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert mla.addVMPermissionsToUser(True, config.USER_NAME, VM_NAME)
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME1, data_center=config.DC_NAME[0]
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME2, data_center=config.DC_NAME[0]
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME3, data_center=config.DC_NAME[0]
        )
        assert networks.addNetwork(
            True, name=config.NETWORK_NAME4, data_center=config.DC_NAME[0]
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME1, config.CLUSTER_NAME[0]
        )
        assert networks.addNetworkToCluster(
            True, config.NETWORK_NAME2, config.CLUSTER_NAME[0]
        )
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME, network=config.NETWORK_NAME1,
            interface='virtio'
        )
        assert vms.addNic(
            True, VM_NAME, name=NIC_NAME2, network=config.NETWORK_NAME2,
            interface='virtio'
        )

    @istest
    @polarion("RHEVM3-8684")
    def visibleNetworksAndManipulation(self):
        """ Visible networks and manipulation """
        loginAsUser(config.USER_NAME)
        assert vms.addNic(
            False, VM_NAME, name=NIC_NAME3, network=config.NETWORK_NAME1,
            interface='virtio'
        )
        assert vms.updateNic(
            False, VM_NAME, NIC_NAME2, network=config.NETWORK_NAME1
        )
        assert vms.removeNic(True, VM_NAME, NIC_NAME)
        self.assertRaises(
            EntityNotFound, vms.addNic, False, VM_NAME, name=NIC_NAME,
            network=config.NETWORK_NAME1, interface='virtio'
        )
        nets = [n.get_name() for n in networks.NET_API.get(absLink=False)]
        LOGGER.info("User can see networks: '%s'", nets)
        # User can see network2 and default rhevm network, because has
        # Everyone VnicProfileUser permissons, None network is not count
        # (is not shown in /api/networks) + Default DC
        if not config.GOLDEN_ENV:
            assert len(nets) == 3
        assert vms.updateNic(True, VM_NAME, NIC_NAME2, network=None)

        try:
            # CLI passes network search
            assert vms.updateNic(
                False, VM_NAME, NIC_NAME2, network=config.NETWORK_NAME2
            )
        except EntityNotFound:
            pass  # SDK/java/rest raise EntityNotFound
        except Exception as e:
            LOGGER.error(e)
            raise e
