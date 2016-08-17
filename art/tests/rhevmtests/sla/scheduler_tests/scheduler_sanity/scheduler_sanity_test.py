"""
Scheduler - Scheduler Sanity Test
Check working of all build-in filter, weight and balance units.
"""
import logging
import random

import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.scheduling_policies as ll_sch
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
import pytest
import rhevmtests.sla.config as conf
from art.test_handler.tools import polarion
from art.unittest_lib import SlaTest as TestCase
from art.unittest_lib import attr

logger = logging.getLogger(__name__)

FILTER_TYPE = conf.ENUMS['policy_unit_type_filter']


@pytest.fixture(scope="module")
def init_scheduler_sanity_test(request):
    """
    1) Deactivate third host
    """
    def fin():
        """
        1) Change cluster scheduler policy to none
        2) Remove all redundant scheduler policies
        3) Activate third host
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.POLICY_NONE
        )
        logger.info("Remove all user specified scheduling policies")
        sched_policies = ll_sch.get_scheduling_policies()
        sched_policies = filter(
            lambda x: x.get_name() not in conf.ENGINE_POLICIES, sched_policies
        )
        for policy in sched_policies:
            ll_sch.remove_scheduling_policy(policy_name=policy.get_name())
        ll_hosts.activateHost(positive=True, host=conf.HOSTS[2])
    request.addfinalizer(fin)

    assert ll_hosts.deactivateHost(positive=True, host=conf.HOSTS[2])


@attr(tier=2)
class BaseSchedulingClass(TestCase):
    """
    Base class to create new scheduler policy.
    """
    __test__ = False
    policy_name = None
    policy_units = None
    policy_properties = None

    @classmethod
    def _populate_policy_by_units(cls):
        for unit_name, unit_type in cls.policy_units.iteritems():
            logger.info(
                "Add policy unit %s of type %s to policy %s.",
                unit_name, unit_type, cls.policy_name
            )
            if not ll_sch.add_scheduling_policy_unit(
                cls.policy_name, unit_name, unit_type
            ):
                raise errors.SchedulerException("Failed to add unit to policy")

    @classmethod
    def setup_class(cls):
        """
        Create new scheduler policy, populate it by units.
        """
        logger.info("Create new scheduler policy %s.", cls.policy_name)
        if not ll_sch.add_new_scheduling_policy(
            name=cls.policy_name, properties=cls.policy_properties
        ):
            raise errors.SchedulerException(
                "Failed to add new scheduler policy."
            )
        if cls.policy_units:
            cls._populate_policy_by_units()

    @classmethod
    def teardown_class(cls):
        """
        Remove scheduler policy.
        """
        logger.info("Remove scheduler policy %s.", cls.policy_name)
        if not ll_sch.remove_scheduling_policy(cls.policy_name):
            logger.error(
                "Failed to remove scheduler policy %s", cls.policy_name
            )


@attr(tier=1)
class TestCRUD(TestCase):
    """
    Test class to create, update and remove cluster policy
    """
    __test__ = True
    policy_name = 'crud_policy'
    new_policy_name = 'new_crud_policy'

    @polarion("RHEVM3-9486")
    def test_crud_check(self):
        """
        Create, update and remove cluster policy
        """
        logger.info("Create new scheduler policy %s.", self.policy_name)
        self.assertTrue(
            ll_sch.add_new_scheduling_policy(name=self.policy_name),
            "Failed to create new cluster policy"
        )
        logger.info(
            "Update cluster policy %s name to %s",
            self.policy_name, self.new_policy_name
        )
        self.assertTrue(
            ll_sch.update_scheduling_policy(
                self.policy_name, name=self.new_policy_name
            ), "Failed to update cluster policy"
        )
        logger.info("Remove cluster policy %s", self.new_policy_name)
        self.assertTrue(
            ll_sch.remove_scheduling_policy(self.new_policy_name),
            "Failed to remove cluster policy"
        )
        # TODO: Still no api to clone cluster policy via REST


class AttachPolicyToCluster(BaseSchedulingClass):
    """
    Class to attach scheduler policy to cluster.
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Update cluster scheduler policy.
        """
        super(AttachPolicyToCluster, cls).setup_class()
        if not ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=cls.policy_name
        ):
            raise errors.ClusterException()

    @classmethod
    def teardown_class(cls):
        """
        Update cluster scheduler policy to None.
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.POLICY_NONE
        )
        super(AttachPolicyToCluster, cls).teardown_class()


@pytest.mark.usefixtures(init_scheduler_sanity_test.__name__)
class UpdateVms(AttachPolicyToCluster):
    """
    Class to update and to start vm.
    """
    __test__ = False
    vms_new_parameters = None
    old_parameters = None

    @classmethod
    def setup_class(cls):
        """
        Update vm.
        """
        super(UpdateVms, cls).setup_class()
        for vm, params in cls.vms_new_parameters.iteritems():
            logger.info(
                "Update vm %s with parameters %s.", vm, params
            )
            if not ll_vms.updateVm(True, vm, **params):
                raise errors.VMException("Failed to update vm")

    @classmethod
    def teardown_class(cls):
        """
        Stop and update vm.
        """
        ll_vms.stop_vms_safely(conf.VM_NAME[:2])
        for vm in cls.vms_new_parameters.iterkeys():
            logger.info(
                "Update vm %s with parameters %s.", vm, cls.old_parameters
            )
            if not ll_vms.updateVm(True, vm, **cls.old_parameters):
                logger.error("Failed to update vm %s", vm)

        super(UpdateVms, cls).teardown_class()


class TestDeletePolicyInUse(AttachPolicyToCluster):
    """
    Negative: Try to delete scheduler policy,
    when it attached to one of clusters.
    """
    __test__ = True
    policy_name = 'delete_policy_in_use'

    @polarion("RHEVM3-9477")
    def test_delete_policy(self):
        """
        Delete attached policy
        """
        self.assertFalse(ll_sch.remove_scheduling_policy(self.policy_name))


@attr(tier=1)
class TestRemoveBuildInPolicy(TestCase):
    """
    Negative: remove build-in scheduler policy.
    """
    __test__ = True

    @polarion("RHEVM3-9478")
    def test_delete_policy(self):
        """
        Delete build-in policy.
        """
        policy_to_remove = random.choice(conf.ENGINE_POLICIES)
        self.assertFalse(ll_sch.remove_scheduling_policy(policy_to_remove))


class TestPinToHostFilter(UpdateVms):
    """
    Check vm start and migration under PinToHost filter.
    """
    __test__ = True
    policy_name = 'check_pin_to_host'
    policy_units = {conf.ENUMS['filter_pin_to_host']: FILTER_TYPE}
    vms_new_parameters = {
        conf.VM_NAME[0]: {
            'placement_host': None, 'placement_affinity': conf.VM_PINNED
        }
    }
    old_parameters = {
        'placement_host': conf.VM_ANY_HOST,
        'placement_affinity': conf.VM_MIGRATABLE
    }

    @classmethod
    def setup_class(cls):
        cls.vms_new_parameters[conf.VM_NAME[0]][
            'placement_host'
        ] = conf.HOSTS[0]
        super(TestPinToHostFilter, cls).setup_class()

    @polarion("RHEVM3-9479")
    def test_check_filter(self):
        """
        Check filter.
        """
        logger.info("Start vm %s", conf.VM_NAME[0])
        self.assertTrue(
            ll_vms.startVm(True, conf.VM_NAME[0]), "Failed to run vm."
        )
        logger.info(
            "Check if vm %s, started on host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        self.assertEqual(
            conf.HOSTS[0], ll_vms.get_vm_host(conf.VM_NAME[0]),
            "Vm run on different host."
        )
        logger.info("Try to migrate pinned vm %s", conf.VM_NAME[0])
        self.assertFalse(
            ll_vms.migrateVm(True, conf.VM_NAME[0]),
            "Migration successed"
        )


class TestNegativePinToHostFilter(UpdateVms):
    """
    Negative: Check PinToHost filter,
    deactivate host where vm pinned and start vm
    """
    __test__ = True
    policy_name = 'negative_check_pin_to_host'
    policy_units = {conf.ENUMS['filter_pin_to_host']: FILTER_TYPE}
    vms_new_parameters = {
        conf.VM_NAME[0]: {
            'placement_host': None, 'placement_affinity': conf.VM_PINNED
        }
    }
    old_parameters = {
        'placement_host': conf.VM_ANY_HOST,
        'placement_affinity': conf.VM_MIGRATABLE
    }

    @classmethod
    def setup_class(cls):
        """
        Deactivate one of hosts.
        """
        cls.vms_new_parameters[conf.VM_NAME[0]][
            'placement_host'
        ] = conf.HOSTS[0]
        super(TestNegativePinToHostFilter, cls).setup_class()
        logger.info("Deactivate host %s.", conf.HOSTS[0])
        if not ll_hosts.deactivateHost(True, conf.HOSTS[0]):
            raise errors.HostException("Failed to deactivate host.")

    @polarion("RHEVM3-9485")
    def test_check_filter(self):
        """
        Check filter.
        """
        logger.info("Start vm %s", conf.VM_NAME[0])
        self.assertFalse(
            ll_vms.startVm(True, conf.VM_NAME[0]),
            "Success to run vm on other host"
        )

    @classmethod
    def teardown_class(cls):
        """
        Activate host.
        """
        logger.info("Activate host %s.", conf.HOSTS[0])
        if not ll_hosts.activateHost(True, conf.HOSTS[0]):
            raise errors.HostException("Failed to activate host.")
        super(TestNegativePinToHostFilter, cls).teardown_class()


class TestMemoryFilter(UpdateVms):
    """
    Create new scheduler policy with memory filter
    and check that filter prevent to start or migrate vm.
    """
    __test__ = True
    policy_name = 'memory_filter'
    policy_units = {conf.ENUMS['filter_memory']: FILTER_TYPE}
    vms_new_parameters = {}
    old_parameters = {
        'memory': conf.GB, 'memory_guaranteed': conf.GB
    }

    @classmethod
    def setup_class(cls):
        """
        Change vms memory to prevent start of vms on the same host
        """
        logger.info(
            "Update cluster %s over commit to 100 percent",
            conf.CLUSTER_NAME[0]
        )
        if not ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            mem_ovrcmt_prc=conf.CLUSTER_OVERCOMMITMENT_NONE
        ):
            raise errors.ClusterException("Failed to update cluster")
        host_list = conf.HOSTS[:2]
        hosts_mem = hl_vms.calculate_memory_for_memory_filter(host_list)
        vm_memory_dict = dict(zip(conf.VM_NAME[:2], hosts_mem))
        for vm, memory in vm_memory_dict.iteritems():
            cls.vms_new_parameters[vm] = {
                'memory': memory,
                'memory_guaranteed': memory,
                'os_type': conf.VM_OS_TYPE
            }
        super(TestMemoryFilter, cls).setup_class()
        logger.info("Start vms %s", conf.VM_NAME[:2])
        for vm in conf.VM_NAME[:2]:
            logger.info("Start vm %s", vm)
            if not ll_vms.startVm(True, vm, wait_for_status=conf.VM_UP):
                raise errors.VMException("Failed to start vms")

    @polarion("RHEVM3-9480")
    def test_check_filter(self):
        """
        Check if vms start on different hosts, because memory filter and
        that migration failed because memory filter
        """
        logger.info(
            "Check if vm %s and %s run on different hosts",
            conf.VM_NAME[0], conf.VM_NAME[1]
        )
        self.assertNotEqual(
            ll_vms.get_vm_host(conf.VM_NAME[0]),
            ll_vms.get_vm_host(conf.VM_NAME[1]),
            "Vms started on the same host."
        )
        logger.info("Try to migrate vm %s", conf.VM_NAME[0])
        self.assertFalse(ll_vms.migrateVm(
            True, conf.VM_NAME[0]), "Migration successed"
        )


class TestCpuFilter(UpdateVms):
    """
    Create new scheduling policy, with CPU filter and
    check that filter not prevent to start vm with correct number of vcpu's.
    """
    __test__ = True
    policy_name = 'cpu_filter'
    policy_units = {
        conf.ENUMS['filter_cpu']: FILTER_TYPE,
        conf.ENUMS['filter_pin_to_host']: FILTER_TYPE
    }
    vms_new_parameters = {}
    old_parameters = {
        'cpu_socket': 1, 'cpu_cores': 1, 'placement_host': conf.VM_ANY_HOST
    }

    @classmethod
    def setup_class(cls):
        """
        Change vm vcpu to exact number of cpu's on host.
        """
        host_topology = ll_hosts.get_host_topology(conf.HOSTS[0])
        cls.vms_new_parameters[conf.VM_NAME[0]] = {
            'cpu_socket': host_topology.sockets,
            'cpu_cores': host_topology.cores,
            'placement_host': conf.HOSTS[0]
        }
        super(TestCpuFilter, cls).setup_class()

    @polarion("RHEVM3-9481")
    def test_check_filter(self):
        """
        Check if vm success to run
        """
        logger.info(
            "Start vm %s on host %s", conf.VM_NAME[0], conf.HOSTS[0]
        )
        self.assertTrue(
            ll_vms.startVm(True, conf.VM_NAME[0]), "Vm failed to run"
        )
        logger.info(
            "Check that vm %s started on host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        self.assertEqual(
            conf.HOSTS[0], ll_vms.get_vm_host(conf.VM_NAME[0]),
            "Vm run on different host."
        )
        dst_host_topology = ll_hosts.get_host_topology(conf.HOSTS[1])
        dst_host_cpus = dst_host_topology.cores * dst_host_topology.sockets
        v_sockets = self.vms_new_parameters[conf.VM_NAME[0]]['cpu_socket']
        v_cores = self.vms_new_parameters[conf.VM_NAME[0]]['cpu_cores']
        migrate_bool = True if dst_host_cpus >= v_sockets * v_cores else False
        logger.info("Try to migrate vm %s", conf.VM_NAME[0])
        self.assertTrue(ll_vms.migrateVm(migrate_bool, conf.VM_NAME[0]))


class TestNegativeCpuFilter(UpdateVms):
    """
    Create new scheduling policy, with CPU filter and
    check that filter not prevent to start vm with correct number of vcpu's.
    """
    __test__ = True
    policy_name = 'negative_cpu_filter'
    policy_units = {
        conf.ENUMS['filter_cpu']: FILTER_TYPE,
        conf.ENUMS['filter_pin_to_host']: FILTER_TYPE
    }
    vms_new_parameters = {}
    old_parameters = {
        'cpu_socket': 1, 'cpu_cores': 1,
        'placement_host': conf.VM_ANY_HOST,
        'placement_affinity': conf.VM_MIGRATABLE
    }

    @classmethod
    def setup_class(cls):
        """
        Change vm vcpu to exact number of cpu's on host.
        """
        host_topology = ll_hosts.get_host_topology(conf.HOSTS[0])
        cls.vms_new_parameters[conf.VM_NAME[0]] = {
            'cpu_socket': host_topology.sockets,
            'cpu_cores': host_topology.cores * 2,
            'placement_host': conf.HOSTS[0],
            'placement_affinity': conf.VM_PINNED
        }
        super(TestNegativeCpuFilter, cls).setup_class()

    @polarion("RHEVM3-9476")
    def test_check_filter(self):
        """
        Check if vm success to run
        """
        logger.info(
            "Start vm %s on host %s", conf.VM_NAME[0], conf.HOSTS[0]
        )
        self.assertFalse(
            ll_vms.startVm(True, conf.VM_NAME[0]), "Vm successed to run"
        )


class TestNetworkFilter(UpdateVms):
    """
    Create new scheduler policy with network filter and
    check that filter prevent to start vm on host without specific network.
    """
    __test__ = True
    apis = set(['rest', 'java', 'sdk'])
    policy_name = 'network_filter'
    policy_units = {
        conf.ENUMS['filter_network']: FILTER_TYPE,
        conf.ENUMS['filter_pin_to_host']: FILTER_TYPE
    }
    old_parameters = {
        'placement_host': conf.VM_ANY_HOST,
        'placement_affinity': conf.VM_MIGRATABLE
    }
    vms_new_parameters = {
        conf.VM_NAME[1]: {
            'placement_host': None,
            'placement_affinity': conf.VM_PINNED
        }
    }
    network_name = 'network_filter'

    @classmethod
    def setup_class(cls):
        """
        Create new network, attach it to one of hosts and
        update vm nic to use new network
        """
        if len(conf.VDS_HOSTS[0].nics) < 2:
            pytest.skip("%s does not have enough nics" % conf.VDS_HOSTS[0])
        logger.info(
            "Create new network %s and attach it to host %s",
            cls.network_name, conf.HOSTS[0]
        )
        if not hl_networks.createAndAttachNetworkSN(
            conf.DC_NAME[0], conf.CLUSTER_NAME[0],
            host=[conf.VDS_HOSTS[0]],
            auto_nics=[0], network_dict={cls.network_name: {"nic": 1}}
        ):
            raise errors.NetworkException("Failed to add new network")
        for vm in conf.VM_NAME[:2]:
            logger.info(
                "Update vm %s to use network %s", vm, cls.network_name
            )
            if not ll_vms.updateNic(
                True, vm, conf.NIC_NAME[0], network=cls.network_name
            ):
                raise errors.VMException("Failed to update vm nic")
        cls.vms_new_parameters[conf.VM_NAME[1]][
            'placement_host'
        ] = conf.HOSTS[1]
        super(TestNetworkFilter, cls).setup_class()

    @polarion("RHEVM3-9482")
    def test_check_filter(self):
        """
        Check if vms success to run
        """
        logger.info("Start vm %s", conf.VM_NAME[0])
        self.assertTrue(
            ll_vms.startVm(True, conf.VM_NAME[0]), "Vm failed to run"
        )
        logger.info(
            "Check if vm %s run on host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        self.assertEqual(
            ll_vms.get_vm_host(conf.VM_NAME[0]), conf.HOSTS[0],
            "Vm run on different host"
        )
        logger.info("Try to migrate vm %s", conf.VM_NAME[0])
        self.assertFalse(ll_vms.migrateVm(
            True, conf.VM_NAME[0]), "Migration successed"
        )
        logger.info(
            "Check that vm %s failed to run because network filter",
            conf.VM_NAME[1]
        )
        self.assertFalse(
            ll_vms.startVm(True, conf.VM_NAME[1]), "Vm success to run"
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove change vm network to old one, detach new network from host
        and remove new network
        """
        ll_vms.stop_vms_safely([conf.VM_NAME[0]])
        for vm in conf.VM_NAME[:2]:
            logger.info(
                "Update vm %s to use network %s", vm, conf.MGMT_BRIDGE
            )
            if not ll_vms.updateNic(
                True, vm, conf.NIC_NAME[0],
                network=conf.MGMT_BRIDGE
            ):
                raise errors.VMException("Failed to update vm nic")
        logger.info(
            "Remove and detach network %s", cls.network_name
        )
        if not hl_networks.remove_net_from_setup(
            [conf.HOSTS[0]], network=[cls.network_name],
            data_center=conf.DC_NAME[0]
        ):
            raise errors.HostException(
                "Failed to remove and detach network"
            )
        super(TestNetworkFilter, cls).teardown_class()
