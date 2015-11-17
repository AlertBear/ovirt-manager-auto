"""
Testing memory overcomitment manager consisting of KSM and ballooning
Prerequisites: 1 DC, 2 hosts, 1 SD (NFS), 1 export domain
Tests covers:
    KSM
        progressive startup of VMs
        1 moment startup of multiple VMs
        KSM with migration of VMs
        and stopping KSM by migrating VM
    Balloon
        testing inflation and deflation of ballooning on
        1 VM, 2 VMs with different memories options, different OS,
        VM with memory set to max guaranteed memory, VM without guest
        agent, multiple VMs on one host with ballooning enabled
"""
from art.unittest_lib import SlaTest as TestCase, attr
import logging
import config
from time import sleep
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import clusters
import art.rhevm_api.tests_lib.high_level.hosts as h_hosts
import art.test_handler.exceptions as errors
from art.test_handler import find_test_file
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.rhevm_api.utils.test_utils import getStat
import rhevmtests.helpers as helpers

logger = logging.getLogger(__name__)
find_test_file.__test__ = False

SLEEP_TIME = 20
WAIT_FOR_IP_TIMEOUT = 300
BALLOON_ITERATIONS = 25  # number of iterations for testing test ballooning
MEMORY_OVERCOMMITMENT = 200
NONE_MEMORY_OVERCOMMITMENT = 100
HOST_ALLOC_PATH = "/tmp/hostAlloc.py"
ALLOC_SCRIPT_LOCAL = "tests/rhevmtests/sla/mom/hostAlloc.py"
SERVICE_PUPPET = "puppet"
SERVICE_GUEST_AGENT = "ovirt-guest-agent"
########################################################################
#                             Base Class                               #
########################################################################


@attr(tier=2)
class MOM(TestCase):
    """
    Base class for vm watchdog operations
    """
    __test__ = False
    pid_list = []

    @classmethod
    def ksm_running(cls, host_resource):
        """
        Check if KSM is running on host

        :param host_resource: host resource
        :type host_resource: instance of VDS
        :returns: True if KSM run, otherwise False
        :rtype: bool
        :raises: HostException
        """
        rc, out, err = host_resource.executor().run_cmd(
            [
                "vdsClient", "-s", host_resource.ip,
                "getVdsStats", "|", "grep", "-i", "ksmState"
            ]
        )
        return True if "True" in out else False

    def allocate_host_memory(
            self, host_resource, perc=0.7, path=HOST_ALLOC_PATH
    ):
        """
        Saturate host memory to 70%

        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param perc: load host memory on specific percent
        :type perc: int
        :param path: path to allocation script
        :type path: str
        :returns: True and pid of allocated process, otherwise False and None
        :rtype: bool
        """
        out = None
        memory_allocated = False
        logger.info("copying allocate test file to host %s", host_resource)
        host_resource.copy_to(
            config.ENGINE_HOST, find_test_file(ALLOC_SCRIPT_LOCAL), path
        )

        for i in range(BALLOON_ITERATIONS):
            stats = getStat(
                hosts.get_host_name_from_engine(host_resource.ip),
                "host", "hosts", ["memory.free"]
            )

            allocate_memory = int(stats["memory.free"] * perc)
            logger.info(
                "Allocating %d B of memory on host %s",
                allocate_memory, host_resource.ip
            )
            rc, out, err = host_resource.executor().run_cmd(
                [
                    "python", path, str(allocate_memory),
                    "&>", "/tmp/OUT1", "&", "echo", "$!"
                ]
            )
            out = out.strip("\n\t ")
            if rc:
                logger.info("Failed to run script, err: %s", err)
            sleep(SLEEP_TIME)

            if host_resource.fs.exists("/proc/%s" % out):
                memory_allocated = True
                break

            logger.info("Last allocation failed creating new")

        return memory_allocated, out

    def cancel_host_allocation(self, pid, host_resource, path=HOST_ALLOC_PATH):
        """
        Cancel host host memory load

        :param pid: pid of process allocating memory
        :type pid: str
        :param host_resource: host resource
        :type host_resource: instance of VDS
        :param path: path to script allocating memory
        :type path: str
        :returns: True on success, otherwise False
        :rtype: bool
        """
        killed = False
        for i in range(BALLOON_ITERATIONS):
            host_resource.executor().run_cmd(["kill", "-9", pid])

            sleep(SLEEP_TIME)
            if not host_resource.fs.exists("/proc/%s" % pid):
                killed = True
                break

        return killed and host_resource.fs.remove(path)

    def prepare_balloon(self, sleep_mult=1, host_id=1):
        """
        Prepare environment for testing deflation of balloon

        :param sleep_mult: sleep multiplier
        :type sleep_mult: int
        :param host_id: host index
        :type host_id: int
        :returns: pid of allocation process
        :rtype: str
        """
        wait_time = sleep_mult * SLEEP_TIME
        logger.info(
            "Waiting %d s for guests to allocate memory on host %s",
            wait_time, config.HOSTS[host_id]
        )
        sleep(wait_time)

        rc, out = self.allocate_host_memory(config.VDS_HOSTS[host_id])
        self.assertTrue(
            rc,
            "Failed to allocate memory on host %s, output %s" %
            (config.HOSTS[host_id], out)
        )
        self.pid_list.append(out)
        logger.info("Host process pid allocating memory - %s", out)
        logger.info(
            "Waiting %d s for host %s to compute ballooning info",
            SLEEP_TIME, config.HOSTS[host_id]
        )
        sleep(SLEEP_TIME)
        return out

    def balloon_usage(self, vm_list, host_id=1):
        """
        Run balloon inflation and deflation tests

        :param vm_list: list of VMs to be tested
        :type vm_list: list
        :param host_id: host index
        :type host_id: int
        """
        logger.info("Start vms: %s", vm_list)
        vms.start_vms(vm_list)
        pid = self.prepare_balloon(len(vm_list))

        logger.info("Testing deflation of balloon")
        self.assertTrue(
            self.deflation(vm_list),
            "Deflation of balloons is not working properly"
        )
        self.balloon_clean([], pid)

        logger.info(
            "Waiting %d s for host %s to compute ballooning info",
            SLEEP_TIME, config.HOSTS[host_id]
        )
        sleep(SLEEP_TIME)
        logger.info("Testing inflation of balloon")
        self.assertTrue(
            self.deflation(vm_list, False),
            "Inflation of balloon not working properly"
        )

    def balloon_usage_negative(self, vm):
        """
        Run negative tests,of deflation of balloons
        Testing should succeed on VMs without guest agent and
        with memory set to Minimum Guaranteed memory

        :param vm: vm_name
        :type vm: str
        :returns: True, if method success, otherwise False
        :rtype: bool
        """
        self.prepare_balloon()
        return self.deflation([vm], True, True)

    def get_vm_mem_stats(self, vm_list):
        """
        Create dict with vm name and his current balloon and max balloon
        the information comes from vdsClient command.

        :param vm_list: list of vm names
        :type vm_list: list
        :return: dict with vm name and his current balloon and max balloon
        """
        mom_dict = {}
        for vm in vm_list:
            vm_id = vms.get_vm(vm).get_id()
            rc, out, error = config.VDS_HOSTS[1].executor().run_cmd(
                [
                    "vdsClient", "-s", config.VDS_HOSTS[1].ip,
                    "getVmStats", str(vm_id), "|", "grep",
                    "balloonInfo", "|", "cut", "-d=", "-f2"
                ]
            )
            try:
                mom_dict[vm] = eval(out.strip())
                logger.info(
                    "VM %s - balloons max: %s, current: %s",
                    vm, mom_dict[vm]["balloon_max"],
                    mom_dict[vm]["balloon_cur"]
                )
            except SyntaxError:
                logger.error("failed to obtain ballooning statistics")
        return mom_dict

    def balloon_clean(self, vm_list, pid, dealloc=True, host_id=1):
        """
        Stop all running VMs and cancel host memory allocation

        :param vm_list: list of vms
        :type vm_list: list
        :param pid: pid of host memory allocation process
        :type pid: str
        :param dealloc: enable cancelling the memory allocation
        :type dealloc: bool
        :param host_id: host index
        :type host_id: int
        """
        sleep(SLEEP_TIME)
        if vm_list:
            logger.info("Stop vms: %s", vm_list)
            vms.stop_vms_safely(vm_list)
        if dealloc and self.pid_list:
            rc = self.cancel_host_allocation(pid, config.VDS_HOSTS[host_id])
            self.assertTrue(
                rc,
                "Failed to cancel memory load on host %s"
                % config.HOSTS[host_id]
            )
            self.pid_list.pop()

    def deflation(self, vm_list, deflation=True, negative_test=False):
        """
        If deflation is True, checking ballooning deflation
        it means if the current memory < max memory

        if deflation is False, checking ballooning Inflation
        it means if the current memory = max memory

        :param vm_list: list of vms on which the deflation/inflation will run
        :type vm_list: list
        :param deflation: True if deflation, False if Inflation
        :type deflation: bool
        :param negative_test: True if negative test, False otherwise
        :type negative_test: bool
        :return: True if deflation or inflation passed, False otherwise

        """

        for i in range(BALLOON_ITERATIONS):
            logger.info(
                "Iteration number %d out of %d", i + 1, BALLOON_ITERATIONS
            )
            mem_dict = self.get_vm_mem_stats(vm_list)
            if not mem_dict:
                logger.warning("Failed to obtain information from mom")
                continue

            if negative_test and deflation:
                vm = vm_list[0]
                self.assertEqual(
                    mem_dict[vm]["balloon_max"], mem_dict[vm]["balloon_cur"]
                )

            if deflation and not negative_test:

                for vm in vm_list:
                    if (int(mem_dict[vm]["balloon_max"]) >
                       int(mem_dict[vm]["balloon_cur"])):
                        logger.info("deflation is working!!!")
                        return True

            if not deflation:
                for vm in vm_list:
                    if (
                        mem_dict[vm]["balloon_max"] !=
                        mem_dict[vm]["balloon_cur"]
                    ):
                        break
                else:
                    logger.info("inflation is working!!!")
                    return True

            logger.info(
                "Waiting %d s for host %s to compute ballooning info",
                SLEEP_TIME, config.HOSTS[1]
            )
            sleep(SLEEP_TIME)
        return False


########################################################################
#                             Test Cases                               #
########################################################################


class KSM(MOM):
    """
    KSM tests
    """

    __test__ = True
    host_id = 0

    @classmethod
    def setup_class(cls):
        """
        KSM setup-
        pin all VMs to host
        change VMs memory
        disable balloon and enable ksm on cluster
        """
        stats = getStat(config.HOSTS[0], "host", "hosts", ["memory.free"])
        host_mem = stats["memory.free"]

        cls.threshold = []
        cls.vm_list = []
        cls.threshold_list = []

        logger.info(
            "Running KSM tests on host %s memory - %s B",
            config.HOSTS[0], str(host_mem)
        )
        for vm_index in range(int(config.VM_NUM)):
            vm = "%s-%s" % (config.POOL_NAME, str(vm_index + 1))
            cls.vm_list.append(vm)
            vm_mem = int(
                round(host_mem * 2 / config.VM_NUM / config.GB) * config.GB
            )
            user_migratable = config.ENUMS["vm_affinity_user_migratable"]
            if not vms.updateVm(
                    True, vm, placement_host=config.HOSTS[0],
                    placement_affinity=user_migratable,
                    memory=vm_mem, memory_guaranteed=vm_mem
            ):
                raise errors.VMException("Failed to update vm %s" % vm)
            logger.info(
                "Pinned vm %s with %s B memory, to host %s",
                vm, vm_mem, config.HOSTS[0]
            )
        if not clusters.updateCluster(
                True, config.CLUSTER_NAME[0], ksm_enabled=True,
                ballooning_enabled=False, mem_ovrcmt_prc=MEMORY_OVERCOMMITMENT
        ):
            raise errors.VMException("Failed to update cluster")

        h_hosts.restart_vdsm_and_wait_for_activation(
            [config.VDS_HOSTS[cls.host_id]],
            config.DC_NAME[0], config.STORAGE_NAME[0]
        )

        logger.info(
            "Cluster memory overcommitment percentage set to %d",
            MEMORY_OVERCOMMITMENT
        )

    @polarion("RHEVM3-4969")
    def test_a_ksm_progressive(self):
        """
        Finds the threshold where KSM starts
        """
        vm_started = []
        for vm in self.vm_list:
            logger.info("Start vm %s.", vm)
            self.assertTrue(
                vms.startVm(
                    positive=True, vm=vm,
                    wait_for_status=config.VM_UP
                ),
                "Failed to run Vm %s" % vm
            )
            vm_started.append(vm)
            logger.info(
                "Waiting %d for start of VM and guest agent",
                SLEEP_TIME
            )
            self.assertTrue(
                vms.waitForIP(vm, timeout=300), "Vm still not have ip"
            )
            sleep(SLEEP_TIME)
            self.threshold_list.append(vm)
            ksm_running = self.ksm_running(config.VDS_HOSTS[0])
            if ksm_running:
                self.threshold.append(int(vm[-1]))
                logger.info(
                    "KSM triggered on %s-th vm", self.threshold[0]
                )
                break
            else:
                logger.info("KSM not running after starting vm %s", vm)

        logger.info("Stop vms: %s", vm_started)
        vms.stop_vms_safely(vm_started)
        self.assertTrue(self.threshold[0], "KSM was not triggered")

    @polarion("RHEVM3-4977")
    def test_b_ksm_kicking(self):
        """
        Run VMs in one moment to trigger KSM
        """
        logger.info(
            "Running Vms that should trigger KSM: %s",
            " ,".join(self.threshold_list)
        )
        vms.start_vms(self.threshold_list, config.VM_NUM)
        logger.info(
            "VMs started, waiting %d for start of VM and guest agent",
            SLEEP_TIME * self.threshold[0]
        )
        sleep(SLEEP_TIME * self.threshold[0])
        self.assertTrue(
            self.ksm_running(config.VDS_HOSTS[0]),
            "KSM not running on %d vms" % self.threshold[0]
        )
        logger.info("KSM successfully triggered")

    @polarion("RHEVM3-4976")
    def test_c_ksm_migration(self):
        """
        Migrate VMs with KSM enabled
        """
        if (len(config.HOSTS)) < 2:
            raise errors.SkipTest("Too few hosts.")
        for vm in self.threshold_list:
            self.assertTrue(
                vms.migrateVm(True, vm, force=True),
                "Failed to migrate VM %s" % vm
            )

        logger.info("Waiting %d s", SLEEP_TIME * self.threshold[0])
        sleep(SLEEP_TIME * self.threshold[0])
        self.assertFalse(
            self.ksm_running(config.VDS_HOSTS[0]),
            "KSM still running after migration from host %s" % config.HOSTS[0]
        )
        if not self.ksm_running(config.VDS_HOSTS[1]):
            logger.warning(
                "KSM not running after migration on host %s", config.HOSTS[1]
            )
        logger.info("KSM successfully turned off after migration")

    @polarion("RHEVM3-4975")
    def test_d_ksm_stop(self):
        """
        Stop KSM by migrating to other host
        """
        if (len(config.HOSTS)) < 2:
            raise errors.SkipTest("Too few hosts.")

        for vm in self.threshold_list[:len(self.threshold_list) / 2]:
            self.assertTrue(
                vms.migrateVm(True, vm, force=True),
                "Cannot migrate VM %s" % vm
            )

        logger.info("Waiting %d s", SLEEP_TIME * self.threshold[0])
        sleep(SLEEP_TIME * self.threshold[0])
        self.assertFalse(
            self.ksm_running(config.VDS_HOSTS[0]),
            "KSM running after migration on host %s" % config.HOSTS[0]
        )
        logger.info("KSM successfully turned off after migration")

    @classmethod
    def teardown_class(cls):
        """
        Teardown ksm tests
        """
        logger.info("Stop vms: %s", cls.threshold_list)
        vms.stop_vms_safely(cls.threshold_list)
        if not clusters.updateCluster(
                True, config.CLUSTER_NAME[0], mem_ovrcmt_prc=100,
                ksm_enabled=True
        ):
            raise errors.VMException("Failed to update cluster")
        h_hosts.restart_vdsm_and_wait_for_activation(
            [config.VDS_HOSTS[cls.host_id]],
            config.DC_NAME[0], config.STORAGE_NAME[0]
        )


####################################################################

class Balloon(MOM):
    """
    Balloon tests
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create necessary VMS
        """
        if not clusters.updateCluster(
                True, config.CLUSTER_NAME[0], ballooning_enabled=True,
                ksm_enabled=False, mem_ovrcmt_prc=NONE_MEMORY_OVERCOMMITMENT
        ):
            raise errors.VMException("Failed to update cluster")

        h_hosts.restart_vdsm_and_wait_for_activation(
            config.VDS_HOSTS[:2], config.DC_NAME[0], config.STORAGE_NAME[0]
        )
        # vms for ballooning
        list_id = range(int(config.VM_NUM))
        vm_list = ["%s-%s" % (config.POOL_NAME, str(i + 1)) for i in list_id]
        # vm_list.extend(i["name"] for i in config.windows_images)

        for vm in vm_list:
            if not vms.updateVm(
                    True, vm, placement_host=config.HOSTS[1],
                    placement_affinity=config.VM_PINNED,
                    memory=2 * config.GB, memory_guaranteed=config.GB,
                    ballooning=True
            ):
                raise errors.VMException("Failed to update vm %s" % vm)

    @polarion("RHEVM3-4974")
    def test_a_balloon_usage(self):
        """
        Tests inflation and deflation of balloon
        """
        self.vm_list = ["%s-1" % config.POOL_NAME]
        self.balloon_usage(self.vm_list)

    @polarion("RHEVM3-4973")
    def test_b_balloon_multi_memory(self):
        """
        Tests inflation and deflation of balloon on 2 VMs
        with different memories
        """
        self.vm_list = ["%s-%d" % (config.POOL_NAME, i + 1) for i in range(2)]
        counter = 1
        memory = config.GB * 5 if config.PPC_ARCH else config.GB / 2
        for vm in self.vm_list:
            memory_guaranteed = memory - 128 * config.MB * counter
            self.assertTrue(
                vms.updateVm(
                    True, vm, memory=memory,
                    memory_guaranteed=memory_guaranteed
                ),
                "Vm update failed"
            )
            counter += 1

        self.balloon_usage(self.vm_list, 1)

    # TODO - create windows vm's in glance
    # @polarion("RHEVM3-4972")
    # def test_c_balloon_multi_os(self):
    #     """
    #     Test usage of balloon on different OS types
    #     """
    #     self.vm_list = [i["image"] for i in config.windows_images]
    #     self.balloon_usage(self.vm_list)

    @polarion("RHEVM3-4978")
    def test_d_balloon_max(self):
        """
        Negative test case of balloon with minimum
        guaranteed memory set to maximum memory
        """
        vm = "%s-%d" % (config.POOL_NAME, 1)
        self.vm_list = [vm]
        self.assertTrue(
            vms.updateVm(
                True, vm, memory=2*config.GB, memory_guaranteed=2 * config.GB
            ),
            "Failed to update rhel vm %s" % vm
        )
        self.assertTrue(
            vms.startVm(True, vm, wait_for_status=config.VM_UP),
            "Failed to start vm %s" % vm
        )
        self.balloon_usage_negative(vm)

    @polarion("RHEVM3-4971")
    def test_e_balloon_no_agent(self):
        """
        Negative test case to test balloon without agent
        """
        vm = "%s-%d" % (config.POOL_NAME, 1)
        self.vm_list = [vm]
        self.assertTrue(
            vms.updateVm(
                True, vm, memory=2 * config.GB, memory_guaranteed=config.GB
            ),
            "Failed to update rhel vm"
        )

        self.assertTrue(
            vms.startVm(True, vm, wait_for_status=config.VM_UP),
            "Failed to start vm %s" % vm
        )

        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(vm), config.VMS_LINUX_PW
        )
        if vm_resource.package_manager.exist(SERVICE_PUPPET):
            logger.info("remove %s", SERVICE_PUPPET)
            if not vm_resource.package_manager.remove(SERVICE_PUPPET):
                raise errors.VMException(
                    "Failed to remove %s" % SERVICE_PUPPET
                )

        logger.info("Stop %s service", SERVICE_GUEST_AGENT)
        if not vm_resource.service(SERVICE_GUEST_AGENT).stop():
            raise errors.VMException(
                "Failed to stop service %s on VM %s" %
                (SERVICE_GUEST_AGENT, vm)
            )
        self.balloon_usage_negative(vm)

    @polarion("RHEVM3-4970")
    def test_f_balloon_multiple_vms(self):
        """
        Test ballooning with multiple (8) small VMs
        """
        list_id = range(config.VM_NUM)
        if config.PPC_ARCH:
            memory = 2 * config.GB
            memory_guaranteed = config.GB
        else:
            memory = int(config.GB/4)
            memory_guaranteed = int(config.GB/8)
        self.vm_list = ["%s-%d" % (config.POOL_NAME, i + 1) for i in list_id]
        for vm in self.vm_list:
            self.assertTrue(
                vms.updateVm(
                    True, vm, memory=memory,
                    memory_guaranteed=memory_guaranteed
                ),
                "Vm update failed"
            )

        self.balloon_usage(self.vm_list)

    def setUp(self):
        if hosts.getHostState(config.HOSTS[1]) == config.HOST_NONOPERATIONAL:
            logger.info("Activate host %s.", config.HOSTS[1])
            if not hosts.activateHost(True, config.HOSTS[1]):
                raise errors.HostException("Failed to activate host")
        logger.info(
            "Wait %d second to get time to host up all vdsm services",
            SLEEP_TIME
        )
        sleep(SLEEP_TIME)

    def tearDown(self):
        if self.pid_list:
            self.balloon_clean(self.vm_list, self.pid_list[-1])
        else:
            self.balloon_clean(self.vm_list, "", False)

    @classmethod
    def teardown_class(cls):
        """
        Remove memory load from hosts
        """
        logger.info(
            "Pids of processes allocating memory - %s",
            " ".join(str(i) for i in cls.pid_list)
        )
        if cls.pid_list:
            cmd = ["kill", "-9"].extend(cls.pid_list)
            config.VDS_HOSTS[1].executor().run_cmd(cmd)

        if not clusters.updateCluster(
                True, config.CLUSTER_NAME[0], ballooning_enabled=False,
                ksm_enabled=True,
                mem_ovrcmt_prc=NONE_MEMORY_OVERCOMMITMENT
        ):
            logger.error("Failed to disable ballooning on cluster")

        h_hosts.restart_vdsm_and_wait_for_activation(
            config.VDS_HOSTS[:2], config.DC_NAME[0], config.STORAGE_NAME[0]
        )
