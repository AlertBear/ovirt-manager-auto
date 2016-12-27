import pytest
import logging
import config
from art.core_api.apis_exceptions import APITimeout
from art.test_handler import exceptions
from art.unittest_lib.common import testflow
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
from art.rhevm_api.resources import storage
from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils.storage_api import unblockOutgoingConnection
from concurrent.futures import ThreadPoolExecutor
import rhevmtests.storage.helpers as storage_helpers
import rhevmtests.helpers as rhevm_helpers
from rhevmtests.networking import helper as network_helper

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
    cluster = getattr(self, 'cluster_name', config.CLUSTER_NAME)
    clone = getattr(self, 'deep_copy', False)
    self.installation = getattr(self, 'installation', True)
    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = self.storage_domain
    vm_args['cluster'] = cluster
    vm_args['vmName'] = self.vm_name
    vm_args['installation'] = self.installation
    vm_args['deep_copy'] = clone
    if hasattr(self, 'vm_args'):
        vm_args.update(self.vm_args)
    testflow.setup("Creating VM %s", self.vm_name)
    assert storage_helpers.create_vm_or_clone(**vm_args), (
        "Failed to create VM %s" % self.vm_name
    )


@pytest.fixture()
def add_disk_permutations(request):
    """
    Creating all possible combinations of disks for test
    """
    self = request.node.cls

    self.shared = getattr(self, 'shared', None)
    self.polarion_test_case = getattr(self, 'polarion_test_case', 'Test')
    testflow.setup("Creating all disk permutations")
    self.disk_names = storage_helpers.create_disks_from_requested_permutations(
        domain_to_use=self.storage_domain,
        interfaces=storage_helpers.INTERFACES,
        shared=self.shared,
        size=config.DISK_SIZE,
        test_name=self.polarion_test_case
    )
    assert ll_disks.wait_for_disks_status(self.disk_names), (
        "At least one of the disks %s was not in the expected state 'OK"
        % self.disk_names
    )


@pytest.fixture()
def attach_and_activate_disks(request):
    """
    Attach and activate disks to a VM
    """
    self = request.node.cls

    storage_helpers.prepare_disks_for_vm(self.vm_name, self.disk_names)


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

    wait_for_ip = getattr(self, 'vm_wait_for_ip', False)

    run_on_spm = getattr(self, 'vm_run_on_spm', None)
    if run_on_spm:
        host = ll_hosts.getSPMHost(config.HOSTS)
    elif run_on_spm is False:
        host = ll_hosts.getHSMHost(config.HOSTS)
    else:
        host = None

    testflow.setup("Starting VM %s", self.vm_name)
    assert ll_vms.startVm(
        True, self.vm_name, config.VM_UP, wait_for_ip,
        placement_host=host
    ), (
        "Failed to start VM %s" % self.vm_name
    )
    if hasattr(self, 'get_vm_ip'):
        self.vm_ip = storage_helpers.get_vm_ip(self.vm_name)


@pytest.fixture(scope='class')
def add_disk(request):
    """
    Add disk and initialize parameters
    """
    self = request.node.cls

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
def delete_disk(request):
    """
    Removes disk
    """
    self = request.node.cls

    def finalizer():
        if ll_disks.checkDiskExists(True, self.disk_name):
            assert ll_disks.wait_for_disks_status([self.disk_name]), (
                "Failed to get disk %s status" % self.disk_alias
            )
            testflow.teardown("Deleting disk %s", self.disk_name)
            assert ll_disks.deleteDisk(True, self.disk_name), (
                "Failed to delete disk %s" % self.disk_name
            )
    request.addfinalizer(finalizer)


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

    self.snapshot_description = getattr(
        self, 'snapshot_description',
        storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
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
        snapshot_description = ll_vms.get_snapshot_description_in_preview(
            self.vm_name
        )
        if snapshot_description:
            testflow.teardown("Undoing snapshot of VM %s", self.vm_name)
            assert ll_vms.undo_snapshot_preview(True, self.vm_name), (
                "Failed to undo previewed snapshot %s" % snapshot_description
            )
            ll_vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK]
            )
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
        assert ll_vms.stop_vms_safely([self.vm_name]), (
            "Failed to power off VM %s" % self.vm_name
        )
    request.addfinalizer(finalizer)


@pytest.fixture()
def poweroff_vm_setup(request):
    """
    Power off VM
    """
    self = request.node.cls

    testflow.setup("Power off VM %s", self.vm_name)
    assert ll_vms.stop_vms_safely([self.vm_name]), (
        "Failed to power off VM %s" % self.vm_name
    )


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
    test_utils.wait_for_tasks(
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
    test_utils.wait_for_tasks(
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


@pytest.fixture()
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


@pytest.fixture()
def set_spm_priorities(request):
    """
    Set hosts' SPM priorities according to spm_priorities list
    """
    self = request.node.cls

    def finalizer():
        """
        Resetting SPM priority to all hosts
        """
        result_list = list()
        testflow.teardown(
            "Resetting SPM priority to %s for all hosts", self.spm_priorities
        )
        for host, priority in zip(config.HOSTS, self.spm_priorities):
            result_list.append(ll_hosts.setSPMPriority(True, host, priority))
        assert all(result_list)
    request.addfinalizer(finalizer)

    self.spm_priorities = getattr(
        self, 'spm_priorities', (
            [config.DEFAULT_SPM_PRIORITY] * len(config.HOSTS)
        )
    )
    testflow.setup(
        "Setting SPM priorities for hosts: %s", self.spm_priorities
    )
    for host, priority in zip(config.HOSTS, self.spm_priorities):
        if not ll_hosts.setSPMPriority(True, host, priority):
            raise exceptions.HostException(
                'Unable to set host %s priority' % host
            )
    self.spm_host = getattr(
        self, 'spm_host', ll_hosts.getSPMHost(config.HOSTS)
    )
    if not hasattr(self, 'hsm_hosts'):
        self.hsm_hosts = [
            host for host in config.HOSTS if host != self.spm_host
        ]
    testflow.setup("Ensuring SPM priority is for all hosts")
    for host, priority in zip(config.HOSTS, self.spm_priorities):
        if not ll_hosts.checkSPMPriority(True, host, str(priority)):
            raise exceptions.HostException(
                'Unable to check host %s priority' % host
            )


@pytest.fixture()
def init_master_domain_params(request):
    """
    Extract master domain name and address
    """
    self = request.node.cls

    found, master_domain_obj = ll_sd.findMasterStorageDomain(
        True, datacenter=config.DATA_CENTER_NAME
    )
    assert found, (
        "Could not find master storage domain on Data center '%s'" %
        config.DATA_CENTER_NAME
    )

    self.master_domain = master_domain_obj.get('masterDomain')

    if not hasattr(self, 'master_domain_address'):
        rc, master_domain_address = ll_sd.getDomainAddress(
            True, self.master_domain
        )
        assert rc, "Could not get the address of '%s'" % self.master_domain
        self.master_domain_address = master_domain_address['address']
    logger.info(
        'Found master %s domain in address: %s',
        self.master_domain, self.master_domain_address,
    )


@pytest.fixture(scope='class')
def create_dc(request):
    """
    Add data-center with one host to the environment
    """
    self = request.node.cls

    self.new_dc_name = getattr(
        self, 'new_dc_name', storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_DC
        )
    )
    self.cluster_name = getattr(
        self, 'cluster_name', storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_CLUSTER
        )
    )
    self.dc_version = getattr(self, 'dc_version', config.COMPATIBILITY_VERSION)
    self.host_name = getattr(
        self, 'host_name', ll_hosts.getHSMHost(config.HOSTS)
    )
    testflow.setup(
        "Create data-center %s with cluster %s and host %s", self.new_dc_name,
        self.cluster_name, self.host_name
    )
    storage_helpers.create_data_center(
        self.new_dc_name, self.cluster_name, self.host_name, self.dc_version
    )


@pytest.fixture(scope='class')
def clean_dc(request):
    """
    Remove data-center from the the environment
    """
    self = request.node.cls

    def finalizer():
        master_domain = getattr(self, 'master_domain', config.MASTER_DOMAIN)
        testflow.teardown(
            "Clean data-center %s and remove it", self.new_dc_name
        )
        storage_helpers.clean_dc(
            self.new_dc_name, self.cluster_name, self.host_name,
            sd_name=master_domain
        )
    request.addfinalizer(finalizer)


@pytest.fixture()
def clean_mount_point(request):
    """
    Clean storage domain mount point
    """
    self = request.node.cls

    def finalizer():

        spm_host = ll_hosts.getSPMHost(config.HOSTS)

        if self.storage == NFS or self.storage == POSIX:
            assert storage.clean_mount_point(
                spm_host, config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_DATA_DOMAIN_PATHS[0],
                rhevm_helpers.NFS_MNT_OPTS
            ), "Failed to clean mount point address: %s, path: %s" % (
                config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_DATA_DOMAIN_PATHS[0],
            )
        elif self.storage == GLUSTER:
            assert storage.clean_mount_point(
                spm_host, config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0],
                rhevm_helpers.GLUSTER_MNT_OPTS
            ), "Failed to clean mount point address: %s, path: %s" % (
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0],
            )
    request.addfinalizer(finalizer)


@pytest.fixture()
def remove_vm_from_export_domain(request):
    """
    Remove VM from export domain
    """
    self = request.node.cls

    def finalizer():
        export_domain = getattr(
            self, 'export_domain', config.EXPORT_DOMAIN_NAME
        )

        testflow.teardown(
            "Removing VM: %s from export domain: %s", self.vm_name,
            export_domain
        )
        assert ll_vms.remove_vm_from_export_domain(
            positive=True, vm=self.vm_name, datacenter=config.DATA_CENTER_NAME,
            export_storagedomain=export_domain
        ), "Failed to remove VM: %s from export domain: %s" % (
            self.vm_name, export_domain
        )

    request.addfinalizer(finalizer)


@pytest.fixture()
def remove_template_from_export_domain(request):
    """
    Remove template from export domain
    """
    self = request.node.cls

    def finalizer():
        export_domain = getattr(
            self, 'export_domain', config.EXPORT_DOMAIN_NAME
        )

        testflow.teardown(
            "Remove template: %s from export domain: %s",
            self.template_name, export_domain
        )
        assert ll_templates.removeTemplateFromExportDomain(
            positive=True, template=self.template_name,
            export_storagedomain=export_domain
        ), "Failed to remove template: %s from export domain: %s" % (
            self.vm_name, export_domain
        )
    request.addfinalizer(finalizer)


@pytest.fixture()
def seal_vm(request):
    """
    Seal VM
    """
    self = request.node.cls

    assert network_helper.seal_vm(self.vm_name, config.VM_PASSWORD), (
        "Failed to set a persistent network for VM '%s'" % self.vm_name
    )


@pytest.fixture()
def export_vm(request):
    """
    Export VM to export domain
    """
    self = request.node.cls

    export_domain = getattr(
        self, 'export_domain', config.EXPORT_DOMAIN_NAME
    )
    testflow.setup(
        "Export VM: %s to export domain: %s", self.vm_name, export_domain
    )
    assert ll_vms.exportVm(True, self.vm_name, export_domain), (
        "Failed to export VM: '%s' into export domain: %s" % (
            self.vm_name, export_domain
        )
    )


@pytest.fixture()
def create_fs_on_disk(request):
    """
    Creates a filesystem on a disk and mounts it in the vm
    """

    self = request.node.cls
    out, config.MOUNT_POINT = storage_helpers.create_fs_on_disk(
        self.vm_name, self.disk_name
    )

    assert out, (
        "Unable to create a filesystem on disk: %s of VM %s" %
        (self.disk_name, self.vm_name)
    )


@pytest.fixture(scope='class')
def prepare_disks_with_fs_for_vm(request):
    """
    Prepare disks with filesystem for vm
    """
    self = request.node.cls

    testflow.setup(
        "Creating disks with filesystem and attach to VM %s", self.vm_name,
    )
    disks, mount_points = storage_helpers.prepare_disks_with_fs_for_vm(
        self.storage_domain, self.storage, self.vm_name
    )
    self.disks_to_remove = disks
    config.MOUNT_POINTS = mount_points


@pytest.fixture()
def wait_for_all_snapshot_tasks(request):
    """
    Wait for snapshot creation and LSM tasks
    """
    self = request.node.cls

    def finalizer():
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        disks = [d.get_id() for d in ll_vms.getVmDisks(self.vm_name)]
        ll_disks.wait_for_disks_status(disks, key='id')
        try:
            ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        except APITimeout:
            logger.error(
                "Snapshots failed to reach OK state on VM '%s'", self.vm_name
            )

        try:
            ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        except APITimeout:
            logger.error(
                "Snapshots failed to reach OK state on VM '%s'", self.vm_name
            )
        ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
        if not ll_vms.waitForVmsDisks(self.vm_name):
            logger.error(
                "Disks in VM '%s' failed to reach state 'OK'", self.vm_name
            )
    request.addfinalizer(finalizer)


@pytest.fixture()
def unblock_connectivity_storage_domain_teardown(request):
    """
    Unblock connectivity from host to storage domain
    """
    self = request.node.cls

    def finalizer():
        assert unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip
        ), "Failed to block connects from %s to %s" % (
            self.host_ip, self.storage_domain_ip
        )

    request.addfinalizer(finalizer)


@pytest.fixture()
def initialize_variables_block_domain(request):
    """
    Initialize variables for blocking connection from the SPM to a
    storage domain
    """
    self = request.node.cls

    self.host = getattr(self, 'host', ll_hosts.getSPMHost(config.HOSTS))
    self.host_ip = ll_hosts.getHostIP(self.host)
    found, address = ll_sd.getDomainAddress(True, self.storage_domain)
    assert found, "IP for storage domain %s not found" % self.storage_domain
    self.storage_domain_ip = address['address']


@pytest.fixture()
def add_nic(request):
    """
    Add a nic to the VM
    """
    self = request.node.cls

    self.nic = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_NIC
    )
    assert ll_vms.addNic(
        True, vm=self.vm_name, name=self.nic, mac_address=None,
        network=config.MGMT_BRIDGE, vnic_profile=config.MGMT_BRIDGE,
        plugged='true', linked='true'
    ), "Failed to add nic %s to VM %s" % (self.nic, self.vm_name)


@pytest.fixture()
def export_template(request):
    """
    Export template to export domain
    """
    self = request.node.cls

    export_domain = getattr(
        self, 'export_domain', config.EXPORT_DOMAIN_NAME
    )
    testflow.setup(
        "Export template %s to export domain %s",
        self.template_name, export_domain
    )
    exclusive = getattr(self, 'exclusive', 'false')
    assert ll_templates.exportTemplate(
        True, self.template_name, export_domain, exclusive=exclusive, wait=True
    ), "Failed to export template %s into export domain %s" % (
        self.template_name, export_domain
    )


@pytest.fixture()
def remove_templates(request):
    """
    Remove templates
    """
    self = request.node.cls

    def finalizer():
        for template in self.templates_names:
            if ll_templates.check_template_existence(template):
                testflow.teardown("Remove template %s", template)
                assert ll_templates.removeTemplate(True, template), (
                    "Failed to remove template %s" % template
                )

    request.addfinalizer(finalizer)
    if not hasattr(self, 'templates_names'):
        self.templates_names = list()


@pytest.fixture()
def clone_vm_from_template(request):
    """
    Clone VM from template
    """
    self = request.node.cls

    self.vm_from_template = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    )
    testflow.setup(
        "Clone VM %s from template %s", self.vm_from_template,
        self.template_name
    )
    assert ll_vms.cloneVmFromTemplate(
        positive=True, name=self.vm_from_template, template=self.template_name,
        cluster=config.CLUSTER_NAME, vol_sparse=True,
        vol_format=config.COW_DISK
    ), "Failed to clone VM %s from template %s" % (
        self.vm_from_template, self.template_name
    )


@pytest.fixture()
def create_export_domain(request):
    """
    Create and attach export domain
    """

    self = request.node.cls

    self.export_domain = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_SD
    )
    self.spm = getattr(self, 'spm', ll_hosts.getSPMHost(config.HOSTS))

    assert ll_sd.addStorageDomain(
        True, name=self.export_domain, host=self.spm, type=config.EXPORT_TYPE,
        **self.storage_domain_kwargs
    ), "Unable to add export domain %s" % self.export_domain

    assert ll_sd.attachStorageDomain(
        True, config.DATA_CENTER_NAME, self.export_domain
    ), "Unable to attach export domain %s to data center" % (
        self.export_domain
    )


@pytest.fixture()
def remove_export_domain(request):
    """
    Remove export domain
    """
    self = request.node.cls

    def finalizer():
        if ll_sd.checkIfStorageDomainExist(True, self.export_domain):
            testflow.teardown("Remove export domain %s", self.export_domain)
            assert hl_sd.remove_storage_domain(
                self.export_domain, config.DATA_CENTER_NAME, self.spm, True
            ), "Failed to remove export domain %s" % self.export_domain
    request.addfinalizer(finalizer)
