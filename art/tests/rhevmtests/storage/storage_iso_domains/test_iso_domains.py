"""
Test ISO Storage Domain

https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/2_3_Storage_Import_ISO_Export_Domains

https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Sanity

Check with shared and local DCs
Check with RHEL and windows OSs
Check with NFS, POSIXFS and local ISO domains
"""


import shlex
import config
from art.unittest_lib import (
    StorageTest as TestCase,
    attr
)
import helpers
import pytest
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd
)
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    vms as ll_vms,
    jobs as ll_jobs,
    hosts as ll_hosts
)
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion
from art.unittest_lib.common import testflow
from art.test_handler.settings import opts
from rhevmtests.storage.fixtures import (
    create_vm, remove_storage_domain, init_host_or_engine_executor
)

from rhevmtests.storage.fixtures import remove_vm  # noqa


@pytest.mark.usefixtures(
    init_host_or_engine_executor.__name__,
    create_vm.__name__,
    remove_vm.__name__,
    remove_storage_domain.__name__
)
class BaseCaseIsoDomains(TestCase):
    """
    Base case including methods used in the tests classes
    """
    local = None
    machine = None
    vm_name = None
    mount_target = None
    storagedomains = []
    dc_name = config.DATA_CENTER_NAME
    spm_host = None
    executor_type = 'engine'

    def clean_environment(self):
        """
        Make sure VM is stopped and doesn't have an ISO attached
        Remove the directory in the engine where the ISO repository is mounted
        Clean the ISO domains
        """

        testflow.setup("Ejecting CD from VM %s", self.vm_name)
        assert ll_vms.eject_cdrom_vm(self.vm_name), (
            "Failed to eject CD from VM %s" % self.vm_name
        )

        testflow.setup("Stopping VM %s", self.vm_name)
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to power off %s" % self.vm_name
        )

        testflow.setup(
            "Un-mounting ISO repository from the engine"
        )
        rc, _, error = self.executor.run_cmd(
            shlex.split(config.UMOUNT_CMD)
        )
        assert not rc, (
            "Failed to unmount ISO repository from the engine with error %s"
            % error
        )

        testflow.setup(
            "Removing the target dir where the ISO repository is mounted"
        )
        rc, _, error = self.executor.run_cmd(
            shlex.split(config.RMDIR_CMD)
        )
        assert not rc, (
            "Failed to remove directory %s in the engine with error %s" % (
                config.TARGETDIR, error
            )
        )

        if self.storage_domain:
            testflow.setup("Removing ISO domain %s", self.storage_domain)
            assert hl_sd.remove_storage_domain(
                self.storage_domain, self.dc_name, self.spm_host,
                format_disk=True
            ), ("Failed to remove storage domain %s", self.storage_domain)

        ll_jobs.wait_for_jobs([config.JOB_REMOVE_DOMAIN])

    def attach_iso_and_maintenance(self, run_once=None, iso_domain=None):
        """
        1. Attach an ISO domain to the DC
        2. Attach an ISO from the ISO domain to a VM
        3. Enter the ISO domain to maintenance while the ISO is attached
        4. Eject the ISO and try to put the domain in maintenance
        """

        testflow.setup("Adding ISO domain %s", iso_domain['name'])
        self.storage_domain = None
        self.spm_host = ll_hosts.getSPMHost(config.HOSTS)
        assert helpers.add_storage_domain(
            self.dc_name, self.spm_host, **iso_domain
        )

        self.storage_domain = iso_domain['name']
        testflow.setup(
            "Mounting the ISO repository in the engine"
        )
        rc, _, error = self.executor.run_cmd(
            shlex.split(config.MKDIR_CMD)
        )
        assert not rc, (
            "Failed to create directory %s for mount point with error %s" %
            config.TARGETDIR, error
        )

        # Mount the nfs partition with all the ISOs
        rc, _, error = self.executor.run_cmd(
            shlex.split(config.MOUNT_CMD)
        )
        assert not rc, (
            "Failed to mount ISO repository with error %s" % error
        )

        testflow.setup("Uploading ISO %s to the domain", config.ISO_IMAGE)
        # This will upload one ISO to the new created ISO domain
        find_cmd = 'find %s |grep %s' % (config.TARGETDIR, config.ISO_IMAGE)
        rc, iso_file, error = self.executor.run_cmd(
            shlex.split(find_cmd)
        )
        assert not rc, (
            "Failed to find ISO file with error %s" % error
        )
        upload_cmd = (
            "engine-iso-uploader --conf-file=%s -f upload -i %s %s --insecure"
            % (
                config.ISO_UPLOADER_CONF_FILE,
                self.storage_domain, iso_file[:-1]
            )
        )
        testflow.setup("Executing %s", upload_cmd)
        rc, _, error = self.executor.run_cmd(
            shlex.split(upload_cmd)
        )
        assert not rc, (
            "Failed to upload ISO %s to ISO domain %s with error %s" % (
                config.ISO_IMAGE, self.storage_domain, error
            )
        )

        if run_once:
            assert ll_vms.runVmOnce(
                True, self.vm_name, cdrom_image=config.ISO_IMAGE
            )
        else:
            assert ll_vms.attach_cdrom_vm(True, self.vm_name, config.ISO_IMAGE)
            assert ll_vms.startVm(True, self.vm_name)

        testflow.setup(
            "Wait for tasks to complete before storage domain deactivation"
        )
        test_utils.wait_for_tasks(config.ENGINE, self.dc_name)
        status = ll_sd.deactivateStorageDomain(
            False, self.dc_name, self.storage_domain
        )
        assert status, (
            "ISO domain %s was deactivated while one of the ISOs "
            "is attached to VM %s" % (iso_domain['name'], self.vm_name)
        )

        assert ll_vms.eject_cdrom_vm(self.vm_name)
        testflow.setup(
            "Wait for tasks to complete before deactivating the storage domain"
        )
        test_utils.wait_for_tasks(config.ENGINE, self.dc_name)
        assert ll_sd.deactivateStorageDomain(
            True, self.dc_name, self.storage_domain
        ), (
            "ISO domain %s wasn't deactivated after ejecting one of the ISOs"
            "from the VM %s" % (self.storage_domain, self.vm_name)
        )


class TestCase11576Shared(BaseCaseIsoDomains):
    """
    Test detaching ISO domains when an ISO image is inserted in a VM under a
    shared DC
    """
    # Please note that the following bug may cause this case to fail
    # intermittently: https://bugzilla.redhat.com/show_bug.cgi?id=1215402
    # The Posix ISO domain fails to Detach and can only be removed by using
    # the Destroy option (which the code doesn't do)
    # Gluster doesn't support being used as an ISO domain
    __test__ = (
        config.STORAGE_TYPE_NFS in opts['storages']
        or config.STORAGE_TYPE_CEPH in opts['storages']
    )
    storages = set([config.STORAGE_TYPE_NFS, config.STORAGE_TYPE_CEPH])
    local = False
    # Bugzilla history
    # 1225356: CLI: update cdrom is not ejecting the ISO image when the file-id
    # option is not provided
    # 1254936: Deactivate storage domain sometimes fails without any warning

    @attr(tier=2)
    @polarion("RHEVM3-11576")
    def test_detaching_iso_vm_and_vm_runonce(self):
        """
        Try detaching a posixfs/nfs ISO domain from VM while ISO is attached
        """
        testflow.setup(
            "Testing detaching posixfs ISO domain while ISO image is "
            "attached to VM"
        )
        self.attach_iso_and_maintenance(iso_domain=config.ISO_POSIX_DOMAIN)
        self.clean_environment()

        testflow.setup(
            "Testing detaching nfs ISO domain while ISO image is "
            "attached to VM"
        )
        self.attach_iso_and_maintenance(iso_domain=config.ISO_NFS_DOMAIN)
        self.clean_environment()

        testflow.setup(
            "Testing detaching posixfs ISO domain while ISO image is "
            "attached to VM and run it once"
        )
        self.attach_iso_and_maintenance(
            run_once=True, iso_domain=config.ISO_POSIX_DOMAIN)
        self.clean_environment()

        testflow.setup(
            "Testing detaching nfs ISO domain while ISO image is "
            "attached to VM and run it once"
        )
        self.attach_iso_and_maintenance(
            run_once=True, iso_domain=config.ISO_NFS_DOMAIN)
        self.clean_environment()


class PlanIsoDomainLocal(BaseCaseIsoDomains):
    """
    Test detaching ISO domains when an ISO image is inserted in a VM under a
    local DC
    """
    # Local data center tests are not supported by the golden environment
    __test__ = False
    local = True
    storagedomains = [config.LOCAL_DOMAIN]

    @attr(tier=2)
    @polarion("RHEVM3-11859")
    def test_detaching_local_iso_vm(self):
        """
        Try detaching a local ISO domain from vm while ISO is attached
        """
        self.attach_iso_and_maintenance(iso_domain=config.ISO_LOCAL_DOMAIN)

    @attr(tier=2)
    @polarion("RHEVM3-11860")
    def test_detaching_local_iso_vm_runonce(self):
        """
        Try detaching a local ISO domain from vm after attaching it with
        run once
        """
        self.attach_iso_and_maintenance(
            run_once=True, iso_domain=config.ISO_LOCAL_DOMAIN
        )
