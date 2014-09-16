"""
Scheduler - Scheduler Sanity Test
Check working of all build-in filter, weight and balance units.
"""
import random
import logging

from rhevmtests.sla import config

from art.unittest_lib import attr
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.unittest_lib import SlaTest as TestCase
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api
import art.rhevm_api.tests_lib.high_level.vms as high_vm_api
import art.rhevm_api.tests_lib.high_level.networks as high_network_api
import art.rhevm_api.tests_lib.low_level.clusters as cluster_api
import art.rhevm_api.tests_lib.low_level.scheduling_policies as sch_api
from art.rhevm_api.tests_lib.low_level.clusters import updateCluster

logger = logging.getLogger(__name__)

TCMS_PLAN_ID = '9904'

PINNED = config.ENUMS['vm_affinity_pinned']
ANY_HOST = config.ENUMS['placement_host_any_host_in_cluster']
MIGRATABLE = config.ENUMS['vm_affinity_migratable']

BUILD_IN_POLICIES = [
    config.ENUMS['scheduling_policy_power_saving'],
    config.ENUMS['scheduling_policy_evenly_distributed'],
    config.ENUMS['scheduling_policy_vm_evenly_distributed']
]

FILTER_TYPE = config.ENUMS['policy_unit_type_filter']


@attr(tier=1)
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
            if not sch_api.add_scheduling_policy_unit(
                    cls.policy_name, unit_name, unit_type
            ):
                raise errors.SchedulerException("Failed to add unit to policy")

    @classmethod
    def setup_class(cls):
        """
        Create new scheduler policy, populate it by units.
        """
        logger.info("Create new scheduler policy %s.", cls.policy_name)
        if not sch_api.add_new_scheduling_policy(
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
        if not sch_api.remove_scheduling_policy(cls.policy_name):
            raise errors.SchedulerException(
                "Failed to remove scheduler policy."
            )


@attr(tier=0)
class TestCRUD(TestCase):
    """
    Test class to create, update and remove cluster policy
    """
    __test__ = True
    policy_name = 'crud_policy'
    new_policy_name = 'new_crud_policy'

    @bz(
        {
            '1189095': {'engine': ['cli', 'sdk', 'java'], 'version': ['3.5']},
        }
    )
    @tcms(TCMS_PLAN_ID, '287142')
    def test_crud_check(self):
        """
        Create, update and remove cluster policy
        """
        logger.info("Create new scheduler policy %s.", self.policy_name)
        self.assertTrue(
            sch_api.add_new_scheduling_policy(name=self.policy_name),
            "Failed to create new cluster policy"
        )
        logger.info(
            "Update cluster policy %s name to %s",
            self.policy_name, self.new_policy_name
        )
        self.assertTrue(
            sch_api.update_scheduling_policy(
                self.policy_name, name=self.new_policy_name
            ), "Failed to update cluster policy"
        )
        logger.info("Remove cluster policy %s", self.new_policy_name)
        self.assertTrue(
            sch_api.remove_scheduling_policy(self.new_policy_name),
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
        logger.info(
            "Change cluster %s scheduler policy to %s.",
            config.CLUSTER_NAME[0], cls.policy_name
        )
        if not updateCluster(
                True, config.CLUSTER_NAME[0], scheduling_policy=cls.policy_name
        ):
            raise errors.ClusterException("Failed to update cluster.")

    @classmethod
    def teardown_class(cls):
        """
        Update cluster scheduler policy to None.
        """
        if not updateCluster(
                True, config.CLUSTER_NAME[0], scheduling_policy='none'
        ):
            raise errors.ClusterException("Failed to update cluster.")
        super(AttachPolicyToCluster, cls).teardown_class()


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
            if not vm_api.updateVm(True, vm, **params):
                raise errors.VMException("Failed to update vm")

    @classmethod
    def teardown_class(cls):
        """
        Stop and update vm.
        """
        vm_api.stop_vms_safely(config.VM_NAME[:2])
        for vm in cls.vms_new_parameters.iterkeys():
            logger.info(
                "Update vm %s with parameters %s.", vm, cls.old_parameters
            )
            if not vm_api.updateVm(True, vm, **cls.old_parameters):
                raise errors.VMException("Failed to update vm")

        super(UpdateVms, cls).teardown_class()


class TestDeletePolicyInUse(AttachPolicyToCluster):
    """
    Negative: Try to delete scheduler policy,
    when it attached to one of clusters.
    """
    __test__ = True
    policy_name = 'delete_policy_in_use'

    @bz(
        {
            '1189095': {'engine': ['cli', 'sdk', 'java'], 'version': ['3.5']}
        }
    )
    @tcms(TCMS_PLAN_ID, '287260')
    def test_delete_policy(self):
        """
        Delete attached policy
        """
        self.assertFalse(sch_api.remove_scheduling_policy(self.policy_name))


@attr(tier=0)
class TestRemoveBuildInPolicy(TestCase):
    """
    Negative: remove build-in scheduler policy.
    """

    @tcms(TCMS_PLAN_ID, '287261')
    def test_delete_policy(self):
        """
        Delete build-in policy.
        """
        policy_to_remove = random.choice(BUILD_IN_POLICIES)
        self.assertFalse(sch_api.remove_scheduling_policy(policy_to_remove))


class TestPinToHostFilter(UpdateVms):
    """
    Check vm start and migration under PinToHost filter.
    """
    __test__ = True
    policy_name = 'check_pin_to_host'
    policy_units = {config.ENUMS['filter_pin_to_host']: FILTER_TYPE}
    vms_new_parameters = {
        config.VM_NAME[0]: {
            'placement_host': config.HOSTS[0], 'placement_affinity': PINNED
        }
    }
    old_parameters = {
        'placement_host': ANY_HOST, 'placement_affinity': MIGRATABLE
    }

    @tcms(TCMS_PLAN_ID, '287262')
    def test_check_filter(self):
        """
        Check filter.
        """
        logger.info("Start vm %s", config.VM_NAME[0])
        self.assertTrue(
            vm_api.startVm(True, config.VM_NAME[0]), "Failed to run vm."
        )
        logger.info(
            "Check if vm %s, started on host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )
        self.assertEqual(
            config.HOSTS[0], vm_api.get_vm_host(config.VM_NAME[0]),
            "Vm run on different host."
        )
        logger.info("Try to migrate pinned vm %s", config.VM_NAME[0])
        self.assertFalse(
            vm_api.migrateVm(True, config.VM_NAME[0]),
            "Migration successed"
        )


class TestNegativePinToHostFilter(UpdateVms):
    """
    Negative: Check PinToHost filter,
    deactivate host where vm pinned and start vm
    """
    __test__ = False
    policy_name = 'negative_check_pin_to_host'
    policy_units = {config.ENUMS['filter_pin_to_host']: FILTER_TYPE}
    vms_new_parameters = {
        config.VM_NAME[0]: {
            'placement_host': config.HOSTS[0], 'placement_affinity': PINNED
        }
    }
    old_parameters = {
        'placement_host': ANY_HOST, 'placement_affinity': MIGRATABLE
    }

    @classmethod
    def setup_class(cls):
        """
        Deactivate one of hosts.
        """
        super(TestNegativePinToHostFilter, cls).setup_class()
        logger.info("Deactivate host %s.", config.HOSTS[0])
        if not host_api.deactivateHost(True, config.HOSTS[0]):
            raise errors.HostException("Failed to deactivate host.")

    @tcms(TCMS_PLAN_ID, '447691')
    def test_check_filter(self):
        """
        Check filter.
        """
        logger.info("Start vm %s", config.VM_NAME[0])
        self.assertFalse(
            vm_api.startVm(True, config.VM_NAME[0]),
            "Success to run vm on other host"
        )

    @classmethod
    def teardown_class(cls):
        """
        Activate host.
        """

        logger.info("Activate host %s.", config.HOSTS[0])
        if not host_api.activateHost(True, config.HOSTS[0]):
            raise errors.HostException("Failed to activate host.")
        super(TestNegativePinToHostFilter, cls).setup_class()


class TestMemoryFilter(UpdateVms):
    """
    Create new scheduler policy with memory filter
    and check that filter prevent to start or migrate vm.
    """
    __test__ = True
    policy_name = 'memory_filter'
    policy_units = {config.ENUMS['filter_memory']: FILTER_TYPE}
    vms_new_parameters = {}
    old_parameters = {
        'memory': config.GB, 'memory_guaranteed': config.GB, 'os_type': 'other'
    }

    @classmethod
    def setup_class(cls):
        """
        Change vms memory to prevent start of vms on the same host
        """
        logger.info(
            "Update cluster %s over commit to 100 percent",
            config.CLUSTER_NAME[0]
        )
        if not cluster_api.updateCluster(
                True, config.CLUSTER_NAME[0], mem_ovrcmt_prc=0
        ):
            raise errors.ClusterException("Failed to update cluster")
        host_list = config.HOSTS[:2]
        hosts_mem = high_vm_api.calculate_memory_for_memory_filter(host_list)
        vm_memory_dict = dict(zip(config.VM_NAME[:2], hosts_mem))
        for vm, memory in vm_memory_dict.iteritems():
            cls.vms_new_parameters[vm] = {
                'memory': memory, 'memory_guaranteed': memory,
                'os_type': 'rhel_6x64'
            }
        super(TestMemoryFilter, cls).setup_class()
        logger.info("Start vms %s", config.VM_NAME[:2])
        vm_api.start_vms(config.VM_NAME[:2], max_workers=2, wait_for_ip=False)

    @bz({'1142081': {'engine': None, 'version': ['3.5']}})
    @tcms(TCMS_PLAN_ID, '287263')
    def test_check_filter(self):
        """
        Check if vms start on different hosts, because memory filter and
        that migration failed because memory filter
        """
        logger.info(
            "Check if vm %s and %s run on different hosts",
            config.VM_NAME[0], config.VM_NAME[1]
        )
        self.assertNotEqual(
            vm_api.get_vm_host(config.VM_NAME[0]),
            vm_api.get_vm_host(config.VM_NAME[1]),
            "Vms started on the same host."
        )
        logger.info("Try to migrate vm %s", config.VM_NAME[0])
        self.assertFalse(vm_api.migrateVm(
            True, config.VM_NAME[0]), "Migration successed"
        )


class TestCpuFilter(UpdateVms):
    """
    Create new scheduling policy, with CPU filter and
    check that filter not prevent to start vm with correct number of vcpu's.
    """
    __test__ = True
    policy_name = 'cpu_filter'
    policy_units = {
        config.ENUMS['filter_cpu']: FILTER_TYPE,
        config.ENUMS['filter_pin_to_host']: FILTER_TYPE
    }
    vms_new_parameters = {}
    old_parameters = {
        'cpu_socket': 1, 'cpu_cores': 1, 'placement_host': ANY_HOST
    }

    @classmethod
    def setup_class(cls):
        """
        Change vm vcpu to exact number of cpu's on host.
        """
        host_topology = host_api.get_host_topology(config.HOSTS[0])
        cls.vms_new_parameters[config.VM_NAME[0]] = {
            'cpu_socket': host_topology.sockets,
            'cpu_cores': host_topology.cores,
            'placement_host': config.HOSTS[0]
        }
        super(TestCpuFilter, cls).setup_class()

    @tcms(TCMS_PLAN_ID, '287453')
    def test_check_filter(self):
        """
        Check if vm success to run
        """
        logger.info(
            "Start vm %s on host %s", config.VM_NAME[0], config.HOSTS[0]
        )
        self.assertTrue(
            vm_api.startVm(True, config.VM_NAME[0]), "Vm failed to run"
        )
        logger.info(
            "Check that vm %s started on host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )
        self.assertEqual(
            config.HOSTS[0], vm_api.get_vm_host(config.VM_NAME[0]),
            "Vm run on different host."
        )
        dst_host_topology = host_api.get_host_topology(config.HOSTS[1])
        dst_host_cpus = dst_host_topology.cores * dst_host_topology.sockets
        v_sockets = self.vms_new_parameters[config.VM_NAME[0]]['cpu_socket']
        v_cores = self.vms_new_parameters[config.VM_NAME[0]]['cpu_cores']
        migrate_bool = True if dst_host_cpus >= v_sockets * v_cores else False
        logger.info("Try to migrate vm %s", config.VM_NAME[0])
        self.assertTrue(vm_api.migrateVm(migrate_bool, config.VM_NAME[0]))


class TestNegativeCpuFilter(UpdateVms):
    """
    Create new scheduling policy, with CPU filter and
    check that filter not prevent to start vm with correct number of vcpu's.
    """
    __test__ = True
    policy_name = 'negative_cpu_filter'
    policy_units = {
        config.ENUMS['filter_cpu']: FILTER_TYPE,
        config.ENUMS['filter_pin_to_host']: FILTER_TYPE
    }
    vms_new_parameters = {}
    old_parameters = {
        'cpu_socket': 1, 'cpu_cores': 1,
        'placement_host': ANY_HOST, 'placement_affinity': MIGRATABLE
    }

    @classmethod
    def setup_class(cls):
        """
        Change vm vcpu to exact number of cpu's on host.
        """
        host_topology = host_api.get_host_topology(config.HOSTS[0])
        cls.vms_new_parameters[config.VM_NAME[0]] = {
            'cpu_socket': host_topology.sockets,
            'cpu_cores': host_topology.cores * 2,
            'placement_host': config.HOSTS[0],
            'placement_affinity': PINNED
        }
        super(TestNegativeCpuFilter, cls).setup_class()

    @tcms(TCMS_PLAN_ID, '447692')
    def test_check_filter(self):
        """
        Check if vm success to run
        """
        logger.info(
            "Start vm %s on host %s", config.VM_NAME[0], config.HOSTS[0]
        )
        self.assertFalse(
            vm_api.startVm(True, config.VM_NAME[0]), "Vm successed to run"
        )


class TestNetworkFilter(UpdateVms):
    """
    Create new scheduler policy with network filter and
    check that filter prevent to start vm on host without specific network.
    """
    __test__ = True
    policy_name = 'network_filter'
    policy_units = {
        config.ENUMS['filter_network']: FILTER_TYPE,
        config.ENUMS['filter_pin_to_host']: FILTER_TYPE
    }
    old_parameters = {
        'placement_host': ANY_HOST, 'placement_affinity': MIGRATABLE
    }
    vms_new_parameters = {
        config.VM_NAME[1]: {
            'placement_host': config.HOSTS[1], 'placement_affinity': PINNED
        }
    }
    network_name = 'network_filter'

    @classmethod
    def setup_class(cls):
        """
        Create new network, attach it to one of hosts and
        update vm nic to use new network
        """
        super(TestNetworkFilter, cls).setup_class()
        logger.info(
            "Create new network %s and attach it to host %s",
            cls.network_name, config.HOSTS[0]
        )
        if not high_network_api.createAndAttachNetworkSN(
            config.DC_NAME[0], config.CLUSTER_NAME[0],
            host=[config.VDS_HOSTS[0]],
            auto_nics=[0], network_dict={cls.network_name: {"nic": 1}}
        ):
            raise errors.NetworkException("Failed to add new network")
        for vm in config.VM_NAME[:2]:
            logger.info("Update vm %s to use network %s", vm, cls.network_name)
            if not vm_api.updateNic(
                    True, vm, config.NIC_NAME[0], network=cls.network_name
            ):
                raise errors.VMException("Failed to update vm nic")

    @tcms(TCMS_PLAN_ID, '287454')
    def test_check_filter(self):
        """
        Check if vms success to run
        """
        logger.info("Start vm %s", config.VM_NAME[0])
        self.assertTrue(
            vm_api.startVm(True, config.VM_NAME[0]), "Vm failed to run"
        )
        logger.info(
            "Check if vm %s run on host %s", config.VM_NAME[0], config.HOSTS[0]
        )
        self.assertEqual(
            vm_api.get_vm_host(config.VM_NAME[0]), config.HOSTS[0],
            "Vm run on different host"
        )
        logger.info("Try to migrate vm %s", config.VM_NAME[0])
        self.assertFalse(vm_api.migrateVm(
            True, config.VM_NAME[0]), "Migration successed"
        )
        logger.info(
            "Check that vm %s failed to run because network filter",
            config.VM_NAME[1]
        )
        self.assertFalse(
            vm_api.startVm(True, config.VM_NAME[1]), "Vm success to run"
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove change vm network to old one, detach new network from host
        and remove new network
        """
        vm_api.stop_vms_safely([config.VM_NAME[0]])
        for vm in config.VM_NAME[:2]:
            logger.info(
                "Update vm %s to use network %s", vm, config.MGMT_BRIDGE
            )
            if not vm_api.updateNic(
                    True, vm, config.NIC_NAME[0], network=config.MGMT_BRIDGE
            ):
                raise errors.VMException("Failed to update vm nic")
        logger.info(
            "Remove and detach network %s", cls.network_name
        )
        if not high_network_api.remove_net_from_setup(
                [config.VDS_HOSTS[0]], network=[cls.network_name],
                data_center=config.DC_NAME[0]
        ):
            raise errors.HostException("Failed to remove and detach network")
        super(TestNetworkFilter, cls).teardown_class()
