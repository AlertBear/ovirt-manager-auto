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
from art.unittest_lib import SlaTest as TestCase

import logging
import config

from time import sleep
from concurrent.futures import ThreadPoolExecutor

from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains

import art.test_handler.exceptions as errors

from art.test_handler import find_test_file
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.rhevm_api.utils.test_utils import getStat
from art.core_api.apis_utils import TimeoutingSampler
from art.core_api.apis_exceptions import APITimeout

from nose.plugins.attrib import attr

logger = logging.getLogger(__name__)

SLEEP_TIME = 20
WAIT_FOR_IP_TIMEOUT = 300
BALLOON_ITERATIONS = 25  # number of iterations for testing test ballooning
MULTI_VMS_ITERATIONS = 100  # number of iterations VMs with different memory
NEGATIVE_ITERATIONS = 10  # number of iterations for negative test cases
RESTART_VDSM_INDEX = 10  # index of restarting VDSM
MEMORY_OVERCOMMITMENT = 200
HOST_ALLOC_PATH = "/tmp/hostAlloc.py"
ALLOC_SCRIPT_LOCAL = "tests/rhevmtests/sla/mom/hostAlloc.py"
CURRENT = 0
MAX = 1


########################################################################
#                             Base Class                               #
########################################################################


@attr(tier=1)
class MOM(TestCase):
    """
    Base class for vm watchdog operations
    """
    __test__ = False
    pid_list = []

    @classmethod
    def _start_vms_and_check_status(cls, vm_list):
        """
        Start vms and check vms status

        :param vm_list: list of vms
        :type vm_list: list
        :returns: True, if all vms in state powering up or up, otherwise False
        :rtype: bool
        """
        vms.start_vms(vm_list, wait_for_status=None, wait_for_ip=False)
        logger.info(
            "Check that all vms %s have statuses %s or %s",
            vm_list, config.VM_POWERING_UP, config.VM_UP
        )
        for vm in vm_list:
            if vms.get_vm_state(vm) not in (
                    config.VM_POWERING_UP, config.VM_UP
            ):
                return False
        return True

    @classmethod
    def _wait_until_vms_start(cls, vm_list):
        """
        Wait until all vms up or powering up

        :param vm_list: list of vms
        :type vm_list: list
        :raises: VMException
        """
        sampler = TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            cls._start_vms_and_check_status, vm_list
        )
        try:
            for sample in sampler:
                if sample:
                    logger.info("All vms %s run", vm_list)
                    break
        except APITimeout:
            raise errors.VMException(
                "Timeout when waiting for all vms to up"
            )

    @classmethod
    def _wait_for_ip_multi_thread(cls, vm_list):
        """
        Wait for vms ip via ThreadPoolExecutor

        :param vm_list: vm list
        :type vm_list: list
        :raises: VMException
        """
        results = list()
        with ThreadPoolExecutor(max_workers=4) as executor:
            for vm in vm_list:
                logger.info("Wait for ip for vm %s", vm)
                results.append(
                    executor.submit(
                        vms.waitForIP, vm, timeout=WAIT_FOR_IP_TIMEOUT
                    )
                )
        for vm, res in zip(vm_list, results):
            if res.exception():
                logger.error(
                    "Got exception while waiting of ip of vm %s: %s",
                    vm, res.exception()
                )
                raise res.exception()
            if not res.result():
                raise errors.VMException("Vm %s still not have ip" % vm)

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
        rc, out, err = hosts.get_mom_statistics(host_resource)
        if not rc:
            raise errors.HostException(
                "Failed to obtain ksm_run, output - %s" % err
            )
        return out["host"]["ksm_run"]

    def allocate_host_memory(
            self, host_resource, perc=0.9, path=HOST_ALLOC_PATH
    ):
        """
        Saturate host memory to 90%

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

        logger.info("Testing deflation of balloon")
        return out

    def balloon_usage(self, vm_list, host_id=1, multi_os=False):
        """
        Test inflation and deflation of balloons

        :param vm_list: list of VMs to be tested
        :type vm_list: list
        :param host_id: host index
        :type host_id: int
        :param multi_os: different number of iterations for multi os test
        :type multi_os: bool
        """
        logger.info("Start vms: %s", vm_list)
        self._wait_until_vms_start(vm_list)
        logger.info("Wait until all vms %s will have ips", vm_list)
        self._wait_for_ip_multi_thread(vm_list)

        pid = self.prepare_balloon(len(vm_list))
        deflated = self.wait_for_balloon_change(True, True, vm_list, multi_os)

        self.assertTrue(
            deflated, "Deflation of balloons not working properly"
        )

        self.balloon_clean([], pid)

        logger.info(
            "Waiting %d s for host %s to compute ballooning info",
            SLEEP_TIME, config.HOSTS[host_id]
        )
        sleep(SLEEP_TIME)

        logger.info("Testing inflation of balloon")
        inflated = self.wait_for_balloon_change(
            True, False, vm_list, multi_os
        )

        self.assertTrue(inflated, "Inflation of balloon not working properly")
        logger.info("inflation successful")

    def balloon_usage_negative(self, vm):
        """
        Negative test, tests inflation and deflation of balloons
        Testing should succeed on VMs without guest agent and
        with memory set to Minimum Guaranteed memory

        :param vm: vm_name
        :type vm: str
        :returns: True, if method success, otherwise False
        :rtype: bool
        """
        self.prepare_balloon()

        return self.wait_for_balloon_change(False, True, [vm])

    def get_mem_stats(self, i, vm_list, host_id):
        """
        Get current and max memory of VM

        :param i: iteration index
        :type i: int
        :param vm_list: list of vms
        :type vm_list: list
        :param host_id: host index
        :type host_id: int
        :returns: dictionary of mom stats
        :rtype: dict
        """
        rc, stats, err = hosts.get_mom_statistics(config.VDS_HOSTS[host_id])
        self.assertTrue(rc, "Failed to obtain mom statistics")

        for vm in vm_list:
            if vm not in stats["guests"]:
                logger.warning("VM %s not in MOM statistics", vm)
                return False

        maxb = stats["guests"][vm_list[0]]["balloon_max"]
        curb = stats["guests"][vm_list[0]]["balloon_cur"]

        mom_off = maxb == curb

        if (not i % RESTART_VDSM_INDEX) and mom_off:
            self.assertTrue(
                config.VDS_HOSTS[host_id].service("vdsmd").restart(),
                "Restart of vdsm failed"
            )

        for vm in vm_list:
            logger.info(
                "VM %s - balloons max: %s, current: %s",
                vm, stats["guests"][vm]["balloon_max"],
                stats["guests"][vm]["balloon_cur"]
            )

        guests = stats["guests"]
        return dict(
            (
                vm, [guests[vm]["balloon_cur"], guests[vm]["balloon_max"]]
            ) for vm in vm_list
        )

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

    def wait_for_balloon_change(
            self, positive, deflate, vm_list, multi_vms=False, host_id=1
    ):
        """
        Test balloon usage in number of iterations

        :param positive: testing should be positive
        :type positive: bool
        :param deflate: True if testing deflation False if testing inflation
        :type deflate: bool
        :param vm_list: list of vms to test ballooning on
        :type vm_list: list
        :param multi_vms: adjusts test for multi vms case
        :type multi_vms: bool
        :param host_id: host index
        :type host_id: int
        :returns: True, if method success, otherwise False
        :rtype: bool
        """
        iterations = MULTI_VMS_ITERATIONS if multi_vms else BALLOON_ITERATIONS
        if not positive:
            iterations = NEGATIVE_ITERATIONS

        failed_attempts = 0
        for i in range(iterations):
            logger.info("Iteration number %d out of %d", i+1, iterations)
            mem_dict = self.get_mem_stats(i, vm_list, host_id)

            if not mem_dict:
                logger.warning("Failed to obtain information from mom")
                if not positive:
                    return True
                failed_attempts += 1
                sleep(SLEEP_TIME)
                continue

            if failed_attempts >= 10:
                config.VDS_HOSTS[0].service("vdsmd").restart()
                failed_attempts = 0

            for vm in vm_list:
                logger.info("VM stats: max - %d, current - %d",
                            mem_dict[vm][MAX], mem_dict[vm][CURRENT])

            if not positive:
                vm = vm_list[0]
                self.assertEqual(
                    mem_dict[vm][MAX], mem_dict[vm][CURRENT], "Balloon edited")

            if deflate and multi_vms:
                if mem_dict[
                    vm_list[0]
                ][CURRENT] != mem_dict[
                    vm_list[1]
                ][CURRENT]:
                    return positive
            else:
                for vm in vm_list:
                    vm_cur = mem_dict[vm][CURRENT]
                    vm_max = mem_dict[vm][MAX]
                    if ((deflate and vm_cur == vm_max) or
                       (not deflate and vm_cur != vm_max)):
                        break
                else:
                    return positive

            logger.info(
                "Waiting %d s for host %s to compute ballooning info",
                SLEEP_TIME, config.HOSTS[host_id]
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

    @classmethod
    def setup_class(cls):
        """
        Create pool of 8 VMs from template
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
            vm_mem = round(
                host_mem * 2 / config.VM_NUM / config.GB
            ) * config.GB
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

        if not config.VDS_HOSTS[0].service("vdsmd").restart():
            raise errors.VMException("Failed to restart vdsm")
        if not hosts.waitForHostsStates(True, config.HOSTS[0]):
            raise errors.VMException("Failed to reactivate host")
        if not storagedomains.waitForStorageDomainStatus(
                True, config.DC_NAME[0], config.STORAGE_NAME[0],
                config.ENUMS["storage_domain_state_active"]
        ):
            raise errors.StorageDomainException(
                "Failed to activate storage domain after restart of VDSM"
            )
        logger.info(
            "Cluster memory overcommitment percentage set to %d",
            MEMORY_OVERCOMMITMENT
        )

    @tcms("9860", "326204")
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
                    wait_for_status=config.ENUMS["vm_state_up"]
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

    @tcms("9860", "326206")
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
        sleep(SLEEP_TIME*self.threshold[0])
        self.assertTrue(
            self.ksm_running(config.VDS_HOSTS[0]),
            "KSM not running on %d vms" % self.threshold[0]
        )
        logger.info("KSM successfully triggered")

    @tcms("9860", "326207")
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

    @tcms("9860", "326207")
    def test_d_ksm_stop(self):
        """
        Stop KSM by migrating to other host
        """
        if (len(config.HOSTS)) < 2:
            raise errors.SkipTest("Too few hosts.")

        for vm in self.threshold_list[:len(self.threshold_list)/2]:
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
        teardown ksm tests
        """
        logger.info("Stop vms: %s", cls.threshold_list)
        vms.stop_vms_safely(cls.threshold_list)
        if not clusters.updateCluster(
                True, config.CLUSTER_NAME[0], mem_ovrcmt_prc=100,
                ksm_enabled=True
        ):
            raise errors.VMException("Failed to update cluster")

        if not config.VDS_HOSTS[0].service("vdsmd").restart():
            raise errors.VMException("Failed to restart vdsm")
        if not hosts.waitForHostsStates(True, config.HOSTS[0]):
            raise errors.VMException("Failed to reactivate host")
        if not storagedomains.waitForStorageDomainStatus(
                True, config.DC_NAME[0], config.STORAGE_NAME[0],
                config.ENUMS["storage_domain_state_active"]
        ):
            raise errors.StorageDomainException(
                "Failed to activate storage domain after restart of VDSM")


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
                ksm_enabled=False
        ):
            raise errors.VMException("Failed to update cluster")
        # vms for ballooning
        list_id = range(int(config.VM_NUM))
        vm_list = ["%s-%s" % (config.POOL_NAME, str(i+1)) for i in list_id]
        # vm_list.append(config.W7)
        # vm_list.append(config.W2K)
        for vm in vm_list:
            if not vms.updateVm(
                    True, vm, placement_host=config.HOSTS[1],
                    placement_affinity=config.ENUMS["vm_affinity_pinned"],
                    memory=2*config.GB, memory_guaranteed=config.GB
            ):
                raise errors.VMException("Failed to update vm %s" % vm)

    @tcms("9860", "326209")
    def test_a_balloon_usage(self):
        """
        Tests inflation and deflation of balloon
        """
        self.vm_list = ["%s-1" % config.POOL_NAME]
        self.balloon_usage(self.vm_list)

    @tcms("9860", "326211")
    def test_b_balloon_multi_memory(self):
        """
        Tests inflation and deflation of balloon on 2 VMs
        with different memories
        """
        self.vm_list = ["%s-%d" % (config.POOL_NAME, i + 1) for i in range(2)]
        counter = 1
        for vm in self.vm_list:
            memory_guaranteed = config.GB / 2 - 128 * config.MB * counter
            self.assertTrue(
                vms.updateVm(
                    True, vm, memory=config.GB / 2,
                    memory_guaranteed=memory_guaranteed
                ),
                "Vm update failed"
            )
            counter += 1

        self.balloon_usage(self.vm_list, 1, True)

    # TODO: test need export domain with windows vms with
    # last version of guest agent
    # @bz({"1125331": {"engine": ["cli"], "version": None},
    #      "1132833": {"engine": None, "version": None}})
    # @tcms("9860", "326212")
    # def test_c_balloon_multi_os(self):
    #     """
    #     Test usage of balloon on different OS types
    #     """
    #     self.vm_list = ["balloon-1", config.W7, config.W2K]
    #     self.balloon_usage(self.vm_list)

    @tcms("9860", "326216")
    def test_d_balloon_max(self):
        """
        Negative test case of balloon with minimum
        guaranteed memory set to maximum memory
        """
        vm = "%s-%d" % (config.POOL_NAME, 1)
        self.vm_list = [vm]
        self.assertTrue(
            vms.updateVm(
                True, vm, memory=2*config.GB, memory_guaranteed=2*config.GB
            ),
            "Failed to update rhel vm %s" % vm
        )
        self.assertTrue(
            vms.startVm(True, vm, wait_for_status=config.ENUMS["vm_state_up"]),
            "Failed to start vm %s" % vm
        )
        self.balloon_usage_negative(vm)

    @bz({"1184135": {"engine": None, "version": None}})
    @tcms("9860", "326214")
    def test_e_balloon_no_agent(self):
        """
        Negative test case to test balloon without agent
        """
        vm = "%s-%d" % (config.POOL_NAME, 1)
        self.vm_list = [vm]
        self.assertTrue(
            vms.updateVm(
                True, vm, memory=2*config.GB, memory_guaranteed=config.GB
            ),
            "Failed to update rhel vm"
        )

        self.assertTrue(
            vms.startVm(True, vm, wait_for_status=config.ENUMS["vm_state_up"]),
            "Failed to start vm %s" % vm
        )
        vm_machine = vms.get_vm_machine(
            vm, config.VMS_LINUX_USER, config.VMS_LINUX_PW
        )
        for i in range(BALLOON_ITERATIONS):
            if vm_machine.stopService("ovirt-guest-agent"):
                break
            sleep(SLEEP_TIME)
        else:
            self.assertTrue(vms.stopVm(True, vm), "Failed to stop vm %s" % vm)
            raise errors.VMException(
                "Failed to stop guest agent on VM %s" % vm)

        self.balloon_usage_negative(vm)

    @tcms("9860", "326215")
    def test_f_balloon_multiple_vms(self):
        """
        Test ballooning with multiple (8) small VMs
        """
        list_id = range(config.VM_NUM)
        self.vm_list = ["%s-%d" % (config.POOL_NAME, i+1) for i in list_id]
        for vm in self.vm_list:
            self.assertTrue(
                vms.updateVm(
                    True, vm, memory=int(config.GB/4),
                    memory_guaranteed=int(config.GB/8)
                ),
                "Vm update failed"
            )

        self.balloon_usage(self.vm_list)

    def setUp(self):
        if hosts.getHostState(config.HOSTS[1]) == config.HOST_NONOPERATIONAL:
            logger.info("Activate host %s.", config.HOSTS[1])
            if not hosts.activateHost(True, config.HOSTS[1]):
                raise errors.HostException("Failed to activate host.")
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
        remove all VMS
        """
        # if any test fail remove memory load from hosts
        logger.info(
            "Pids of processes allocating memory - %s",
            " ".join(str(i) for i in cls.pid_list)
        )
        if cls.pid_list:
            cmd = ["kill", "-9"].extend(cls.pid_list)
            config.VDS_HOSTS[1].executor().run_cmd(cmd)

        if not clusters.updateCluster(
                True, config.CLUSTER_NAME[0], ballooning_enabled=False,
                ksm_enabled=True
        ):
            raise errors.VMException("Failed to disable ballooning on cluster")
