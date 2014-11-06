#!/usr/bin/python
# -*- coding: utf8 -*-
"""
All test-exposing bugs
"""
import config
import logging
import os
from art.rhevm_api.utils.log_listener import watch_logs
from art.unittest_lib.common import StorageTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils.test_utils import restartOvirtEngine
from utilities.utils import getIpAddressByHostName
from utilities.machine import Machine
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import datacenters as ll_dc
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import disks as ll_disks
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs

from art.test_handler.tools import tcms  # pylint: disable=E0611
import art.test_handler.exceptions as errors
from rhevmtests.storage.helpers import create_vm_or_clone

logger = logging.getLogger(__name__)

GB = config.GB
ENUMS = config.ENUMS

TIMEOUT_10_MINUTES = 600
SLEEP_TIME = 10

STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')
VDSM_RESPAWN_FILE = '/usr/share/vdsm/respawn'
LINUX = test_utils.LINUX

VDSM_LOG_FILE = "/var/log/vdsm/vdsm.log"
IO_ERROR_TIMEOUT = 10
IO_ERROR_READ_RETRIES = 10
IO_ERROR_IN_VDSM_LOG_REGEX = "new extend msg created"

# Install fake dd
CLI_CMD_MV_DD = 'mv /bin/dd /usr/bin/dd.real'
CLI_CMD_LN_DD = 'ln -sf /usr/bin/dd.fake /bin/dd'
CLI_CMD_TRIGGER_IO_ERR = 'touch /tmp/dd.error'

# UnInstall fake dd
CLI_CMD_DISABLE_IO_ERR = 'rm /tmp/dd.error'
CLI_CMD_UNLINK_DD = 'unlink /bin/dd'
CLI_CMD_MV_REAL_DD_BACK = 'mv -f /usr/bin/dd.real /bin/dd'
CLI_CMD_RM_FAKE_DD = 'rm -f /usr/bin/dd.fake'

FILE_REMOVE_FAILURE = 'No such file or directory'
CLI_CMD_GENERATE_BIG_FILE = 'dd if=/dev/urandom of=sample1.txt bs=64M count=32'
GENERATE_BIG_FILE_TIMEOUT = 60 * 5


def _create_vm(vm_name, vm_description="",
               disk_interface=config.INTERFACE_VIRTIO,
               sparse=True, volume_format=config.DISK_FORMAT_COW,
               vm_type=config.VM_TYPE_DESKTOP, storage_domain=None,
               installation=True, placement_host=None,
               highly_available=None):
    """ helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    logger.info("Creating VM %s", vm_name)
    return create_vm_or_clone(
        True, vm_name, vm_description, cluster=config.CLUSTER_NAME,
        nic=config.NIC_NAME[0], storageDomainName=storage_domain,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=GB, cpu_socket=config.CPU_SOCKET,
        cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
        user=config.VMS_LINUX_USER, password=config.VMS_LINUX_PW, type=vm_type,
        installation=installation, bootable=True, image=config.COBBLER_PROFILE,
        slim=True, highly_available=highly_available,
        network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT,
        placement_host=placement_host)


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config=config.PARAMETERS, storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(
            True,
            config.DATA_CENTER_NAME,
            vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )


class EnvironmentWithTwoHosts(TestCase):
    """Setup/teardown for an environment with 2 hosts as part of a cluster"""
    __test__ = False
    hosts = []
    num_active_hosts = 2

    @classmethod
    def setup_class(cls):
        """
        Make sure there are only two active hosts for the given cluster
        """
        wait_for_jobs()
        cls.hosts = []
        for host in config.HOSTS:
            if hosts.getHostCluster(host) == config.CLUSTER_NAME:
                if hosts.isHostUp(True, host):
                    if cls.num_active_hosts > 0:
                        cls.num_active_hosts -= 1
                    else:
                        hosts.deactivateHost(True, host)
            else:
                hosts.deactivateHost(True, host)

        hosts.waitForSPM(
            config.DATA_CENTER_NAME, TIMEOUT_10_MINUTES, SLEEP_TIME)
        logger.info("Getting SPM host")
        cls.spm_host = hosts.getSPMHost(config.HOSTS)

        logger.info("Getting HSM host")
        cls.hsm_host = hosts.getAnyNonSPMHost(
            config.HOSTS,
            expected_states=[config.HOST_UP],
            cluster_name=config.CLUSTER_NAME,
        )[1]['hsmHost']

        cls.hosts = [cls.spm_host, cls.hsm_host]

    @classmethod
    def teardown_class(cls):
        """Activate all the hosts"""
        for host in config.HOSTS:
            if not hosts.isHostUp(True, host):
                logger.info("Activating host %s", host)
                hosts.activateHost(True, host)


"""
TCMS Test Case 355191 355191, exposing BZ 1066834
Add a second bootable disks to a vm should fail
"""


@attr(tier=1)
class TestCase355191(TestCase):
    """
    Test case 355191 - Test that exposes BZ1066834

    https://tcms.engineering.redhat.com/case/355191/edit/?from_plan=2515
    """
    tcms_plan_id = '2515'
    tcms_test_case = '355191'
    expected_disk_number = 2
    vm_name = "vm_%s" % tcms_test_case
    bz_id = '1066834'
    __test__ = True

    def setUp(self):
        """
        Create a vm with a bootable disk
        """
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage,
        )[0]
        assert _create_vm(
            self.vm_name, storage_domain=self.storage_domain,
            installation=False,
        )

    @tcms(tcms_plan_id, tcms_test_case)
    def test_add_multiple_bootable_disks(self):
        """
        Verify adding a second bootable disk should fail
        """
        disks = ll_vms.getVmDisks(self.vm_name)
        assert len(disks) == 1
        assert disks[0].get_bootable()

        # Could add a non bootable disk
        logger.info("Adding a new non bootable disk works")
        self.second_disk = "second_disk_%s" % self.bz_id
        assert ll_vms.addDisk(
            True, self.vm_name, GB, wait=True,
            storagedomain=self.storage_domain, bootable=False,
            alias=self.second_disk)

        disks = ll_vms.getVmDisks(self.vm_name)
        assert len(disks) == self.expected_disk_number
        assert False in [disk.get_bootable() for disk in disks]

        logger.info("Adding a second bootable disk to vm %s should fail",
                    self.vm_name)
        self.bootable_disk = "bootable_disk_%s" % self.bz_id
        self.assertTrue(ll_vms.addDisk(False, self.vm_name, GB, wait=True,
                                       alias=self.bootable_disk,
                                       storagedomain=self.storage_domain,
                                       bootable=True),
                        "Shouldn't be possible to add a second bootable disk")

    def tearDown(self):
        """
        Remove created vm
        """
        # If it fails, the disk are still being added, wait for them
        disks_aliases = [disk.get_alias() for disk in ll_vms.getVmDisks(
            self.vm_name)]
        ll_disks.wait_for_disks_status(disks=disks_aliases)
        assert ll_vms.removeVm(True, self.vm_name)


"""
Test exposing BZ 1002249, checks that creating a template
from a vm with non-ascii character in its name is working
"""


@attr(tier=1)
class TestCase305452(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=1002249
    scenario:
    * create a VM with a non-ascii char in the disk's name
    * Create a template from the vm

    https://tcms.engineering.redhat.com/case/305452/?from_plan=6468
    """
    __test__ = True
    tcms_plan_id = '6468'
    tcms_test_case = '305452'

    def setUp(self):
        """Create the vm"""
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage,
        )[0]
        if not ll_vms.addVm(True, name=config.VM_BASE_NAME,
                            storagedomain=self.storage_domain,
                            cluster=config.CLUSTER_NAME):
            raise errors.VMException("Cannot create vm %s" %
                                     config.VM_BASE_NAME)

        # Add a disk to the VM
        if not ll_vms.addDisk(True, config.VM_BASE_NAME, config.DISK_SIZE,
                              storagedomain=self.storage_domain):
            raise errors.DiskException("Cannot create disk for vm %s" %
                                       config.VM_BASE_NAME)

    def tearDown(self):
        """Remove template and vm"""
        if self.template_created:
            if not templates.removeTemplate(positive=True,
                                            template=self.template_name):
                logger.error("Failure to remove template %s",
                             self.template_name)

        if not ll_vms.removeVm(
                True, config.VM_BASE_NAME, **{'stopVM': 'true'}):
            logger.error("Cannot delete vm %s", config.VM_BASE_NAME)

        wait_for_jobs()

    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_template_from_vm(self):
        """ creates template from vm
        """
        self.template_created = False
        logger.info("Adding a non-ascii character to the disk name")
        disk_name = u"DiskNonAsciié"
        disk_params = {"disk": "%s_Disk1" % config.VM_BASE_NAME,
                       "alias": disk_name}
        self.assertTrue(ll_vms.updateVmDisk(True, config.VM_BASE_NAME,
                                            **disk_params))

        self.template_name = '%s_%s_template_' % (
            config.VM_BASE_NAME, self.storage)
        template_kwargs = {"vm": config.VM_BASE_NAME,
                           "name": self.template_name}
        logger.info("Creating template %s", self.template_name)
        self.template_created = templates.createTemplate(True,
                                                         **template_kwargs)
        self.assertTrue(
            self.template_created,
            "Couldn't create template %s" % self.template_name,
        )


"""
Test elect spm before start vm
Test exposing BZ 969343
"""


@attr(tier=1)
class TestCase289683(EnvironmentWithTwoHosts):
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
    # TODO: Due to BZ1210771 this test case couldn't be fully verified (as in
    # is sure to PASS after the bz is fixed), so marking it as False until it
    # can be fully verified.
    __test__ = False
    tcms_plan_id = '9583'
    tcms_test_case = '289683'
    vm_name_base = "vm_%s" % tcms_test_case
    num_of_vms = 6
    vm_names = []
    vm_ips = []
    bz = {'1210771': {'engine': None, 'version': ["3.5", "3.6"]}}

    def setUp(self):
        """
        create 6 VMs
        """
        self.machine_rebooted = None
        self.vm_names = []
        self.vm_ips = []
        self.original_perms = None
        self.sd = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]
        self.spm_host = hosts.getSPMHost(config.HOSTS)
        self.spm_host_ip = hosts.getHostIP(self.spm_host)
        self.spm_admin = config.HOSTS_USER
        self.spm_password = config.HOSTS_PW

        args = {
            "highly_available": True,
            "placement_host": self.spm_host,
            "storage_domain": self.sd,
        }

        logger.info("Create VMs")
        for i in range(self.num_of_vms):
            name = "%s_%s" % (self.vm_name_base, i)
            self.vm_names.append(name)
            args["vm_name"] = name
            if not _create_vm(**args):
                logger.error("Error creating vm %s", name)

        for name in self.vm_names:
            self.vm_ips.append(ll_vms.waitForIP(name, timeout=30)[1]['ip'])

    def _shutdown_machine(self, ip):
        machine = test_utils.Machine(ip, config.VMS_LINUX_USER,
                                     config.VMS_LINUX_PW).util(LINUX)
        machine.shutdown()

    @tcms(tcms_plan_id, tcms_test_case)
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
        assert ll_vms.waitForVmsStates(True, ",".join(self.vm_names))

        logger.info("Stopping vdsm")
        test_utils.stopVdsmd(self.spm_host_ip, self.spm_password)

        machine = test_utils.Machine(
            self.spm_host_ip, self.spm_admin, self.spm_password).util(LINUX)

        self.machine_rebooted = False
        rc, out = machine.runCmd(['chmod', '111', VDSM_RESPAWN_FILE])
        logger.info("output: %s" % out)
        assert rc

        logger.info("Waiting for host being non responsive")
        hosts.waitForHostsStates(
            True, self.spm_host, ENUMS['search_host_state_non_responsive'],
            timeout=TIMEOUT_10_MINUTES,
        )

        logger.info("Waiting for VM state unknown")
        assert ll_vms.waitForVmsStates(
            True, ",".join(self.vm_names), ENUMS['vm_state_unknown'],
            timeout=300,
        )

        logger.info("Waiting for storage domain state")
        storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.sd,
            ENUMS['storage_domain_state_unknown'], timeOut=900,
        )

        logger.info("Shutting down the VMs")
        for ip in self.vm_ips:
            logger.info("Shutting down %s", ip)
            self._shutdown_machine(ip)

        rc, out = machine.runCmd(['chmod', '755', VDSM_RESPAWN_FILE])
        assert rc

        logger.info("Rebooting the old SPM host")
        self.machine_rebooted = test_utils.rebootMachine(
            True, self.spm_host_ip, self.spm_admin, self.spm_password, LINUX)

        logger.info("Wait for hosts being up")
        assert hosts.waitForHostsStates(True, [self.spm_host])

        logger.info("Wait for SPM")
        assert hosts.waitForSPM(
            config.DATA_CENTER_NAME, 2 * TIMEOUT_10_MINUTES, SLEEP_TIME,
        )

        logger.info("Wait from VMs being up")
        assert ll_vms.waitForVmsStates(True, ",".join(self.vm_names))

    def tearDown(self):
        """Make sure host and datacenter are up and remove vms"""
        if not self.machine_rebooted:
            # Make sure that if something went wrong duing the test, the
            # permissions are correct and the machine is rebooted
            machine = test_utils.Machine(
                self.spm_host_ip, self.spm_admin,
                self.spm_password).util(LINUX)
            rc, out = machine.runCmd(['chmod', '755', VDSM_RESPAWN_FILE])
            result = 'succeed' if rc else 'failed'
            logger.info("Putting permissions back %s: %s", result, out)
            test_utils.rebootMachine(
                True, self.spm_host_ip, self.spm_admin, self.spm_password,
                LINUX,
            )

            logger.info("Wait for the host to come up")
            if not hosts.waitForHostsStates(True, [self.spm_host]):
                logger.error("Host %s didn't came back up", self.spm_host)

        logger.info("Make sure the Data Center is up before cleaning up")
        if not hosts.waitForSPM(config.DATA_CENTER_NAME, TIMEOUT_10_MINUTES,
                                SLEEP_TIME):
            logger.error("Datacenter %s didn't came back up",
                         config.DATA_CENTER_NAME)

        ll_vms.stop_vms_safely(self.vm_names)
        ll_vms.removeVms(True, self.vm_names)


"""
Test image lock free after engine restart
"""


@attr(tier=3)
class TestCase320223(TestCase):
    """
    bug coverage test, restart engine during template creation
    https://tcms.engineering.redhat.com/case/320223/
    """
    __test__ = True
    tcms_plan_id = '5392'
    tcms_test_case = '320223'

    vm_name = "base_vm"
    vm_desc = "VM for creating template"
    template_name = "template_from_%s" % vm_name
    vm_from_template = "vm_from_template"

    def setUp(self):
        """Create vm for test"""
        self.test_failed = False
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage,
        )[0]
        if not _create_vm(self.vm_name, self.vm_desc, config.INTERFACE_VIRTIO,
                          storage_domain=self.storage_domain):
            raise errors.VMException("Failed to create vm %s" % self.vm_name)
        logger.info("Successfully created VM.")

        if not ll_vms.shutdownVm(True, self.vm_name, async="false"):
            raise errors.VMException("Cannot shutdown vm %s" % self.vm_name)
        logger.info("Successfully shutdown VM.")

    def _create_template(self):
        logger.info("Creating new template")
        self.assertTrue(templates.createTemplate(positive=True,
                                                 vm=self.vm_name,
                                                 name=self.template_name,
                                                 wait=False),
                        "Failed to create template from vm %s" % self.vm_name)
        logger.info("Successfully created template")

    @tcms(tcms_plan_id, tcms_test_case)
    def test_restart_engine_while_image_lock(self):
        """ test checks if restarting the engine while creating a new template
            (image lock) works properly
        """
        logger.info("Start creating the template")
        self._create_template()

        # Wait until VM becomes lock
        self.assertTrue(
            ll_vms.waitForVMState(
                self.vm_name,
                state=config.VM_LOCK_STATE),
            "image status won't change to lock")

        engine = config.VDC
        engine_ip = getIpAddressByHostName(engine)
        engine_object = Machine(host=engine_ip, user=config.VMS_LINUX_USER,
                                password=config.VMS_LINUX_PW).util('linux')

        self.assertTrue(restartOvirtEngine(engine_object, 5, 30, 75),
                        "Failed restarting ovirt-engine")
        logger.info("Successfully restarted ovirt-engine")

        # Wait until VM is down
        self.assertTrue(
            ll_vms.waitForVMState(self.vm_name, state=config.VM_DOWN_STATE),
            "image status won't change to down")

        logger.info("starting vm %s", self.vm_name)
        self.assertTrue(ll_vms.startVm(True, self.vm_name),
                        "Failed to start vm %s" % self.vm_name)
        logger.info("Successfully started VM %s", self.vm_name)

        logger.info("wait for template %s - state to be 'ok'",
                    self.template_name)

        self.assertTrue(templates.waitForTemplatesStates(self.template_name),
                        "template %s state is not ok" % self.template_name)
        logger.info("template %s - state is 'ok'",
                    self.template_name)

        logger.info("adding new vm %s from template %s",
                    self.vm_from_template, self.template_name)
        self.assertTrue(
            ll_vms.addVm(
                positive=True,
                name=self.vm_from_template,
                vmDescription="Server - copy",
                cluster=config.CLUSTER_NAME,
                template=self.template_name),
            "Failed to create vm from template %s" %
            self.template_name)
        logger.info("Successfully created VM from template")

        logger.info("starting vm %s", self.vm_from_template)
        self.assertTrue(ll_vms.startVm(True, self.vm_from_template),
                        "Can't start vm %s" % self.vm_from_template)
        logger.info("Successfully started VM %s", self.vm_from_template)

    def tearDown(self):
        """
        Remove vms and template
        """
        for vm in [self.vm_name, self.vm_from_template]:
            logger.info("Removing vm %s", vm)
            if not ll_vms.removeVm(positive=True, vm=vm, stopVM='true'):
                logger.error("Cannot remove vm %s", vm)
                self.test_failed = True

        logger.info("Removing template %s", self.template_name)
        if not templates.removeTemplate(positive=True,
                                        template=self.template_name):
            logger.error("Failed to remove template %s", self.template_name)
            self.test_failed = True
        if self.test_failed:
            raise errors.TestException("Test failed during tearDown")


"""
Test exposing BZ 986961
Maintenance spm with a running vm
"""


@attr(tier=0)
class TestCase315489(EnvironmentWithTwoHosts):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=986961
    scenario:
        * on 2 host cluster with connected pool and running VM on SPM
        * maintenance SPM

    https://tcms.engineering.redhat.com/case/315489/?from_plan=2337
    """
    __test__ = True
    tcms_plan_id = '2337'
    tcms_test_case = '315489'
    vm_name_base = "vm_%s" % tcms_test_case

    def setUp(self):
        """
        create a VM on SPM
        """
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage)[0]

        logger.info("Create VM")
        assert _create_vm(self.vm_name_base,
                          storage_domain=self.storage_domain,
                          placement_host=self.spm_host,
                          highly_available=True)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_maintenance_spm_with_running_vm(self):
        """
            * maintenance SPM
        """
        logger.info("Deactivating SPM host %s", self.spm_host)
        hosts.deactivateHost(True, self.spm_host)
        hosts.waitForHostsStates(True, self.spm_host, config.HOST_MAINTENANCE)

        logger.info("Waiting DC state to be up with the new spm")
        ll_dc.wait_for_datacenter_state_api(config.DATA_CENTER_NAME)

        assert hosts.waitForSPM(
            config.DATA_CENTER_NAME, TIMEOUT_10_MINUTES, SLEEP_TIME,
        )
        new_spm = hosts.getSPMHost(self.hosts)
        logger.info("New SPM is: %s", new_spm)

    def tearDown(self):
        """Delete the vm"""
        assert ll_vms.removeVm(True, self.vm_name_base, **{'stopVM': 'true'})


"""
Test exposing BZ 960430

TCMS plan: https://tcms.engineering.redhat.com/plan/9583
"""


@attr(tier=1)
class TestCase284324(TestCase):
    """ Test exposing https://bugzilla.redhat.com/show_bug.cgi?id=960430
    Tries to create a disk via REST API without specifying 'sparse' tag.

    https://tcms.engineering.redhat.com/case/284324/?from_plan=9583
    """
    __test__ = True
    tcms_plan_id = '9583'
    tcms_test_case = '284324'

    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_raw_disk_without_sparse_tag_test(self):
        """
        Tries to create a raw disk via REST API without specifying 'sparse'
        flag. Such call should fail.
        """
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage,
        )[0]
        self.disk_name = "disk_%s" % self.tcms_test_case

        assert ll_disks.addDisk(
            False, alias=self.disk_name, shareable=False, bootable=False,
            size=1 * GB, storagedomain=self.storage_domain, sparse=None,
            format=ENUMS['format_raw'], interface=ENUMS['interface_ide'])

    def tearDown(self):
        """Remove the disk in case the test fails (since disk is created)"""
        if ll_disks.checkDiskExists(True, self.disk_name):
            ll_disks.waitForDisksState([self.disk_name])
            assert ll_disks.deleteDisk(True, self.disk_name)


"""
Test exposing BZ 962549

TCMS plan: https://tcms.engineering.redhat.com/plan/9583
"""


@attr(tier=1)
class TestCase280628(TestCase):
    """ Test exposing https://bugzilla.redhat.com/show_bug.cgi?id=962549

    Test scenario:
    * create a VM with RHEL, run it on SPM
    * create a snapshot
    * run the VM on an HSM
    * stop the VM
    * remove the snapshot
    * run the VM again on the same HSM
    """
    __test__ = True
    tcms_plan_id = '9583'
    tcms_test_case = '280628'
    vm_name = "vm_%s" % tcms_test_case
    snap_name = "snap_%s" % tcms_test_case

    @tcms(tcms_plan_id, tcms_test_case)
    def test_merge_snapshots_on_hsm(self):
        """
        checks that a VM with a snapshot, which where created when the VM was
        run on SPM and removed when the VM was moved to an HSM, can be booted
        """
        logger.info("Create VM")
        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage,
        )[0]
        spm_host = hosts.getSPMHost(config.HOSTS)
        if hosts.getHostCluster(spm_host) != config.CLUSTER_NAME:
            _, host_dict = hosts.getAnyNonSPMHost(
                config.HOSTS, cluster_name=config.CLUSTER_NAME,
            )
            host = host_dict['hsmHost']
            assert hosts.select_host_as_spm(True, host,
                                            config.DATA_CENTER_NAME)
            spm_host = host

        assert hosts.waitForSPM(
            config.DATA_CENTER_NAME, TIMEOUT_10_MINUTES, SLEEP_TIME,
        )

        assert _create_vm(self.vm_name,
                          storage_domain=self.storage_domain,
                          placement_host=spm_host)
        logger.info("Stopping VM")
        assert ll_vms.stopVm(True, self.vm_name)
        logger.info("Adding snapshot")
        assert ll_vms.addSnapshot(True, self.vm_name, self.snap_name)
        hsm_host = hosts.getAnyNonSPMHost(
            config.HOSTS, cluster_name=config.CLUSTER_NAME,
        )[1]['hsmHost']
        assert hsm_host
        assert ll_vms.updateVm(True, self.vm_name, placement_host=hsm_host)
        logger.info("Starting VM on HSM")
        assert ll_vms.startVm(True, self.vm_name, wait_for_ip=True)
        logger.info("Stopping VM")
        assert ll_vms.stopVm(True, self.vm_name)
        logger.info("Removing snapshot")
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snap_name, timeout=30 * 60)
        logger.info("Starting again")
        assert ll_vms.startVm(True, self.vm_name, wait_for_ip=True)

    def tearDown(self):
        """
        Remove the vm
        """
        if not ll_vms.safely_remove_vms([self.vm_name]):
            raise errors.VMException("Failed to remove vm %s" % self.vm_name)


@attr(tier=3)
class TestCase398664(TestCase):
    """
    Test exposing https://bugzilla.redhat.com/show_bug.cgi?id=1119664
    """
    __test__ = True
    tcms_plan_id = '9583'
    tcms_test_case = '398664'
    vm_name = "vm_%s" % tcms_test_case
    snap_name = "snap_%s" % tcms_test_case

    def setUp(self):
        # on the spm host - trigger "read error" by manipulating dd behaviour
        self.test_failed = False
        self.spm_host_name = hosts.getSPMHost(config.HOSTS)
        self.spm_host_ip = hosts.getHostIP(self.spm_host_name)
        connection = Machine(host=self.spm_host_ip, user=config.HOSTS_USER,
                             password=config.HOSTS_PW).util('linux')

        self.storage_domain = storagedomains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage,
        )[0]
        # put all other hosts in maintenance
        for host in config.HOSTS:
            if host != self.spm_host_name and hosts.isHostUp(True, host):
                hosts.deactivateHost(True, host)
        wait_for_jobs()

        # create a vm with 1 thin provision disk
        logger.info("Create a vm named %s ", self.vm_name)
        if not _create_vm(self.vm_name, storage_domain=self.storage_domain):
            raise errors.VMException(
                "Creation of VM %s failed!" % self.vm_name)

        logger.info("Waiting for vm %s state 'up'", self.vm_name)
        if not ll_vms.waitForVMState(self.vm_name):
            raise errors.VMException("Waiting for VM %s status 'up' failed"
                                     % self.vm_name)

        # Installation :
        # cp dd.fake /usr/bin/dd.fake
        assert connection.copyTo(os.path.join(os.path.dirname(__file__),
                                              'dd.fake'), '/usr/bin/')

        # mv /bin/dd /usr/bin/dd.real
        # ln -sf /usr/bin/dd.fake /bin/dd
        # touch /tmp/dd.error
        hosts.run_command(self.spm_host_name, config.HOSTS_USER,
                          config.HOSTS_PW, CLI_CMD_MV_DD)
        hosts.run_command(self.spm_host_name, config.HOSTS_USER,
                          config.HOSTS_PW, CLI_CMD_LN_DD)
        hosts.run_command(self.spm_host_name, config.HOSTS_USER,
                          config.HOSTS_PW, CLI_CMD_TRIGGER_IO_ERR)

    def tearDown(self):
        # Uninstalling:
        # rm -f /tmp/dd.error
        # unlink /bin/dd
        # mv -f /usr/bin/dd.real /bin/dd
        # rm -f /usr/bin/dd.fake
        try:
            output = hosts.run_command(self.spm_host_name, config.HOSTS_USER,
                                       config.HOSTS_PW, CLI_CMD_DISABLE_IO_ERR)
            if FILE_REMOVE_FAILURE not in output:
                hosts.run_command(self.spm_host_name, config.HOSTS_USER,
                                  config.HOSTS_PW, CLI_CMD_UNLINK_DD)
                hosts.run_command(self.spm_host_name, config.HOSTS_USER,
                                  config.HOSTS_PW, CLI_CMD_MV_REAL_DD_BACK)
                hosts.run_command(self.spm_host_name, config.HOSTS_USER,
                                  config.HOSTS_PW, CLI_CMD_RM_FAKE_DD)

        except RuntimeError, e:
            logger.error(e)
            self.test_failed = True

        logger.info("Restarting vdsmd")
        test_utils.restartVdsmd(self.spm_host_ip, config.HOSTS_PW)
        if not hosts.waitForHostsStates(
            True, [self.spm_host_name], ENUMS['host_state_connecting'],
        ):
            logger.error("Host %s didn't change to status 'connecting'",
                         self.spm_host_name)
            self.test_failed = True

        logger.info("Waiting for host %s to be back up", self.spm_host_name)
        if not hosts.waitForHostsStates(True, [self.spm_host_name]):
            logger.error("Waiting for Host %s status 'up' failed",
                         self.spm_host_name)
            self.test_failed = True

        if not hosts.waitForSPM(config.DATA_CENTER_NAME, TIMEOUT_10_MINUTES,
                                SLEEP_TIME):
            logger.error("Waiting for SPM host status 'up' failed")
            self.test_failed = True

        logger.info("Shutting down %s", self.vm_name)
        if not ll_vms.stopVm(True, self.vm_name):
            logger.error("shutting down %s failed", self.vm_name)
            self.test_failed = True

        logger.info("Waiting for vm %s state 'down'", self.vm_name)
        if not ll_vms.waitForVMState(self.vm_name, state=config.VM_DOWN):
            logger.error(
                "Waiting for VM %s status 'down' failed", self.vm_name)
            self.test_failed = True

        logger.info("removing vm's %s state 'down'", self.vm_name)
        if not ll_vms.removeVm(True, self.vm_name):
            logger.error(
                "Waiting for VM %s status 'down' failed", self.vm_name)
            self.test_failed = True

        if self.test_failed:
            raise errors.TestException("Test failed during tearDown")

    @classmethod
    def teardown_class(cls):
        """Make sure that the hosts are activated even if tearDown fails"""
        logger.info("Activating hosts back again")
        for host in config.HOSTS:
            if not hosts.isHostUp(True, host):
                hosts.activateHost(True, host, True)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_io_error(self):
        """
        Simulate IO Read Error while expand request
        Covers https://bugzilla.redhat.com/show_bug.cgi?id=1119664
        # Setup :
        # create a vm with 1 thin provision disk
        # on the host - trigger "read error" by manipulating dd beheviure
        #Test steps :
        # on the vm , run a dd command to make the the HD expend.
        # parse /var/log/vdsm.log for making sure that an expand request
        # starts and fails.
        """

        logger.info("Running dd of some 2G, to trigger extend request, "
                    "this may take few minutes .")

        # on the vm , run a dd command to make the the HD expend.
        # dd if=/dev/urandom of=sample1.txt bs=64M count=32
        rc, out = ll_vms.run_cmd_on_vm(self.vm_name, CLI_CMD_GENERATE_BIG_FILE,
                                       config.VMS_LINUX_USER,
                                       config.VMS_LINUX_PW,
                                       GENERATE_BIG_FILE_TIMEOUT)
        logger.info("\n Generating a big file on vm, the output is %s \n", out)

        # parse /var/log/vdsm.log for making sure that an expand request
        for i in range(1, IO_ERROR_READ_RETRIES):
            regex_flag, rc = watch_logs(VDSM_LOG_FILE,
                                        IO_ERROR_IN_VDSM_LOG_REGEX,
                                        '', IO_ERROR_TIMEOUT,
                                        self.spm_host_ip,
                                        config.HOSTS_USER,
                                        config.HOSTS_PW)
        self.assertTrue(regex_flag,
                        "Couldn't find expend request for %s sec" %
                        IO_ERROR_TIMEOUT)
