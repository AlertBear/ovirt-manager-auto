"""
This is all of test case for libvirt_suite
Author: Alex Jia <ajia@redhat.com>, Bing Li <bili@redhat.com>
"""

import time
import logging
from unittest2 import TestCase
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sds,
    datacenters as ll_dcs,
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sds,
    datacenters as hl_dcs,
)
from art.rhevm_api.utils.test_utils import get_api

from art.test_handler import exceptions
from sys import modules

import config
import common

logger = logging.getLogger(__name__)

__THIS_MODULE = modules[__name__]

HOST_API = get_api('host', 'hosts')
DC_API = get_api('data_center', 'datacenters')

TCMS_PLAN_ID = '9621'
VM_MIGRATION = config.VM_MIGRATION


def setup_module():
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if config.DATA_CENTER_TYPE == config.STORAGE_TYPE_NFS:
        domain_path = config.PATH
        config.PARAMETERS['data_domain_path'] = [domain_path[0]]
    else:
        luns = config.LUNS
        config.PARAMETERS['lun'] = [luns[0]]

    logger.info("Preparing datacenter %s with hosts %s",
                config.DATA_CENTER_NAME, config.VDC)

    hl_dcs.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.DATA_CENTER_TYPE, basename=config.BASENAME
    )

    if config.DATA_CENTER_TYPE == config.STORAGE_TYPE_NFS:
        config.PARAMETERS['data_domain_path'] = domain_path
    else:
        config.PARAMETERS['lun'] = luns


def teardown_module():
    """
    Removes created datacenter, storages etc.
    """
    hl_dcs.clean_datacenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD
    )


class BaseTestCase(TestCase):
    """
    Base test case class
    """
    __test__ = False
    vm_name = config.VM_NAME
    disk_iface = config.INTERFACE_VIRTIO_SCSI
    diskless = False
    installation = True
    boot_options = 'hd network'
    net_name = 'net_1'
    vms_list = []
    snap_name_list = []

    @classmethod
    def setup_class(cls):
        """
        Create VM w/ or w/o OS installation
        """
        if cls.installation:
            logger.info('Creating vm and installing OS on it')
            if not common.install_vm(
                    vm_name=cls.vm_name, vm_description=cls.vm_name,
                    disk_interface=cls.disk_iface
            ):
                raise exceptions.VMException("Failed to create VM")
        else:
            logger.info('Creating vm without installing OS on it')
            # Add a VM w/ a network interface
            common.add_vm_with_nic(cls.vm_name, cls.net_name, cls.boot_options)

            # Add a disk into VM if needs
            if not cls.diskless:
                common.add_disk_into_vm(cls.vm_name)

            assert ll_vms.startVm(True, cls.vm_name)

    @classmethod
    def teardown_class(cls):
        """
        Removes disks and vm
        """
        logger.info("Removing the VMs: %s", cls.vms_list)
        assert ll_vms.removeVms(True, cls.vms_list, stop='true')


class TestInstallVMWithDisplayType(BaseTestCase):
    """
    Install VM with different display type
    """
    __test__ = (VM_MIGRATION == 'false')
    tcms_test_case = common.tcms_case_id(['279579', '309549'])

    def test_install_vm_with_different_disk_type(self):
        """
        Testing install vm with spice or vnc display type
        """
        logger.info("Booting up a %s vm and installing "
                    "OS on it", config.DISPLAY_TYPE)


class TestSuspendVMWithDiskless(BaseTestCase):
    """
    Suspend VM with diskless
    """
    __test__ = (VM_MIGRATION == 'false')
    tcms_test_case = common.tcms_case_id(['278104', '279577'])
    vm_name = 'vm_%s' % tcms_test_case
    diskless = True
    installation = False

    def test_suspend_stop_start_vm_with_diskless(self):
        """
        Create a VM w/o disk
        Start it from PXE network
        Suspend VM
        Stop VM
        Start VM
        """
        self.diskless = True
        self.boot_options = 'network hd'

        action_list = ['suspend', 'stop', 'start']
        for action in action_list:
            common.perform_actions(self.vm_name, action)

        logger.info("Test finished successfully")


class TestSuspendStartVMWithDiskNoSystem(BaseTestCase):
    """
    Suspend, start VM with disk no system
    """
    __test__ = (VM_MIGRATION == 'false')
    tcms_test_case = common.tcms_case_id(['278088', '279572'])
    vm_name = 'vm_%s' % tcms_test_case
    installation = False

    def test_suspend_start_vm_with_disk_but_no_system(self):
        """
        Create a VM with disk but no system
        Start VM from HD
        Suspend VM
        Start VM
        """
        action_list = ['suspend', 'start']
        for action in action_list:
            common.perform_actions(self.vm_name, action)

        logger.info("Test finished successfully")


class TestDisconnectHostFromStorageDomain(BaseTestCase):
    """
    Disconnect host from storage domain
    """
    __test__ = False
    tcms_test_case = common.tcms_case_id(['279583', '279573'])
    vm_name = 'vm_%s' % tcms_test_case
    net_name = 'net_%s_1' % tcms_test_case
    new_vm_name = 'vm_%s_1' % tcms_test_case
    sd_address = None
    installation = False
    host = config.FIRST_HOST
    ht_user = config.VDS_USER
    ht_pwd = config.VDS_PASSWORD[0]

    def add_one_more_vm(self):
        """
        Add another VM w/o OS installation
        """
        self.vms_list = common.add_vm_with_nic(
            vm_name=self.new_vm_name, net_name=self.net_name
        )
        common.add_disk_into_vm(vm_name=self.new_vm_name)

        logger.info("Successfully add new VM: %s.", self.new_vm_name)

    @classmethod
    def teardown_class(cls):
        """
        unblock all connections that were blocked during the test
        """
        logger.info('Unblocking connections')
        try:
            # Unblock connection
            common.unblock_storage(
                cls.host, cls.ht_user, cls.ht_pwd, cls.sd_address
            )
        except exceptions.NetworkException as msg:
            logger.info("Connection already unblocked. reason: %s", msg)

    def wait_for_dc_host_sd_up(self):
        """
        After unblocking connection everything should work.
        """
        dc_name = config.DATA_CENTER_NAME
        sd_name = config.SD_NAME_0
        ht_state = config.HOST_STATE_UP
        dc_state = config.DC_STATE_UP
        sd_state = config.SD_STATE_ACTIVE

        logger.info("Waiting for master domain to become active")
        assert ll_sds.waitForStorageDomainStatus(
            True, dataCenterName=dc_name,
            storageDomainName=sd_name,
            expectedStatus=sd_state,
            timeOut=1800
        )

        logger.info("Waiting until DC is up")
        assert ll_dcs.waitForDataCenterState(dc_name)

        logger.info("Validating that host is up")
        host_obj = HOST_API.find(self.host)
        assert host_obj.get_status() == ht_state

        logger.info("Validate master domain %s is UP", sd_name)
        sd_obj = ll_sds.getDCStorage(dc_name, sd_name)
        assert sd_obj.get_status() == sd_state

        logger.info("Validate that DC is UP")
        dc_obj = DC_API.find(dc_name)
        logger.info("DC is %s", dc_obj.get_status())
        assert dc_obj.get_status() == dc_state

    def test_disconnect_host_from_storage(self):
        """
        Create and start a VM
        Block connection from the host to storage server
        Wait until host goes to non-operational
        Stop the VM
        Unblock connection
        Check that the host is UP again
        """
        # Add another VM w/o OS installation and start it
        self.add_one_more_vm()
        self.vm_name = self.new_vm_name
        common.perform_actions(self.vm_name, "start")

        # Get storage address
        if config.DATA_CENTER_TYPE == 'nfs':
            self.sd_address = config.ADDRESS[0]
        elif config.DATA_CENTER_TYPE == 'iscsi':
            self.sd_address = config.LUN_ADDRESS[0]

        logger.info("Master domain ip found : %s", self.sd_address)

        # Block connection from host to storage domain
        assert common.block_storage(
            self.host, self.ht_user, self.ht_pwd, self.sd_address
        )
        # Sleep 60s then stop VM
        time.sleep(60)
        # Stop VM
        common.perform_actions(self.vm_name, 'stop')
        # Wait for VM down
        ll_vms.waitForVMState(self.vm_name, 'down')
        # Unblock connection
        assert common.unblock_storage(
            self.host, self.ht_user, self.ht_pwd, self.sd_address
        )
        # Wait for DC, SD and host recovery
        self.wait_for_dc_host_sd_up()
        logger.info("Test finished successfully")


class TestKillVMWithMultipleSnapshots(BaseTestCase):
    """
    Kill VM with multiple live snapshots
    """
    __test__ = (VM_MIGRATION == 'false')
    tcms_test_case = common.tcms_case_id(['362877', '278065'])
    vm_name = 'vm_%s' % tcms_test_case

    def test_multiple_live_snapshots_on_vm(self):
        """
        Install and start a VM
        Create 3 live snapshots
        Kill -9 VM's pid
        Try to start VM again
        """
        # Create 3 live snapshots for vm
        iter_num = 3
        self.snap_name_list = common.create_live_snapshots(
            self.vm_name, iter_num
        )
        # Kill vms
        assert common.kill_all_vms(
            config.FIRST_HOST, config.VDS_USER, config.VDS_PASSWORD[0]
        )
        # Wait for vm down
        ll_vms.waitForVMState(self.vm_name, 'down')
        # Try to start vm again
        common.perform_actions(self.vm_name, 'start')


class TestMigrateVMWithMultipleSnapshots(BaseTestCase):
    """
    Migrate VM with multiple live snapshots
    """
    __test__ = (VM_MIGRATION == 'true')
    tcms_test_case = common.tcms_case_id(['362877', '278065'])
    vm_name = 'vm_%s' % tcms_test_case
    snap_state = config.SNAPSHOT_OK

    def check_snapshots_state(self):
        """
        Check VM snapshots state
        """
        snapshots = common.get_vm_snapshots(self.vm_name, False)
        for snapshot in snapshots:
            assert snapshot.snapshot_status == self.snap_state

    def test_live_migration_vm_with_multiple_snapshots(self):
        """
        Intall and start a VM
        Create 3 live snapshots
        Live migrating of a VM with snapshots
        """
        # Create 3 live snapshots for VM
        iter_num = 3
        self.snap_name_list = common.create_live_snapshots(
            self.vm_name, iter_num
        )

        # Get original host address of the running VM
        orig_host = common.get_host(self.vm_name)

        # Get source and target host address
        ht_nic = config.HOST_NICS[0]
        src, dst = common.find_ip(
            self.vm_name, host_list=config.HOSTS, nic=ht_nic
        )

        # Migrate VM more than once
        iter_num = 2
        assert common.migrate_vm_more_than_once(
            self.vm_name, orig_host, ht_nic, src, dst, iter_num
        )
        # Check VM snapshots state
        self.check_snapshots_state()


class TestMigrationWithInactiveISODomain(BaseTestCase):
    """
    Migrate VM with inactive ISO domain
    """
    __test__ = (VM_MIGRATION == 'true')
    tcms_test_case = common.tcms_case_id(['279133', '279575'])
    vm_name = 'vm_%s' % tcms_test_case

    def test_migrating_vm_with_inactive_iso_domain(self):
        """
        Install a VM
        Attach existing ISO domain to data center and activate it
        RunOnce VM with an active ISO file, keep VM running
        Deactivate ISO domain and detach it from data center
        Migrate the VM
        Migrate the VM back
        """
        # attach and active ISO_DOMAIN.
        common.attach_and_activate_domain(
            config.DATA_CENTER_NAME, config.ISO_DOMAIN_NAME
        )

        # shut down the VM if need
        if "Down" not in ll_vms.get_vm_state(self.vm_name):
            common.perform_actions(self.vm_name, 'shutdown')
            ll_vms.waitForVMState(self.vm_name, 'down')

        # attach iso image to VM
        ll_vms.runVmOnce(
            True, vm=self.vm_name, cdrom_image='rhev-tools-setup.iso'
        )
        ll_vms.waitForVMState(self.vm_name, 'up')

        # deactive and detach ISO_DOMAIN
        hl_sds.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, config.ISO_DOMAIN_NAME
        )

        # Get original host address of the running VM
        orig_host = common.get_host(self.vm_name)

        # Get source and target host address
        ht_nic = config.HOST_NICS[0]
        src, dst = common.find_ip(
            self.vm_name, host_list=config.HOSTS, nic=ht_nic
        )

        # Migrate VM more than once
        iter_num = 2
        assert common.migrate_vm_more_than_once(
            self.vm_name, orig_host, ht_nic, src, dst, iter_num
        )


class TestLiveStorageMigration(BaseTestCase):
    """
    Live storage migration
    """
    __test__ = (VM_MIGRATION == 'false')
    disk_name = None
    tcms_test_case = common.tcms_case_id(['279585', '279581'])
    vm_name = 'vm_%s' % tcms_test_case

    dc_name = config.DATA_CENTER_NAME
    sd_name1 = config.SD_NAMES_LIST[0]
    sd_name2 = config.SD_NAMES_LIST[1]
    host = config.FIRST_HOST
    sd_type = config.SD_TYPE
    dc_type = config.DATA_CENTER_TYPE

    def test_live_storage_migration(self):
        """
        Install and start a VM
        Add a new storage domain into data center
        Attach the storage domain to data center and activate it
        Do live storage migration(move VM disk)
        Move VM disk back
        """
        sd_args = {'type': self.sd_type,
                   'storage_type': self.dc_type,
                   'host': self.host}

        # create one more storage domain
        common.create_one_more_sd(sd_args)

        # attach and active storage domain
        common.attach_and_activate_domain(self.dc_name, self.sd_name2)

        # start the VM if need
        if "up" not in ll_vms.get_vm_state(self.vm_name):
            common.perform_actions(self.vm_name, 'start')
            ll_vms.waitForVMState(self.vm_name, 'up')

        # get vm disk's name
        self.disk_name = '%s%s' % (self.vm_name, '_Disk1')

        # live storage migrate vm's disk
        assert common.move_vm_disk(
            self.vm_name, self.disk_name, self.sd_name2
        )

        # migrate back
        assert common.move_vm_disk(
            self.vm_name, self.disk_name, self.sd_name1
        )
