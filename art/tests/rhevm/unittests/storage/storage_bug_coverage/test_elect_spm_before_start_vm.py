"""
Test exposing BZ 969343

"""
import logging
from art.unittest_lib import BaseTestCase as TestCase
from concurrent.futures import ThreadPoolExecutor

from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils.name2ip import LookUpVMIpByName

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains

import config

LOGGER = logging.getLogger(__name__)
GB = 1024 * 1024 * 1024

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')
VDSM_RESPAWN_FILE = '/usr/share/vdsm/respawn'
LINUX = test_utils.LINUX


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE, basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME)


class TestCase281163(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=969343
    scenario:
        * stop vdsm on SPM and prevent it from restarting
        * wait until host status is changed to non-responsive
        * wait until VMs & storage domain statuses are unknown
        * shutdown all the VMs
        * reboot the old SPM host
        * wait for everything being up (host & VMs)

    https://tcms.engineering.redhat.com/case/289683/?from_plan=9583
    """
    __test__ = True
    tcms_plan_id = '9583'
    tcms_test_case = '289683'
    vm_name_base = "vm_%s" % tcms_test_case
    num_of_vms = 6
    vm_names = []
    vm_ips = []

    def _createVm(self, vm_name, sd, host):
        return vms.createVm(
            True, vm_name, vm_name, config.CLUSTER_NAME,
            storageDomainName=sd, size=config.DISK_SIZE,
            installation=True, diskType=config.DISK_TYPE_SYSTEM, memory=GB,
            cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO, highly_available=True,
            display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE, user=config.VM_LINUX_USER,
            password=config.VM_LINUX_PASSWORD, type=config.VM_TYPE_SERVER,
            slim=True, nic=config.HOST_NICS[0], volumeType=True,
            volumeFormat=ENUMS['format_cow'], useAgent=config.USE_AGENT,
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
            placement_host=host)

    def setUp(self):
        """
        create 6 VMs
        """
        self.original_perms = None
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']
        host = hosts.getSPMHost(config.HOSTS)

        LOGGER.info("Create VMs")
        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for i in range(self.num_of_vms):
                name = "%s_%s" % (self.vm_name_base, i)
                self.vm_names.append(name)
                results.append(
                    executor.submit(self._createVm, name, master_domain, host))

        for result in results:
            if not result.result():
                self.fail("Creation of at least one VM failed: %s" %
                          [x.result() for x in results])

        for name in self.vm_names:
            self.vm_ips.append(LookUpVMIpByName('ip', 'name').get_ip(name))

    def _shutdown_machine(self, ip):
        machine = test_utils.Machine(
            ip, config.VM_LINUX_USER, config.VM_LINUX_PASSWORD).util(LINUX)
        machine.shutdown()

    def test_elect_new_spm_after_failure(self):
        """
            * stop vdsm and prevent it from restarting
              (change perms to respawn file)
            * wait until host status is changed to non-responsive
            * wait until VMs status is unknown
            * wait until storage domain is unknown
            * shutdown all the VMs
            * change the perms of the respawn file and reboot the old SPM host
            * wait for everything being up (host & VMs)
        """
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']
        self.spm_host = hosts.getSPMHost(config.HOSTS)
        index = config.HOSTS.index(self.spm_host)
        self.spm_admin = config.ADMINS[index]
        self.spm_password = config.PASSWORDS[index]

        LOGGER.info("Stopping vdsm")
        test_utils.stopVdsmd(self.spm_host, self.spm_password)

        machine = test_utils.Machine(
            self.spm_host, self.spm_admin, self.spm_password).util(LINUX)

        rc, self.original_perms = machine.runCmd(
            ['stat', '-c', '%a', VDSM_RESPAWN_FILE])
        assert rc

        rc, out = machine.runCmd(['chmod', '111', VDSM_RESPAWN_FILE])
        LOGGER.info("output: %s" % out)
        assert rc

        LOGGER.info("Waiting for host being non responsive")
        hosts.waitForHostsStates(
            True, self.spm_host, ENUMS['search_host_state_non_responsive'],
            timeout=1800)

        LOGGER.info("Waiting for VM state unknown")
        assert vms.waitForVmsStates(
            True, ",".join(self.vm_names), ENUMS['vm_state_unknown'],
            timeout=900)

        LOGGER.info("Waiting for storage domain state")
        storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, master_domain,
            ENUMS['storage_domain_state_unknown'], timeOut=900)

        LOGGER.info("Shutting down the VMs")
        for ip in self.vm_ips:
            LOGGER.info("Shutting down %s" % ip)
            self._shutdown_machine(ip)

        rc, out = machine.runCmd(['chmod', '755', VDSM_RESPAWN_FILE])
        assert rc

        LOGGER.info("Rebooting the old SPM host")
        test_utils.rebootMachine(
            True, self.spm_host, self.spm_admin, self.spm_password, LINUX)

        LOGGER.info("Wait for hosts being up")
        assert hosts.waitForHostsStates(True, self.spm_host)

        LOGGER.info("Wait for SPM")
        assert hosts.waitForSPM(config.DATA_CENTER_NAME, 1200, 10)

        LOGGER.info("Wait from VMs being up")
        assert vms.waitForVmsStates(True, ",".join(self.vm_names))

        def tearDown(self):
            machine = test_utils.Machine(
                self.spm_host, self.spm_admin, self.spm_password).util(LINUX)
            if self.original_perms is not None:
                machine.runCmd(
                    ['chmod', self.original_perms, VDSM_RESPAWN_FILE])
