"""
Testing network permissions feature. Positive cases.
1 Host, 1 SD, 1 DC, 1 cluster will be created for test.
It will cover scenarios for creating/deleting/viewing networks and vnicprofiles
if user is permitted for it.
"""
import logging
import pytest

from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level import (
    datacenters, mla, networks, templates, users, vms, clusters
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib import testflow

import common
import config

from test_network_permissions_negative import (
    NetworkingNegative, ignore_all_exceptions
)

ROLE_NAME = '_NetworkCreator'
EVERYONE = 'Everyone'

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Log in as admin.")
        common.login_as_admin()

        for user in config.USER_NAMES:
            testflow.teardown("Removing user %s@%s.", user, config.USER_DOMAIN)
            assert users.removeUser(True, user)

    request.addfinalizer(finalize)

    for user in config.USER_NAMES:
        testflow.setup("Adding user %s@%s.", user, config.USER_DOMAIN)
        assert common.add_user(
            True,
            user_name=user,
            domain=config.USER_DOMAIN
        )


@tier2
class NetworkingPositive(NetworkingNegative):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NetworkingPositive, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown("Removing role %s.", ROLE_NAME)
            ignore_all_exceptions(
                mla.removeRole,
                positive=True,
                role=ROLE_NAME
            )

        request.addfinalizer(finalize)


class TestPositiveNetworkPermissions231821(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions231821, cls).setup_class(request)

        testflow.setup(
            "Adding permission role %s for datacenter %s to user %s.",
            config.role.SuperUser,
            config.DC_NAME[0],
            config.USER_NAMES[0]
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            role=config.role.SuperUser
        )

        testflow.setup(
            "Adding permission role %s for datacenter %s to user %s.",
            config.role.DataCenterAdmin,
            config.DC_NAME[0],
            config.USER_NAMES[1]
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[1],
            config.DC_NAME[0],
            role=config.role.DataCenterAdmin
        )

        testflow.setup(
            "Adding permission role %s for datacenter %s to user %s.",
            config.role.NetworkAdmin,
            config.DC_NAME[0],
            config.USER_NAMES[2]
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[2],
            config.DC_NAME[0],
            role=config.role.NetworkAdmin
        )

    @polarion("RHEVM3-8369")
    def test_create_network_in_datacenter(self):
        """ Create network in datacenter """
        for user_name in config.USER_NAMES:
            testflow.step("Log in as user.")
            common.login_as_user(user_name=user_name, filter_=False)

            assert networks.add_network(
                True,
                name=config.NETWORK_NAMES[0],
                data_center=config.DC_NAME[0]
            )

            testflow.step("Log in as admin.")
            common.login_as_admin()

            testflow.step(
                "Removing network %s from datacenter %s.",
                config.NETWORK_NAMES[0], config.DC_NAME[0]
            )
            assert networks.remove_network(
                True,
                network=config.NETWORK_NAMES[0],
                data_center=config.DC_NAME[0]
            )


class TestPositiveNetworkPermissions231822(NetworkingPositive):
    MTU = 800
    STP = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions231822, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.setup(
            "Adding permission role %s for "
            "network %s in datacenter %s to user %s.",
            config.role.DataCenterAdmin, config.NETWORK_NAMES[0],
            config.DC_NAME[0], config.USER_NAMES[0]
        )
        assert mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.DataCenterAdmin
        )

        testflow.setup(
            "Adding permission role %s for "
            "network %s in datacenter %s to user %s.",
            config.role.NetworkAdmin, config.NETWORK_NAMES[0],
            config.DC_NAME[0], config.USER_NAMES[1]
        )
        assert mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[1],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.NetworkAdmin
        )

    @polarion("RHEVM3-8384")
    def test_edit_network_in_datacenter(self):
        """ Edit network in DC """
        for user_name in config.USER_NAMES[:2]:
            testflow.step(
                "Log in as user %s@%s.", user_name, config.USER_DOMAIN
            )
            common.login_as_user(user_name=user_name, filter_=False)

            assert networks.update_network(
                True,
                config.NETWORK_NAMES[0],
                data_center=config.DC_NAME[0],
                mtu=self.MTU,
                stp=str(self.STP).lower()
            )
            self.MTU += 100
            self.STP = not self.STP


class TestPositiveNetworkPermissions231823(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions231823, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.setup(
            "Adding permission role %s for network %s to user %s.",
            config.role.NetworkAdmin,
            config.NETWORK_NAMES[0],
            config.USER_NAMES[0]
        )
        assert mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.NetworkAdmin
        )

        for username in config.USER_NAMES[:2]:
            testflow.setup(
                "Adding cluster %s permissions for user %s.",
                config.CLUSTER_NAME[0], username
            )
            assert mla.addClusterPermissionsToUser(
                True,
                username,
                cluster=config.CLUSTER_NAME[0]
            )

    @polarion("RHEVM3-8383")
    def test_attaching_network_to_cluster(self):
        """ Attaching network to cluster """
        cluster_obj = clusters.get_cluster_object(
            cluster_name=config.CLUSTER_NAME[0]
        )
        testflow.step("Log in as user.")
        common.login_as_user(filter_=False)

        testflow.step(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

        testflow.step(
            "Removing network %s from cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        assert networks.remove_network_from_cluster(
            True,
            config.NETWORK_NAMES[0],
            cluster_obj
        )

        testflow.step(
            "Log in as user %s@%s.", config.USER_NAMES[1], config.USER_DOMAIN
        )
        common.login_as_user(user_name=config.USER_NAMES[1])

        testflow.step(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        with pytest.raises(EntityNotFound):
            networks.add_network_to_cluster(
                False,
                config.NETWORK_NAMES[0],
                config.CLUSTER_NAME[0]
            )


class TestSwitching(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestSwitching, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.setup(
            "Adding cluster %s permissions to user %s.",
            config.CLUSTER_NAME[0], config.USER_NAMES[0]
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

        testflow.setup(
            "Adding permissions for network %s to user %s.",
            config.NETWORK_NAMES[0], config.USER_NAMES[1]
        )
        assert mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[1],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.NetworkAdmin
        )

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

    @staticmethod
    def _inverse_params(kwargs):
        """ inverse required or/and display param if exists """
        if 'required' in kwargs:
            kwargs['required'] = not kwargs['required']
        if 'display' in kwargs:
            kwargs['display'] = not kwargs['display']
        if 'usages' in kwargs:
            kwargs['usages'] = (
                'vm' if kwargs['usages'] == 'display' else 'display')

    def _test_switching_display_and_required(self, **kwargs):
        cluster_obj = clusters.get_cluster_object(
            cluster_name=config.CLUSTER_NAME[0]
        )
        testflow.step(
            "Update network %s in cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        assert networks.update_cluster_network(
            True,
            cluster_obj,
            config.NETWORK_NAMES[0],
            **kwargs
        )
        for user_name in config.USER_NAMES[:2]:
            testflow.step(
                "Log in as user %s@%s.", user_name, config.USER_DOMAIN
            )
            common.login_as_user(user_name=user_name, filter_=False)

            testflow.step("Inverting params.")
            self._inverse_params(kwargs)

            testflow.step(
                "Updating network %s in cluster %s.",
                config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
            )
            assert networks.update_cluster_network(
                True,
                cluster_obj,
                config.NETWORK_NAMES[0],
                **kwargs
            )

            testflow.step("Inverting params.")
            self._inverse_params(kwargs)

            testflow.step(
                "Updating network %s in cluster %s.",
                config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
            )
            assert networks.update_cluster_network(
                True,
                cluster_obj,
                config.NETWORK_NAMES[0],
                **kwargs
            )


class TestPositiveNetworkPermissions231824(TestSwitching):
    @polarion("RHEVM3-8382")
    def test_required_to_non_required_and_vice_versa(self):
        """ Required to non-required and vice versa """
        self._test_switching_display_and_required(required=True)


class TestPositiveNetworkPermissions236073(TestSwitching):
    @polarion("RHEVM3-8377")
    def test_display_network(self):
        """ Display network """
        self._test_switching_display_and_required(
            display=True,
            usages='display'
        )


class TestPositiveNetworkPermissions231826(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions231826, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        testflow.setup(
            "Adding VM %s permissions to user %s.",
            config.VM_NAME, config.USER_NAMES[0]
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

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

        testflow.setup(
            "Adding permission role %s to "
            "vnic profile %s in network %s to user %s.",
            config.role.VnicProfileUser,
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.USER_NAMES[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )

    @polarion("RHEVM3-8381")
    def test_attach_detach_network_to_vm(self):
        """ Attach/Detach a network to VM  """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step(
            "Adding nic %s to network %s and VM %s.",
            config.NIC_NAMES[0],
            config.NETWORK_NAMES[0],
            config.VM_NAME
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )

        testflow.step(
            "Removing nic %s from %s.", config.NIC_NAMES[0], config.VM_NAME
        )
        assert vms.removeNic(True, config.VM_NAME, config.NIC_NAMES[0])


class TestPositiveNetworkPermissions231827(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions231827, cls).setup_class(request)

        # Not possible to create public vnicprofile, just add Everyone perms
        for net in config.NETWORK_NAMES:
            assert networks.add_network(
                True,
                name=net,
                data_center=config.DC_NAME[0]
            )

            testflow.setup(
                "Add vnic profile %s in network %s "
                "in datacenter %s permissions to group %s.",
                net, net,
                config.DC_NAME[0], EVERYONE
            )
            assert mla.addVnicProfilePermissionsToGroup(
                True,
                EVERYONE,
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

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        testflow.setup(
            "Adding VM %s permissions to user %s.",
            config.VM_NAME, config.USER_NAMES[0]
        )
        assert mla.addVMPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.VM_NAME
        )

        testflow.setup(
            "Adding nic %s to VM %s with network %s.",
            config.NIC_NAMES[0],
            config.VM_NAME,
            config.NETWORK_NAMES[0]
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )

    @polarion("RHEVM3-8380")
    def test_visible_networks_and_manipulations(self):
        """ Visible networks and manipulations """
        testflow.step("Log in as user.")
        common.login_as_user()

        for net in config.NETWORK_NAMES:
            testflow.step(
                "Adding nic %s to VM %s with network %s.",
                net, config.VM_NAME, net
            )
            assert vms.addNic(
                True,
                config.VM_NAME,
                name=net,
                network=net,
                interface='virtio'
            )

            testflow.step("Updating nic %s on VM %s.", net, config.VM_NAME)
            assert vms.updateNic(
                True,
                config.VM_NAME,
                net,
                name="{0}-x".format(net)
            )

        testflow.step("Getting networks names.")
        nets = [n.get_name() for n in networks.NET_API.get(abs_link=False)]

        testflow.step("User can see networks: %s", nets)

        testflow.step(
            "Removing nic %s from VM %s.",
            config.NIC_NAMES[0], config.VM_NAME
        )
        assert vms.removeNic(True, config.VM_NAME, config.NIC_NAMES[0])


class TestPositiveNetworkPermissions231830(NetworkingPositive):

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions231830, cls).setup_class(request)

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

        for net in config.NETWORK_NAMES[:2]:
            testflow.setup(
                "Adding network %s to cluster %s.", net, config.CLUSTER_NAME[0]
            )
            assert networks.add_network_to_cluster(
                True,
                net,
                config.CLUSTER_NAME[0]
            )

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )

        testflow.setup(
            "Adding nic %s with network %s to VM %s.",
            config.NETWORK_NAMES[0],
            config.NIC_NAMES[0],
            config.VM_NAME
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )

        testflow.setup(
            "Creating template %s from VM %s.",
            config.TEMPLATE_NAMES[0], config.VM_NAME
        )
        assert templates.createTemplate(
            True,
            vm=config.VM_NAME,
            name=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

    @staticmethod
    def can_see(net1, net2, vnic1, vnic2):
        for net in [net1, net2, vnic1, vnic2]:
            if net['filt']:
                assert net['func'](net['name']) is not None
            else:
                with pytest.raises(EntityNotFound):
                    net['func'](net['name'])

    @staticmethod
    def filter_net(name, filt, func):
        return {'name': name, 'filt': filt, 'func': func}

    def _test_wrap(self, p1, p2, p3, p4, filter_=True):
        """ wrap assert """
        net1 = config.NETWORK_NAMES[0]
        net2 = config.NETWORK_NAMES[1]

        testflow.step("Log in as user.")
        common.login_as_user(filter_=filter_)

        testflow.step("Checking if user can see networks.")
        self.can_see(
            self.filter_net(net1, p1, networks.find_network),
            self.filter_net(net2, p2, networks.find_network),
            self.filter_net(net1, p3, networks.VNIC_PROFILE_API.find),
            self.filter_net(net2, p4, networks.VNIC_PROFILE_API.find)
        )

        testflow.step("Log in as admin.")
        common.login_as_admin()

    def _test_permissions_on_vnic_profile(self):
        testflow.step(
            "Adding role %s permissions for vnic profile %s to user %s.",
            config.role.VnicProfileUser,
            config.NETWORK_NAMES[0],
            config.USER_NAMES[0]
        )
        mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )

        self._test_wrap(True, False, True, False)

        testflow.step(
            "Removing user %s permissions from vnic profile %s.",
            config.USERS[0], config.NETWORK_NAMES[0]
        )
        mla.removeUserPermissionsFromVnicProfile(
            True,
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            config.USERS[0]
        )

    def _test_permissions_on_vm(self):
        testflow.step(
            "Adding VM %s permissions to user %s.",
            config.VM_NAME, config.USER_NAMES[0]
        )
        mla.addVMPermissionsToUser(True, config.USER_NAMES[0], config.VM_NAME)

        self._test_wrap(True, False, True, False)

        testflow.step(
            "Removing user %s permissions from VM %s.",
            config.USERS[0], config.VM_NAME
        )
        mla.removeUserPermissionsFromVm(True, config.VM_NAME, config.USERS[0])

    def _test_permissions_on_template(self):
        testflow.step(
            "Adding permissions for template %s to user %s.",
            config.TEMPLATE_NAMES[0], config.USER_NAMES[0]
        )
        mla.addPermissionsForTemplate(
            True,
            config.USER_NAMES[0],
            config.TEMPLATE_NAMES[0]
        )

        self._test_wrap(True, False, True, False)

        testflow.step(
            "Removing user %s permissions from template %s.",
            config.USERS[0], config.TEMPLATE_NAMES[0]
        )
        mla.removeUserPermissionsFromTemplate(
            True,
            config.TEMPLATE_NAMES[0],
            config.USERS[0]
        )

    def _test_permissions_on_datacenter(self):
        testflow.step(
            "Adding permissions for datacenter %s to user %s.",
            config.DC_NAME[0], config.USER_NAMES[0]
        )
        mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0]
        )

        self._test_wrap(True, True, True, True, False)

        testflow.step(
            "Removing user %s permissions from datacenter %s.",
            config.USERS[0], config.DC_NAME[0]
        )
        mla.removeUserPermissionsFromDatacenter(
            True,
            config.DC_NAME[0],
            config.USERS[0]
        )

    def _test_permissions_on_cluster(self):
        testflow.step(
            "Adding cluster %s permissions to user %s.",
            config.CLUSTER_NAME[0], config.USER_NAMES[0]
        )
        mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0]
        )

        self._test_wrap(True, True, True, True, False)

        testflow.step(
            "Removing user %s permissions from cluster %s.",
            config.USERS[0], config.CLUSTER_NAME[0]
        )
        mla.removeUserPermissionsFromCluster(
            True,
            config.CLUSTER_NAME[0],
            config.USERS[0]
        )

    def _test_permissions_on_system(self):
        testflow.step(
            "Adding role %s to user %s.",
            config.role.UserRole, config.USER_NAMES[0]
        )
        users.addRoleToUser(
            True,
            config.USER_NAMES[0],
            config.role.UserRole
        )

        self._test_wrap(True, True, True, True)

        testflow.step(
            "Removing user %s@%s.", config.USER_NAMES[0], config.USER_DOMAIN
        )
        users.removeUser(True, config.USER_NAMES[0])

        testflow.step(
            "Adding user %s@%s.", config.USER_NAMES[0], config.USER_DOMAIN
        )
        common.add_user(
            True,
            user_name=config.USER_NAMES[0],
            domain=config.USER_DOMAIN
        )

    def _test_permissions_on_network(self):
        testflow.step(
            "Adding role %s permissions for network %s to user %s.",
            config.role.VnicProfileUser,
            config.NETWORK_NAMES[0],
            config.USER_NAMES[0]
        )
        mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            config.role.VnicProfileUser
        )

        self._test_wrap(True, False, True, False)

        testflow.step(
            "Removing user %s permissions from network %s.",
            config.USERS[0], config.NETWORK_NAMES[0]
        )
        mla.removeUserPermissionsFromNetwork(
            True,
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            config.USERS[0]
        )

    @polarion("RHEVM3-8379")
    def test_network_visibility_in_api(self):
        """ Network visibility in RestAPI """
        self._test_permissions_on_vnic_profile()
        self._test_permissions_on_vm()
        self._test_permissions_on_template()
        self._test_permissions_on_datacenter()
        self._test_permissions_on_cluster()
        self._test_permissions_on_network()
        self._test_permissions_on_system()


class TestPositiveNetworkPermissions231832(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions231832, cls).setup_class(request)

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
            "Updating vnic profile %s.", config.NETWORK_NAMES[0]
        )
        assert networks.update_vnic_profile(
            name=config.NETWORK_NAMES[0],
            network=config.NETWORK_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            port_mirroring=True
        )

        for user_name, user_role in zip(
                config.USER_NAMES[:2],
                [
                    config.role.NetworkAdmin,
                    config.role.VnicProfileUser
                ]
        ):
            for vnic_profile in config.NETWORK_NAMES[:2]:
                testflow.setup(
                    "Adding role %s permissions for vnic %s to user %s.",
                    user_role, vnic_profile, user_name
                )
                assert mla.addPermissionsForVnicProfile(
                    positive=True,
                    user=user_name,
                    vnicprofile=vnic_profile,
                    network=vnic_profile,
                    data_center=config.DC_NAME[0],
                    role=user_role
                )

        testflow.setup(
            "Adding role %s permissions for datacenter %s to user %s.",
            config.role.UserRole, config.DC_NAME[0], config.USER_NAMES[1]
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[1],
            config.DC_NAME[0],
            config.role.UserRole
        )

        for net in config.NETWORK_NAMES[:2]:
            testflow.setup(
                "Adding network %s to cluster %s.",
                net, config.CLUSTER_NAME[0]
            )
            assert networks.add_network_to_cluster(
                True,
                net,
                config.CLUSTER_NAME[0]
            )

    @polarion("RHEVM3-8378")
    def test_port_mirroring(self):
        """ Port mirroring """
        testflow.step("Log in as user %s.", config.USER_NAMES[1])
        common.login_as_user(user_name=config.USER_NAMES[1])

        testflow.step(
            "Updating vnic profile %s port mirroring.", config.NETWORK_NAMES[0]
        )
        assert not networks.update_vnic_profile(
            name=config.NETWORK_NAMES[0],
            network=config.NETWORK_NAMES[0],
            port_mirroring=False,
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0]
        )

        testflow.step(
            "Updating vnic profile %s port mirroring.", config.NETWORK_NAMES[1]
        )
        assert not networks.update_vnic_profile(
            name=config.NETWORK_NAMES[1],
            network=config.NETWORK_NAMES[1],
            port_mirroring=True,
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0]
        )

        testflow.step("Log in as user.")
        common.login_as_user(filter_=False)

        testflow.step(
            "Updating vnic profile %s port mirroring.", config.NETWORK_NAMES[0]
        )
        assert networks.update_vnic_profile(
            name=config.NETWORK_NAMES[0],
            network=config.NETWORK_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            port_mirroring=False
        )

        testflow.step(
            "Updating vnic profile %s port mirroring.", config.NETWORK_NAMES[1]
        )
        assert networks.update_vnic_profile(
            name=config.NETWORK_NAMES[1],
            network=config.NETWORK_NAMES[1],
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            port_mirroring=True
        )


class TestPositiveNetworkPermissions236367(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions236367, cls).setup_class(request)

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

        testflow.setup(
            "Adding role %s permissions for vnic %s to user %s.",
            config.role.VnicProfileUser,
            config.NETWORK_NAMES[0],
            config.USER_NAMES[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )

        for user_name in config.USER_NAMES[:2]:
            testflow.setup(
                "Adding VM %s permissions to user %s.",
                config.VM_NAME, user_name
            )
            assert mla.addVMPermissionsToUser(
                True,
                user_name,
                config.VM_NAME
            )

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8376")
    def test_add_vnic_to_vm(self):
        """ Add a VNIC to VM  """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step(
            "Adding nic %s to VM %s.",
            config.NIC_NAMES[0], config.VM_NAME
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=None,
            interface='virtio'
        )

        testflow.step(
            "Adding nic %s with network %s to VM %s.",
            config.NIC_NAMES[0], config.NETWORK_NAMES[0], config.VM_NAME
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[1],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )

        testflow.step(
            "Log in as user %s@%s.", config.USER_NAMES[1], config.USER_DOMAIN
        )
        common.login_as_user(user_name=config.USER_NAMES[1])

        testflow.step(
            "Adding nic %s to VM %s.",
            config.NIC_NAMES[0], config.VM_NAME
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[2],
            network=None,
            interface='virtio'
        )


class TestPositiveNetworkPermissions236406(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions236406, cls).setup_class(request)

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

        testflow.setup(
            "Adding role %s permissions for vnic profile %s to user %s.",
            config.role.VnicProfileUser,
            config.NETWORK_NAMES[0],
            config.USER_NAMES[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )

        for user_name in config.USER_NAMES[:2]:
            testflow.setup(
                "Adding VM %s permissions to user %s.",
                config.VM_NAME, user_name
            )
            assert mla.addVMPermissionsToUser(
                True,
                user_name,
                config.VM_NAME
            )

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

        testflow.setup(
            "Adding nic %s with network %s to VM %s.",
            config.NIC_NAMES[0], config.NETWORK_NAMES[0], config.VM_NAME
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )

    @polarion("RHEVM3-8375")
    def test_update_vnic_on_vm(self):
        """ Update a VNIC on VM """
        testflow.step("Log in as user.")
        common.login_as_user()

        for network in [None, config.NETWORK_NAMES[0]]:
            testflow.step(
                "Updating nic %s on VM %s.",
                config.NIC_NAMES[0], config.VM_NAME
            )
            assert vms.updateNic(
                True,
                config.VM_NAME,
                config.NIC_NAMES[0],
                network=network
            )

        testflow.step(
            "Log in as user %s@%s.", config.USER_NAMES[1], config.USER_DOMAIN
        )
        common.login_as_user(user_name=config.USER_NAMES[1])

        testflow.step(
            "Updating nic %s on VM %s.",
            config.NIC_NAMES[0], config.VM_NAME
        )
        assert vms.updateNic(
            True,
            config.VM_NAME,
            config.NIC_NAMES[0],
            network=None
        )


class TestPositiveNetworkPermissions236408(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions236408, cls).setup_class(request)

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.setup(
            "Adding role %s permissions for vnic %s to user %s.",
            config.role.VnicProfileUser,
            config.NETWORK_NAMES[0],
            config.USER_NAMES[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )

        for user_name in config.USER_NAMES[:2]:
            testflow.setup(
                "Adding VM %s permissions to user %s.",
                config.VM_NAME, user_name
            )
            assert mla.addVMPermissionsToUser(
                True,
                user_name,
                config.VM_NAME
            )

        testflow.setup(
            "Adding role %s permissions for datacenter %s to user %s.",
            config.role.TemplateCreator,
            config.DC_NAME[0],
            config.USER_NAMES[0]
        )
        assert mla.addPermissionsForDataCenter(
            positive=True,
            user=config.USER_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.TemplateCreator
        )

        testflow.setup(
            "Adding role %s permissions for datacenter %s to user %s.",
            config.role.TemplateOwner,
            config.DC_NAME[0],
            config.USER_NAMES[1]
        )
        assert mla.addPermissionsForDataCenter(
            positive=True,
            user=config.USER_NAMES[1],
            data_center=config.DC_NAME[0],
            role=config.role.TemplateOwner
        )

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8374")
    def test_add_vnic_to_template(self):
        """ Add a VNIC to template """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step(
            "Creating template %s from VM %s.",
            config.TEMPLATE_NAMES[0], config.VM_NAME
        )
        assert templates.createTemplate(
            True,
            vm=config.VM_NAME,
            name=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

        testflow.step(
            "Adding nic %s to template %s.",
            config.NIC_NAMES[0], config.TEMPLATE_NAMES[0]
        )
        assert templates.addTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            name=config.NIC_NAMES[0],
            network=None
        )

        testflow.step(
            "Adding nic %s to template %s.",
            config.NIC_NAMES[1], config.TEMPLATE_NAMES[0]
        )
        assert templates.addTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            name=config.NIC_NAMES[1],
            network=config.NETWORK_NAMES[0]
        )

        testflow.step(
            "Log in as user %s@%s.", config.USER_NAMES[1], config.USER_DOMAIN
        )
        common.login_as_user(user_name=config.USER_NAMES[1])

        testflow.step(
            "Adding nic %s to template %s.",
            config.NIC_NAMES[2], config.TEMPLATE_NAMES[0]
        )
        assert templates.addTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            name=config.NIC_NAMES[2],
            network=None
        )


class TestPositiveNetworkPermissions236409(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions236409, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

        testflow.setup(
            "Adding role %s permissions for vnic profile %s to user %s.",
            config.role.VnicProfileUser,
            config.NETWORK_NAMES[0],
            config.USER_NAMES[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )

        testflow.setup("Creating VM %s.", config.VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        testflow.setup(
            "Adding nic %s with network %s to VM %s.",
            config.NIC_NAMES[0],
            config.NETWORK_NAMES[0],
            config.VM_NAME
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )

        for user_name in config.USER_NAMES[:2]:
            testflow.setup(
                "Adding VM %s permissions to user %s.",
                config.VM_NAME, user_name
            )
            assert mla.addVMPermissionsToUser(True, user_name, config.VM_NAME)

        testflow.setup(
            "Creating template %s from VM %s.",
            config.TEMPLATE_NAMES[0], config.VM_NAME
        )
        assert templates.createTemplate(
            True,
            vm=config.VM_NAME,
            name=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

        for user_name in config.USER_NAMES[:2]:
            testflow.setup(
                "Adding role %s permissions for template %s to user %s.",
                config.role.TemplateOwner,
                config.TEMPLATE_NAMES[0],
                user_name
            )
            assert mla.addPermissionsForTemplate(
                positive=True,
                user=user_name,
                template=config.TEMPLATE_NAMES[0],
                role=config.role.TemplateOwner
            )

    @polarion("RHEVM3-8373")
    def test_update_vnic_on_template(self):
        """ Update a VNIC on the template """
        testflow.step("Log in as user.")
        common.login_as_user()

        testflow.step(
            "Updating template %s nic %s.",
            config.TEMPLATE_NAMES[0], config.NIC_NAMES[0]
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            network=None
        )

        testflow.step(
            "Updating template %s nic %s.",
            config.TEMPLATE_NAMES[0], config.NIC_NAMES[0]
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0]
        )

        testflow.step(
            "Updating template %s nic %s.",
            config.TEMPLATE_NAMES[0], config.NIC_NAMES[0]
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            name='_'
        )

        testflow.step(
            "Updating template %s nic %s.",
            config.TEMPLATE_NAMES[0], config.NIC_NAMES[0]
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            '_',
            name=config.NIC_NAMES[0]
        )

        testflow.step(
            "Log in as user %s@%s.", config.USER_NAMES[1], config.USER_DOMAIN
        )
        common.login_as_user(user_name=config.USER_NAMES[1])

        testflow.step(
            "Updating template %s nic %s.",
            config.TEMPLATE_NAMES[0], config.NIC_NAMES[0]
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            network=None
        )

        testflow.step(
            "Updating template %s nic %s.",
            config.TEMPLATE_NAMES[0], config.NIC_NAMES[0]
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            name='_'
        )


class TestPositiveNetworkPermissions236577(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions236577, cls).setup_class(request)

        testflow.setup(
            "Adding role %s permissions for datacenter %s to user %s.",
            config.role.NetworkAdmin, config.DC_NAME[0], config.USER_NAMES[0]
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            config.role.NetworkAdmin
        )

    @polarion("RHEVM3-8372")
    def test_remove_network_from_datacenter(self):
        """ Remove Network From DC """
        msg = "NetworkAdmin role wasn't removed after network {0} was removed."

        testflow.step("Log in as user.")
        common.login_as_user(filter_=False)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.step(
            "Removing network %s from datacenter %s.",
            config.NETWORK_NAMES[0], config.DC_NAME[0]
        )
        assert networks.remove_network(
            True,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step(
            "Removing user %s permissions from datacenter %s.",
            config.USERS[0], config.DC_NAME[0]
        )
        assert mla.removeUserPermissionsFromDatacenter(
            True,
            config.DC_NAME[0],
            config.USERS[0]
        )

        perm_persist = False
        testflow.step("Getting user %s object.", config.USER_NAMES[0])
        obj = mla.userUtil.find(config.USER_NAMES[0])

        testflow.step("Getting user %s permits.", config.USER_NAMES[0])
        obj_permits = mla.permisUtil.getElemFromLink(obj, get_href=False)

        testflow.step("Getting id of role %s.", config.role.NetworkAdmin)
        role_id = users.rlUtil.find(config.role.NetworkAdmin).get_id()

        testflow.step("Checking if permissions were removed.")
        for perm in obj_permits:
            perm_persist = perm_persist or perm.get_role().get_id() == role_id
        assert not perm_persist, msg.format(config.NETWORK_NAMES[0])


class TestPositiveNetworkPermissions236664(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions236664, cls).setup_class(request)

        def finalize():
            testflow.teardown("Log in as admin.")
            common.login_as_admin()

            testflow.teardown(
                "Removing user %s permissions from datacenter %s.",
                config.USER_NAMES[0], config.DC_NAME[0]
            )
            assert mla.removeUserPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USER_NAMES[0]
            )

        request.addfinalizer(finalize)

        testflow.setup("Adding role %s.", ROLE_NAME)
        assert mla.addRole(
            True,
            name=ROLE_NAME,
            administrative='true',
            permits='login create_storage_pool_network'
        )

        testflow.setup(
            "Adding role %s permissions for datacenter %s to user %s.",
            ROLE_NAME, config.USER_NAMES[0], config.DC_NAME[0]
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            ROLE_NAME
        )

    @polarion("RHEVM3-8371")
    def test_custom_role(self):
        """ Custom Role """
        MTU = 1405

        testflow.step("Log in as user.")
        common.login_as_user(filter_=False)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        assert networks.update_network(
            True,
            config.NETWORK_NAMES[0],
            mtu=MTU,
            data_center=config.DC_NAME[0]
        )

        testflow.step(
            "Removing network %s from datacenter %s.",
            config.NETWORK_NAMES[0], config.DC_NAME[0]
        )
        assert networks.remove_network(
            True,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )


class TestPositiveNetworkPermissions317269(NetworkingPositive):
    dc_name = 'rand_dc_name'

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions317269, cls).setup_class(request)

        def finalize():
            testflow.teardown("Removing datacenter %s.", cls.dc_name)
            ignore_all_exceptions(
                datacenters.remove_datacenter,
                positive=True,
                datacenter=cls.dc_name
            )

        request.addfinalizer(finalize)

        testflow.setup(
            "Adding datacenter %s with version %s.",
            cls.dc_name, config.COMP_VERSION
        )
        assert datacenters.addDataCenter(
            True,
            name=cls.dc_name,
            version=config.COMP_VERSION,
            local=True
        )

    @polarion("RHEVM3-4031")
    def test_automatic_creation_of_permissions(self):
        """ Check auto permission creation on new datacenter """
        # newly created dc, vnicprofile has VnicProfileUser role on Everyone
        testflow.step("Checking if permissions were created.")
        assert mla.hasGroupPermissionsOnObject(
            'Everyone',
            mla.groupUtil.find('Everyone'),
            role=config.role.VnicProfileUser
        ), "Permission was not created at datacenter for Everyone."


class TestPositiveNetworkPermissions317133(NetworkingPositive):
    dc_name = 'rand_dc_name'

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions317133, cls).setup_class(request)

        def finalize():
            testflow.teardown("Removing datacenter %s.", cls.dc_name)
            ignore_all_exceptions(
                datacenters.remove_datacenter,
                positive=True,
                datacenter=cls.dc_name
            )

        request.addfinalizer(finalize)

        testflow.setup(
            "Adding role %s to user %s.",
            config.role.DataCenterAdmin, config.USER_NAMES[0]
        )
        assert users.addRoleToUser(
            True,
            config.USER_NAMES[0],
            config.role.DataCenterAdmin
        )

        testflow.setup("Log in as user.")
        common.login_as_user(filter_=False)

        testflow.setup(
            "Adding datacenter %s with version %s.",
            cls.dc_name, config.COMP_VERSION
        )
        assert datacenters.addDataCenter(
            True,
            name=cls.dc_name,
            version=config.COMP_VERSION,
            local=True
        )

    @polarion("RHEVM3-4030")
    def test_automatic_creation_to_user(self):
        """ Check that network admin permissions are added automatically  """
        testflow.step("Log in as admin.")
        common.login_as_admin()

        testflow.step("Getting vnic %s.", config.MGMT_BRIDGE)
        vnic = networks.get_vnic_profile_obj(
            config.MGMT_BRIDGE,
            config.MGMT_BRIDGE,
            data_center=self.dc_name
        )

        testflow.step("Finding network %s.", config.MGMT_BRIDGE)
        net = networks.find_network(
            config.MGMT_BRIDGE,
            data_center=self.dc_name,
        )

        testflow.step(
            "Checking if user %s has role %s permissions on vnic %s.",
            config.USERS[0], config.role.NetworkAdmin, config.MGMT_BRIDGE
        )
        assert mla.has_user_permissions_on_object(
            config.USERS[0],
            vnic,
            role=config.role.NetworkAdmin
        ), "Permission was not created at datacenter for vnicprofile."

        testflow.step(
            "Checking if user %s has role %s permissions on network %s.",
            config.USERS[0], config.role.NetworkAdmin, config.MGMT_BRIDGE
        )
        assert mla.has_user_permissions_on_object(
            config.USERS[0],
            net,
            role=config.role.NetworkAdmin
        ), "Permission was not created at datacenter for network."


class TestPositiveNetworkPermissions320610(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions320610, cls).setup_class(request)

        networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.setup(
            "Adding network %s to cluster %s.",
            config.NETWORK_NAMES[0], config.CLUSTER_NAME[0]
        )
        networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

        testflow.setup(
            "Adding vnic profile %s to network %s in "
            "cluster %s in datacenter %s.",
            config.NETWORK_NAMES[1], config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0], config.DC_NAME[0]
        )
        networks.add_vnic_profile(
            True,
            config.NETWORK_NAMES[1],
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            network=config.NETWORK_NAMES[0]
        )

        testflow.setup(
            "Adding role %s permissions for vnic profile %s to user %s.",
            config.role.VnicProfileUser,
            config.NETWORK_NAMES[0],
            config.USER_NAMES[0]
        )
        mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )

        testflow.setup(
            "Adding role %s permissions for "
            "network %s in datacenter %s to user %s.",
            config.role.VnicProfileUser, config.NETWORK_NAMES[0],
            config.DC_NAME[0], config.USER_NAMES[0]
        )
        mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )

        testflow.setup("Creating VM %s.", config.VM_NAME)
        vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.STORAGE_NAME[0],
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )

        testflow.setup(
            "Adding VM %s permissions to user %s.",
            config.VM_NAME, config.USER_NAMES[0]
        )
        mla.addVMPermissionsToUser(True, config.USER_NAMES[0], config.VM_NAME)

    @polarion("RHEVM3-4044")
    def test_vnic_permissions_are_restricted_to_specific_profile(self):
        """
        vnicProfile perms on vNIC profile are restricted to specific profile
        """
        common.login_as_user()
        testflow.step(
            "Adding nic:%s with vnic profile:%s to VM:%s.",
            config.NIC_NAMES[0], config.NETWORK_NAMES[0], config.VM_NAME
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            vnic_profile=config.NETWORK_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )
        testflow.step(
            "Adding nic:%s with vnic profile:%s to VM:%s.",
            config.NIC_NAMES[0], config.NETWORK_NAMES[1], config.VM_NAME
        )
        assert vms.addNic(
            False,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            vnic_profile=config.NETWORK_NAMES[1],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )


class TestPositiveNetworkPermissions317270(NetworkingPositive):
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestPositiveNetworkPermissions317270, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            usages='vm'
        )

        testflow.setup(
            "Adding role %s permissions for vnic %s to user %s.",
            config.role.UserRole, config.NETWORK_NAMES[0], config.USER_NAMES[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.UserRole
        )

    @polarion("RHEVM3-4032")
    def test_non_vm_to_vm_network(self):
        """ When network is switched to nonvm permissions should be removed """
        testflow.step("Getting vnic objects.")
        vnic = networks.get_vnic_profile_obj(
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )

        testflow.step(
            "Checking if user %s has permissions of role %s on vnic %s.",
            config.USERS[0], vnic, config.role.UserRole
        )
        assert mla.has_user_permissions_on_object(
            config.USERS[0],
            vnic,
            role=config.role.UserRole
        )

        assert networks.update_network(
            True,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            usages=''
        )

        testflow.step(
            "Checking if user %s hasn't permissions of role %s on vnic %s.",
            config.USERS[0], config.role.UserRole, vnic
        )
        assert not mla.has_user_permissions_on_object(
            config.USERS[0],
            vnic,
            role=config.role.UserRole
        ), "Permission persists on vnicprofile after switched to nonvm."
