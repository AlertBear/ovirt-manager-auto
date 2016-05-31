"""
Hot Plug CPU - Testing
- Test hot plug cpu
- Test that the number of CPUs changed is also changed on the VM OS
- Test hot plug with host maximum cpu
- Test migration after hot plug cpu
- Test CPU hot plug while threads is enabled on the cluster.
- Negative test: check hot plug cpu while migration
- Negative test: check hot unplug while cores are pinned
"""
import pytest
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import VirtTest as TestCase
from art.unittest_lib.common import attr
from rhevmtests import helpers
from rhevmtests.virt import config
from rhevmtests.virt import helper
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.test_handler.exceptions as errors

logger = config.logging.getLogger(__name__)
NPROC_COMMAND = 'nproc'
MAX_NUM_CORES_PER_SOCKET = 16


class BaseCPUHotPlugClass(TestCase):
    """
    Base Class for hot plug cpu
    """

    @classmethod
    def get_number_of_cores(cls, resource):
        """
        Get the number of cores on the resource using `nproc` command
        :param resource: the resource of the VM/host
        :type: resource: VM/Host resource
        :return: the number of cores on the host
        :rtype: int
        """

        logger.info(
            "Run %s on %s in order to get the number of cores",
            NPROC_COMMAND, resource
        )
        rc, out, _ = resource.run_command([NPROC_COMMAND])
        if rc:
            return 0
        logger.info("Number of cores on:%s is:%s", resource, out)
        return int(out)

    @classmethod
    def calculate_the_cpu_topology(cls, cpu_number):
        """
        Calculate the cpu topology (cores and sockets) with some limitations:
        - Maximum number of cores per socket is 16
        - A prime number of CPU can't be set

        :param cpu_number: the total number of CPU
        :type cpu_number: int
        :return: list with cpu_socket and cpu_core
        :rtype: list
        """
        if cpu_number > MAX_NUM_CORES_PER_SOCKET:
            for number in range(2, cpu_number):
                if cpu_number % number == 0:
                    cpu_core = number
                    cpu_socket = cpu_number / number
                    if cpu_socket <= MAX_NUM_CORES_PER_SOCKET:
                        break
            else:
                errors.TestException(
                    "Can't set cpu_topology with %d, because it's a primary"
                    " number that is larger then %s"
                    % cpu_number, MAX_NUM_CORES_PER_SOCKET
                )
        else:
            cpu_socket = cpu_number
            cpu_core = 1
        logger.info("cpu socket:%d, cpu_core:%d", cpu_socket, cpu_core)
        return cpu_socket, cpu_core

    @classmethod
    def setup_class(cls):
        """
        Update vm cpu socket and core
        :raise: errors.VMException
        """
        logger.info(
            "Update VM %s CPUs to %s cores * %s sockets",
            config.VM_NAME[0], cls.cpu_cores, cls.cpu_socket
        )
        if not ll_vms.updateVm(
            True, config.VM_NAME[0],
            cpu_cores=cls.cpu_cores,
            cpu_socket=cls.cpu_socket
        ):
            raise errors.VMException(
                "Failed to update VM %s" % config.VM_NAME[0]
            )
        logger.info("Start VM %s", config.VM_NAME[0])
        if not ll_vms.startVm(
            True, config.VM_NAME[0],
            wait_for_ip=True,
            wait_for_status=config.VM_UP
        ):
            raise errors.VMException(
                "Failed to start VM %s" % config.VM_NAME[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Stop Vm and update cores and sockets to 1
        """
        logger.info("Stop VM %s", config.VM_NAME[0])
        if not ll_vms.stopVm(True, config.VM_NAME[0]):
            logger.error("Failed to stop VM %s", config.VM_NAME[0])
        logger.info("Update VM %s cores and sockets to 1", config.VM_NAME[0])
        if not ll_vms.updateVm(
            True, config.VM_NAME[0],
            cpu_cores=1,
            cpu_socket=1
        ):
            logger.error("Failed to update VM %s" % config.VM_NAME[0])


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@attr(tier=1)
class TestAddCPUHotPlug(BaseCPUHotPlugClass):
    """
    Test cpu hot plug when increasing the cpu sockets number
    while VM is running.
    """

    __test__ = True
    cpu_cores = 1
    cpu_socket = 1

    @polarion("RHEVM3-9638")
    def test_a_migrate_vm_hot_plugged_with_CPUs(self):
        """
        Test migration after increasing the number of CPUs
        """
        self.assertTrue(
            ll_vms.updateVm(True, config.VM_NAME[0], cpu_socket=2),
            "Failed to Increasing the the number of cpu_sockets"
        )
        self.assertTrue(
            ll_vms.migrateVm(True, config.VM_NAME[0], wait=True),
            "Failed To migrate VM %s after increasing the "
            "number of cpu sockets" % config.VM_NAME[0]
        )
        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(config.VM_NAME[0]), config.VMS_LINUX_PW
        )
        self.assertEqual(
            self.get_number_of_cores(vm_resource), 2,
            "The Cores number should be 2 and not: %s" %
            ll_vms.get_vm_cores(config.VM_NAME[0])
        )

    @polarion("RHEVM3-9628")
    def test_b_add_cpu(self):
        """
        Increase CPU sockets while VM is running
        """
        logger.info("Add sockets to VM %s", config.VM_NAME[0])
        self.assertTrue(
            ll_vms.updateVm(True, config.VM_NAME[0], cpu_socket=4),
            "Can't update number of sockets on VM %s" % config.VM_NAME[0]
        )

    @polarion("RHEVM3-9627")
    def test_c_system(self):
        """
        Test that the number of CPUs changed is also changed on the VM OS
        """
        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(config.VM_NAME[0]), config.VMS_LINUX_PW
        )
        working_cores = self.get_number_of_cores(vm_resource)
        self.assertEqual(
            working_cores, 4,
            "The number of working cores: %s isn't correct" % working_cores
        )

    @polarion("RHEVM3-9639")
    def test_d_add_max_cpu(self):
        """
        Increase The number of CPUs to host cpu number, while VM is running
        """
        logger.info("Get the number of host CPUs")
        host_index = config.HOSTS.index(ll_vms.get_vm_host(config.VM_NAME[0]))
        cpu_number = self.get_number_of_cores(config.VDS_HOSTS[host_index])
        self.assertTrue(
            ll_vms.updateVm(
                True, config.VM_NAME[0], cpu_cores=1, cpu_socket=cpu_number
            ),
            "Failed to update VM %s cpu sockets to host Cpus cores" %
            config.VM_NAME[0]
        )


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@attr(tier=1)
class TestNegativeCpuPiningHotPlug(BaseCPUHotPlugClass):
    """
    Negative test -
    Have a VM with cpu pinning defined to 3 first CPUs, in ordered manner.
    Hot unplug 2 CPUs while VM is running.
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Update VM with cpu pinning defined to 3 first CPUs, in ordered manner
        and update the Vm CPUs to 4
        """
        logger.info(
            "Update VM %s CPUs to 2 cores * 2 sockets and pin",
            config.VM_NAME[0]
        )
        vcpu_pinning = ([{str(i): str(i)} for i in range(3)])
        if not ll_vms.updateVm(
            True, config.VM_NAME[0],
            cpu_cores=2, cpu_socket=2,
            placement_affinity=config.VM_PINNED,
            placement_host=config.HOSTS[0],
            vcpu_pinning=vcpu_pinning
        ):
            raise errors.VMException(
                "Failed to update VM %s cpu and pinning" % config.VM_NAME[0]
            )

    @polarion("RHEVM3-9629")
    def test_negative_cpu_pinning(self):
        """
        Negative test - unplug vm CPUs while
        cpu pinning defined to 3 first CPUs and VM is running
        """
        logger.info("Start VM %s", config.VM_NAME[0])
        self.assertTrue(
            ll_vms.startVm(True, config.VM_NAME[0], wait_for_ip=True),
            "Failed to start VM %s" % config.VM_NAME[0]
        )
        logger.info("Remove cores from VM %s", config.VM_NAME[0])
        self.assertFalse(
            ll_vms.updateVm(True, config.VM_NAME[0], cpu_socket=1),
            "The action of remove cores didn't failed"
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove CPU pinning from VM
        """
        logger.info("Remove CPU pinning from VM %s " % config.VM_NAME[0])
        if not ll_vms.updateVm(
            True, config.VM_NAME[0],
            placement_affinity=config.VM_MIGRATABLE,
            placement_host=config.VM_ANY_HOST,
            vcpu_pinning=[],
        ):
            logger.error(
                "Failed to remove host pinning from VM %s", config.VM_NAME[1]
            )
        super(TestNegativeCpuPiningHotPlug, cls).teardown_class()


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@attr(tier=1)
class TestHotPlugDuringMigration(BaseCPUHotPlugClass):
    """
    Negative test- testing hot plug during migration
    """

    __test__ = True
    cpu_cores = 2
    cpu_socket = 1

    @classmethod
    def setup_class(cls):
        """
        Create memory load on the vm
        so that the migration process will be very slow
        """
        super(TestHotPlugDuringMigration, cls).setup_class()
        logger.info("Load VM %s memory", config.VM_NAME[0])
        if not helper.load_vm_memory(config.VM_NAME[0], memory_size='0.5'):
            raise errors.VMException(
                "Failed to load VM %s memory" % config.VM_NAME[0]
            )
        logger.info("Migrate VM %s", config.VM_NAME[0])
        if not ll_vms.migrateVm(True, config.VM_NAME[0], wait=False):
            raise errors.VMException(
                "Failed to migrate VM %s" % config.VM_NAME[0]
            )

    @polarion("RHEVM3-9637")
    def test_negative_hotplug_during_migration(self):
        """
        Test hot plug while migrating VM
        """
        logger.info("Update VM %s cpu socket to 2", config.VM_NAME[0])
        self.assertFalse(
            ll_vms.updateVm(True, config.VM_NAME[0], cpu_socket=2),
            "hot plug  worked while migrating VM "
        )

    @classmethod
    def teardown_class(cls):
        """
        Cancel migration
        """
        if ll_vms.get_vm_state == "migrating":
            hl_vms.cancel_vm_migrate(config.VM_NAME[0])
        super(TestHotPlugDuringMigration, cls).teardown_class()


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@attr(tier=1)
class TestCpuThreadHotPlug(BaseCPUHotPlugClass):
    """
    Test CPU hot plug while threads is enabled on the cluster.
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Enable threads on the cluster, pin vm to a specific host,
        Change the vm CPU core and socket.
        """
        logger.info("Enable threads on cluster %s", config.CLUSTER_NAME[0])
        if not ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0], threads=True
        ):
            raise errors.ClusterException(
                "Failed to enable threads on cluster %s" %
                config.CLUSTER_NAME[0]
            )
        logger.info(
            "pin VM %s to host %s and update the VM CPUs",
            config.VM_NAME[0], config.HOSTS[0]
        )
        cpu_number = cls.get_number_of_cores(config.VDS_HOSTS[0]) * 2
        cpu_topology = cls.calculate_the_cpu_topology(cpu_number)
        if not ll_vms.updateVm(
            True, config.VM_NAME[0],
            placement_host=config.HOSTS[0], cpu_core=cpu_topology[1]
        ):
            raise errors.VMException(
                "Failed to update vm %s" % config.VM_NAME[0]
            )

        if not ll_vms.startVm(True, config.VM_NAME[0], wait_for_ip=True):
            raise errors.VMException(
                "Failed to start VM %s" % config.VM_NAME[0]
            )

    @polarion("RHEVM3-9630")
    def test_thread_cpu(self):
        """
        Test CPU hot plug while threads is enabled on the cluster
        """
        cpu_number = self.get_number_of_cores(config.VDS_HOSTS[0]) * 2
        cpu_topology = self.calculate_the_cpu_topology(cpu_number)
        self.assertTrue(
            ll_vms.updateVm(
                True, config.VM_NAME[0], cpu_socket=cpu_topology[0]
            ),
            "Failed to update VM %s cpu socket to %s" %
            (config.VM_NAME[0], cpu_number)
        )

    @classmethod
    def teardown_class(cls):
        """
        Update the CPU core and socket
        And disable the threads on the cluster
        """
        super(TestCpuThreadHotPlug, cls).teardown_class()
        logger.info("Disable threads on %s", config.CLUSTER_NAME[0])
        if not ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0], threads=False
        ):
            logger.error(
                "Failed to enable threads on %s" % config.CLUSTER_NAME[0]
            )
