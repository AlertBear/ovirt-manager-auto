"""
SLA test
"""

from nose.tools import istest
from unittest import TestCase
from unittest2 import skipIf
from functools import wraps
import logging
import random

import art.rhevm_api.tests_lib.low_level.vms as vms
import art.rhevm_api.tests_lib.low_level.clusters as clusters
from art.core_api.apis_utils import data_st


from art.rhevm_api.utils.test_utils import get_api
import art.test_handler.exceptions as errors
from art.test_handler.settings import opts
from art.test_handler.tools import bz
from utilities import machine
import config
import re

import art.rhevm_api.tests_lib.low_level.vms as vms

HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')

logger = logging.getLogger(__package__ + __name__)

DISK_SIZE = 3 * 1024 * 1024 * 1024
ENUMS = opts['elements_conf']['RHEVM Enums']
ANY_HOST = ENUMS['placement_host_any_host_in_cluster']
MIGRATABLE = ENUMS['vm_affinity_migratable']
USER_MIGRATABLE = ENUMS['vm_affinity_user_migratable']
PINNED = ENUMS['vm_affinity_pinned']

########################################################################


def getPinnedCPUInfo(host, host_user, host_pwd, vm, vcpu):
    '''
    Gets the pCPU which vCPU is running on.
    Author: ibegun
    Parameters:
        * host - ip of host
        * host_user - user for the host
        * host_pwd - user password
        * vm - name of the vm
        * vcpu - number of virtual CPU
    Return value: On success, returns the number of the pcpu that the vcpu
        is running on and it's pinning affinity. Otherwise returns False.
    '''
    host_machine = machine.Machine(host, host_user, host_pwd).util('linux')
    rc, output = host_machine.runCmd(['virsh', '-r', 'list', '|grep', vm])
    if not rc or not output:
        logger.error("Can't read 'virsh -r list' on %s", host)
        return False
    vm_id = output.split()[0]
    logger.info("VM pid is %s", vm_id)
    rc, output = host_machine.runCmd(['virsh', '-r', 'vcpuinfo', vm_id])
    if not rc or not output:
        logger.error("Can't read 'virsh -r vcpuinfo {0}'"
                     " on {1}".format(vm_id, host))
        return False
    regex = r'VCPU:\s+' + str(vcpu) + r'\s+CPU:\s+(\d)'
    running = re.search(regex, output).group(1)
    regex = r'VCPU:\s+' + str(vcpu) + r'[\w\W]+?CPU Affinity:\s+([-y]+)'
    affinity = re.search(regex, output).group(1)
    logger.info("vCPU {0} of VM {1} is pinned to physical "
                "CPU {2}, and has affinity of {3}."
                "".format(vcpu, vm, running, affinity))
    return running, affinity


def getCpuFlags(host, host_user, host_pwd):
    '''
    Gets the CPU flags for given machine.
    Author: ibegun
    Parameters:
        * host - ip of host
        * host_user - user for the host
        * host_pwd - user password
    Return value: On success, returns a list of CPU flags.
        Otherwise returns False.
    '''
    output = None
    host_machine = machine.Machine(host, host_user, host_pwd).util('linux')
    rc, output = host_machine.runCmd(['cat', '/proc/cpuinfo', '|grep',
                                      'flags', '|uniq'])
    if not rc or not output:
        logger.error("Can't read '/proc/cpuinfo' on {0}".format(host))
        return False
    return output.split()[2:]


def getQemuValue(host, host_user, host_pwd, vm, arg):
    '''
    Gets the relevant QEMU argument
    Author: ibegun
    Parameters:
        * host - ip of host
        * host_user - user for the host
        * host_pwd - user password
        * vm - name of the vm
        * arg - argument to be checked
    Return value: On success, returns a list of CPU flags.
        Otherwise returns False.
    '''
    host_machine = machine.Machine(host, host_user, host_pwd).util('linux')
    rc, output = host_machine.runCmd(['ps', '-F', '-C', 'qemu-kvm',
                                      '|grep', vm])
    if not rc or not output:
        logger.error("Can't read 'ps' on {0}".format(host))
        return False
    regex = r'[\w\W]+ -' + arg + r' ([\w]+) [\w\W]+'
    res = re.search(regex, output).group(1)
    return res
########################################################################
#                             Test Cases                               #
########################################################################


class ProtectedVm_Case1(TestCase):
    """
    Negative: Remove protected VM
    """
    __test__ = True
    vm_name = "protected_vm1"

    @classmethod
    def setup_class(cls):
        '''
        Create a delete protected VM
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="Delete protected VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1', protected=True):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a delete protected VM.")

    @istest
    def remove_protected_vm(self):
        """
        Attemp to remove the protected VM
        """
        logger.info("Attempting to remove the protected "
                    "VM %s." % self.vm_name)
        self.assertTrue(vms.removeVm(positive=False, vm=self.vm_name))
        logger.info("Failed to remove protected VM %s." % self.vm_name)

    @classmethod
    def teardown_class(cls):
        '''
        Remove protection from VM and delete it.
        '''
        if not vms.updateVm(positive=True, vm=cls.vm_name, protected=False):
            raise errors.VMException("Cannot update vm %s" % cls.vm_name)
        logger.info("Successfully created a delete protected "
                    "VM %s." % cls.vm_name)
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class ProtectedVm_Case2(TestCase):
    """
    Negative: Force remove protected VM
    """
    __test__ = True
    vm_name = "protected_vm2"

    @classmethod
    def setup_class(cls):
        '''
        Create a delete protected VM
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="Delete protected VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1', protected=True):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a delete protected VM.")

    @istest
    def force_remove_protected_vm(self):
        '''
        Attemp to force remove the protected VM
        '''
        logger.info("Attempting to force remove the protected "
                    "VM %s." % self.vm_name)
        self.assertTrue(vms.removeVm(positive=False, vm=self.vm_name,
                                     force=True))
        logger.info("Failed to force remove protected VM %s." % self.vm_name)

    @classmethod
    def teardown_class(cls):
        '''
        Remove protection from VM and delete it.
        '''
        if not vms.updateVm(positive=True, vm=cls.vm_name, protected=False):
            raise errors.VMException("Cannot update vm %s" % cls.vm_name)
        logger.info("Successfully removed delete protection "
                    "VM %s." % cls.vm_name)
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUHost_Case1(TestCase):
    """
    Negative: Change migratable VM to use CPU host
    """
    __test__ = True
    vm_name = "cpuhost_vm1"

    @classmethod
    def setup_class(cls):
        '''
        Create a migratable VM
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU Host VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created VM.")

    @istest
    def set_migratable_cpuhost(self):
        '''
        Negative: Attemp to set a migratable VM to use CPU host
        '''
        logger.info("Attemping to update VM to use CPU host.")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     cpu_mode='host_passthrough'))
        logger.info("Failed to change a migratable VM to use CPU host")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUHost_Case2(TestCase):
    """
    Set CPU host to a user migratable VM
    """
    __test__ = True
    vm_name = "cpuhost_vm2"

    @classmethod
    def setup_class(cls):
        '''
        Create a user migratable VM with cpu host
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU Host VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a user migratable VM.")

    @istest
    @bz('928402')
    def set_cpuhost_user_migratable(self):
        '''
        Attemp to change a VM to use CPU host + user migratable
        '''
        logger.info("Attemping to change VM to migratable.")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     placement_affinity=USER_MIGRATABLE,
                                     cpu_mode='host_passthrough'))
        logger.info("Successfully changed a CPU host VM's placement affinity "
                    "from user migratable to migratable")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUHost_Case3(TestCase):
    """
    Negative: Change VM with CPU host mode (pinned) to migratable
    """
    __test__ = True
    vm_name = "cpuhost_vm3"

    @classmethod
    def setup_class(cls):
        '''
        Create a non migratable VM with CPU host
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU Host VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1',
                            placement_affinity=PINNED,
                            placement_host=config.hosts[0],
                            cpu_mode='host_passthrough'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a cpu host (pinned) VM.")

    @istest
    def set_pinned_cpuhost_vm_migratable(self):
        '''
        Attemp to change a non migratable VM with CPU host
        to migratable.
        '''
        logger.info("Attemping to change VM to migratable.")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     placement_affinity=MIGRATABLE,
                                     placement_host=ANY_HOST))
        logger.info("Failed to change a CPU host VM's placement affinity "
                    "from pinned to migratable")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUHost_Case4(TestCase):
    """
    Set a CPU host non migratable VM to have no host specified to run on
    """
    __test__ = True
    vm_name = "cpuhost_vm4"

    @classmethod
    def setup_class(cls):
        '''
        Create a non migratable CPU host vm
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU Host VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1',
                            placement_affinity=PINNED,
                            placement_host=config.hosts[0],
                            cpu_mode='host_passthrough'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a non migratable with"
                    "not specific host to run on VM.")

    @istest
    def set_user_migratable_cpuhost_pinned(self):
        '''
        Attemp to change a user migratable VM with CPU host
        to non migratable.
        '''
        logger.info("Attemping to change VM to non migratable.")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     placement_host=ANY_HOST))
        logger.info("Successfully change a CPU host VM's placement affinity "
                    "from user migratable to pinned")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUHost_Case5(TestCase):
    """
    Change CPU host vm's placement affinity from pinned
    to user migratable.
    """
    __test__ = True
    vm_name = "cpuhost_vm5"

    @classmethod
    def setup_class(cls):
        '''
        Create a non migratable CPU host VM
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU Host VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1',
                            placement_affinity=PINNED,
                            placement_host=config.hosts[0],
                            cpu_mode='host_passthrough'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a non migratable VM.")

    @istest
    @bz("928402")
    def set_pinned_cpuhost_vm_user_migratable(self):
        '''
        Attemp to change a non migratable VM with CPU host
        to user migratable.
        '''
        logger.info("Attemping to change VM to user migratable.")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     placement_affinity=USER_MIGRATABLE,
                                     placement_host=ANY_HOST))
        logger.info("Successfully change a CPU host VM's placement affinity "
                    "from pinned to user migratable")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUHost_Case6(TestCase):
    """
    Check if VM with CPU host is running with correct QEMU values
    """
    __test__ = True
    vm_name = "cpuhost_vm6"

    @classmethod
    def setup_class(cls):
        '''
        Create a user migratable CPU host VM
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU Host VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1',
                            placement_affinity=USER_MIGRATABLE,
                            cpu_mode='host_passthrough'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a user migratable cpu host VM.")

    @istest
    def check_qemu_params(self):
        '''
        Check if VM is running with correct '-cpu' value on QEMU
        '''
        logger.info("Starting VM.")
        self.assertTrue(vms.startVm(positive=True, vm=self.vm_name),
                        "Cannot start vm %s" % self.vm_name)
        logger.info("Successfully started VM.")
        value = getQemuValue(config.hosts[0], 'root', config.hosts_pw[0],
                             self.vm_name, 'cpu')
        self.assertTrue(value,
                        "Cannot check host processes")
        self.assertTrue(value == "host",
                        "-cpu value is not 'host'")
        logger.info("VM is running with '-cpu host'")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.stopVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot stop vm %s" % cls.vm_name)
        logger.info("Successfully stopped %s." % cls.vm_name)
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class Threads_Case1(TestCase):
    """
    Verify number of cores on host, depending on cluster policy
    """
    __test__ = True
    vm_name = "threads_vm"
    cores = 1
    threads = 1
    sockets = 1

    @classmethod
    def setup_class(cls):
        '''
        Create VM and check how many sockets/cores/threads are on the host.
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU Host VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created VM.")
        host_obj = HOST_API.find(config.hosts[0])
        if not host_obj:
            raise errors.HostException("Cannot find host %s"
                                       % config.hosts[0])
        cls.sockets = host_obj.cpu.topology.sockets
        logger.info("Number of sockets on host: %s" % cls.sockets)
        cls.cores = host_obj.cpu.topology.cores
        logger.info("Number of cores per socket on host: %s" % cls.cores)
        cls.threads = host_obj.cpu.topology.threads
        logger.info("Number of threads per core on host: %s" % cls.threads)

    @istest
    def cores_as_threads_off1(self):
        '''
        Setting VM with number of cores equal to number of
        the host's physical cores, while cluster policy "count
        threads as cores" is off.
        '''
        self.assertTrue(clusters.updateCluster(positive=True,
                                               cluster=config.cluster_name,
                                               threads_as_cores=False))
        logger.info("Updating {0} to have {1} cores."
                    .format(self.vm_name, self.cores*self.sockets))
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     cpu_sockets=self.sockets,
                                     cpu_cores=self.cores))
        logger.info("Update successful. Starting VM %s:" % self.vm_name)
        self.assertTrue(vms.startVm(positive=True, vm=self.vm_name))
        logger.info("Started succefully. Stopping VM %s:" % self.vm_name)
        self.assertTrue(vms.shutdownVm(positive=True, vm=self.vm_name))
        logger.info("Stopped VM %s" % self.vm_name)

    @istest
    def cores_as_threads_off2(self):
        '''
        Negative: Setting VM with number of cores equal to double the number of
        the host's physical cores, while cluster policy "count
        threads as cores" is off.
        '''
        self.assertTrue(clusters.updateCluster(positive=True,
                                               cluster=config.cluster_name,
                                               threads_as_cores=False))
        logger.info("Setting {0} to have {1} cores."
                    .format(self.vm_name, self.cores*self.sockets*2))
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     cpu_sockets=self.sockets,
                                     cpu_cores=self.cores*2))
        logger.info("Update successful. Starting VM %s:" % self.vm_name)
        self.assertTrue(vms.startVm(positive=False, vm=self.vm_name))
        logger.info("Starting VM failed.")

    @istest
    def cores_as_threads_on1(self):
        '''
        Setting VM with number of cores equal to double the number of
        the host's physical cores, while cluster policy "count
        threads as cores" is on.
        '''
        self.assertTrue(clusters.updateCluster(positive=True,
                                               cluster=config.cluster_name,
                                               threads_as_cores=True))
        logger.info("Setting {0} to have {1} cores."
                    .format(self.vm_name,
                            self.cores*self.sockets*self.threads))
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     cpu_sockets=self.sockets,
                                     cpu_cores=self.cores*self.threads))
        logger.info("Update successful. Starting VM %s:" % self.vm_name)
        self.assertTrue(vms.startVm(positive=True, vm=self.vm_name))
        logger.info("Started succefully. Stopping VM %s:" % self.vm_name)
        self.assertTrue(vms.stopVm(positive=True, vm=self.vm_name))
        logger.info("Stopped VM %s" % self.vm_name)

    @istest
    def cores_as_threads_on2(self):
        '''
        Negative: Setting VM with number of cores equal to double the number of
        the host's physical cores, while cluster policy "count
        threads as cores" is on.
        '''
        self.assertTrue(clusters.updateCluster(positive=True,
                                               cluster=config.cluster_name,
                                               threads_as_cores=True))
        logger.info("Setting {0} to have {1} cores."
                    .format(self.vm_name,
                            self.cores*self.sockets*self.threads*2))
        if vms.updateVm(positive=True, vm=self.vm_name,
                        cpu_sockets=self.sockets,
                        cpu_cores=self.cores*self.threads*2):
            logger.info("Update successful. Starting VM %s:" % self.vm_name)
            self.assertTrue(vms.startVm(positive=False, vm=self.vm_name))
            logger.info("Starting VM failed.")
        else:
            logger.info("Cannot set VM {0} to have {1} cores."
                        .format(self.vm_name,
                                self.cores*self.sockets*self.threads*2))

    @classmethod
    def teardown_class(cls):
        '''
        Return cluster to original state and remove VM
        '''
        if not (clusters.updateCluster(positive=True,
                                       cluster=config.cluster_name,
                                       threads_as_cores=False)):
            raise errors.ClusterException("Cannot update cluster "
                                          " %s" % config.cluster_name)
        logger.info("Returned cluster %s to its original "
                    "state." % config.cluster_name)
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUPin_Case1(TestCase):
    """
    Check CPU pinning format correctness
    """
    __test__ = True
    vm_name = "cpupin_vm1"
    cores = 1
    sockets = 1

    @classmethod
    def setup_class(cls):
        '''
        Create a non migratable VM and count number of cores on host
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU Host VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1',
                            placement_affinity=PINNED,
                            placement_host=config.hosts[0]):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a non migratable VM.")
        logger.info("Setting cluster %s mode: 'count threads as cores' "
                    "off." % config.cluster_name)
        if not (clusters.updateCluster(positive=True,
                                       cluster=config.cluster_name,
                                       threads_as_cores=False)):
            raise errors.ClusterException("Cannot update cluster "
                                          " %s" % config.cluster_name)
        host_obj = HOST_API.find(config.hosts[0])
        if not host_obj:
            raise errors.HostException("Cannot find host %s"
                                       % config.hosts[0])
        cls.sockets = host_obj.cpu.topology.sockets
        logger.info("Number of sockets on host: %s" % cls.sockets)
        cls.cores = host_obj.cpu.topology.cores
        logger.info("Number of cores per socket on host: %s" % cls.cores)

    @istest
    def cpupin_format1(self):
        '''
        Set pinning to 0#0
        '''
        logger.info("Setting VCPU pinning to 0#0:")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning={'0': '0'}),
                        "Failed to change VCPU pinning")
        logger.info("Successfully changed VCPU pinning to 0#0.")

    @istest
    def cpupin_format2(self):
        '''
        Set pinning to 0#0-(number of cores-1)
        '''
        upper = self.sockets * self.cores - 1
        logger.info("Setting VCPU pinning to 0#0-{0}".format(upper))
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning={'0': '0-%s' % upper}),
                        "Failed to change VCPU pinning")
        logger.info("Successfully changed VCPU pinning to 0#1-{0}."
                    "".format(upper))

    @istest
    def cpupin_format3(self):
        '''
        Negative: Set pinning to 0#^1
        '''
        logger.info("Setting VCPU pinning to 0#^1")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     vcpu_pinning={'0': '^1'}),
                        "Successfully changed VCPU pinning")
        logger.info("Unable to change VCPU pinning to 0#^1.")

    @istest
    def cpupin_format4(self):
        '''
        Negative: Set pinning to 0#^1,^2
        '''
        logger.info("Setting VCPU pinning to 0#^1,^2")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     vcpu_pinning={'0': '^1,^2'}),
                        "Successfully changed VCPU pinning")
        logger.info("Unable to change VCPU pinning to 0#^1,^2.")

    @istest
    def cpupin_format5(self):
        '''
        Set pinning to 0#0-3,^1
        '''
        if (self.cores * self.sockets) < 4:
            raise errors.SkipTest("Too few CPU cores")
        logger.info("Setting VCPU pinning to 0#0-3,^1")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning={'0': '0-3,^1'}),
                        "Failed to change VCPU pinning")
        logger.info("Successfully changed VCPU pinning to 0#0-3,^1.")

    @istest
    def cpupin_format6(self):
        '''
        Set pinning to 0#0-3,^1,^2
        '''
        if (self.cores * self.sockets) < 4:
            raise errors.SkipTest("Too few CPU cores")
        logger.info("Setting VCPU pinning to 0#0-3,^1,^2")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning={'0': '0-3,^1,^2'}),
                        "Failed to change VCPU pinning")
        logger.info("Successfully changed VCPU pinning to 0#0-3,^1,^2.")

    @istest
    def cpupin_format7(self):
        '''
        Set pinning to 0#1,2,3
        '''
        if (self.cores * self.sockets) < 4:
            raise errors.SkipTest("Too few CPU cores")
        logger.info("Setting VCPU pinning to 0#1,2,3")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning={'0': '1,2,3'}),
                        "Failed to change VCPU pinning")
        logger.info("Successfully changed VCPU pinning to 0#1,2,3.")

    @istest
    def cpupin_format8(self):
        '''
        Set pinning to 0#0-3,5-7
        '''
        if (self.cores * self.sockets) < 8:
            raise errors.SkipTest("Too few CPU cores")
        logger.info("Setting VCPU pinning to 0#0-3,5-7")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning={'0': '0-3,5-7'}),
                        "Failed to change VCPU pinning")
        logger.info("Successfully changed VCPU pinning to 0#0-3,5-7.")

    @istest
    def cpupin_format9(self):
        '''
        Set pinning to 0#0-2,4-5,6-7
        '''
        if (self.cores * self.sockets) < 8:
            raise errors.SkipTest("Too few CPU cores")
        logger.info("Setting VCPU pinning to 0#0-2,4-5,6-7")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning={'0': '0-2,4-5,6-7'}),
                        "Failed to change VCPU pinning")
        logger.info("Successfully changed VCPU pinning to 0#0-2,4-5,6-7.")

    @istest
    def cpupin_format10(self):
        '''
        Set pinning to 0#0-3,^2,5-7
        '''
        if (self.cores * self.sockets) < 8:
            raise errors.SkipTest("Too few CPU cores")
        logger.info("Setting VCPU pinning to 0#0-3,^2,5-7")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning={'0': '0-3,^2,5-7'}),
                        "Failed to change VCPU pinning")
        logger.info("Successfully changed VCPU pinning to 0#0-3,^2,5-7.")

    @istest
    def cpupin_format11(self):
        '''
        Set pinning to 0#0-3,^2,5-7,^6
        '''
        if (self.cores * self.sockets) < 8:
            raise errors.SkipTest("Too few CPU cores")
        logger.info("Setting VCPU pinning to 0#0-3,^2,5-7,^6")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning={'0': '0-3,^2,5-7,^6'}),
                        "Failed to change VCPU pinning")
        logger.info("Successfully changed VCPU pinning to 0#0-3,^2,5-7,^6.")

    @istest
    def cpupin_format12(self):
        '''
        Negative: Set pinning to 0#0_0#1
        '''
        if (self.cores * self.sockets) < 2:
            raise errors.SkipTest("Too few CPU cores")
        logger.info("Setting VCPU pinning to 0#0_0#1")
        vmObj = VM_API.find(self.vm_name)
        vmObjNew = data_st.VM(name=self.vm_name)
        cpuTuneObj = data_st.CpuTune([data_st.VCpuPin(vcpu='0', cpu_set='0'),
                                      data_st.VCpuPin(vcpu='0', cpu_set='1')])
        vmObjNew.set_cpu(data_st.CPU(cpu_tune=cpuTuneObj))
        vmObjNew, status = VM_API.update(vmObj, vmObjNew, False)
        self.assertTrue(status, "Unable to change VCPU to 0#0_0#1")
        logger.info("Successfully changed VCPU pinning to 0#0_0#1.")

    @istest
    def cpupin_format13(self):
        '''
        Negative: Letter instead of pCPU
        '''
        logger.info("Setting VCPU pinning to 0#A")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     vcpu_pinning={'0': 'A'}),
                        "Successfully changed VCPU pinning")
        logger.info("Unable to change VCPU pinning to 0#A.")

    @istest
    def cpupin_format14(self):
        '''
        Negative: Letter instead of vCPU
        '''
        logger.info("Setting VCPU pinning to A#0")
        try:
            cpuTuneObj = data_st.CpuTune([data_st.VCpuPin(vcpu='A',
                                                          cpu_set='0')])
            self.assertTrue(False, "Successfully changed VCPU pinning"
                            "to A#0")
        except Exception:
            logger.info("Unable to change VCPU pinning to A#0.")

    @istest
    def cpupin_format15(self):
        '''
        Negative: Pinning to empty range
        '''
        logger.info("Setting VCPU pinning to 0#0-1,^0,^1")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     vcpu_pinning={'0': '0-1,^0,^1'}),
                        "Successfully changed VCPU pinning")
        logger.info("Unable to change VCPU pinning to 0#0-1,^0,^1.")

    @istest
    def cpupin_format16(self):
        '''
        Negative: Pinning to non-existing pCPU
        '''
        logger.info("Setting VCPU pinning to 0#4096")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     vcpu_pinning={'0': '4096'}),
                        "Successfully changed VCPU pinning")
        logger.info("Unable to change VCPU pinning to 0#4096.")

    @istest
    def cpupin_format17(self):
        '''
        Negative: Pinning to an empty string
        '''
        logger.info("Setting VCPU pinning to 0#")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     vcpu_pinning={'0': ''}),
                        "Successfully changed VCPU pinning")
        logger.info("Unable to change VCPU pinning to 0#.")

    @istest
    def cpupin_format18(self):
        '''
        Negative: Pinning non-existing vCPU
        '''
        logger.info("Setting VCPU pinning to 4096#0")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     vcpu_pinning={'4096': '0'}),
                        "Successfully changed VCPU pinning")
        logger.info("Unable to change VCPU pinning to 4096#0.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUPin_Case2(TestCase):
    """
    Negative: Set CPU pinning to a migratable VM
    """
    __test__ = True
    vm_name = "cpupin_vm2"

    @classmethod
    def setup_class(cls):
        '''
        Create a migratable VM
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU pin VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created VM.")

    @istest
    def set_migratable_cpupin(self):
        '''
        Attemp to set a migratable VM to use CPU pinning
        '''
        logger.info("Attemping to update VM to use CPU pinning.")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     vcpu_pinning={'0': '0'}))
        logger.info("Failed to change a migratable VM to use CPU pinning")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUPin_Case3(TestCase):
    """
    Negative: Change CPU pinned VM to migratable
    """
    __test__ = True
    vm_name = "cpupin_vm3"

    @classmethod
    def setup_class(cls):
        '''
        Create a non migratable VM with CPU pinning
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU pin VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1',
                            placement_affinity=PINNED,
                            placement_host=config.hosts[0],
                            vcpu_pinning={'0': '0'}):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a VM with cpu pinning.")

    @istest
    def set_pinned_cpupin_vm_migratable(self):
        '''
        Attemp to change a non migratable VM with CPU pinning
        to migratable.
        '''
        logger.info("Attemping to change VM to migratable.")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     placement_affinity=MIGRATABLE,
                                     placement_host=ANY_HOST))
        logger.info("Failed to change a CPU host VM's placement affinity "
                    "from pinned to migratable")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUPin_Case4(TestCase):
    """
    Negative: Set CPU pinning to a user migratable VM
    """
    __test__ = True
    vm_name = "cpupin_vm4"

    @classmethod
    def setup_class(cls):
        '''
        Create a user migratable VM
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU pin VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            placement_affinity=USER_MIGRATABLE,
                            size=DISK_SIZE, nic='nic1'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a user migratable VM.")

    @istest
    @bz("926962")
    def set_user_migratable_cpupin(self):
        '''
        Attemp to set a user migratable VM to use CPU pinning
        '''
        if (float(config.version)) < 3.3:
            raise errors.SkipTest("Not testing in < 3.3")
        logger.info("Attemping to update VM to use CPU pinning.")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     vcpu_pinning={'0': '0'}))
        logger.info("Failed to change a user migratable VM to"
                    " use CPU pinning")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUPin_Case5(TestCase):
    """
    Negative: Change CPU pinned VM to user migratable
    """
    __test__ = True
    vm_name = "cpupin_vm5"

    @classmethod
    def setup_class(cls):
        '''
        Create a non migratable VM with CPU pinning
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU pin VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1',
                            placement_affinity=PINNED,
                            placement_host=config.hosts[0],
                            vcpu_pinning={'0': '0'}):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a non migratable cpu pinned VM.")

    @istest
    @bz("926962")
    def set_pinned_cpupin_vm_user_migratable(self):
        '''
        Attemp to change a non migratable VM with CPU pinning
        to user migratable.
        '''
        if (float(config.version)) < 3.3:
            raise errors.SkipTest("Not testing in < 3.3")
        logger.info("Attemping to change VM to user migratable.")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     placement_affinity=USER_MIGRATABLE,
                                     placement_host=ANY_HOST))
        logger.info("Failed to change a CPU host VM's placement affinity "
                    "from pinned to user migratable")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUPin_Case6(TestCase):
    """
    Check if pinning holds on random pCPU's
    """
    __test__ = True
    vm_name = "cpupin_vm6"
    total_cores = 1

    @classmethod
    def setup_class(cls):
        '''
        Create a non migratable
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU pin VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1',
                            placement_affinity=PINNED,
                            placement_host=config.hosts[0],
                            vcpu_pinning={'0': '0'}):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a non migratable cpu pinned VM.")
        host_obj = HOST_API.find(config.hosts[0])
        if not host_obj:
            raise errors.HostException("Cannot find host %s"
                                       % config.hosts[0])
        sockets = host_obj.cpu.topology.sockets
        logger.info("Number of sockets on host: %s" % sockets)
        cores = host_obj.cpu.topology.cores
        logger.info("Number of cores per socket on host: %s" % cores)
        cls.total_cores = sockets * cores

    @istest
    def check_random_pinning(self):
        '''
        Set CPU pinning to random pCPU cores and check if pining holds.
        '''
        iterations = config.cpupin_iter if self.total_cores > 1 else 1
        for n in range(iterations):
            logger.info("Attempt %s:" % (n+1))
            expected_pin = str(random.randint(0, self.total_cores - 1))
            expected_affinity = '-' * int(expected_pin) + 'y' + \
                                '-'*(self.total_cores-int(expected_pin)-1)
            logger.info("Setting CPU pinning to 0#%s" % expected_pin)
            self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                         vcpu_pinning={'0': expected_pin}),
                            "Failed to update VM.")
            self.assertTrue(vms.startVm(positive=True, vm=self.vm_name),
                            "Failed to start VM.")
            res = getPinnedCPUInfo(config.hosts[0], "root",
                                   config.hosts_pw[0], self.vm_name, '0')
            self.assertTrue(res, "Failed to get VM CPU pinning stats.")
            self.assertTrue(vms.stopVm(positive=True, vm=self.vm_name),
                            "Failed to stop VM.")
            logger.info("vCPU #0 is expected to be pinned to vCPU #{0}, and "
                        "is actually pinned to vCPU #{1}."
                        "".format(expected_pin, res[0]))
            logger.info("vCPU #0 is expected to have pinning affinity of {0},"
                        " and actually has {1}."
                        "".format(expected_affinity,
                                  res[1][:self.total_cores]))
            self.assertTrue(expected_pin == res[0] and
                            expected_affinity == res[1][:self.total_cores],
                            "Actual CPU pinning does not match expectation.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUPin_Case7(TestCase):
    """
    Check if pinning holds when all vCPU's are running on the same pCPU
    """
    __test__ = True
    vm_name = "cpupin_vm7"
    total_cores = 1

    @classmethod
    def setup_class(cls):
        '''
        Create a non migratable VM
        '''
        host_obj = HOST_API.find(config.hosts[0])
        if not host_obj:
            raise errors.HostException("Cannot find host %s"
                                       % config.hosts[0])
        sockets = host_obj.cpu.topology.sockets
        logger.info("Number of sockets on host: %s" % sockets)
        cores = host_obj.cpu.topology.cores
        logger.info("Number of cores per socket on host: %s" % cores)
        cls.total_cores = sockets * cores
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU pin VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1',
                            cpu_socket=sockets, cpu_cores=cores,
                            placement_affinity=PINNED,
                            placement_host=config.hosts[0]):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created a non migratable VM.")

    @istest
    def check_pinning_load(self):
        '''
        Set CPU pinning to random pCPU cores and check if pining holds.
        '''
        if (self.total_cores) < 1:
            raise errors.SkipTest("Too few cores.")
        pinning = dict()
        for i in range(self.total_cores):
            pinning[str(i)] = '0'
        logger.info("Pinning all vCPU's to pCPU #0.")
        self.assertTrue(vms.updateVm(positive=True, vm=self.vm_name,
                                     vcpu_pinning=pinning),
                        "Failed to update VM.")
        self.assertTrue(vms.startVm(positive=True, vm=self.vm_name),
                        "Failed to start VM.")
        for i in range(self.total_cores):
            pin_info = getPinnedCPUInfo(host=config.hosts[0],
                                        host_user='root',
                                        host_pwd=config.hosts_pw[0],
                                        vm=self.vm_name,
                                        vcpu=i)
            self.assertTrue(pin_info[0],
                            "Could not retrieve VM pinning information.")
            self.assertTrue(pin_info[0] == '0',
                            "vCPU #{0} is not running on pCPU #0.".format(i))
        logger.info("All vCPU's are running on pCPU #0.")
        self.assertTrue(vms.stopVm(positive=True, vm=self.vm_name),
                        "Failed to stop VM.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################


class CPUPin_Case8(TestCase):
    """
    Negative: Set CPU pinning to a non migratable VM with no host
    specified to run on
    """
    __test__ = True
    vm_name = "cpupin_vm8"

    @classmethod
    def setup_class(cls):
        '''
        Create VM
        '''
        if not vms.createVm(positive=True, vmName=cls.vm_name,
                            vmDescription="CPU pin VM",
                            cluster=config.cluster_name,
                            storageDomainName=config.data_name[0],
                            size=DISK_SIZE, nic='nic1'):
            raise errors.VMException("Cannot create vm %s" % cls.vm_name)
        logger.info("Successfully created VM.")

    @istest
    @bz("928689")
    def set_pinned_cpupin_vm_a(self):
        '''
        Negative: Attemp to change VM to use CPU pinning, be non-migratable
        with no host specified to run on.
        '''
        logger.info("Attemping to change VM to user migratable.")
        self.assertTrue(vms.updateVm(positive=False, vm=self.vm_name,
                                     placement_affinity=PINNED,
                                     placement_host=ANY_HOST,
                                     vcpu_pinning={'0': '0'}))
        logger.info("Failed to change a VM to use CPU pinning, be non "
                    "migratable with no host specified to run on.")

    @classmethod
    def teardown_class(cls):
        '''
        Remove VM
        '''
        if not vms.removeVm(positive=True, vm=cls.vm_name):
            raise errors.VMException("Cannot remove vm %s" % cls.vm_name)
        logger.info("Successfully removed %s." % cls.vm_name)

########################################################################
