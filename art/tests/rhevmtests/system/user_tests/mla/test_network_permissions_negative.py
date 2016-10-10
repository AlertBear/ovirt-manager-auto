"""
Testing network permissions feature. Negative cases.
1 Host, 1 SD, 1 DC, 1 cluster will be created for test.
It will cover scenarios for creating/deleting/viewing networks and vnicprofiles
if user is not permitted for it.
"""
import logging
import pytest

from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level import mla, networks, templates, vms
from art.test_handler.tools import polarion
from art.unittest_lib import attr

from rhevmtests.system.user_tests.mla import common, config

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        common.login_as_admin()
        for user_name in config.USER_NAMES[:3]:
            assert common.remove_user(True, user_name)

    request.addfinalizer(finalize)

    for user_name in config.USER_NAMES[:3]:
        assert common.add_user(
            True,
            user_name=user_name,
            domain=config.USER_DOMAIN
        )


def ignore_all_exceptions(method, **kwargs):
    """ Run method and ignore all exceptions. """
    try:
        method(**kwargs)
    except:
        pass


@attr(tier=2)
class NetworkingNegative(common.BaseTestCase):
    __test__ = False

    # Network is not supported in CLI
    apis = set(['rest', 'sdk', 'java'])

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NetworkingNegative, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            ignore_all_exceptions(
                vms.removeVm,
                positive=True,
                vm=config.VM_NAME
            )
            ignore_all_exceptions(
                templates.removeTemplate,
                positive=True,
                template=config.TEMPLATE_NAMES[0]
            )

            for network in config.NETWORK_NAMES:
                ignore_all_exceptions(
                    networks.remove_network,
                    positive=True,
                    network=network,
                    data_center=config.DC_NAME[0]
                )

            mla.removeUsersPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USERS[:3]
            )
            mla.removeUsersPermissionsFromCluster(
                True,
                config.CLUSTER_NAME[0],
                config.USERS[:3]
            )

        request.addfinalizer(finalize)


class NegativeNetworkPermissions231915(NetworkingNegative):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NegativeNetworkPermissions231915, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8676")
    def test_create_delete_network_in_datacenter(self):
        """ Create/Delete network in DC """
        msg = "User %s with %s can't add/remove network."
        common.login_as_user(filter_=False)

        for net in config.NETWORK_NAMES[:2]:
            assert networks.add_network(
                False,
                name=net,
                data_center=config.DC_NAME[0]
            )
        logger.info(msg, config.USERS[0], config.role.ClusterAdmin)


class NegativeNetworkPermissions231916(NetworkingNegative):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NegativeNetworkPermissions231916, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8677")
    def test_edit_network_in_datacenter(self):
        """  Edit network in DC """
        msg = "User %s with %s can't update network."
        common.login_as_user(filter_=False)
        assert networks.update_network(
            False,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            mtu=1502
        )
        assert networks.update_network(
            False,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            vlan_id=3
        )
        assert networks.update_network(
            False,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            usages=''
        )
        assert networks.update_network(
            False,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            usages='VM'
        )
        logger.info(msg, config.USERS[0], config.role.ClusterAdmin)


class NegativeNetworkPermissions231917(NetworkingNegative):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NegativeNetworkPermissions231917, cls).setup_class(request)

        for network_name in config.NETWORK_NAMES[:2]:
            assert networks.add_network(
                True,
                name=network_name,
                data_center=config.DC_NAME[0]
            )

            for user_name in config.USER_NAMES[:2]:
                assert mla.addPermissionsForVnicProfile(
                    True,
                    user_name,
                    network_name,
                    network_name,
                    config.DC_NAME[0],
                    role=config.role.VnicProfileUser
                )

        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[1],
            config.CLUSTER_NAME[0],
            config.role.HostAdmin
        )

        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8678")
    def test_attaching_detaching_network_to_from_cluster(self):
        """ Attaching/Detaching network to/from Cluster """
        for user_name in config.USER_NAMES[:2]:
            common.login_as_user(
                user_name=user_name,
                filter_=False
            )
            assert networks.remove_network_from_cluster(
                False,
                config.NETWORK_NAMES[0],
                config.CLUSTER_NAME[0]
            )
            assert networks.add_network_to_cluster(
                False,
                config.NETWORK_NAMES[1],
                config.CLUSTER_NAME[0]
            )


class NegativeNetworkPermissions231918(NetworkingNegative):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NegativeNetworkPermissions231918, cls).setup_class(request)

        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            role=config.role.HostAdmin
        )
        for net in config.NETWORK_NAMES[:2]:
            assert networks.add_network(
                True,
                name=net,
                data_center=config.DC_NAME[0]
            )
            assert mla.addPermissionsForVnicProfile(
                True,
                config.USER_NAMES[0],
                net,
                net,
                config.DC_NAME[0]
            )

            assert networks.add_network_to_cluster(
                True,
                net,
                config.CLUSTER_NAME[0]
            )
            assert networks.update_cluster_network(
                True,
                config.CLUSTER_NAME[0],
                net,
                required=True if net == config.NETWORK_NAMES[0] else False
            )

    @polarion("RHEVM3-8679")
    def test_network_required_to_non_required_and_vice_versa(self):
        """ Network required to non-required and vice versa """
        common.login_as_user(filter_=False)

        for req in [True, False]:
            assert networks.update_cluster_network(
                False,
                config.CLUSTER_NAME[0],
                config.NETWORK_NAMES[0],
                required=req
            )


class NegativeNetworkPermissions231919(NetworkingNegative):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NegativeNetworkPermissions231919, cls).setup_class(request)

        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            role=config.role.HostAdmin
        )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME,
            role=config.role.UserRole
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.MGMT_BRIDGE,
            interface='virtio'
        )

    @polarion("RHEVM3-8680")
    def test_attaching_vnic_to_vm(self):
        """ Attaching VNIC to VM """
        common.login_as_user(filter_=False)
        assert vms.addNic(
            False,
            config.VM_NAME,
            name=config.NIC_NAMES[1],
            network=config.MGMT_BRIDGE,
            interface='virtio'
        )
        assert vms.removeNic(
            False,
            config.VM_NAME,
            config.NIC_NAMES[0]
        )
        assert vms.updateNic(
            False,
            config.VM_NAME,
            config.NIC_NAMES[0],
            name='newName'
        )


class NegativeNetworkPermissions234215(NetworkingNegative):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NegativeNetworkPermissions234215, cls).setup_class(request)

        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            role=config.role.HostAdmin
        )
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert templates.createTemplate(
            True,
            vm=config.VM_NAME,
            name=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )
        assert templates.addTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            name=config.NIC_NAMES[0],
            network=config.MGMT_BRIDGE
        )

    @polarion("RHEVM3-8682")
    def test_attach_vnic_to_template(self):
        """ Attach VNIC to Template """
        common.login_as_user(filter_=False)
        assert templates.addTemplateNic(
            False,
            config.TEMPLATE_NAMES[0],
            name=config.NIC_NAMES[1],
            network=config.MGMT_BRIDGE
        )
        assert templates.removeTemplateNic(
            False,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0]
        )
        assert templates.updateTemplateNic(
            False,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            name='newName'
        )


class NegativeNetworkPermissions236686(NetworkingNegative):
    """ Attach a network to VM """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NegativeNetworkPermissions236686, cls).setup_class(request)

        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[1],
            data_center=config.DC_NAME[0]
        )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[1],
            config.CLUSTER_NAME[0]
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[1],
            interface='virtio'
        )

    @polarion("RHEVM3-8683")
    def test_attach_network_to_vm(self):
        """ Attach a network to VM """
        common.login_as_user()
        with pytest.raises(EntityNotFound):
            vms.addNic(
                False,
                config.VM_NAME,
                name=config.NIC_NAMES[2],
                network=config.NETWORK_NAMES[0],
                interface='virtio'
            )
        with pytest.raises(EntityNotFound):
            vms.updateNic(
                False,
                config.VM_NAME,
                config.NIC_NAMES[0],
                network=config.NETWORK_NAMES[0]
            )


class NegativeNetworkPermissions236736(NetworkingNegative):
    """ Visible networks and manipulation """
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NegativeNetworkPermissions236736, cls).setup_class(request)

        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME
        )
        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[1],
            data_center=config.DC_NAME[0]
        )
        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[2],
            data_center=config.DC_NAME[0]
        )
        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[3],
            data_center=config.DC_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[1],
            config.CLUSTER_NAME[0]
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[1],
            network=config.NETWORK_NAMES[1],
            interface='virtio'
        )

    @polarion("RHEVM3-8684")
    def test_visible_networks_and_manipulation(self):
        """ Visible networks and manipulation """
        common.login_as_user()
        assert vms.addNic(
            False,
            config.VM_NAME,
            name=config.NIC_NAMES[2],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )
        assert vms.updateNic(
            False,
            config.VM_NAME,
            config.NIC_NAMES[1],
            network=config.NETWORK_NAMES[0]
        )
        assert vms.removeNic(True, config.VM_NAME, config.NIC_NAMES[0])
        with pytest.raises(EntityNotFound):
            vms.addNic(
                False,
                config.VM_NAME,
                name=config.NIC_NAMES[0],
                network=config.NETWORK_NAMES[0],
                interface='virtio'
            )
        nets = [n.get_name() for n in networks.NET_API.get(absLink=False)]
        logger.info("User can see networks: '%s'", nets)
        # User can see network2 and default rhevm network, because has
        # Everyone VnicProfileUser permissons, None network is not count
        # (is not shown in /api/networks) + Default DC
        if not config.GOLDEN_ENV:
            assert len(nets) == 3
        assert vms.updateNic(
            True,
            config.VM_NAME,
            config.NIC_NAMES[1],
            network=None
        )

        try:
            # CLI passes network search
            assert vms.updateNic(
                False,
                config.VM_NAME,
                config.NIC_NAMES[1],
                network=config.NETWORK_NAMES[1]
            )
        except EntityNotFound:
            pass  # SDK/java/rest raise EntityNotFound
        except Exception as e:
            logger.error(e)
            raise e
