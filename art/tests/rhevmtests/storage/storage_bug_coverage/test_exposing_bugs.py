#!/usr/bin/python
# -*- coding: utf8 -*-
"""
All test-exposing bugs
"""
import logging
from art.unittest_lib.common import StorageTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.utils import test_utils
from concurrent.futures import ThreadPoolExecutor
from art.rhevm_api.utils.name2ip import LookUpVMIpByName
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

from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
import art.test_handler.exceptions as errors

import config

logger = logging.getLogger(__name__)

GB = config.GB
ENUMS = config.ENUMS

BZID = "1066834"
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')
VDSM_RESPAWN_FILE = '/usr/share/vdsm/respawn'
LINUX = test_utils.LINUX


"""
TCMS Test Case 355191 355191, exposing BZ 1066834
Add a second bootable disks to a vm should fail
"""


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME,
                                   vdc=config.VDC,
                                   vdc_password=config.VDC_PASSWORD)


@attr(tier=2)
class TestCase355191(TestCase):
    """
    Test case 355191 - Test that exposes BZ1066834

    https://tcms.engineering.redhat.com/case/355191/edit/?from_plan=2515
    """
    tcms_plan_id = '2515'
    tcms_test_case = '355191'
    expected_disk_number = 2
    __test__ = True

    def _create_vm(
            self, vm_name, disk_interface, sparse=True,
            volume_format=ENUMS['format_cow'],
            vm_type=config.VM_TYPE_DESKTOP):
        """
        helper function for creating vm (passes common arguments, mostly taken
        from the configuration file)
        """
        storage_domain = storagedomains.getDCStorages(
            config.DATA_CENTER_NAME, False)[0].get_name()
        logger.info("Creating VM %s at SD %s", vm_name, storage_domain)
        return ll_vms.createVm(
            True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
            nic=config.HOST_NICS[0], storageDomainName=storage_domain,
            size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
            volumeType=sparse, volumeFormat=volume_format,
            diskInterface=disk_interface, memory=GB,
            cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW, type=vm_type,
            installation=False,
            slim=True, network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT,
            bootable=True)

    def setUp(self):
        """
        Create a vm with a bootable disk
        """
        assert self._create_vm(
            config.VM_NAME[0],
            ENUMS['interface_virtio_scsi']
        )
        self.storage_domain = storagedomains.getDCStorages(
            config.DATA_CENTER_NAME, False)[0].get_name()

    @bz(BZID)
    @tcms(tcms_plan_id, tcms_test_case)
    def test_add_multiple_bootable_disks(self):
        """
        Verify adding a second bootable disk should fail
        """
        disks = ll_vms.getVmDisks(config.VM_NAME[0])
        assert len(disks) == 1
        assert disks[0].get_bootable()

        # Could add a non bootable disk
        logger.info("Adding a new non bootable disk works")
        self.second_disk = "second_disk_%s" % BZID
        assert ll_vms.addDisk(
            True, config.VM_NAME[0], GB, wait=True,
            storagedomain=self.storage_domain, bootable=False,
            alias=self.second_disk)

        disks = ll_vms.getVmDisks(config.VM_NAME[0])
        assert len(disks) == self.expected_disk_number
        assert False in [disk.get_bootable() for disk in disks]

        logger.info("Adding a second bootable disk to vm %s should fail",
                    config.VM_NAME[0])
        self.bootable_disk = "bootable_disk_%s" % BZID
        self.assertTrue(ll_vms.addDisk(
            False, config.VM_NAME[0], GB, wait=True, alias=self.bootable_disk,
            storagedomain=self.storage_domain, bootable=True),
            "Shouldn't be possible to add a second bootable disk")

    def tearDown(self):
        """
        Remove created vm
        """
        # If it fails, the disk are still being added, wait for them
        disks_aliases = [disk.get_alias() for disk in ll_vms.getVmDisks(
            config.VM_NAME[0])]
        ll_disks.waitForDisksState(disksNames=disks_aliases)
        assert ll_vms.removeVm(True, config.VM_NAME[0])


"""
Test exposing BZ 1002249, checks that creating a template
from a vm with non-ascii character in its name is working
"""


@attr(tier=2)
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

    @classmethod
    def setUp(self):
        # Add a VM
        if not ll_vms.addVm(True, name=config.VM_BASE_NAME,
                            storagedomain=config.DOMAIN_NAME_1,
                            cluster=config.CLUSTER_NAME):
            raise errors.VMException("Cannot create vm %s" %
                                     config.VM_BASE_NAME)

        # Add a disk to the VM
        if not ll_vms.addDisk(True, config.VM_BASE_NAME, config.DISK_SIZE,
                              storagedomain=config.DOMAIN_NAME_1):
            raise errors.DiskException("Cannot create disk for vm %s" %
                                       config .VM_BASE_NAME)

    @classmethod
    def tearDown(self):
        # Remove the vm
        if not ll_vms.removeVm(
                True, config.VM_BASE_NAME, **{'stopVM': 'true'}):
            raise errors.VMException("Cannot delete vm %s" %
                                     config.VM_BASE_NAME)

    @bz(1002249)
    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_template_from_vm(self):
        """ creates template from vm
        """
        logger.info("Adding a non-ascii character to the disk name")
        disk_name = u"DiskNonAsciié"
        disk_params = {"disk": "%s_Disk1" % config.VM_BASE_NAME,
                       "alias": disk_name}
        self.assertTrue(ll_vms.updateVmDisk(True, config.VM_BASE_NAME,
                                            **disk_params))

        template_name = '%s_%s_template_' % (
            config.VM_BASE_NAME, config.STORAGE_TYPE)
        template_kwargs = {"vm": config.VM_BASE_NAME,
                           "name": template_name}
        logger.info("Creating template")
        self.assertTrue(templates.createTemplate(True, **template_kwargs))

    @classmethod
    def teardown_class(cls):
        """
        Wait for un-finished tasks
        """
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DATA_CENTER_NAME)

"""
Test elect spm before start vm
Test exposing BZ 969343
"""


@attr(tier=1)
class TestCase289683(TestCase):
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
        return ll_vms.createVm(
            True, vm_name, vm_name, config.CLUSTER_NAME,
            storageDomainName=sd, size=config.DISK_SIZE,
            installation=True, diskType=config.DISK_TYPE_SYSTEM, memory=GB,
            cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO, highly_available=True,
            display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW, type=config.VM_TYPE_SERVER,
            slim=True, nic=config.HOST_NICS[0], volumeType=True,
            volumeFormat=ENUMS['format_cow'], useAgent=config.USE_AGENT,
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
            placement_host=host)

    def setUp(self):
        """
        create 6 VMs
        """
        self.vm_names = []
        self.vm_ips = []
        self.original_perms = None
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']
        host = hosts.getSPMHost(config.HOSTS)

        logger.info("Create VMs")
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
            ip, config.VMS_LINUX_USER, config.VMS_LINUX_PW).util(LINUX)
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
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']
        self.spm_host = hosts.getSPMHost(config.HOSTS)
        self.spm_admin = config.HOSTS_USER
        self.spm_password = config.HOSTS_PW

        logger.info("Stopping vdsm")
        test_utils.stopVdsmd(self.spm_host, self.spm_password)

        machine = test_utils.Machine(
            self.spm_host, self.spm_admin, self.spm_password).util(LINUX)

        rc, self.original_perms = machine.runCmd(
            ['stat', '-c', '%a', VDSM_RESPAWN_FILE])
        assert rc

        rc, out = machine.runCmd(['chmod', '111', VDSM_RESPAWN_FILE])
        logger.info("output: %s" % out)
        assert rc

        logger.info("Waiting for host being non responsive")
        hosts.waitForHostsStates(
            True, self.spm_host, ENUMS['search_host_state_non_responsive'],
            timeout=1800)

        logger.info("Waiting for VM state unknown")
        assert ll_vms.waitForVmsStates(
            True, ",".join(self.vm_names), ENUMS['vm_state_unknown'],
            timeout=900)

        logger.info("Waiting for storage domain state")
        storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, master_domain,
            ENUMS['storage_domain_state_unknown'], timeOut=900)

        logger.info("Shutting down the VMs")
        for ip in self.vm_ips:
            logger.info("Shutting down %s" % ip)
            self._shutdown_machine(ip)

        rc, out = machine.runCmd(['chmod', '755', VDSM_RESPAWN_FILE])
        assert rc

        logger.info("Rebooting the old SPM host")
        test_utils.rebootMachine(
            True, self.spm_host, self.spm_admin, self.spm_password, LINUX)

        logger.info("Wait for hosts being up")
        assert hosts.waitForHostsStates(True, self.spm_host)

        logger.info("Wait for SPM")
        assert hosts.waitForSPM(config.DATA_CENTER_NAME, 1200, 10)

        logger.info("Wait from VMs being up")
        assert ll_vms.waitForVmsStates(True, ",".join(self.vm_names))

    def tearDown(self):
        machine = test_utils.Machine(
            self.spm_host, self.spm_admin, self.spm_password).util(LINUX)
        if self.original_perms is not None:
            machine.runCmd(
                ['chmod', self.original_perms, VDSM_RESPAWN_FILE])
        ll_vms.removeVms(True, self.vm_names)


"""
Test image lock free after engine restart
"""


@attr(tier=2)
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

    @classmethod
    def _create_vm(
            cls, vm_name, vm_description, disk_interface,
            sparse=True, volume_format=ENUMS['format_cow']):
        """ helper function for creating vm
        (passes common arguments, mostly taken from the configuration file)
        """
        logger.info("Creating VM %s" % vm_name)
        storage_domain_name = storagedomains.getDCStorages(
            config.DATA_CENTER_NAME, False)[0].name
        logger.info("storage domain: %s" % storage_domain_name)
        return ll_vms.createVm(
            True, vm_name, vm_description, cluster=config.CLUSTER_NAME,
            nic=config.HOST_NICS[0], storageDomainName=storage_domain_name,
            size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
            volumeType=sparse, volumeFormat=volume_format,
            diskInterface=disk_interface, memory=GB,
            cpu_socket=config.CPU_SOCKET,
            cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
            display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
            user=config.VMS_LINUX_USER, password=config.VMS_LINUX_PW,
            type=config.VM_TYPE_DESKTOP, installation=True, slim=True,
            image=config.COBBLER_PROFILE,
            network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT,
            attempt=3, interval=20)

    @classmethod
    def setup_class(cls):

        if not cls._create_vm(cls.vm_name, cls.vm_desc, config.INTERFACE_IDE):
            raise errors.VMException("Failed to create vm %s" % cls.vm_name)
        logger.info("Successfully created VM.")

        if not ll_vms.shutdownVm(True, cls.vm_name, async="false"):
            raise errors.VMException("Cannot shutdown vm %s" % cls.vm_name)
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
        engine_object = Machine(
            host=engine_ip,
            user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW).util('linux')

        self.assertTrue(restartOvirtEngine(engine_object, 5, 30, 75),
                        "Failed restarting ovirt-engine")
        logger.info("Successfully restarted ovirt-engine")

        # Wait until VM is down
        self.assertTrue(
            ll_vms.waitForVMState(
                self.vm_name,
                state=config.VM_DOWN_STATE),
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
                    self.vm_from_template,  self.template_name)
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

    @classmethod
    def teardown_class(cls):
        """
        Remove VM's and template
        """
        for vm in [cls.vm_name, cls.vm_from_template]:
            logger.info("Removing vm %s", vm)
            if not ll_vms.removeVm(positive=True, vm=vm, stopVM='true'):
                raise errors.VMException("Cannot remove vm %s" % vm)
            logger.info("Successfully removed %s.", vm)

        logger.info("Removing template %s", cls.template_name)
        if not templates.removeTemplate(positive=True,
                                        template=cls.template_name):
            raise errors.TemplateException("Failed to remove template %s"
                                           % cls.template_name)
        logger.info("Successfully removed %s." % cls.template_name)


"""
Test exposing BZ 986961
Maintenance spm with a running vm
"""


@attr(tier=0)
class TestCase315489(TestCase):
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

    def _createVm(self, vm_name, sd, host):
        return ll_vms.createVm(
            True, vm_name, vm_name, config.CLUSTER_NAME,
            storageDomainName=sd, size=config.DISK_SIZE,
            installation=True, diskType=config.DISK_TYPE_SYSTEM, memory=GB,
            cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO, highly_available=True,
            display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW, type=config.VM_TYPE_SERVER,
            slim=True, nic=config.HOST_NICS[0], volumeType=True,
            volumeFormat=ENUMS['format_cow'], useAgent=config.USE_AGENT,
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
            placement_host=host)

    def setUp(self):
        """
        create a VM on SPM
        """
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']
        host = hosts.getSPMHost(config.HOSTS)

        logger.info("Create VM")
        assert self._createVm(self.vm_name_base, master_domain, host)

    @tcms(tcms_plan_id, tcms_test_case)
    def test_maintenance_spm_with_running_vm(self):
        """
            * maintenance SPM
        """
        self.spm_host = hosts.getSPMHost(config.HOSTS)

        logger.info("Deactivating SPM host %s", self.spm_host)
        assert hosts.deactivateHost(True, self.spm_host)

        logger.info("Waiting DC state to be up with the new spm")
        ll_dc.wait_for_datacenter_state_api(config.DATA_CENTER_NAME)

        new_spm = hosts.getSPMHost(config.HOSTS)
        logger.info("New SPM is: %s", new_spm)

    def tearDown(self):
        # delete vm
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
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']
        disk_name = "disk_%s" % self.tcms_test_case

        assert ll_disks.addDisk(
            False, alias=disk_name, shareable=False, bootable=False,
            size=1 * GB, storagedomain=master_domain, sparse=None,
            format=ENUMS['format_raw'], interface=ENUMS['interface_ide'])


"""
Test exposing BZ 962549

TCMS plan: https://tcms.engineering.redhat.com/plan/9583
"""


@attr(tier=2)
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
        master_domain = storagedomains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)[1]['masterDomain']
        spm_host = hosts.getSPMHost(config.HOSTS)
        assert ll_vms.createVm(
            True, self.vm_name, self.vm_name, config.CLUSTER_NAME,
            installation=True, nic=config.HOST_NICS[0],
            storageDomainName=master_domain, size=config.DISK_SIZE,
            diskType=config.DISK_TYPE_SYSTEM, memory=GB,
            cpu_socket=config.CPU_SOCKET, cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO, display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE, user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW, type=config.VM_TYPE_DESKTOP,
            slim=True, placement_host=spm_host, volumeType=False,
            volumeFormat=ENUMS['format_raw'],
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
            useAgent=config.USE_AGENT)
        logger.info("Stopping VM")
        assert ll_vms.stopVm(True, self.vm_name)
        logger.info("Adding snapshot")
        assert ll_vms.addSnapshot(True, self.vm_name, self.snap_name)
        hsm_host = hosts.getAnyNonSPMHost(",".join(config.HOSTS))[1]['hsmHost']
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

    @classmethod
    def teardown_class(cls):
        ll_vms.removeVm(True, cls.vm_name, stopVM='true')
