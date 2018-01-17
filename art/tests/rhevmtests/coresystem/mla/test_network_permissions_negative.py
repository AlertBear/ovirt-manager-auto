"""
Testing network permissions feature. Negative cases.
1 Host, 1 SD, 1 DC, 1 cluster will be created for test.
It will cover scenarios for creating/deleting/viewing networks and vnicprofiles
if user is not permitted for it.
"""
import logging
import pytest

from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level import (
    mla, networks, templates, vms, users, clusters
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import testflow

import common
import config

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Log in as admin.")
        common.login_as_admin()

        for user_name in config.USER_NAMES[:3]:
            testflow.teardown(
                "Removing user %s@%s.", user_name, config.USER_DOMAIN
            )
            assert users.removeUser(True, user_name)

    request.addfinalizer(finalize)

    for user_name in config.USER_NAMES[:3]:
        testflow.setup("Adding user %s@%s.", user_name, config.USER_DOMAIN)
        assert common.add_user(
            True,
            user_name=user_name,
            domain=config.USER_DOMAIN
        )


def ignore_all_exceptions(method, **kwargs):
    """ Run method and ignore all exceptions. """
    try:
        method(**kwargs)
    except Exception as err:
        logger.warning(err)


@tier2
class NetworkingNegative(common.BaseTestCase):
    # Network is not supported in CLI

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NetworkingNegative, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Remove VM %s.", config.VM_NAME)
            ignore_all_exceptions(
                vms.removeVm,
                positive=True,
                vm=config.VM_NAME
            )

            testflow.teardown("Remove template %s.", config.TEMPLATE_NAMES[0])
            ignore_all_exceptions(
                templates.remove_template,
                positive=True,
                template=config.TEMPLATE_NAMES[0]
            )

            for network in config.NETWORK_NAMES:
                testflow.teardown(
                    "Removing network %s from datacenter %s.",
                    network, config.DC_NAME[0]
                )
                ignore_all_exceptions(
                    networks.remove_network,
                    positive=True,
                    network=network,
                    data_center=config.DC_NAME[0]
                )

            testflow.teardown(
                "Removing all users permissions from datacenter %s.",
                config.DC_NAME[0]
            )
            mla.removeUsersPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USERS[:3]
            )

            testflow.teardown(
                "Removing all users permissions from cluster %s.",
                config.CLUSTER_NAME[0]
            )
            mla.removeUsersPermissionsFromCluster(
                True,
                config.CLUSTER_NAME[0],
                config.USERS[:3]
            )

        request.addfinalizer(finalize)


class TestNegativeNetworkPermissions231915(NetworkingNegative):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNegativeNetworkPermissions231915, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.setup(
            "Adding cluster %s permissions to user %s@%s.",
            config.CLUSTER_NAME[0], config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8676")
    def test_create_delete_network_in_datacenter(self):
        """ Create/Delete network in DC """
        testflow.step("Log in as user.")
        common.login_as_user()

        for net in config.NETWORK_NAMES[:2]:
            assert networks.add_network(
                False,
                name=net,
                data_center=config.DC_NAME[0]
            )


class TestNegativeNetworkPermissions231916(NetworkingNegative):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNegativeNetworkPermissions231916, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.setup(
            "Adding cluster %s permissions to user %s@%s.",
            config.CLUSTER_NAME[0], config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8677")
    def test_edit_network_in_datacenter(self):
        """  Edit network in DC """
        MTU = 1502
        VLAN_ID = 3
        USAGES = ["", "VM"]

        testflow.step("Log in as user.")
        common.login_as_user(filter_=False)

        assert networks.update_network(
            False,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            mtu=MTU
        )

        assert networks.update_network(
            False,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            vlan_id=VLAN_ID
        )

        for usages in USAGES:
            assert networks.update_network(
                False,
                network=config.NETWORK_NAMES[0],
                data_center=config.DC_NAME[0],
                usages=usages
            )


class TestNegativeNetworkPermissions231917(NetworkingNegative):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNegativeNetworkPermissions231917, cls).setup_class(request)

        for network_name in config.NETWORK_NAMES[:2]:
            assert networks.add_network(
                True,
                name=network_name,
                data_center=config.DC_NAME[0]
            )

            for user_name in config.USER_NAMES[:2]:
                testflow.setup(
                    "Adding role %s permissions for "
                    "vnic profile %s of network %s "
                    "to user %s in datacenter %s.",
                    config.role.VnicProfileUser, network_name, network_name,
                    user_name, config.DC_NAME[0]
                )
                assert mla.addPermissionsForVnicProfile(
                    True,
                    user_name,
                    network_name,
                    network_name,
                    config.DC_NAME[0],
                    role=config.role.VnicProfileUser
                )

        testflow.setup(
            "Adding cluster %s permissions to user %s@%s.",
            config.CLUSTER_NAME[0], config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0]
        )

        testflow.setup(
            "Adding cluster %s permissions to user %s@%s.",
            config.CLUSTER_NAME[0], config.USER_NAMES[1], config.USER_DOMAIN
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[1],
            config.CLUSTER_NAME[0],
            config.role.HostAdmin
        )

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8678")
    def test_attaching_detaching_network_to_from_cluster(self):
        """ Attaching/Detaching network to/from Cluster """
        cluster_obj = clusters.get_cluster_object(
            cluster_name=config.CLUSTER_NAME[0]
        )
        for user_name in config.USER_NAMES[:2]:
            testflow.step(
                "Log in as user %s@%s.", user_name, config.USER_DOMAIN
            )
            common.login_as_user(user_name=user_name)

            testflow.step(
                "Removing network %s from cluster %s.",
                config.NETWORK_NAMES[0],
                config.CLUSTER_NAME[0]
            )
            assert networks.remove_network_from_cluster(
                False,
                config.NETWORK_NAMES[0],
                cluster_obj
            )

            testflow.step(
                "Adding network %s to cluster %s.",
                config.NETWORK_NAMES[1],
                config.CLUSTER_NAME[0]
            )
            assert networks.add_network_to_cluster(
                False,
                config.NETWORK_NAMES[1],
                config.CLUSTER_NAME[0]
            )


class TestNegativeNetworkPermissions231918(NetworkingNegative):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNegativeNetworkPermissions231918, cls).setup_class(request)

        testflow.setup(
            "Adding datacenter %s permission for user %s@%s.",
            config.DC_NAME[0], config.USER_NAMES[0], config.USER_DOMAIN
        )
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

            testflow.setup(
                "Adding permissions for "
                "vnic profile %s of network %s "
                "to user %s in datacenter %s.",
                net, net,
                config.USER_NAMES[0], config.DC_NAME[0]
            )
            assert mla.addPermissionsForVnicProfile(
                True,
                config.USER_NAMES[0],
                net,
                net,
                config.DC_NAME[0]
            )

            testflow.setup(
                "Adding network %s to cluster %s.",
                net, config.CLUSTER_NAME[0]
            )
            assert networks.add_network_to_cluster(
                True,
                net,
                config.CLUSTER_NAME[0]
            )

            testflow.setup(
                "Updating cluster %s network %s.",
                config.CLUSTER_NAME[0], net
            )
            assert networks.update_cluster_network(
                True,
                clusters.get_cluster_object(
                    cluster_name=config.CLUSTER_NAME[0]
                ),
                net,
                required=True if net == config.NETWORK_NAMES[0] else False
            )

    @polarion("RHEVM3-8679")
    def test_network_required_to_non_required_and_vice_versa(self):
        """ Network required to non-required and vice versa """
        common.login_as_user(filter_=False)

        for req in [True, False]:
            testflow.step(
                "Updating cluster %s network %s.",
                config.CLUSTER_NAME[0],
                config.NETWORK_NAMES[0]
            )
            assert networks.update_cluster_network(
                False,
                clusters.get_cluster_object(
                    cluster_name=config.CLUSTER_NAME[0]
                ),
                config.NETWORK_NAMES[0],
                required=req
            )


class TestNegativeNetworkPermissions231919(NetworkingNegative):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNegativeNetworkPermissions231919, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        testflow.setup(
            "Adding permissions for datacenter %s to user %s@%s.",
            config.DC_NAME[0], config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            role=config.role.HostAdmin
        )

        testflow.setup(
            "Adding VM %s permission role %s to user %s@%s.",
            config.VM_NAME, config.role.UserRole,
            config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME,
            role=config.role.UserRole
        )

        testflow.setup(
            "Adding Nic %s to VM %s.", config.NIC_NAMES[0], config.VM_NAME
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
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step(
            "Adding Nic %s to VM %s.", config.NIC_NAMES[1], config.VM_NAME
        )
        assert vms.addNic(
            False,
            config.VM_NAME,
            name=config.NIC_NAMES[1],
            network=config.MGMT_BRIDGE,
            interface='virtio'
        )

        testflow.step(
            "Removing Nic %s from VM %s.", config.NIC_NAMES[0], config.VM_NAME
        )
        assert vms.removeNic(
            False,
            config.VM_NAME,
            config.NIC_NAMES[0]
        )

        testflow.step(
            "Updating Nic %s from VM %s.", config.NIC_NAMES[0], config.VM_NAME
        )
        assert vms.updateNic(
            False,
            config.VM_NAME,
            config.NIC_NAMES[0],
            name='newName'
        )


class TestNegativeNetworkPermissions234215(NetworkingNegative):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNegativeNetworkPermissions234215, cls).setup_class(request)

        testflow.setup(
            "Adding permissions for datacenter %s to user %s@%s.",
            config.DC_NAME[0], config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            role=config.role.HostAdmin
        )

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        testflow.setup("Creating template %s.", config.TEMPLATE_NAMES[0])
        assert templates.createTemplate(
            True,
            vm=config.VM_NAME,
            name=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

        testflow.setup("Adding nic %s to template.", config.NIC_NAMES[0])
        assert templates.addTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            name=config.NIC_NAMES[0],
            network=config.MGMT_BRIDGE
        )

    @polarion("RHEVM3-8682")
    def test_attach_vnic_to_template(self):
        """ Attach VNIC to Template """
        testflow.step("Log in as user.")
        common.login_as_user(filter_=False)

        testflow.step(
            "Adding nic %s to template %s.",
            config.NIC_NAMES[1], config.TEMPLATE_NAMES[0]
        )
        assert templates.addTemplateNic(
            False,
            config.TEMPLATE_NAMES[0],
            name=config.NIC_NAMES[1],
            network=config.MGMT_BRIDGE
        )

        testflow.step(
            "Removing nic %s from template %s.",
            config.NIC_NAMES[0], config.TEMPLATE_NAMES[0]
        )
        assert templates.removeTemplateNic(
            False,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0]
        )

        testflow.step(
            "Updating nic %s on template %s.",
            config.NIC_NAMES[0], config.TEMPLATE_NAMES[0]
        )
        assert templates.updateTemplateNic(
            False,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            name='newName'
        )


class TestNegativeNetworkPermissions236686(NetworkingNegative):
    """ Attach a network to VM """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNegativeNetworkPermissions236686, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NAME)
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

        testflow.setup(
            "Adding VM %s permissions to user %s@%s.",
            config.VM_NAME, config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME
        )

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[1],
            config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[1],
            config.CLUSTER_NAME[0]
        )

        testflow.setup(
            "Adding nic %s to VM %s.", config.NIC_NAMES[0], config.VM_NAME
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
        testflow.step("Log in as user.")
        common.login_as_user()

        with pytest.raises(EntityNotFound):
            testflow.step(
                "Adding nic %s to VM %s.", config.NIC_NAMES[2], config.VM_NAME
            )
            vms.addNic(
                False,
                config.VM_NAME,
                name=config.NIC_NAMES[2],
                network=config.NETWORK_NAMES[0],
                interface='virtio'
            )

        with pytest.raises(EntityNotFound):
            testflow.step(
                "Updating nic %s on VM %s.",
                config.NIC_NAMES[0], config.VM_NAME
            )
            vms.updateNic(
                False,
                config.VM_NAME,
                config.NIC_NAMES[0],
                network=config.NETWORK_NAMES[0]
            )


class TestNegativeNetworkPermissions236736(NetworkingNegative):
    """ Visible networks and manipulation """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestNegativeNetworkPermissions236736, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        testflow.setup(
            "Adding VM %s permissions to user %s@%s.",
            config.VM_NAME, config.USER_NAMES[0], config.USER_DOMAIN
        )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME
        )

        for network in config.NETWORK_NAMES:
            assert networks.add_network(
                True,
                name=network,
                data_center=config.DC_NAME[0]
            )

        for network in config.NETWORK_NAMES[:2]:
            testflow.setup(
                "Adding network %s to cluster %s.",
                network, config.CLUSTER_NAME[0]
            )
            assert networks.add_network_to_cluster(
                True, network,
                config.CLUSTER_NAME[0]
            )

        testflow.setup(
            "Adding vnic %s to network %s.",
            config.NIC_NAMES[0],
            config.NETWORK_NAMES[0]
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )

        testflow.setup(
            "Adding vnic %s to network %s.",
            config.NIC_NAMES[1],
            config.NETWORK_NAMES[1]
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
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step(
            "Adding nic %s to VM %s.", config.NIC_NAMES[2], config.VM_NAME
        )
        assert vms.addNic(
            False,
            config.VM_NAME,
            name=config.NIC_NAMES[2],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )

        testflow.step(
            "Updating nic %s on VM %s.", config.NIC_NAMES[1], config.VM_NAME
        )
        assert vms.updateNic(
            False,
            config.VM_NAME,
            config.NIC_NAMES[1],
            network=config.NETWORK_NAMES[0]
        )

        testflow.step(
            "Removing nic %s from VM %s.", config.NIC_NAMES[0], config.VM_NAME
        )
        assert vms.removeNic(True, config.VM_NAME, config.NIC_NAMES[0])

        with pytest.raises(EntityNotFound):
            testflow.step(
                "Adding nic %s to VM %s.", config.NIC_NAMES[0], config.VM_NAME
            )
            vms.addNic(
                False,
                config.VM_NAME,
                name=config.NIC_NAMES[0],
                network=config.NETWORK_NAMES[0],
                interface='virtio'
            )

        testflow.step(
            "Updating nic %s on VM %s.", config.NIC_NAMES[1], config.VM_NAME
        )
        assert vms.updateNic(
            True,
            config.VM_NAME,
            config.NIC_NAMES[1],
            network=None
        )

        try:
            # CLI passes network search
            testflow.step(
                "Updating nic %s on VM %s.",
                config.NIC_NAMES[1], config.VM_NAME
            )
            assert vms.updateNic(
                False,
                config.VM_NAME,
                config.NIC_NAMES[1],
                network=config.NETWORK_NAMES[1]
            )
        except EntityNotFound as err:
            # SDK/java/rest raise EntityNotFound
            logger.warning(err)
        except Exception as err:
            logger.error(err)
            raise err
