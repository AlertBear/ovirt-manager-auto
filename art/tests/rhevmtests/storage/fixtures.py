import pytest
import logging
import config
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    vms as ll_vms,
    storagedomains as ll_sd,
    templates as ll_templates,
    jobs as ll_jobs,
)
from art.rhevm_api.utils.test_utils import wait_for_tasks
from concurrent.futures import ThreadPoolExecutor
import rhevmtests.storage.helpers as storage_helpers
from art.unittest_lib.common import testflow


logger = logging.getLogger(__name__)
ISCSI = config.STORAGE_TYPE_ISCSI
FCP = config.STORAGE_TYPE_FCP
NFS = config.STORAGE_TYPE_NFS
GLUSTER = config.STORAGE_TYPE_GLUSTER
POSIX = config.STORAGE_TYPE_POSIX
CEPH = config.STORAGE_TYPE_CEPH


@pytest.fixture(scope='class')
def create_vm(request, remove_vm):
    """
    Create VM and initialize parameters
    """
    self = request.node.cls

    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    self.vm_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    if not hasattr(self, 'installation'):
        self.installation = True
    clone = getattr(self, 'deep_copy', False)
    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = self.storage_domain
    vm_args['vmName'] = self.vm_name
    vm_args['installation'] = self.installation
    vm_args['deep_copy'] = clone
    testflow.setup("Creating VM %s", self.vm_name)
    assert storage_helpers.create_vm_or_clone(**vm_args), (
        "Failed to create VM %s" % self.vm_name
    )


@pytest.fixture(scope='class')
def remove_vm(request):
    """
    Remove VM
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Remove VM %s", self.vm_name)
        assert ll_vms.safely_remove_vms([self.vm_name]), (
            "Failed to power off and remove VM %s" % self.vm_name
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def start_vm(request):
    """
    Start VM
    """
    self = request.node.cls

    wait_for_ip = False
    if hasattr(self, 'installation'):
        wait_for_ip = True if self.installation else False
    testflow.setup("Starting VM %s", self.vm_name)
    assert ll_vms.startVm(True, self.vm_name, config.VM_UP, wait_for_ip), (
        "Failed to start VM %s" % self.vm_name
    )


@pytest.fixture(scope='class')
def add_disk(request):
    """
    Add disk and initialize parameters
    """
    self = request.node.cls

    def finalizer():
        if ll_disks.checkDiskExists(True, self.disk_name):
            ll_disks.wait_for_disks_status([self.disk_name])
            testflow.teardown("Deleting disk %s", self.disk_name)
            assert ll_disks.deleteDisk(True, self.disk_name), (
                "Failed to delete disk %s" % self.disk_name
            )
    request.addfinalizer(finalizer)
    disk_params = config.disk_args.copy()
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    disk_params['storagedomain'] = self.storage_domain
    if hasattr(self, 'add_disk_params'):
        disk_params.update(self.add_disk_params)
    if hasattr(self, 'disk_size'):
        disk_params['provisioned_size'] = self.disk_size

    self.disk_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DISK
    )
    disk_params['alias'] = self.disk_name

    testflow.setup("Creating disk %s", self.disk_name)
    assert ll_disks.addDisk(True, **disk_params), (
        "Failed to create disk %s" % self.disk_name
    )
    ll_disks.wait_for_disks_status([self.disk_name])


@pytest.fixture(scope='class')
def attach_disk(request):
    """
    Attach a disk to VM
    """
    self = request.node.cls
    attach_kwargs = config.attach_disk_params.copy()
    if hasattr(self, 'update_attach_params'):
        attach_kwargs.update(self.update_attach_params)

    testflow.setup("Attach disk %s to VM %s", self.disk_name, self.vm_name)
    assert ll_disks.attachDisk(
        True, alias=self.disk_name, vm_name=self.vm_name, **attach_kwargs
    ), ("Failed to attach disk %s to VM %s" % (self.disk_name, self.vm_name))
    ll_disks.wait_for_disks_status([self.disk_name])


@pytest.fixture(scope='class')
def update_vm(request):
    """
    Update VM
    """
    self = request.node.cls

    if not ll_vms.updateVm(True, self.vm_name, **self.update_vm_params):
        assert "Failed to update vm %s with params %s" % (
            self.disk_name, self.update_vm_params
        )


@pytest.fixture(scope='class')
def create_snapshot(request):
    """
    Create snapshot of VM
    """
    self = request.node.cls

    if not hasattr(self, 'snapshot_description'):
        self.snapshot_description = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
    testflow.setup(
        "Creating snapshot %s of VM %s",
        self.snapshot_description, self.vm_name
    )
    assert ll_vms.addSnapshot(True, self.vm_name, self.snapshot_description), (
        "Failed to create snapshot of VM %s" % self.vm_name
    )
    ll_vms.wait_for_vm_snapshots(
        self.vm_name, [config.SNAPSHOT_OK], self.snapshot_description
    )
    ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])


@pytest.fixture(scope='class')
def preview_snapshot(request):
    """
    Create snapshot of VM
    """
    self = request.node.cls

    testflow.setup(
        "Preview snapshot %s of VM %s", self.snapshot_description, self.vm_name
    )
    assert ll_vms.preview_snapshot(
        True, self.vm_name, self.snapshot_description
    ), ("Failed to preview snapshot %s" % self.snapshot_description)
    ll_jobs.wait_for_jobs([config.JOB_PREVIEW_SNAPSHOT])


@pytest.fixture(scope='class')
def undo_snapshot(request):
    """
    Undo snapshot
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Undoing snapshot of VM %s", self.vm_name)
        assert ll_vms.undo_snapshot_preview(True, self.vm_name), (
            "Failed to undo previewed snapshot %s" %
            self.snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(self.vm_name, [config.SNAPSHOT_OK])
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def delete_disks(request):
    """
    Delete disks
    """
    self = request.node.cls

    def finalizer():
        results = list()
        with ThreadPoolExecutor(
            max_workers=len(self.disks_to_remove)
        ) as executor:
            for disk in self.disks_to_remove:
                if ll_disks.checkDiskExists(True, disk):
                    ll_disks.wait_for_disks_status([disk])
                    testflow.teardown("Deleting disk %s", disk)
                    results.append(
                        executor.submit(
                            ll_disks.deleteDisk, True, disk
                        )
                    )
        for index, result in enumerate(results):
            if result.exception():
                raise result.exception()
            if not result.result:
                raise exceptions.HostException(
                    "Delete disk %s failed." % self.disks_to_remove[index]
                )
            logger.info(
                "Delete disk %s succeeded", self.disks_to_remove[index]
            )
    request.addfinalizer(finalizer)
    if not hasattr(self, 'disk_name'):
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_DISK
        )
    if not hasattr(self, 'disks_to_remove'):
        self.disks_to_remove = list()


@pytest.fixture()
def poweroff_vm(request):
    """
    Power off VM
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Power off VM %s", self.vm_name)
        if not ll_vms.stop_vms_safely([self.vm_name]):
            logger.error("Failed to power off VM %s", self.vm_name)
            self.test_failed = True
        self.teardown_exception()
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def create_template(request):
    """
    Create a template from GE VM
    """
    self = request.node.cls

    def finalizer():
        if ll_templates.check_template_existence(self.template_name):
            testflow.teardown("Remove template %s", self.template_name)
            assert ll_templates.removeTemplate(True, self.template_name), (
                "Failed to remove template %s" % self.template_name
            )

    request.addfinalizer(finalizer)
    if not hasattr(self, 'template_name'):
        self.template_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_TEMPLATE
        )
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    base_vm_for_snapshot = getattr(self, 'vm_name', config.VM_NAME[0])
    testflow.setup("Creating template %s", self.template_name)
    assert ll_templates.createTemplate(
        True, vm=base_vm_for_snapshot, name=self.template_name,
        cluster=config.CLUSTER_NAME, storagedomain=self.storage_domain
    ), ("Failed to create template %s from VM %s" %
        (self.template_name, base_vm_for_snapshot))


@pytest.fixture(scope='class')
def remove_template(request):
    """
    Remove a template
    """
    self = request.node.cls

    def finalizer():
        if ll_templates.check_template_existence(self.template_name):
            testflow.teardown("Remove template %s", self.template_name)
            assert ll_templates.removeTemplate(True, self.template_name), (
                "Failed to remove template %s" % self.template_name
            )

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def initialize_storage_domains(request):
    """
    Initialize storage domain parameters
    """
    self = request.node.cls

    self.storage_domains = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, self.storage
    )
    self.storage_domain = self.storage_domains[0]
    self.storage_domain_1 = self.storage_domains[1]
    self.storage_domain_2 = self.storage_domains[2]


@pytest.fixture(scope='class')
def deactivate_domain(request):
    """
    Deactivates GE storage domain
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown(
            "Activating storage domain %s", self.sd_to_deactivate
        )
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_to_deactivate
        ), ("Failed to activate storage domain %s" % self.sd_to_deactivate)

    request.addfinalizer(finalizer)
    if not hasattr(self, 'sd_to_deactivate_index'):
        self.sd_to_deactivate = self.storage_domains[1]
    else:
        self.sd_to_deactivate = self.storage_domains[
            self.sd_to_deactivate_index
        ]
    wait_for_tasks(
        config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
    )
    testflow.setup(
        "Deactivating storage domain %s", self.sd_to_deactivate
    )
    assert ll_sd.deactivateStorageDomain(
        True, config.DATA_CENTER_NAME, self.sd_to_deactivate
    ), ("Failed to deactivate storage domain %s" % self.sd_to_deactivate)


@pytest.fixture(scope='class')
def create_storage_domain(request):
    """
    Create new storage domain
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown(
            "Remove storage domain %s", self.new_storage_domain
        )
        assert hl_sd.remove_storage_domain(
            self.new_storage_domain, config.DATA_CENTER_NAME,
            config.HOSTS[0], True
        ), ("Failed to remove storage domain %s" % self.new_storage_domain)
    request.addfinalizer(finalizer)
    if not hasattr(self, 'new_storage_domain'):
        self.new_storage_domain = (
            storage_helpers.create_unique_object_name(
                self.__name__, config.OBJECT_TYPE_SD
            )
        )
    if not hasattr(self, 'index'):
        self.index = 0
    name = self.new_storage_domain
    spm = ll_hosts.getSPMHost(config.HOSTS)
    testflow.setup(
        "Create new storage domain %s", self.new_storage_domain
    )
    if self.storage == ISCSI:
        status = hl_sd.addISCSIDataDomain(
            spm,
            name,
            config.DATA_CENTER_NAME,
            config.UNUSED_LUNS[self.index],
            config.UNUSED_LUN_ADDRESSES[self.index],
            config.UNUSED_LUN_TARGETS[self.index],
            override_luns=True
        )

    elif self.storage == FCP:
        status = hl_sd.addFCPDataDomain(
            spm,
            name,
            config.DATA_CENTER_NAME,
            config.UNUSED_FC_LUNS[self.index],
            override_luns=True
        )
    elif self.storage == NFS:
        nfs_address = config.UNUSED_DATA_DOMAIN_ADDRESSES[self.index]
        nfs_path = config.UNUSED_DATA_DOMAIN_PATHS[self.index]
        status = hl_sd.addNFSDomain(
            host=spm,
            storage=name,
            data_center=config.DATA_CENTER_NAME,
            address=nfs_address,
            path=nfs_path,
            format=True
        )
    elif self.storage == GLUSTER:
        gluster_address = (
            config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[self.index]
        )
        gluster_path = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[self.index]
        status = hl_sd.addGlusterDomain(
            host=spm,
            name=name,
            data_center=config.DATA_CENTER_NAME,
            address=gluster_address,
            path=gluster_path,
            vfs_type=config.ENUMS['vfs_type_glusterfs']
        )
    elif self.storage == CEPH:
        # TODO: remove this when the patch related to the vfs_type will merge
        name = "{0}_{1}".format(CEPH, self.non_master)
        self.non_master = name
        posix_address = (
            config.UNUSED_CEPHFS_DATA_DOMAIN_ADDRESSES[self.index]
        )
        posix_path = config.UNUSED_CEPHFS_DATA_DOMAIN_PATHS[self.index]
        status = hl_sd.addPosixfsDataDomain(
            host=spm,
            storage=name,
            data_center=config.DATA_CENTER_NAME,
            address=posix_address,
            path=posix_path,
            vfs_type=CEPH,
            mount_options=config.CEPH_MOUNT_OPTIONS
        )
    assert status, (
        "Creating %s storage domain '%s' failed" % (self.storage, name)
    )
    ll_jobs.wait_for_jobs(
        [config.JOB_ADD_STORAGE_DOMAIN, config.JOB_ACTIVATE_DOMAIN]
    )
    ll_sd.waitForStorageDomainStatus(
        True, config.DATA_CENTER_NAME, name,
        config.SD_ACTIVE
    )
    wait_for_tasks(
        config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
    )


@pytest.fixture()
def remove_storage_domain(request):
    """
    Remove storage domain
    """
    self = request.node.cls

    def finalizer():
        if ll_sd.checkIfStorageDomainExist(True, self.storage_domain):
            testflow.teardown("Remove storage domain %s", self.storage_domain)
            assert hl_sd.remove_storage_domain(
                self.storage_domain, config.DATA_CENTER_NAME,
                config.HOSTS[0], True
            ), ("Failed to remove storage domain %s", self.storage_domain)
    request.addfinalizer(finalizer)
    self.storage_domain = None


@pytest.fixture(scope='class')
def remove_vms(request):
    """
    Remove VM
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Remove VMs %s", ', '.join(self.vm_names))
        assert ll_vms.safely_remove_vms(self.vm_names), (
            "Failed to remove VM from %s" % self.vm_names
        )
    request.addfinalizer(finalizer)
    if not hasattr(self, 'vm_names'):
        self.vm_names = list()


@pytest.fixture()
def clean_export_domain(request):
    """
    Clean export domain from exported entities
    """
    def finalizer():
        testflow.teardown(
            "Cleaning Export Domain %s", config.EXPORT_DOMAIN_NAME
        )
        storage_helpers.clean_export_domain(
            config.EXPORT_DOMAIN_NAME, config.DATA_CENTER_NAME
        )
    request.addfinalizer(finalizer)
