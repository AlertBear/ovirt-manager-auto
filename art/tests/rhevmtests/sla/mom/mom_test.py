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
from unittest2 import SkipTest
from time import sleep
import config
import logging
import art.test_handler.exceptions as errors
from art.test_handler import find_test_file
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.vmpools as pools
from art.rhevm_api.tests_lib.high_level import vmpools as hl_pools
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import rhevmtests.helpers as helpers
import rhevmtests.sla as sla

logger = logging.getLogger(__name__)
find_test_file.__test__ = False

########################################################################
#                             Base Class                               #
########################################################################


def change_mom_pressure_percentage(resource, teardown=False):
    """
    change_mom_pressure_percentage in order to test deflation and inflation
    faster

    :param resource: host resource
    :type resource: host resource
    :param teardown: True if run from teardown, False otherwise
    :type teardown: bool
    :raise: ResourceError
    """

    dpt0_20 = "(defvar pressure_threshold 0.20)"
    dpt0_40 = "(defvar pressure_threshold 0.40)"
    exists_value = dpt0_40 if teardown else dpt0_20
    correct_value = dpt0_20 if teardown else dpt0_40
    logger.info(
        "Replace %s in %s on %s ", exists_value, correct_value,
        config.BALLOON_FILE
    )
    rc, _, _ = resource.run_command(
        ["sed", "-i", "s/%s/%s/" % (exists_value, correct_value),
         config.BALLOON_FILE]
    )
    if rc and not teardown:
        return False


def change_swapping(host_resource, teardown=False):
    """
    disable/enable swap

    :param host_resource: host resource
    :type host_resource: host resource
    :param teardown: True if run from teardown, False otherwise
    :type teardown: bool
    :raise: HostException
    """
    command = "swapon" if teardown else "swapoff"
    logger.info("Running %s on host %s", command, host_resource)
    rc, _, _ = host_resource.run_command([command, "-a"])
    if rc and not teardown:
        return False


def setup_module():
    """
    Prepare environment for MOM test
    """

    # create VMs for KSM and balloon
    logger.info("Create vms pool %s", config.POOL_NAME)
    if not pools.addVmPool(
        True, name=config.POOL_NAME, size=config.VM_NUM,
        cluster=config.CLUSTER_NAME[0],
        template=config.TEMPLATE_NAME[0],
        description="%s pool" % config.POOL_NAME
    ):
        raise errors.VMException(
            "Failed creation of pool for %s" % config.POOL_NAME
        )
    # detach VMs from pool to be editable
    logger.info("Detach vms from vms pool %s", config.POOL_NAME)
    if not hl_pools.detach_vms_from_pool(config.POOL_NAME):
        raise errors.VMException(
            "Failed to detach VMs from %s pool" % config.POOL_NAME
        )
    logger.info("Remove vms pool %s", config.POOL_NAME)
    if not pools.removeVmPool(True, config.POOL_NAME):
        raise errors.VMException("Failed to remove vms from pool")

    # disable swapping on hosts and change mom pressure for faster tests
    for host_resource in config.VDS_HOSTS[:2]:
        change_mom_pressure_percentage(host_resource)
        change_swapping(host_resource)


def teardown_module():
    """
    Cleans the environment
    """

    logger.info("Teardown...")
    for host_resource in config.VDS_HOSTS[:2]:
        change_mom_pressure_percentage(host_resource, True)
        change_swapping(host_resource, True)
    try:
        hl_hosts.restart_vdsm_and_wait_for_activation(
            config.VDS_HOSTS[:2], config.DC_NAME[0], config.STORAGE_NAME[0]
        )
    except errors.HostException as e:
        logger.error("Failed to restart vdsm service, %s", e)
    except errors.StorageDomainException as e:
        logger.error("Failed to activate storage domain, %s", e)
    sla.sla_cleanup()


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
        out = host_resource.run_command(
            [
                "vdsClient", "-s", "0",
                "getVdsStats", "|", "grep", "-i", "ksmState"
            ]
        )[1]
        return True if "True" in out else False

    def allocate_host_memory(self, perc=0.7):
        """
        Saturate host memory to 70%

        :param perc: load host memory on specific percent
        :type perc: int
        :returns: True and pid of allocated process, otherwise False and None
        :rtype: bool
        """
        host_free_memory = ll_hosts.get_host_free_memory(config.HOSTS[1])
        allocate_memory = int(host_free_memory * perc)
        logger.info(
            "Allocating %d B of memory on host %s",
            allocate_memory, config.HOSTS[1]
        )
        rc, out, err = config.VDS_HOSTS[1].run_command(
            [
                "python", config.HOST_ALLOC_PATH, str(allocate_memory),
                "&>", "/tmp/OUT1", "&", "echo", "$!"
            ]
        )
        out = out.strip("\n\t ")
        if rc:
            return False
        return out

    def cancel_host_allocation(self, pid):
        """
        Cancel host host memory load

        :param pid: pid of process allocating memory
        :type pid: str
        :returns: True if success, otherwise False
        :rtype: bool
        """
        config.VDS_HOSTS[1].run_command(["kill", "-9", pid])
        if config.VDS_HOSTS[1].fs.exists("/proc/%s" % pid):
            raise errors.HostException("Failed to kill process %s" % pid)
        return True

    def prepare_balloon(self):
        """
        Running load memory on the host

        :returns: pid of allocation process
        :rtype: str
        """
        pid = self.allocate_host_memory()
        self.pid_list.append(pid)
        logger.info("Host process pid allocating memory - %s", pid)
        return pid

    def balloon_usage(self, vm_list):
        """
        Run balloon inflation and deflation tests

        :param vm_list: list of VMs to be tested
        :type vm_list: list
        """
        logger.info("Start vms: %s", vm_list)
        ll_vms.start_vms(vm_list)
        pid = self.prepare_balloon()

        logger.info("Testing deflation of balloon")
        self.assertTrue(
            self.deflation(vm_list),
            "Deflation of balloons is not working properly"
        )
        self.balloon_clean([], pid)
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
        :rtype: dict
        """
        mom_dict = {}
        for vm in vm_list:
            vm_id = ll_vms.get_vm(vm).get_id()
            _, out, _ = config.VDS_HOSTS[1].run_command(
                [
                    "vdsClient", "-s", "0",
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

    def balloon_clean(self, vm_list, pid):
        """
        Stop all running VMs and cancel host memory allocation

        :param vm_list: list of vms
        :type vm_list: list
        :param pid: pid of host memory allocation process
        :type pid: str
        """
        if vm_list:
            logger.info("Stop vms: %s", vm_list)
            ll_vms.stop_vms_safely(vm_list)
        for pid in self.pid_list:
            if self.cancel_host_allocation(pid):
                self.pid_list.remove(pid)

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
        iter = (
            config.NEGATIVE_ITERATION if negative_test
            else config.BALLOON_ITERATIONS
        )
        for i in range(iter):
            logger.info(
                "Iteration number %d out of %d", i + 1, iter
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
                    if i == iter - 1:
                        if (
                            int(mem_dict[vm]["balloon_max"]) -
                            int(mem_dict[vm]["balloon_cur"]) <= 1024
                        ):
                            logger.info("inflation is working!!!")
                            return True
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
                config.SLEEP_TIME, config.HOSTS[1]
            )
            sleep(config.SLEEP_TIME)
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
        KSM setup-
        pin all VMs to host
        change VMs memory
        disable balloon and enable ksm on cluster
        """
        host_mem = ll_hosts.get_host_free_memory(config.HOSTS[0])

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
            if not ll_vms.updateVm(
                True, vm, placement_host=config.HOSTS[0],
                placement_affinity=user_migratable,
                memory=vm_mem, memory_guaranteed=vm_mem
            ):
                raise errors.VMException("Failed to update vm %s" % vm)
            logger.info(
                "Pinned vm %s with %s B memory, to host %s",
                vm, vm_mem, config.HOSTS[0]
            )
        if not ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0], ksm_enabled=True,
            ballooning_enabled=False,
            mem_ovrcmt_prc=config.CLUSTER_OVERCOMMITMENT_DESKTOP
        ):
            raise errors.VMException("Failed to update cluster")

        hl_hosts.restart_vdsm_and_wait_for_activation(
            [config.VDS_HOSTS[0]],
            config.DC_NAME[0], config.STORAGE_NAME[0]
        )

        logger.info(
            "Cluster memory overcommitment percentage set to %d",
            config.CLUSTER_OVERCOMMITMENT_DESKTOP
        )

    @polarion("RHEVM3-4969")
    def test_a_ksm_progressive(self):
        """
        Finds the threshold where KSM starts

        1. Start vms in vm_list one by one
        2. Check when KSM starts working - this is the threshold
        3. Stop VM safely
        """
        vm_started = []
        for vm in self.vm_list:
            logger.info("Start vm %s.", vm)
            self.assertTrue(
                ll_vms.startVm(
                    positive=True, vm=vm,
                    wait_for_status=config.VM_UP
                ),
                "Failed to run Vm %s" % vm
            )
            vm_started.append(vm)
            self.assertTrue(
                ll_vms.waitForIP(vm, timeout=300), "Vm doesn't have ip"
            )
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
        ll_vms.stop_vms_safely(vm_started)
        self.assertTrue(self.threshold[0], "KSM was not triggered")

    @polarion("RHEVM3-4977")
    def test_b_ksm_kicking(self):
        """
        Run VMs in one moment to trigger KSM

        1. Start Vms (that we found that triggers KSM)
        2. Check if KSM is running
        """
        logger.info(
            "Running Vms that should trigger KSM: %s",
            " ,".join(self.threshold_list)
        )
        ll_vms.start_vms(self.threshold_list, config.VM_NUM)
        logger.info(
            "VMs started, waiting %d for start of VM and guest agent",
            config.SLEEP_TIME * self.threshold[0]
        )
        self.assertTrue(
            self.ksm_running(config.VDS_HOSTS[0]),
            "KSM not running on %d vms" % self.threshold[0]
        )
        logger.info("KSM successfully triggered")

    @polarion("RHEVM3-4976")
    def test_c_ksm_migration(self):
        """
        Migrate VMs with KSM enabled

        1. Migrate VM with KSM enabled
        2. Check if KSM is running
        """
        if (len(config.HOSTS)) < 2:
            raise SkipTest("Too few hosts.")
        for vm in self.threshold_list:
            self.assertTrue(
                ll_vms.migrateVm(True, vm, force=True),
                "Failed to migrate VM %s" % vm
            )

        self.assertFalse(
            self.ksm_running(config.VDS_HOSTS[0]),
            "KSM still running after migration from host %s" % config.HOSTS[0]
        )
        if not self.ksm_running(config.VDS_HOSTS[1]):
            logger.warning(
                "KSM not running after migration on host %s", config.HOSTS[0]
            )
        logger.info("KSM successfully turned off after migration")

    @polarion("RHEVM3-4975")
    def test_d_ksm_stop(self):
        """
        Stop KSM by migrating to other host
        1. Migrate VM with KSM enabled
        2. Check if KSM is not running since is not enabled on the host

        """
        if (len(config.HOSTS)) < 2:
            raise SkipTest("Too few hosts.")
        for vm in self.threshold_list[:len(self.threshold_list) / 2]:
            self.assertTrue(
                ll_vms.migrateVm(True, vm, force=True),
                "Cannot migrate VM %s" % vm
            )

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
        ll_vms.stop_vms_safely(cls.threshold_list)
        if not ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0], mem_ovrcmt_prc=100,
            ksm_enabled=True
        ):
            raise errors.VMException("Failed to update cluster")

####################################################################


class Balloon(MOM):
    """
    Balloon tests
    """

    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1. Enable Ballooning and disabling KSM
        2. Restart VDSM and wait for activation
        3. Update VMs
        """
        if not ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0],
            ballooning_enabled=True,
            ksm_enabled=False,
            mem_ovrcmt_prc=config.CLUSTER_OVERCOMMITMENT_NONE
        ):
            raise errors.VMException("Failed to update cluster")

        hl_hosts.restart_vdsm_and_wait_for_activation(
            [config.VDS_HOSTS[1]], config.DC_NAME[0], config.STORAGE_NAME[0]
        )
        # vms for ballooning
        list_id = range(int(config.VM_NUM))
        vm_list = ["%s-%s" % (config.POOL_NAME, str(i + 1)) for i in list_id]

        for vm in vm_list:
            if not ll_vms.updateVm(
                True, vm, placement_host=config.HOSTS[1],
                placement_affinity=config.VM_PINNED,
                memory=2 * config.GB, memory_guaranteed=config.GB,
                ballooning=True
            ):
                raise errors.VMException("Failed to update vm %s" % vm)

        logger.info("copying allocate test file from host %s", config.HOSTS[1])
        config.VDS_HOSTS[1].copy_to(
            config.ENGINE_HOST, find_test_file(config.ALLOC_SCRIPT_LOCAL),
            config.HOST_ALLOC_PATH
        )

    @polarion("RHEVM3-4974")
    def test_a_balloon_usage(self):
        """
        Tests inflation and deflation of balloon

        1. Start VM
        2. Run load memory on the host and check balloon deflation
        3. Cancel host allocation on the host and check balloon inflation
        4. Power off VM
        """
        self.vm_list = ["%s-1" % config.POOL_NAME]
        self.balloon_usage(self.vm_list)

    @polarion("RHEVM3-4973")
    def test_b_balloon_multi_memory(self):
        """
        Test balloon inflation and deflation on 2 VMs with different memories

        1. Update two vms to have a different memory values
        2. Start VMs
        3. Run load memory on the host and check balloon deflation
        4. Cancel host allocation on the host and check balloon inflation
        5. Power off VMs
        """
        self.vm_list = ["%s-%d" % (config.POOL_NAME, i + 1) for i in range(2)]
        counter = 1
        memory = config.GB * 5 if config.PPC_ARCH else config.GB / 2
        for vm in self.vm_list:
            memory_guaranteed = memory - 128 * config.MB * counter
            self.assertTrue(
                ll_vms.updateVm(
                    True, vm, memory=memory,
                    memory_guaranteed=memory_guaranteed
                ),
                "Vm update failed"
            )
            counter += 1

        self.balloon_usage(self.vm_list)

    @polarion("RHEVM3-4978")
    def test_d_negative_balloon_max(self):
        """
        Negative test case of balloon with minimum
        guaranteed memory set to maximum memory

        1. Set the same value in guaranteed memory and in memory
        2. start VMs
        3. Run load memory on the host and check that there is no balloon
        deflation
        4.Power off VM and cancel host allocation on the host
        """
        vm = "%s-%d" % (config.POOL_NAME, 1)
        self.vm_list = [vm]
        self.assertTrue(
            ll_vms.updateVm(
                True, vm, memory=2*config.GB, memory_guaranteed=2 * config.GB
            ),
            "Failed to update rhel vm %s" % vm
        )
        self.assertTrue(
            ll_vms.startVm(True, vm, wait_for_status=config.VM_UP),
            "Failed to start vm %s" % vm
        )
        self.balloon_usage_negative(vm)

    @polarion("RHEVM3-4971")
    def test_e_negative_balloon_no_agent(self):
        """
        Negative test case to test balloon without agent

        1. Start VM
        2. Stop guest agent
        3. Run load memory on the host and check that there is no balloon
        deflation
        4.Power off VM and Cancel host allocation


        """
        vm = "%s-%d" % (config.POOL_NAME, 1)
        self.vm_list = [vm]
        self.assertTrue(
            ll_vms.updateVm(
                True, vm, memory=2 * config.GB, memory_guaranteed=config.GB
            ),
            "Failed to update rhel vm"
        )

        self.assertTrue(
            ll_vms.startVm(True, vm, wait_for_status=config.VM_UP),
            "Failed to start vm %s" % vm
        )

        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(vm), config.VMS_LINUX_PW
        )
        if vm_resource.package_manager.exist(config.SERVICE_PUPPET):
            logger.info("remove %s", config.SERVICE_PUPPET)
            if not vm_resource.package_manager.remove(config.SERVICE_PUPPET):
                raise errors.VMException(
                    "Failed to remove %s" % config.SERVICE_PUPPET
                )

        logger.info("Stop %s service", config.SERVICE_GUEST_AGENT)
        if not vm_resource.service(config.SERVICE_GUEST_AGENT).stop():
            raise errors.VMException(
                "Failed to stop service %s on VM %s" %
                (config.SERVICE_GUEST_AGENT, vm)
            )
        self.balloon_usage_negative(vm)

    @polarion("RHEVM3-4970")
    def test_f_balloon_multiple_vms(self):
        """
        Test ballooning with multiple VMS

        1. Start VMs
        2. Run load memory on the host and check balloon deflation
        3  Cancel host allocation on the host
        4. check balloon inflation
        5. Check balloon inflation
        6. Power off VM

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
                ll_vms.updateVm(
                    True, vm, memory=memory,
                    memory_guaranteed=memory_guaranteed
                ),
                "Vm update failed"
            )

        self.balloon_usage(self.vm_list)

    def setUp(self):
        if (
            ll_hosts.get_host_status(config.HOSTS[1]) ==
            config.HOST_NONOPERATIONAL
        ):
            logger.info("Activate host %s.", config.HOSTS[1])
            if not ll_hosts.activateHost(True, config.HOSTS[1]):
                raise errors.HostException("Failed to activate host")

    def tearDown(self):
        if self.pid_list:
            self.balloon_clean(self.vm_list, self.pid_list[-1])
        else:
            self.balloon_clean(self.vm_list, "")

    @classmethod
    def teardown_class(cls):
        """
        Remove memory load from hosts
        """
        logger.info(
            "Pids of processes allocating memory - %s",
            " ".join(str(i) for i in cls.pid_list)
        )
        for pid in cls.pid_list:
            if cls.cancel_host_allocation(pid):
                cls.pid_list.remove(pid)

        if not ll_clusters.updateCluster(
            True, config.CLUSTER_NAME[0], ballooning_enabled=False,
            ksm_enabled=True,
            mem_ovrcmt_prc=config.CLUSTER_OVERCOMMITMENT_NONE
        ):
            logger.error("Failed to disable ballooning on cluster")
        config.VDS_HOSTS[1].fs.remove(config.HOST_ALLOC_PATH)
