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
    datacenters, mla, networks, templates, users, vms
)
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr

from rhevmtests.system.user_tests.mla import common, config
from test_network_permissions_negative import (
    NetworkingNegative, ignore_all_exceptions
)

ROLE_NAME = '_NetworkCreator'
EVERYONE = 'Everyone'

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        common.login_as_admin()
        for user in config.USER_NAMES:
            assert common.remove_user(True, user)

    request.addfinalizer(finalize)

    for user in config.USER_NAMES:
        assert common.add_user(
            True,
            user_name=user,
            domain=config.USER_DOMAIN
        )


@attr(tier=2)
class NetworkingPositive(NetworkingNegative):
    __test__ = False

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(NetworkingPositive, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            ignore_all_exceptions(
                mla.removeRole,
                positive=True,
                role=ROLE_NAME
            )

        request.addfinalizer(finalize)


class PositiveNetworkPermissions231821(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions231821, cls).setup_class(request)

        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0],
            role=config.role.SuperUser
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[1],
            config.DC_NAME[0],
            role=config.role.DataCenterAdmin
        )
        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[2],
            config.DC_NAME[0],
            role=config.role.NetworkAdmin
        )

    @polarion("RHEVM3-8369")
    @bz({"1379356": {}})
    def test_create_network_in_datacenter(self):
        """ Create network in datacenter """
        for user_name in config.USER_NAMES:
            common.login_as_user(
                user_name=user_name,
                filter_=False
            )
            assert networks.add_network(
                True,
                name=config.NETWORK_NAMES[0],
                data_center=config.DC_NAME[0]
            )
            common.login_as_admin()
            assert networks.remove_network(
                True,
                network=config.NETWORK_NAMES[0],
                data_center=config.DC_NAME[0]
            )


class PositiveNetworkPermissions231822(NetworkingPositive):
    __test__ = True

    apis = NetworkingPositive.apis - set(['java'])

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions231822, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        assert mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.DataCenterAdmin
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
        mtu = 800
        stp = True
        for user_name in config.USER_NAMES[:2]:
            common.login_as_user(
                user_name=user_name,
                filter_=False
            )
            assert networks.update_network(
                True,
                config.NETWORK_NAMES[0],
                data_center=config.DC_NAME[0],
                mtu=mtu,
                stp=str(stp).lower()
            )
            mtu += 100
            stp = not stp


class PositiveNetworkPermissions231823(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions231823, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        assert mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.NetworkAdmin
        )
        assert mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[1],
            cluster=config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8383")
    def test_attaching_network_to_cluster(self):
        """ Attaching network to cluster """
        common.login_as_user(filter_=False)
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        assert networks.remove_network_from_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        common.login_as_user(
            user_name=config.USER_NAMES[1],
            filter_=False
        )
        assert networks.add_network_to_cluster(
            False,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

        logger.info("ClusterAdmin can't attach network to cluster.")


class TestSwitching(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(TestSwitching, cls).setup_class(request)

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
        assert mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[1],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.NetworkAdmin
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
        assert networks.update_cluster_network(
            True,
            config.CLUSTER_NAME[0],
            config.NETWORK_NAMES[0],
            **kwargs
        )
        for user_name in config.USER_NAMES[:2]:
            common.login_as_user(user_name=user_name, filter_=False)
            self._inverse_params(kwargs)
            assert networks.update_cluster_network(
                True,
                config.CLUSTER_NAME[0],
                config.NETWORK_NAMES[0],
                **kwargs
            )
            self._inverse_params(kwargs)
            assert networks.update_cluster_network(
                True,
                config.CLUSTER_NAME[0],
                config.NETWORK_NAMES[0],
                **kwargs
            )


class PositiveNetworkPermissions231824(TestSwitching):
    __test__ = True

    @polarion("RHEVM3-8382")
    def test_required_to_non_required_and_vice_versa(self):
        """ Required to non-required and vice versa """
        self._test_switching_display_and_required(required=True)


class PositiveNetworkPermissions236073(TestSwitching):
    __test__ = True

    @polarion("RHEVM3-8377")
    def test_display_network(self):
        """ Display network """
        self._test_switching_display_and_required(
            display=True,
            usages='display'
        )


class PositiveNetworkPermissions231826(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions231826, cls).setup_class(request)

        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            provisioned_size=config.GB,
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
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
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
        common.login_as_user()
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )
        assert vms.removeNic(True, config.VM_NAME, config.NIC_NAMES[0])


class PositiveNetworkPermissions231827(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions231827, cls).setup_class(request)

        # Not possible to create public vnicprofile, just add Everyone perms
        for net in config.NETWORK_NAMES:
            assert networks.add_network(
                True,
                name=net,
                data_center=config.DC_NAME[0]
            )
            assert mla.addVnicProfilePermissionsToGroup(
                True,
                EVERYONE,
                net,
                net,
                config.DC_NAME[0]
            )
            assert networks.add_network_to_cluster(
                True,
                net,
                config.CLUSTER_NAME[0]
            )

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
        common.login_as_user()
        for net in config.NETWORK_NAMES:
            assert vms.addNic(
                True,
                config.VM_NAME,
                name=net,
                network=net,
                interface='virtio'
            )
            assert vms.updateNic(
                True,
                config.VM_NAME,
                net,
                name="{0}-x".format(net)
            )
        nets = [n.get_name() for n in networks.NET_API.get(abs_link=False)]
        logger.info("User can see networks: '%s'", nets)
        if not config.GOLDEN_ENV:
            assert len(nets) == 6
        assert vms.removeNic(True, config.VM_NAME, config.NIC_NAMES[0])


class PositiveNetworkPermissions231830(NetworkingPositive):
    __test__ = True

    apis = set(['rest'])

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions231830, cls).setup_class(request)

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
            assert networks.add_network_to_cluster(
                True,
                net,
                config.CLUSTER_NAME[0]
            )
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
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
        common.login_as_user(filter_=filter_)
        self.can_see(
            self.filter_net(net1, p1, networks.find_network),
            self.filter_net(net2, p2, networks.find_network),
            self.filter_net(net1, p3, networks.VNIC_PROFILE_API.find),
            self.filter_net(net2, p4, networks.VNIC_PROFILE_API.find)
        )
        common.login_as_admin()

    def _test_permissions_on_vnic_profile(self):
        mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )
        self._test_wrap(True, False, True, False)
        mla.removeUserPermissionsFromVnicProfile(
            True,
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            config.USERS[0]
        )

    def _test_permissions_on_vm(self):
        mla.addVMPermissionsToUser(True, config.USER_NAMES[0], config.VM_NAME)
        self._test_wrap(True, False, True, False)
        mla.removeUserPermissionsFromVm(True, config.VM_NAME, config.USERS[0])

    def _test_permissions_on_template(self):
        mla.addPermissionsForTemplate(
            True,
            config.USER_NAMES[0],
            config.TEMPLATE_NAMES[0]
        )
        self._test_wrap(True, False, True, False)
        mla.removeUserPermissionsFromTemplate(
            True,
            config.TEMPLATE_NAMES[0],
            config.USERS[0]
        )

    def _test_permissions_on_datacenter(self):
        mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[0],
            config.DC_NAME[0]
        )
        self._test_wrap(True, True, True, True, False)
        mla.removeUserPermissionsFromDatacenter(
            True,
            config.DC_NAME[0],
            config.USERS[0]
        )

    def _test_permissions_on_cluster(self):
        mla.addClusterPermissionsToUser(
            True,
            config.USER_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        self._test_wrap(True, True, True, True, False)
        mla.removeUserPermissionsFromCluster(
            True,
            config.CLUSTER_NAME[0],
            config.USERS[0]
        )

    def _test_permissions_on_system(self):
        users.addRoleToUser(
            True,
            config.USER_NAMES[0],
            config.role.UserRole
        )
        self._test_wrap(True, True, True, True)
        common.remove_user(True, config.USER_NAMES[0])
        common.add_user(
            True,
            user_name=config.USER_NAMES[0],
            domain=config.USER_DOMAIN
        )

    def _test_permissions_on_network(self):
        mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            config.role.VnicProfileUser
        )
        self._test_wrap(True, False, True, False)
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


class PositiveNetworkPermissions231832(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions231832, cls).setup_class(request)

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
                assert mla.addPermissionsForVnicProfile(
                    positive=True,
                    user=user_name,
                    vnicprofile=vnic_profile,
                    network=vnic_profile,
                    data_center=config.DC_NAME[0],
                    role=user_role
                )

        assert mla.addPermissionsForDataCenter(
            True,
            config.USER_NAMES[1],
            config.DC_NAME[0],
            config.role.UserRole
        )
        for net in config.NETWORK_NAMES[:2]:
            assert networks.add_network_to_cluster(
                True,
                net,
                config.CLUSTER_NAME[0]
            )

    @polarion("RHEVM3-8378")
    def test_port_mirroring(self):
        """ Port mirroring """
        common.login_as_user(user_name=config.USER_NAMES[1])
        assert not networks.update_vnic_profile(
            name=config.NETWORK_NAMES[0],
            network=config.NETWORK_NAMES[0],
            port_mirroring=False,
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0]
        )
        assert not networks.update_vnic_profile(
            name=config.NETWORK_NAMES[1],
            network=config.NETWORK_NAMES[1],
            port_mirroring=True,
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0]
        )

        common.login_as_user(filter_=False)
        assert networks.update_vnic_profile(
            name=config.NETWORK_NAMES[0],
            network=config.NETWORK_NAMES[0],
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            port_mirroring=False
        )
        assert networks.update_vnic_profile(
            name=config.NETWORK_NAMES[1],
            network=config.NETWORK_NAMES[1],
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            port_mirroring=True
        )


class PositiveNetworkPermissions236367(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions236367, cls).setup_class(request)

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
        assert mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )
        for user_name in config.USER_NAMES[:2]:
            assert mla.addVMPermissionsToUser(
                True,
                user_name,
                config.VM_NAME
            )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8376")
    def test_add_vnic_to_vm(self):
        """ Add a VNIC to VM  """
        common.login_as_user()
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=None,
            interface='virtio'
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[1],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )
        common.login_as_user(user_name=config.USER_NAMES[1])
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[2],
            network=None,
            interface='virtio'
        )


class PositiveNetworkPermissions236406(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions236406, cls).setup_class(request)

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
        assert mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )
        for user_name in config.USER_NAMES[:2]:
            assert mla.addVMPermissionsToUser(
                True,
                user_name,
                config.VM_NAME
            )

        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
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
        common.login_as_user()
        for network in [None, config.NETWORK_NAMES[0]]:
            assert vms.updateNic(
                True,
                config.VM_NAME,
                config.NIC_NAMES[0],
                network=network
            )
        common.login_as_user(user_name=config.USER_NAMES[1])
        assert vms.updateNic(
            True,
            config.VM_NAME,
            config.NIC_NAMES[0],
            network=None
        )


class PositiveNetworkPermissions236408(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions236408, cls).setup_class(request)

        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )
        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
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
            assert mla.addVMPermissionsToUser(
                True,
                user_name,
                config.VM_NAME
            )
        assert mla.addPermissionsForDataCenter(
            positive=True,
            user=config.USER_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.TemplateCreator
        )
        assert mla.addPermissionsForDataCenter(
            positive=True,
            user=config.USER_NAMES[1],
            data_center=config.DC_NAME[0],
            role=config.role.TemplateOwner
        )

        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-8374")
    @bz({'1209505': {}})
    def test_add_vnic_to_template(self):
        """ Add a VNIC to template """
        common.login_as_user()
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
            network=None
        )
        assert templates.addTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            name=config.NIC_NAMES[1],
            network=config.NETWORK_NAMES[0]
        )

        common.login_as_user(user_name=config.USER_NAMES[1])
        assert templates.addTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            name=config.NIC_NAMES[2],
            network=None
        )


class PositiveNetworkPermissions236409(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions236409, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        assert networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        assert mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )
        assert vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )
        for user_name in config.USER_NAMES[:2]:
            assert mla.addVMPermissionsToUser(True, user_name, config.VM_NAME)

        assert templates.createTemplate(
            True,
            vm=config.VM_NAME,
            name=config.TEMPLATE_NAMES[0],
            cluster=config.CLUSTER_NAME[0]
        )

        for user_name in config.USER_NAMES[:2]:
            assert mla.addPermissionsForTemplate(
                positive=True,
                user=user_name,
                template=config.TEMPLATE_NAMES[0],
                role=config.role.TemplateOwner
            )

    @polarion("RHEVM3-8373")
    def test_update_vnic_on_template(self):
        """ Update a VNIC on the template """
        common.login_as_user()
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            network=None
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            network=config.NETWORK_NAMES[0]
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            name='_'
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            '_',
            name=config.NIC_NAMES[0]
        )
        common.login_as_user(user_name=config.USER_NAMES[1])
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            network=None
        )
        assert templates.updateTemplateNic(
            True,
            config.TEMPLATE_NAMES[0],
            config.NIC_NAMES[0],
            name='_'
        )


class PositiveNetworkPermissions236577(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions236577, cls).setup_class(request)
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
        common.login_as_user(filter_=False)
        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        assert networks.remove_network(
            True,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        common.login_as_admin()
        assert mla.removeUserPermissionsFromDatacenter(
            True,
            config.DC_NAME[0],
            config.USERS[0]
        )
        # Check if permissions was removed
        perm_persist = False
        obj = mla.userUtil.find(config.USER_NAMES[0])
        obj_permits = mla.permisUtil.getElemFromLink(obj, get_href=False)
        role_id = users.rlUtil.find(config.role.NetworkAdmin).get_id()
        for perm in obj_permits:
            perm_persist = perm_persist or perm.get_role().get_id() == role_id
        assert not perm_persist, msg.format(config.NETWORK_NAMES[0])


class PositiveNetworkPermissions236664(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions236664, cls).setup_class(request)

        def finalize():
            common.login_as_admin()
            assert mla.removeUserPermissionsFromDatacenter(
                True,
                config.DC_NAME[0],
                config.USER_NAMES[0]
            )

        request.addfinalizer(finalize)

        assert mla.addRole(
            True,
            name=ROLE_NAME,
            administrative='true',
            permits='login create_storage_pool_network'
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
        common.login_as_user(filter_=False)
        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        assert networks.update_network(
            True,
            config.NETWORK_NAMES[0],
            mtu=1405,
            data_center=config.DC_NAME[0]
        )
        assert networks.remove_network(
            True,
            network=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )


class PositiveNetworkPermissions317269(NetworkingPositive):
    __test__ = True
    dc_name = 'rand_dc_name'

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions317269, cls).setup_class(request)

        def finalize():
            ignore_all_exceptions(
                datacenters.remove_datacenter,
                positive=True,
                datacenter=cls.dc_name
            )

        request.addfinalizer(finalize)

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
        assert mla.hasGroupPermissionsOnObject(
            'Everyone',
            mla.groupUtil.find('Everyone'),
            role=config.role.VnicProfileUser
        ), "Permission was not created at datacenter for Everyone."


class PositiveNetworkPermissions317133(NetworkingPositive):
    __test__ = True
    dc_name = 'rand_dc_name'

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions317133, cls).setup_class(request)

        def finalize():
            ignore_all_exceptions(
                datacenters.remove_datacenter,
                positive=True,
                datacenter=cls.dc_name
            )

        request.addfinalizer(finalize)

        assert users.addRoleToUser(
            True,
            config.USER_NAMES[0],
            config.role.DataCenterAdmin
        )

        common.login_as_user(filter_=False)

        assert datacenters.addDataCenter(
            True,
            name=cls.dc_name,
            version=config.COMP_VERSION,
            local=True
        )

    @polarion("RHEVM3-4030")
    @bz({'1214805': {}})
    def test_automatic_creation_to_user(self):
        """ Check that network admin permissions are added automatically  """
        common.login_as_admin()

        vnic = networks.get_vnic_profile_obj(
            config.MGMT_BRIDGE,
            config.MGMT_BRIDGE,
            data_center=self.dc_name
        )
        net = networks.find_network(
            config.MGMT_BRIDGE,
            data_center=self.dc_name,
        )

        assert mla.has_user_permissions_on_object(
            config.USERS[0],
            vnic,
            role=config.role.NetworkAdmin
        ), "Permission was not created at datacenter for vnicprofile."

        assert mla.has_user_permissions_on_object(
            config.USERS[0],
            net,
            role=config.role.NetworkAdmin
        ), "Permission was not created at datacenter for network."


class PositiveNetworkPermissions320610(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions320610, cls).setup_class(request)

        networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
        )
        networks.add_network_to_cluster(
            True,
            config.NETWORK_NAMES[0],
            config.CLUSTER_NAME[0]
        )
        networks.add_vnic_profile(
            True,
            config.NETWORK_NAMES[1],
            cluster=config.CLUSTER_NAME[0],
            data_center=config.DC_NAME[0],
            network=config.NETWORK_NAMES[0]
        )
        mla.addPermissionsForVnicProfile(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )
        mla.addPermissionsForNetwork(
            True,
            config.USER_NAMES[0],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            role=config.role.VnicProfileUser
        )
        vms.createVm(
            positive=True,
            vmName=config.VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            storageDomainName=config.MASTER_STORAGE,
            provisioned_size=config.GB,
            network=config.MGMT_BRIDGE
        )
        mla.addVMPermissionsToUser(True, config.USER_NAMES[0], config.VM_NAME)

    @polarion("RHEVM3-4044")
    def test_vnic_permissions_are_restricted_to_specific_profile(self):
        """
        vnicProfile perms on vNIC profile are restricted to specific profile
        """
        common.login_as_user()
        assert vms.addNic(
            True,
            config.VM_NAME,
            name=config.NIC_NAMES[0],
            vnic_profile=config.NETWORK_NAMES[0],
            network=config.NETWORK_NAMES[0],
            interface='virtio'
        )
        with pytest.raises(EntityNotFound):
            vms.addNic(
                False,
                config.VM_NAME,
                name=config.NIC_NAMES[0],
                vnic_profile=config.NETWORK_NAMES[1],
                network=config.NETWORK_NAMES[0],
                interface='virtio'
            )


class PositiveNetworkPermissions317270(NetworkingPositive):
    __test__ = True

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        super(PositiveNetworkPermissions317270, cls).setup_class(request)

        assert networks.add_network(
            True,
            name=config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0],
            usages='vm'
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
        vnic = networks.get_vnic_profile_obj(
            config.NETWORK_NAMES[0],
            config.NETWORK_NAMES[0],
            data_center=config.DC_NAME[0]
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
        assert not mla.has_user_permissions_on_object(
            config.USERS[0],
            vnic,
            role=config.role.UserRole
        ), "Permission persists on vnicprofile after swtiched to nonvm."
