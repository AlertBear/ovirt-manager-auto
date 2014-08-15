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
        testing infaltion and deflation of ballooning on
        1 VM, 2 VMs with different memories options, different OS,
        VM with memory set to max guaranteed memory, VM without guest
        agent, multipls VMs on one hsot with ballooning enabled
"""

from art.unittest_lib import ComputeTest as TestCase

import logging
import config

from time import sleep

from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains

import art.test_handler.exceptions as errors

from art.test_handler import find_test_file
from art.test_handler.settings import opts
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.rhevm_api.utils.test_utils import getStat

from utilities import machine
from nose.plugins.attrib import attr

logger = logging.getLogger(__name__)

sleep_time = 15
find_test_file.__test__ = False
ENUMS = opts['elements_conf']['RHEVM Enums']
ITERS = 25  # number of iterations for testing test ballooning
ITERS_MULTIMEM = 100  # number of iterations VMs with different memory
ITERS_NEG = 10  # number of iterations for negative testcases
RESTART_VDSM_INDEX = 10  # index of restarting VDSM
GB = 1024 ** 3
MEM_OVERCMT = 200
BALLOON_POOL = "balloon"
KSM_POOL = "ksm"
HOST_ALLOC_PATH = '/tmp/hostAlloc.py'
ALLOC_SCRIPT_LOCAL = 'tests/rhevmtests/mom/hostAlloc.py'
CUR = 0
MAX = 1


########################################################################
#                             Base Class                               #
########################################################################


@attr(tier=1)
class MOM(TestCase):
    """
    Base class for vm watchdog operations
    """
    pid_list = []

    @classmethod
    def ksm_running(cls, host, host_user, host_pwd):
        """
        see if ksm is running on host
        Author: lsvaty
        Parameters:
            * host - ip of host
            * host_user - user on host machine (root)
            * host_pwd - password for host_user
        @return value - None on failure or True(1)/False(0) on success
        """
        stats, out = hosts.get_mom_statistics(host, host_user, host_pwd)
        if stats:
            return out['host']['ksm_run']
        logger.error("Failed to obtain ksm_run, output - %s", out)

    def allocate_host_memory(self, host, host_user, host_pwd, perc=0.9,
                             path=HOST_ALLOC_PATH):
        """
        Saturate host memory to 90%
        Author: lsvaty
        Parameters:
            * host - ip of host
            * host_user - user on host machine (root)
            * host_pwd - password for host_user
            * perc - percentage of free memory to allocate
            * path - path to save the allocation script
        @return value - Pid of thread holding memory on failure return -1
        """

        host_machine = machine.Machine(
            host, host_user, host_pwd).util(machine.LINUX)

        out = ''
        memory_allocated = False
        for i in range(ITERS):
            stats = getStat(host, "host", "hosts", ["memory.free"])

            allocate_memory = int(stats['memory.free'] * perc)
            logger.info("Allocating %d B of memory on host %s",
                        allocate_memory, host)
            host_machine.copyTo(find_test_file(ALLOC_SCRIPT_LOCAL), path)

            rc, out = host_machine.runCmd(
                ['python', path, str(allocate_memory)], timeout=60, bg=True)
            if not rc:
                return False, out

            sleep(sleep_time)
            if host_machine.isProcessExists(int(out)):
                memory_allocated = True
                break

            logger.info("Last allocation failed creating new")

        return memory_allocated, out

    def cancel_host_allocation(self, pid, host, host_user, host_pwd,
                               path=HOST_ALLOC_PATH):
        """
        Cancel host host memory load
        Author: lsvaty
        Parameters:
            * pid - pid of process allocating memory
            * host - ip of host
            * host_user - user on host machine (root)
            * host_pwd - password for host_user
            * path - path to script allocating memory
        @return value - True on success otherwise False
        """
        killed = False
        host_machine = machine.Machine(
            host, host_user, host_pwd).util(machine.LINUX)
        for i in range(ITERS):
            host_machine.killProcess([pid])

            sleep(sleep_time)
            if not host_machine.isProcessExists(pid):
                killed = True
                break

        return killed and host_machine.runCmd(['rm', '-f', path])[0]

    def prepare_balloon(self, sleep_mult=1, host_id=1):
        """
        Prepare environment for testing deflation of balloon
        """
        wait_time = sleep_mult*sleep_time
        logger.info("Waiting %d s for guests to allocate memory on host %s",
                    wait_time, config.HOSTS[host_id])
        sleep(wait_time)

        rc, out = self.allocate_host_memory(config.HOSTS[host_id],
                                            config.HOSTS_USER[host_id],
                                            config.HOSTS_PW[host_id])
        self.assertTrue(rc, "Failed to allocate memory on host %s, output "
                            "%s" % (config.HOSTS[host_id], out))
        pid = int(out)
        self.pid_list.append(pid)
        logger.info("Host process pid allocating memory - %d", pid)

        logger.info("Waiting %d s for host %s to compute ballooning info",
                    sleep_time, config.HOSTS[host_id])
        sleep(sleep_time)

        logger.info("Testing deflation of balloon")

        return pid

    def balloon_usage(self, vm_list, host_id=1, multimem=False):
        """
        Test inflation and deflation of balloons
        Author: lsvaty
        Parameters:
            * vm_list - lsit of VMs to be tested
        """
        vms_string = ', '.join(vm_list)
        self.assertTrue(vms.startVms(vms_string),
                        "Failed to start VMs %s " % vms_string)

        for vm in vm_list:
            self.assertTrue(vms.waitForIP(vm), "Failed to obtain IP of VM %s,"
                                               " guest agent did not load" %
                                               vm)

        pid = self.prepare_balloon(len(vm_list))

        deflated = self.wait_for_balloon_change(True, True, vm_list, multimem)

        self.assertTrue(deflated, "Deflation of balloons "
                                  "not working properly")

        self.balloon_clean([], pid)

        logger.info("Waiting %d s for host %s to compute ballooning info",
                    sleep_time, config.HOSTS[host_id])
        sleep(sleep_time)

        logger.info("Testing inflation of balloon")
        inflated = self.wait_for_balloon_change(True, False,
                                                vm_list, multimem)

        self.assertTrue(inflated, "Inflation of balloon not working properly")
        logger.info("inflation successful")

    def balloon_usage_negative(self, vm):
        """
        Negative test, tests inflation and deflation of balloons
        Testing should succeed on VMs without guest agent and with memory
            set to Minimum Guaranteed memory
        Author: lsvaty
        Parameters:
            vm_list - started VM for test
            host_id - host index in config.HOSTS
        """
        self.prepare_balloon()

        return self.wait_for_balloon_change(False, True, [vm])

    def get_mem_stats(self, i, vm_list, host_id):
        """
        Get current and max memory of VM
        Author: lsvaty
        Parameters:
            vm_list - list of vms
            host_id - host index in config.HOSTS
        """
        rc, stats = hosts.get_mom_statistics(config.HOSTS[host_id],
                                             config.HOSTS_USER[host_id],
                                             config.HOSTS_PW[host_id])
        self.assertTrue(rc, "Failed to obtain mom statistics")

        for vm in vm_list:
            if vm not in stats['guests']:
                logger.warning("VM %s not in MOM statistics", vm)
                return False

        maxb = stats['guests'][vm_list[0]]['balloon_max']
        curb = stats['guests'][vm_list[0]]['balloon_cur']

        mom_off = maxb == curb

        if (not i % RESTART_VDSM_INDEX) and mom_off:
            host_machine = machine.Machine(
                config.HOSTS[host_id],
                config.HOSTS_USER[host_id],
                config.HOSTS_PW[host_id]).util(machine.LINUX)
            self.assertTrue(host_machine.restartService("vdsmd"),
                            "Restart of vdsm failed")

        for vm in vm_list:
            logger.info("VM %s - balloons max: %s, current: %s",
                        vm, stats['guests'][vm]['balloon_max'],
                        stats['guests'][vm]['balloon_cur'])

        guests = stats['guests']
        return dict((vm, [guests[vm]['balloon_cur'],
                          guests[vm]['balloon_max']]) for vm in vm_list)

    def balloon_clean(self, vm_list, pid, dealloc=True, host_id=1):
        """
        Stop all running VMs and cancel host memory allocation
        Author: lsvaty
        Parameters:
            vm_list - list of vms
            pid - pid of host memory allocation process
            dealloc - enable cancelling the memory allocation
            host_id - host index in config.HOSTS
        """
        sleep(sleep_time)
        if vm_list:
            self.assertTrue(vms.stopVms(', '.join(vm_list)),
                            "Failed to stop VMs %s " % ', '.join(vm_list))
        if dealloc:
            rc = self.cancel_host_allocation(pid, config.HOSTS[host_id],
                                             config.HOSTS_USER[host_id],
                                             config.HOSTS_PW[host_id])
            self.assertTrue(rc, "Failed to cancel memory load on host "
                                "%s" % config.HOSTS[host_id])
            if self.pid_list:
                self.pid_list.pop()

    def wait_for_balloon_change(self, positive, deflate, vm_list,
                                multimem=False, host_id=1):
        """
        Test balloon usage in number of iterations
        Author: lsvaty
        Parameters:
            positive - testing should be positive
            vm_list - list of vms to test ballooning on
            deflate - True if testing deflation False if testing inflation
            multimem - adjusts test for multimemory case
            host_id - id of host in config.HOSTS
        """
        iterations = ITERS
        if not positive:
            iterations = ITERS_NEG

        for i in range(iterations):
            logger.info("Iteration number %d out of %d", i+1, iterations)
            mem_dict = self.get_mem_stats(i, vm_list, host_id)

            if not mem_dict:
                logger.warning("Failed to obtain information from mom")
                if not positive:
                    return True
                sleep(sleep_time)
                continue

            if not positive:
                vm = vm_list[0]
                self.assertEqual(
                    mem_dict[vm][MAX], mem_dict[vm][CUR], "Balloon edited")

            if deflate and multimem:
                if mem_dict[vm_list[0]][CUR] != mem_dict[vm_list[1]][CUR]:
                    return positive
            else:
                for vm in vm_list:
                    vm_cur = mem_dict[vm][CUR]
                    vm_max = mem_dict[vm][MAX]
                    if ((deflate and vm_cur == vm_max) or
                       (not deflate and vm_cur != vm_max)):
                        break
                else:
                    return positive

            logger.info("Waiting %d s for host %s to compute ballooning info",
                        sleep_time, config.HOSTS[host_id])
            sleep(sleep_time)
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
        stats = getStat(config.HOSTS[0], 'host', 'hosts', ['memory.free'])
        host_mem = stats['memory.free']

        cls.threshold = []
        cls.vm_list = []
        cls.threshold_list = []

        logger.info("Running KSM tests on host %s memory - %s B",
                    config.HOSTS[0], str(host_mem))
        for vm_index in range(int(config.KSM_VM_NUM)):
            vm = "%s-%s" % (KSM_POOL, str(vm_index + 1))
            cls.vm_list.append(vm)
            vm_mem = round(host_mem*2/config.KSM_VM_NUM/GB)*GB
            if not vms.updateVm(
                    True, vm, placement_host=config.HOSTS[0],
                    placement_affinity=ENUMS['vm_affinity_user_migratable'],
                    memory=vm_mem):
                raise errors.VMException("Failed to update vm %s" % vm)
            logger.info("Pinned vm %s with %s B memory, to host %s",
                        vm, vm_mem, config.HOSTS[0])
        if not clusters.updateCluster(
                True, config.CLUSTER_NAME[0], ksm_enabled=True,
                ballooning_enabled=False, mem_ovrcmt_prc=MEM_OVERCMT):
            raise errors.VMException("Failed to update cluster")

        host_machine = machine.Machine(
            config.HOSTS[0], config.HOSTS_USER[0],
            config.HOSTS_PW[0]).util(machine.LINUX)
        if not host_machine.restartService("vdsmd"):
            raise errors.VMException("Failed to restart vdsm")
        if not hosts.waitForHostsStates(True, config.HOSTS[0]):
            raise errors.VMException("Failed to reactivate host")
        if not storagedomains.waitForStorageDomainStatus(
                True, config.DC_NAME[0], config.STORAGE_NAME[0],
                ENUMS['storage_domain_state_active']):
            raise errors.StorageDomainException(
                "Failed to activate storage domain after restart of VDSM")
        logger.info("Cluster memory overcommitment percentage set to %d",
                    MEM_OVERCMT)

    @tcms('9860', '326204')
    def test_a_ksm_progressive(self):
        """
        Finds the threshold where KSM starts
        """
        vm_started = []
        for vm in self.vm_list:
            self.assertTrue(vms.startVm(positive=True, vm=vm,
                                        wait_for_status=ENUMS['vm_state_up']),
                            "Failed to run Vm %s" % vm)
            vm_started.append(vm)
            logger.info("Waiting %d for start of VM and guest agent",
                        sleep_time)
            sleep(sleep_time)
            self.threshold_list.append(vm)
            ksm_running = self.ksm_running(config.HOSTS[0],
                                           config.HOSTS_USER[0],
                                           config.HOSTS_PW[0])
            if ksm_running is not None:
                if ksm_running:
                    self.threshold.append(int(vm[-1]))
                    logger.info("KSM triggered on %s-th vm",
                                self.threshold[0])
                    break
                else:
                    logger.info("KSM not running after starting vm %s", vm)
            else:
                self.assertTrue(ksm_running, "Failed to get KSM status")

        self.assertTrue(vms.stopVms(', '.join(vm_started)),
                        "Failed to stop VMs %s " % ', '.join(vm_started))
        self.assertTrue(self.threshold[0], "KSM was not triggered")

    @tcms('9860', '326206')
    def test_b_ksm_kicking(self):
        """
        Run VMs in one moment to trigger KSM
        """
        logger.info("Running Vms that should trigger KSM: %s",
                    " ,".join(self.threshold_list))
        vms.start_vms(self.threshold_list, config.KSM_VM_NUM)
        logger.info("VMs started, waiting %d for start of VM and guest agent",
                    sleep_time)
        sleep(sleep_time)
        self.assertTrue(
            self.ksm_running(
                config.HOSTS[0], config.HOSTS_USER[0], config.HOSTS_PW[0]),
            "KSM not running on %d vms" % self.threshold[0])
        logger.info("KSM successfully triggered")

    @tcms('9860', '326207')
    def test_c_ksm_migration(self):
        """
        Migrate VMs with KSM enabled
        """
        if (len(config.HOSTS)) < 2:
            raise errors.SkipTest("Too few hosts.")
        for vm in self.threshold_list:
            self.assertTrue(vms.migrateVm(True, vm, force=True),
                            "Failed to migrate VM %s" % vm)

        logger.info("Waiting %d s", sleep_time)
        sleep(sleep_time)
        self.assertFalse(
            self.ksm_running(
                config.HOSTS[0], config.HOSTS_USER[0], config.HOSTS_PW[0]),
            "KSM not running after migration on host %s" % config.HOSTS[0])
        if not self.ksm_running(
                config.HOSTS[1], config.HOSTS_USER[1], config.HOSTS_PW[1]):
            logger.warning(
                "KSM not running after migration on host %s", config.HOSTS[1])
        logger.info("KSM successfully turned off after migration")

    @tcms('9860', '326207')
    def test_d_ksm_stop(self):
        """
        Stop KSM by migrating to other host
        """
        if (len(config.HOSTS)) < 2:
            raise errors.SkipTest("Too few hosts.")

        for vm in self.threshold_list[:len(self.threshold_list)/2]:
            self.assertTrue(
                vms.migrateVm(True, vm, force=True),
                "Cannot migrate VM %s" % vm)

        logger.info("Waiting %d s", sleep_time)
        sleep(sleep_time)
        self.assertFalse(
            self.ksm_running(
                config.HOSTS[0], config.HOSTS_USER[0], config.HOSTS_PW[0]),
            "KSM running after migration on host %s" % config.HOSTS[0])
        logger.info("KSM successfully turned off after migration")

    @classmethod
    def teardown_class(cls):
        """
        teardown ksm tests
        """
        if not vms.stopVms(', '.join(cls.threshold_list)):
            raise errors.VMException(
                "Failed to stop VMs %s " % ', '.join(cls.threshold_list))
        if not clusters.updateCluster(
                True, config.CLUSTER_NAME[0], mem_ovrcmt_prc=100,
                ksm_enabled=True):
            raise errors.VMException("Failed to update cluster")

        host_machine = machine.Machine(
            config.HOSTS[0], config.HOSTS_USER[0],
            config.HOSTS_PW[0]).util(machine.LINUX)
        if not host_machine.restartService("vdsmd"):
            raise errors.VMException("Failed to restart vdsm")
        if not hosts.waitForHostsStates(True, config.HOSTS[0]):
            raise errors.VMException("Failed to reactivate host")
        if not storagedomains.waitForStorageDomainStatus(
                True, config.DC_NAME[0], config.STORAGE_NAME[0],
                ENUMS['storage_domain_state_active']):
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
                ksm_enabled=False):
            raise errors.VMException("Failed to update cluster")
        # vms for ballooning
        list_id = range(int(config.BALLOON_VM_NUM))
        vm_list = ["%s-%s" % (BALLOON_POOL, str(i+1)) for i in list_id]
        vm_list.append(config.W7)
        vm_list.append(config.W2K)
        for vm in vm_list:
            if not vms.updateVm(
                    True, vm, placement_host=config.HOSTS[1],
                    placement_affinity=ENUMS['vm_affinity_pinned'],
                    memory=2*GB, memory_guaranteed=GB):
                raise errors.VMException("Failed to update vm %s" % vm)

    @attr(tier=0)
    @tcms('9860', '326209')
    def test_a_balloon_usage(self):
        """
        Tests inflation and deflation of balloon
        """
        self.vm_list = ["%s-1" % BALLOON_POOL]
        self.balloon_usage(self.vm_list)

    @tcms('9860', '326211')
    def test_b_balloon_multi_memory(self):
        """
        Tests inflation and deflation of balloon on 2 VMs
        with different memories
        """
        self.vm_list = ["%s-%d" % (BALLOON_POOL, i+1) for i in range(2)]
        self.assertTrue(
            vms.updateVm(True, self.vm_list[1], memory_guaranteed=int(GB/2)),
            "Vm update failed")

        self.balloon_usage(self.vm_list, 1, True)

    @tcms('9860', '326212')
    def test_c_balloon_multi_os(self):
        """
        Test usage of balloon on different OS types
        """
        self.vm_list = ["balloon-1", config.W7, config.W2K]
        self.balloon_usage(self.vm_list)

    @attr(tier=0)
    @tcms('9860', '326216')
    def test_d_balloon_max(self):
        """
        Negative test case of balloon with minimum
        guaranteed memory set to maximum memory
        """
        vm = "balloon-1"
        self.vm_list = [vm]
        self.assertTrue(
            vms.updateVm(True, vm, memory=2*GB, memory_guaranteed=2*GB),
            "Failed to update rhel vm %s" % vm)
        self.assertTrue(
            vms.startVm(True, vm, wait_for_status=ENUMS['vm_state_up']),
            "Failed to start vm %s" % vm)
        self.balloon_usage_negative(vm)

    @attr(tier=0)
    @tcms('9860', '326214')
    def test_e_balloon_no_agent(self):
        """
        Negative test case to test balloon without agent
        """
        vm = "balloon-1"
        self.vm_list = [vm]
        self.assertTrue(
            vms.updateVm(True, vm, memory=2*GB, memory_guaranteed=GB),
            "Failed to update rhel vm")

        self.assertTrue(
            vms.startVm(True, vm, wait_for_status=ENUMS['vm_state_up']),
            "Failed to start vm %s" % vm)
        vm_machine = vms.get_vm_machine(vm, config.VMS_LINUX_USER,
                                        config.VMS_LINUX_PW)
        for i in range(ITERS):
            if vm_machine.stopService('ovirt-guest-agent'):
                break
            sleep(sleep_time)
        else:
            self.assertTrue(vms.stopVm(True, vm), "Failed to stop vm %s" % vm)
            raise errors.VMException(
                "Failed to stop guest agent on VM %s" % vm)

        self.balloon_usage_negative(vm)

    @tcms('9860', '326215')
    def test_f_balloon_multiple_vms(self):
        """
        Test ballooning with multiple (8) small VMs
        """
        list_id = range(config.BALLOON_VM_NUM)
        self.vm_list = ["%s-%d" % (BALLOON_POOL, i+1) for i in list_id]
        for vm in self.vm_list:
            self.assertTrue(
                vms.updateVm(True, vm, memory=int(GB/4),
                             memory_guaranteed=int(GB/8)),
                "Vm update failed")

        self.balloon_usage(self.vm_list)

    def tearDown(self):
        if self.pid_list:
            self.balloon_clean(self.vm_list, self.pid_list[-1])
        else:
            self.balloon_clean(self.vm_list, [], False)

    @classmethod
    def teardown_class(cls):
        """
        remove all VMS
        """
        # if any test fail remove memory load from hosts
        logger.info("Pids of processes allocating memory - %s",
                    " ".join(str(i) for i in cls.pid_list))
        if cls.pid_list:
            host_machine = machine.Machine(
                config.HOSTS[1], config.HOSTS_USER[1],
                config.HOSTS_PW[1]).util(machine.LINUX)
            host_machine.killProcess(cls.pid_list)

        if not clusters.updateCluster(
                True, config.CLUSTER_NAME[0], ballooning_enabled=False,
                ksm_enabled=True):
            raise errors.VMException("Failed to disable ballooning on cluster")
