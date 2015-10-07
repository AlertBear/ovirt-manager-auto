"""
General test of some SLA features: CPU pinning, CPU host, delete protection,
count threads as cores and placement policy
"""


import re
import random
import logging

import art.unittest_lib as libs
import rhevmtests.sla.config as c
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters

logger = logging.getLogger(__name__)

MINUTE = 60
CPUPIN_ITER = 4
HOST_PASSTHROUGH = "host_passthrough"
# TODO: add type as W/A for bug
# https://bugzilla.redhat.com/show_bug.cgi?id=1253261
# add display_type as W/A for bug
# https://bugzilla.redhat.com/show_bug.cgi?id=1253263
# must remove both after bugs fixed
VM_BASIC_PARAMETERS = {
    "cluster": c.CLUSTER_NAME[0],
    "storageDomainName": c.STORAGE_NAME[0],
    "size": c.GB, "nic": c.NIC_NAME[0],
    "network": c.MGMT_BRIDGE,
    "display_type": c.VM_DISPLAY_TYPE,
    "type": c.VM_TYPE_SERVER
}

# Bugs
# 1) Bug 1111128 - If I have vm with domain(also when it empty),
#    update vm via python SDK failed
# 2) Bug 1088914 - Not possible change vm cpu pinning via cli
# 3) Bug 1135976 - Edit pinned vm placement option clear vm cpu pinning options
#    without any error message

########################################################################


def adapt_vcpu_pinning_to_cli(vcpu_pinning):
    """
    Adapt vcpu pinning format to cli engine

    :param vcpu_pinning: vcpu pinning list
    :type vcpu_pinning: list
    :returns: adapted to cli vcpu pinning list
    :rtype: list
    """
    if c.opts["engine"] == "cli":
        cli_vcpu_pinning = []
        for pinning in vcpu_pinning:
            for key, value in pinning.iteritems():
                cli_value = value.replace(",", "\,")
                pinning[key] = cli_value
            cli_vcpu_pinning.append(pinning)
        return cli_vcpu_pinning
    return vcpu_pinning


def get_pinned_cpu_info(host_resource, vm, vcpu):
    """
    Gets the pCPU which vCPU is running on

    :param host_resource: host resource object
    :type host_resource: instance of VDS
    :param vm: name of the vm
    :type vm: str
    :param vcpu: number of virtual CPU
    :type vcpu: int
    :returns: returns the number of the pcpu that the vcpu
    is running on and it's pinning affinity
    :rtype: tuple
    :raises: HostException
    """
    rc, out, err = host_resource.executor().run_cmd(
        ["virsh", "-r", "list", "|grep", vm]
    )
    if rc:
        raise errors.HostException(
            "Can't read 'virsh -r list' on %s, err: %s" % (host_resource, err)
        )
    vm_id = out.split()[0]
    logger.info("VM pid is %s", vm_id)
    rc, out, err = host_resource.executor().run_cmd(
        ["virsh", "-r", "vcpuinfo", vm_id]
    )
    if rc:
        raise errors.HostException(
            "Can't read 'virsh -r vcpuinfo %s' on %s" % (vm_id, host_resource)
        )
    regex = r"VCPU:\s+%s\s+CPU:\s+(\d)" % str(vcpu)
    running = re.search(regex, out).group(1)
    regex = r"VCPU:\s+%s[\w\W]+?CPU Affinity:\s+([-y]+)" % str(vcpu)
    affinity = re.search(regex, out).group(1)
    logger.info(
        "VCPU %s of VM %s pinned to physical CPU %s, and has affinity of %s",
        vcpu, vm, running, affinity
    )
    return running, affinity


def get_qemu_value(host_resource, vm, arg):
    """
    Gets the relevant QEMU argument

    :param host_resource: host resource object
    :type host_resource: instance of VDS
    :param vm: name of the vm
    :type vm: str
    :param arg: argument to be checked
    :type arg: str
    :returns: returns a list of CPU flags
    :rtype: str
    :raises: HostException
    """
    rc, out, err = host_resource.executor().run_cmd(
        ["ps", "-F", "-C", "qemu-kvm", "|grep", vm]
    )
    if rc:
        raise errors.HostException(
            "Can't read 'ps' on %s, err: %s" % (host_resource, err)
        )
    regex = r"[\w\W]+ -%s ([\w]+) [\w\W]+" % arg
    res = re.search(regex, out).group(1)
    return res
########################################################################
#                             Test Cases                               #
########################################################################


@libs.attr(tier=1)
class BasicSlaClass(libs.SlaTest):
    """
    Create and delete after test new vm with different parameters
    """
    __test__ = False
    vm_name = None
    vm_desc = None
    vm_basic_parameters = None
    protected = None

    @classmethod
    def setup_class(cls):
        """
        Create new vm with given parameters
        """
        logger.info("Create new vm %s", cls.vm_name)
        if not ll_vms.createVm(
                True, cls.vm_name, cls.vm_desc, **cls.vm_basic_parameters
        ):
            raise errors.VMException("Cannot create vm")

    @classmethod
    def teardown_class(cls):
        """
        Remove protected flag if needed and remove vm
        """
        logger.info("Stop vm %s if need", cls.vm_name)
        ll_vms.stop_vms_safely([cls.vm_name])
        if cls.protected:
            logger.info("Remove protected flag from vm %s", cls.vm_name)
            if not ll_vms.updateVm(True, cls.vm_name, protected='false'):
                raise errors.VMException("Cannot update vm")
        logger.info("Remove vm %s", cls.vm_name)
        if not ll_vms.removeVm(True, cls.vm_name):
            raise errors.VMException("Cannot remove vm")


@libs.attr(tier=2)
class TestProtectedVmCase1(BasicSlaClass):
    """
    Negative: Remove protected VM
    """
    __test__ = True
    vm_name = "protected_vm1"
    vm_desc = "Delete protected VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters["protected"] = True
    protected = True

    @polarion("RHEVM3-9512")
    def test_remove_protected_vm(self):
        """
        Attempt to remove the protected VM
        """
        logger.info(
            "Attempting to remove the protected VM %s", self.vm_name
        )
        self.assertFalse(ll_vms.removeVm(True, self.vm_name))
        logger.info("Failed to remove protected VM %s", self.vm_name)

########################################################################


@libs.attr(tier=2)
class TestProtectedVmCase2(BasicSlaClass):
    """
    Negative: Force remove protected VM
    """
    __test__ = True
    vm_name = "protected_vm2"
    vm_desc = "Delete protected VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters["protected"] = True
    protected = True

    @polarion("RHEVM3-9519")
    def test_force_remove_protected_vm(self):
        """
        Attempt to force remove the protected VM
        """
        logger.info(
            "Attempting to force remove the protected VM %s", self.vm_name
        )
        self.assertFalse(ll_vms.removeVm(True, self.vm_name, force=True))
        logger.info("Failed to force remove protected VM %s", self.vm_name)

########################################################################


@libs.attr(tier=2)
class TestCPUHostCase1(BasicSlaClass):
    """
    Negative: Change migratable VM to use CPU host
    """
    __test__ = True
    vm_name = "cpuhost_vm1"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    protected = False

    @polarion("RHEVM3-9527")
    def test_set_migratable_cpuhost(self):
        """
        Negative: Attempt to set a migratable VM to use CPU host
        """
        logger.info("Attempting to update VM to use CPU host")
        self.assertTrue(
            ll_vms.updateVm(False, self.vm_name, cpu_mode=HOST_PASSTHROUGH)
        )
        logger.info("Failed to change a migratable VM to use CPU host")

########################################################################


@libs.attr(tier=2)
class TestCPUHostCase2(BasicSlaClass):
    """
    Set CPU host to a user migratable VM
    """
    __test__ = True
    vm_name = "cpuhost_vm2"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    protected = False

    @polarion("RHEVM3-9531")
    def test_set_cpuhost_user_migratable(self):
        """
        Negative: Attempt to change a VM to use CPU host + user migratable
        """
        logger.info("Attempting to change VM to migratable")
        self.assertFalse(
            ll_vms.updateVm(
                True, self.vm_name,
                placement_affinity=c.VM_USER_MIGRATABLE,
                cpu_mode=HOST_PASSTHROUGH
            ),
            "Successfully changed a CPU host vm placement affinity"
        )

########################################################################


@libs.attr(tier=2)
class TestCPUHostCase3(BasicSlaClass):
    """
    Negative: Change VM with CPU host mode (pinned) to migratable
    """
    __test__ = True
    vm_name = "cpuhost_vm3"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "placement_affinity": c.VM_PINNED,
            "placement_host": c.HOSTS[0],
            "cpu_mode": HOST_PASSTHROUGH
        }
    )
    protected = False

    @polarion("RHEVM3-9523")
    def test_set_pinned_cpuhost_vm_migratable(self):
        """
        Attempt to change a non migratable VM with CPU host
        to migratable
        """
        logger.info("Attempting to change VM to migratable.")
        self.assertTrue(
            ll_vms.updateVm(
                False, self.vm_name, placement_affinity=c.VM_MIGRATABLE,
                placement_host=c.VM_ANY_HOST
            )
        )
        logger.info(
            "Failed to change a CPU host VM placement affinity "
            "from pinned to migratable"
        )

########################################################################


class TestCPUHostCase4(BasicSlaClass):
    """
    Set a CPU host non migratable VM to have no host specified to run on
    """
    __test__ = True
    vm_name = "cpuhost_vm4"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "placement_affinity": c.VM_PINNED,
            "placement_host": c.HOSTS[0],
            "cpu_mode": HOST_PASSTHROUGH
        }
    )

    @polarion("RHEVM3-9533")
    def test_set_non_migratable_cpuhost_no_host(self):
        """
        Attempt to change a non migratable VM with CPU host
        to have no specific host to run on
        """
        logger.info(
            "Attempting to change VM to have no specific host to run on"
        )
        self.assertTrue(
            ll_vms.updateVm(
                True, self.vm_name, placement_host=c.VM_ANY_HOST
            )
        )
        logger.info(
            "Successfully change a CPU host VM to "
            "non migratable with no specific host to run on"
        )

########################################################################


class TestCPUHostCase5(BasicSlaClass):
    """
    Change CPU host vm"s placement affinity from pinned
    to user migratable
    """
    __test__ = True
    vm_name = "cpuhost_vm5"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "placement_affinity": c.VM_PINNED,
            "placement_host": c.HOSTS[0],
            "cpu_mode": HOST_PASSTHROUGH
        }
    )

    @polarion("RHEVM3-9535")
    def test_set_pinned_cpuhost_vm_user_migratable(self):
        """
        Attempt to change a non migratable VM with CPU host
        to user migratable
        """
        logger.info("Attempting to change VM to user migratable")
        self.assertTrue(
            ll_vms.updateVm(
                True, self.vm_name,
                placement_affinity=c.VM_USER_MIGRATABLE,
                placement_host=c.VM_ANY_HOST, cpu_mode=""
            )
        )
        logger.info(
            "Successfully change a CPU host VM placement affinity "
            "from pinned to user migratable"
        )

########################################################################


class TestCPUHostCase6(BasicSlaClass):
    """
    Check if VM with CPU host is running with correct QEMU values
    """
    __test__ = True
    vm_name = "cpuhost_vm6"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "placement_affinity": c.VM_PINNED,
            "placement_host": c.HOSTS[0],
            "cpu_mode": HOST_PASSTHROUGH
        }
    )

    @polarion("RHEVM3-9536")
    def test_check_qemu_params(self):
        """
        Check if VM is running with correct "-cpu" value on QEMU
        """
        logger.info("Starting VM")
        self.assertTrue(
            ll_vms.startVm(True, self.vm_name),
            "Cannot start vm %s" % self.vm_name
        )
        self.assertTrue(
            ll_vms.waitForVMState(self.vm_name, state=c.VM_UP),
            "Cannot start vm %s" % self.vm_name
        )
        logger.info("Successfully started VM")
        value = get_qemu_value(c.VDS_HOSTS[0], self.vm_name, "cpu")
        self.assertEqual(value, "host", "-cpu value is not 'host'")
        logger.info("VM is running with '-cpu host'")

########################################################################


class BasicThreadSlaClass(BasicSlaClass):
    """
    Basic Sla class for hyper-threading tests
    """
    __test__ = False

    cpu_cores = None
    cpu_threads = None
    cpu_sockets = None
    negative = False
    thread_on = False

    @classmethod
    def setup_class(cls):
        """
        Create new vm with given parameters, define class variables,
        update cluster with threads and update vm with define number of cores
        """
        super(BasicThreadSlaClass, cls).setup_class()
        if cls.cpu_cores:
            cls.cpu_cores = ll_hosts.get_host_topology(c.HOSTS[0]).cores
            logger.info("Number of cores on host: %s", cls.cpu_cores)
        if cls.cpu_sockets:
            cls.cpu_sockets = ll_hosts.get_host_topology(c.HOSTS[0]).sockets
            logger.info(
                "Number of cores per socket on host: %s", cls.cpu_sockets
            )
        if cls.cpu_threads:
            cls.cpu_threads = ll_hosts.get_host_topology(c.HOSTS[0]).threads
            logger.info(
                "Number of threads per core on host: %s", cls.cpu_threads
            )
        logger.info(
            "Update cluster with threads_as_cores=%s", cls.thread_on
        )
        if not ll_clusters.updateCluster(
                True, c.CLUSTER_NAME[0], threads_as_cores=cls.thread_on
        ):
            raise errors.ClusterException("Failed to update cluster")
        total_cores_number = cls.cpu_cores
        if cls.cpu_threads:
            total_cores_number *= cls.cpu_threads
        # In 3.5 we have limit on number of cores per socket, 16 for one socket
        if cls.negative:
            cls.cpu_sockets *= 2
        logger.info(
            "Updating vm %s to have %s cores",
            cls.vm_name, total_cores_number * cls.cpu_sockets
        )
        if not ll_vms.updateVm(
                True, cls.vm_name, cpu_socket=cls.cpu_sockets,
                cpu_cores=total_cores_number
        ):
            raise errors.VMException("Failed to update vm %s", cls.vm_name)

    @classmethod
    def teardown_class(cls):
        """
        Update cluster with threads option off and remove vm
        """
        logger.info("Update cluster with threads_as_cores=%s", cls.thread_on)
        if not ll_clusters.updateCluster(
                True, c.CLUSTER_NAME[0], threads_as_cores=False
        ):
            raise errors.ClusterException("Failed to update cluster")
        super(BasicThreadSlaClass, cls).teardown_class()


class TestThreadsOff(BasicThreadSlaClass):
    """
    Verify number of cores on host when threads off
    """
    __test__ = True
    vm_name = "threads_off_vm"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    cpu_cores = 1
    cpu_sockets = 1

    @polarion("RHEVM3-9518")
    def test_cores_as_threads_off(self):
        """
        Setting VM with number of cores equal to number of
        the host"s physical cores, while cluster policy "count
        threads as cores" is off
        """
        self.assertTrue(ll_vms.startVm(True, self.vm_name))


@libs.attr(tier=2)
class TestNegativeThreadsOff(BasicThreadSlaClass):
    """
    Negative: Verify number of cores on host when threads off
    """
    __test__ = True
    vm_name = "threads_off_negative_vm"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    cpu_cores = 1
    cpu_sockets = 1
    negative = True

    @polarion("RHEVM3-9517")
    def test_cores_as_threads_off(self):
        """
        Negative: Setting VM with number of cores equal to double the number of
        the host"s physical cores, while cluster policy "count
        threads as cores" is off
        """
        self.assertFalse(ll_vms.startVm(True, self.vm_name))


class TestThreadsOn(BasicThreadSlaClass):
    """
    Verify number of cores on host when threads on
    """
    __test__ = True
    vm_name = "threads_on_vm"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    cpu_cores = 1
    cpu_sockets = 1
    cpu_threads = 1
    thread_on = True

    @polarion("RHEVM3-9515")
    def test_cores_as_threads_on1(self):
        """
        Setting VM with number of cores equal to double the number of
        the host"s physical cores, while cluster policy "count
        threads as cores" is on
        """
        self.assertTrue(ll_vms.startVm(True, self.vm_name))


@libs.attr(tier=2)
class TestThreadsOnNegative(BasicThreadSlaClass):
    """
    Negative: Verify number of cores on host when threads on
    """
    __test__ = True
    vm_name = "threads_on_negative_vm"
    vm_desc = "CPU Host VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    cpu_cores = 1
    cpu_sockets = 1
    cpu_threads = 1
    negative = True
    thread_on = True

    @polarion("RHEVM3-9516")
    def test_cores_as_threads_on2(self):
        """
        Negative: Setting VM with number of cores equal to double the number of
        the host"s physical cores, while cluster policy "count
        threads as cores" is on
        """
        self.assertFalse(ll_vms.startVm(True, self.vm_name))

########################################################################


class TestCPUPinCase1(BasicSlaClass):
    """
    Check CPU pinning format correctness
    """
    __test__ = True
    vm_name = "cpupin_vm1"
    vm_desc = "CPU Pin Vm"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "placement_affinity": c.VM_PINNED,
            "placement_host": c.HOSTS[0]
        }
    )
    cores = 1
    sockets = 1

    @classmethod
    def setup_class(cls):
        """
        Create a non migratable VM and count number of cores on host
        """
        super(TestCPUPinCase1, cls).setup_class()
        cls.sockets = ll_hosts.get_host_topology(c.HOSTS[0]).sockets
        logger.info("Number of sockets on host: %s" % cls.sockets)
        cls.cores = ll_hosts.get_host_topology(c.HOSTS[0]).cores
        logger.info("Number of cores per socket on host: %s" % cls.cores)

    @polarion("RHEVM3-9541")
    def test_cpupin_format1(self):
        """
        Set pinning to 0#0
        """
        logger.info("Setting VCPU pinning to 0#0")
        self.assertTrue(
            ll_vms.updateVm(
                True, self.vm_name, vcpu_pinning=[{"0": "0"}]
            ),
            "Failed to change VCPU pinning"
        )
        logger.info("Successfully changed VCPU pinning to 0#0.")

    @polarion("RHEVM3-12221")
    def test_cpupin_format2(self):
        """
        Set pinning to 0#0-(number of cores-1)
        """
        upper = self.sockets * self.cores - 1
        logger.info("Setting VCPU pinning to 0#0-%s", upper)
        self.assertTrue(
            ll_vms.updateVm(
                True, self.vm_name, vcpu_pinning=[{"0": "0-%s" % upper}]
            ),
            "Failed to change VCPU pinning"
        )
        logger.info(
            "Successfully changed VCPU pinning to 0#1-%s", upper
        )

    @libs.attr(tier=2)
    @polarion("RHEVM3-12222")
    def test_cpupin_format3(self):
        """
        Negative: Set pinning to 0#^1
        """
        logger.info("Setting VCPU pinning to 0#^1")
        self.assertFalse(
            ll_vms.updateVm(
                True, self.vm_name, vcpu_pinning=[{"0": "^1"}]
            ),
            "Successfully changed VCPU pinning"
        )
        logger.info("Unable to change VCPU pinning to 0#^1")

    @libs.attr(tier=2)
    @polarion("RHEVM3-12223")
    def test_cpupin_format4(self):
        """
        Negative: Set pinning to 0#^1,^2
        """
        vcpu_pinning = adapt_vcpu_pinning_to_cli([{"0": "^1,^2"}])
        logger.info("Setting VCPU pinning to 0#^1,^2")
        self.assertFalse(
            ll_vms.updateVm(
                True, self.vm_name, vcpu_pinning=vcpu_pinning
            ),
            "Successfully changed VCPU pinning"
        )
        logger.info("Unable to change VCPU pinning to 0#^1,^2")

    @polarion("RHEVM3-12224")
    def test_cpupin_format5(self):
        """
        Set pinning to 0#0-3,^1
        """
        if (self.cores * self.sockets) < 4:
            raise errors.SkipTest("Too few CPU cores")
        vcpu_pinning = adapt_vcpu_pinning_to_cli([{"0": "0-3,^1"}])
        logger.info("Setting VCPU pinning to 0#0-3,^1")
        compare = c.opts["engine"] != "cli"
        self.assertTrue(
            ll_vms.updateVm(
                True, self.vm_name, vcpu_pinning=vcpu_pinning, compare=compare
            ),
            "Failed to change VCPU pinning"
        )
        logger.info("Successfully changed VCPU pinning to 0#0-3,^1")

    @polarion("RHEVM3-12225")
    def test_cpupin_format6(self):
        """
        Set pinning to 0#0-3,^1,^2
        """
        if (self.cores * self.sockets) < 4:
            raise errors.SkipTest("Too few CPU cores")
        vcpu_pinning = adapt_vcpu_pinning_to_cli([{"0": "0-3,^1,^2"}])
        logger.info("Setting VCPU pinning to 0#0-3,^1,^2")
        compare = c.opts["engine"] != "cli"
        self.assertTrue(
            ll_vms.updateVm(
                True, self.vm_name, vcpu_pinning=vcpu_pinning, compare=compare
            ),
            "Failed to change VCPU pinning"
        )
        logger.info("Successfully changed VCPU pinning to 0#0-3,^1,^2")

    @polarion("RHEVM3-12226")
    def test_cpupin_format7(self):
        """
        Set pinning to 0#1,2,3
        """
        if (self.cores * self.sockets) < 4:
            raise errors.SkipTest("Too few CPU cores")
        vcpu_pinning = adapt_vcpu_pinning_to_cli([{"0": "1,2,3"}])
        logger.info("Setting VCPU pinning to 0#1,2,3")
        compare = c.opts["engine"] != "cli"
        self.assertTrue(
            ll_vms.updateVm(
                True, self.vm_name, vcpu_pinning=vcpu_pinning, compare=compare
            ),
            "Failed to change VCPU pinning"
        )
        logger.info("Successfully changed VCPU pinning to 0#1,2,3")

    @libs.attr(tier=2)
    @polarion("RHEVM3-12227")
    def test_cpupin_format8(self):
        """
        Negative: Set pinning to 0#0_0#1
        """
        if (self.cores * self.sockets) < 2:
            raise errors.SkipTest("Too few CPU cores")
        vcpu_pinning = adapt_vcpu_pinning_to_cli([{"0": "0"}, {"0": "1"}])
        logger.info("Setting VCPU pinning to 0#0_0#1")
        self.assertFalse(
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=vcpu_pinning)
        )
        logger.info("Successfully changed VCPU pinning to 0#0_0#1.")

    @libs.attr(tier=2)
    @polarion("RHEVM3-12228")
    def test_cpupin_format9(self):
        """
        Negative: Letter instead of pCPU
        """
        logger.info("Setting VCPU pinning to 0#A")
        self.assertFalse(
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=[{"0": "A"}]),
            "Successfully changed VCPU pinning"
        )
        logger.info("Unable to change VCPU pinning to 0#A.")

    @libs.attr(tier=2)
    @polarion("RHEVM3-12229")
    def test_cpupin_format10(self):
        """
        Negative: Letter instead of pCPU
        """
        try:
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=[{"A": "0"}])
            self.assertTrue(False, "Successfully changed VCPU pinning to A#0")
        except ValueError:
            logger.info("Unable to change VCPU pinning to A#0")

    @libs.attr(tier=2)
    @polarion("RHEVM3-12230")
    def test_cpupin_format15(self):
        """
        Negative: Pinning to empty range
        """
        vcpu_pinning = adapt_vcpu_pinning_to_cli([{"0": "0-1,^0,^1"}])
        logger.info("Setting VCPU pinning to 0#0-1,^0,^1")
        self.assertFalse(
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=vcpu_pinning),
            "Successfully changed VCPU pinning"
        )
        logger.info("Unable to change VCPU pinning to 0#0-1,^0,^1")

    @libs.attr(tier=2)
    @polarion("RHEVM3-12231")
    def test_cpupin_format16(self):
        """
        Negative: Pinning to non-existing pCPU
        """
        logger.info("Setting VCPU pinning to 0#4096")
        self.assertTrue(
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=[{"0": "4096"}]),
            "Unable changed VCPU pinning"
        )
        logger.info("Successfully to change VCPU pinning to 0#4096")
        logger.info("Try to start vm %s", self.vm_name)
        self.assertFalse(
            ll_vms.startVm(True, self.vm_name, timeout=MINUTE),
            "Success to run vm"
        )

    @libs.attr(tier=2)
    @polarion("RHEVM3-12232")
    def test_cpupin_format17(self):
        """
        Negative: Pinning to an empty string
        """
        logger.info("Setting VCPU pinning to 0#")
        self.assertFalse(
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=[{"0": ""}]),
            "Successfully changed VCPU pinning"
        )
        logger.info("Unable to change VCPU pinning to 0#")

    @libs.attr(tier=2)
    @polarion("RHEVM3-12233")
    def test_cpupin_format18(self):
        """
        Negative: Pinning non-existing vCPU
        """
        logger.info("Setting VCPU pinning to 4096#0")
        self.assertFalse(
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=[{"4096": "0"}]),
            "Successfully changed VCPU pinning"
        )
        logger.info("Unable to change VCPU pinning to 4096#0")

########################################################################


@libs.attr(tier=2)
class TestCPUPinCase2(BasicSlaClass):
    """
    Negative: Set CPU pinning to a migratable VM
    """
    __test__ = True
    vm_name = "cpupin_vm2"
    vm_desc = "CPU Pin Vm"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()

    @polarion("RHEVM3-9532")
    def test_set_migratable_cpupin(self):
        """
        Attempt to set a migratable VM to use CPU pinning
        """
        logger.info("Attempting to update VM to use CPU pinning")
        self.assertFalse(
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=[{"0": "0"}])
        )
        logger.info("Failed to change a migratable VM to use CPU pinning")

########################################################################


@libs.attr(tier=2)
class TestCPUPinCase3(BasicSlaClass):
    """
    Negative: Change CPU pinned VM to migratable
    """
    __test__ = True
    vm_name = "cpupin_vm3"
    vm_desc = "CPU Pin Vm"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "placement_affinity": c.VM_PINNED,
            "placement_host": c.HOSTS[0],
            "vcpu_pinning": [{"0": "0"}]
        }
    )

    @polarion("RHEVM3-9534")
    def test_set_pinned_cpupin_vm_migratable(self):
        """
        Attempt to change a non migratable VM with CPU pinning
        to migratable.
        """
        logger.info("Attempting to change VM to migratable")
        self.assertFalse(
            ll_vms.updateVm(
                True, self.vm_name, placement_affinity=c.VM_MIGRATABLE,
                placement_host=c.VM_ANY_HOST
            )
        )
        logger.info(
            "Failed to change a CPU host VM placement affinity "
            "from pinned to migratable"
        )

########################################################################


@libs.attr(tier=2)
class TestCPUPinCase4(BasicSlaClass):
    """
    Negative: Set CPU pinning to a user migratable VM
    """
    __test__ = True
    vm_name = "cpupin_vm4"
    vm_desc = "CPU Pin Vm"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {"placement_affinity": c.VM_USER_MIGRATABLE}
    )

    @polarion("RHEVM3-9543")
    def test_set_user_migratable_cpupin(self):
        """
        Attempt to set a user migratable VM to use CPU pinning
        """
        logger.info("Attempting to update VM to use CPU pinning")
        self.assertFalse(
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=[{"0": "0"}])
        )
        logger.info(
            "Failed to change a user migratable VM to use CPU pinning"
        )

########################################################################


@libs.attr(tier=2)
class TestCPUPinCase5(BasicSlaClass):
    """
    Negative: Change CPU pinned VM to user migratable
    """
    __test__ = True
    vm_name = "cpupin_vm5"
    vm_desc = "CPU Pin Vm"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "placement_affinity": c.VM_PINNED,
            "placement_host": c.HOSTS[0],
            "vcpu_pinning": [{"0": "0"}]
        }
    )

    @polarion("RHEVM3-9542")
    def set_pinned_cpupin_vm_user_migratable(self):
        """
        Attempt to change a non migratable VM with CPU pinning
        to user migratable
        """
        logger.info("Attempting to change VM to user migratable")
        self.assertFalse(
            ll_vms.updateVm(
                True, self.vm_name,
                placement_affinity=c.VM_USER_MIGRATABLE,
                placement_host=c.VM_ANY_HOST
            )
        )
        logger.info(
            "Failed to change a CPU host VM placement affinity "
            "from pinned to user migratable"
        )

########################################################################


@libs.attr(tier=2)
class TestCPUPinCase6(BasicSlaClass):
    """
    Check if pinning holds on random pCPU"s
    """
    __test__ = True
    vm_name = "cpupin_vm6"
    vm_desc = "CPU Pin Vm"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "placement_affinity": c.VM_PINNED,
            "placement_host": c.HOSTS[0],
            "vcpu_pinning": [{"0": "0"}]
        }
    )
    total_cores = 1

    @classmethod
    def setup_class(cls):
        """
        Create a non migratable
        """
        super(TestCPUPinCase6, cls).setup_class()
        sockets = ll_hosts.get_host_topology(c.HOSTS[0]).sockets
        logger.info("Number of sockets on host: %s" % sockets)
        cores = ll_hosts.get_host_topology(c.HOSTS[0]).cores
        logger.info("Number of cores per socket on host: %s" % cores)
        cls.total_cores = sockets * cores

    @polarion("RHEVM3-9529")
    def test_check_random_pinning(self):
        """
        Set CPU pinning to random pCPU cores and check if pining holds
        """
        iterations = CPUPIN_ITER if self.total_cores > 1 else 1
        for n in range(iterations):
            logger.info("Attempt %s:" % (n + 1))
            online_cpus = ll_sla.get_list_of_online_cpus_on_resource(
                c.VDS_HOSTS[0]
            )
            total_online_cpus = online_cpus[-1] + online_cpus[1]
            expected_pin = str(random.choice(online_cpus))
            hyp_exp = "-" * int(expected_pin)
            hyp_cores = "-" * (total_online_cpus - int(expected_pin) - 1)
            expected_affinity = "%sy%s" % (hyp_exp, hyp_cores)

            logger.info("Setting CPU pinning to 0#%s" % expected_pin)
            self.assertTrue(
                ll_vms.updateVm(
                    True, self.vm_name, vcpu_pinning=[{"0": expected_pin}]
                ),
                "Failed to update VM"
            )
            self.assertTrue(
                ll_vms.startVm(True, self.vm_name), "Failed to start VM"
            )
            res = get_pinned_cpu_info(c.VDS_HOSTS[0], self.vm_name, "0")
            self.assertTrue(
                ll_vms.stopVm(True, self.vm_name), "Failed to stop VM"
            )
            logger.info(
                "vCPU #0 is expected to be pinned to pCPU #%s, "
                "and is actually pinned to pCPU #%s",
                expected_pin, res[0]
            )
            logger.info(
                "vCPU #0 is expected to have pinning affinity of %s, "
                "and actually has %s",
                expected_affinity, res[1][:total_online_cpus]
            )
            self.assertEqual(
                expected_pin, res[0],
                "Actual CPU pinning does not match expectation"
            )
            self.assertEqual(
                expected_affinity, res[1][:total_online_cpus],
                "Actual CPU affinity does not match expectation"
            )

########################################################################


class TestCPUPinCase7(BasicSlaClass):
    """
    Check if pinning holds when all vCPU"s are running on the same pCPU
    """
    __test__ = True
    vm_name = "cpupin_vm7"
    vm_desc = "CPU Pin Vm"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "placement_affinity": c.VM_PINNED,
            "placement_host": c.HOSTS[0]
        }
    )
    total_cores = 1

    @classmethod
    def setup_class(cls):
        """
        Create a non migratable VM
        """
        super(TestCPUPinCase7, cls).setup_class()
        sockets = ll_hosts.get_host_topology(c.HOSTS[0]).sockets
        logger.info("Number of sockets on host: %s" % sockets)
        cores = ll_hosts.get_host_topology(c.HOSTS[0]).cores
        logger.info("Number of cores per socket on host: %s" % cores)
        logger.info("Update vm")
        if not ll_vms.updateVm(
                True, cls.vm_name, cpu_cores=cores, cpu_socket=sockets
        ):
            raise errors.VMException("Failed to update vm")
        cls.total_cores = sockets * cores

    @polarion("RHEVM3-9539")
    def test_check_pinning_load(self):
        """
        Set CPU pinning to random pCPU cores and check if pining holds
        """
        if self.total_cores < 1:
            raise errors.SkipTest("Too few cores")
        pinning = [{str(i): "0"} for i in xrange(self.total_cores)]
        logger.info("Pinning all VCPU's to pCPU #0")
        self.assertTrue(
            ll_vms.updateVm(True, self.vm_name, vcpu_pinning=pinning),
            "Failed to update VM"
        )
        self.assertTrue(
            ll_vms.startVm(True, self.vm_name), "Failed to start VM"
        )
        for i in range(self.total_cores):
            pin_info = get_pinned_cpu_info(
                c.VDS_HOSTS[0], self.vm_name, i
            )
            self.assertTrue(
                pin_info[0], "Could not retrieve VM pinning information"
            )
            self.assertEqual(
                pin_info[0], "0", "VCPU #%d is not running on pCPU #0" % i
            )
        logger.info("All VCPU's are running on pCPU #0")

########################################################################


@libs.attr(tier=2)
class TestCPUPinCase8(BasicSlaClass):
    """
    Negative: Set CPU pinning to a non migratable VM with no host
    specified to run on
    """
    __test__ = True
    vm_name = "cpupin_vm8"
    vm_desc = "Placement policy VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()

    @polarion("RHEVM3-9544")
    def test_set_pinned_cpupin_vm_a(self):
        """
        Negative: Attempt to change VM to use CPU pinning, be non-migratable
        with no host specified to run on
        """
        logger.info("Attempting to change VM to user migratable")
        self.assertFalse(
            ll_vms.updateVm(
                True, self.vm_name, placement_affinity=c.VM_PINNED,
                placement_host=c.VM_ANY_HOST, vcpu_pinning=[{"0": "0"}]
            )
        )
        logger.info(
            "As expected, failed to change a VM to use CPU pinning, "
            "be non migratable with no host specified to run on"
        )


########################################################################


class TestPlacementPolicyCase1(BasicSlaClass):
    """
    Migrate a migratable VM
    """
    __test__ = True
    vm_name = "placement_vm1"
    vm_desc = "Placement policy VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "start": "true",
            "placement_host": c.HOSTS[0]
        }
    )

    @polarion("RHEVM3-9522")
    def test_migrate_migratable(self):
        """
        Migrate a migratable VM
        """
        if (len(c.HOSTS)) < 2:
            raise errors.SkipTest("Too few hosts")
        logger.info("Attempting to migratable a migratable VM")
        self.assertTrue(
            ll_vms.migrateVm(True, self.vm_name, host=c.HOSTS[1]),
            "Error migrating VM"
        )
        logger.info("Successfully migrated VM")

########################################################################


class TestPlacementPolicyCase2(BasicSlaClass):
    """
    Migrate a user-migratable VM
    """
    __test__ = True
    vm_name = "placement_vm2"
    vm_desc = "Placement policy VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "start": "true",
            "placement_host": c.HOSTS[0],
            "placement_affinity": c.VM_USER_MIGRATABLE
        }
    )

    @polarion("RHEVM3-9525")
    def test_migrate_user_migratable(self):
        """
        Migrate a user-migratable VM
        """
        if (len(c.HOSTS)) < 2:
            raise errors.SkipTest("Too few hosts")
        logger.info("Attempting to migratable a migratable VM")
        self.assertTrue(
            ll_vms.migrateVm(
                True, self.vm_name, host=c.HOSTS[1], force=True
            ),
            "Error migrating VM"
        )
        logger.info("Successfully migrated VM")

########################################################################


class TestPlacementPolicyCase3(BasicSlaClass):
    """
    Migrate a non-migratable VM
    """
    __test__ = True
    vm_name = "placement_vm3"
    vm_desc = "Placement policy VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update(
        {
            "start": "true",
            "placement_host": c.HOSTS[0],
            "placement_affinity": c.VM_PINNED
        }
    )

    @polarion("RHEVM3-9526")
    def test_migrate_non_migratable(self):
        """
        Migrate a non-migratable VM
        """
        if (len(c.HOSTS)) < 2:
            raise errors.SkipTest("Too few hosts")
        logger.info("Attempting to migratable a migratable VM")
        self.assertFalse(
            ll_vms.migrateVm(True, self.vm_name, host=c.HOSTS[1]),
            "Successfully migrated VM"
        )
        logger.info("Failed to to migrate VM")

########################################################################


class TestPlacementPolicyCase4(BasicSlaClass):
    """
    Run non migratable VM with no specific host
    """
    __test__ = True
    vm_name = "placement_vm4"
    vm_desc = "Placement policy VM"
    vm_basic_parameters = VM_BASIC_PARAMETERS.copy()
    vm_basic_parameters.update({"placement_affinity": c.VM_PINNED})

    @polarion("RHEVM3-9530")
    def test_run_non_migratable_no_specific(self):
        """
        Start a non-migratable VM with no specific host to run on
        """
        self.assertTrue(
            ll_vms.startVm(
                True, self.vm_name, wait_for_status=c.VM_UP
            ),
            "Cannot start vm %s" % self.vm_name
        )
        logger.info("Successfully started VM")
