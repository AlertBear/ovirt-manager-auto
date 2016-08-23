import shlex
import pytest
import os
import logging

import config
from art.core_api.apis_exceptions import APITimeout
from art.test_handler import exceptions
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    storagedomains as hl_sd,
    hosts as hl_hosts,
    vmpools as hl_vmpools,
)
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    vms as ll_vms,
    storagedomains as ll_sd,
    templates as ll_templates,
    jobs as ll_jobs,
)
from art.rhevm_api.resources import storage as storage_resource
from art.rhevm_api.utils import test_utils
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
def create_vm(request, storage, remove_vm):
    """
    Create VM and initialize parameters
    """
    self = request.node.cls

    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
    if hasattr(self, 'vm_name'):
        if self.vm_name is None:
            self.vm_name = storage_helpers.create_unique_object_name(
                self.__name__, config.OBJECT_TYPE_VM
            )
    else:
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
    cluster = getattr(self, 'cluster_name', config.CLUSTER_NAME)
    clone = getattr(self, 'deep_copy', False)
    clone_from_template = getattr(self, 'clone_from_template', True)
    template_name = getattr(self, 'template_name', None)
    self.installation = getattr(self, 'installation', True)
    volume_format = getattr(self, 'volume_format', config.DISK_FORMAT_COW)
    volume_type = getattr(self, 'volume_type', True)

    diskless_vm = getattr(self, 'diskless_vm', False)

    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = None if diskless_vm else self.storage_domain
    vm_args['cluster'] = cluster
    vm_args['vmName'] = self.vm_name
    vm_args['installation'] = self.installation
    vm_args['deep_copy'] = clone
    vm_args['clone_from_template'] = clone_from_template
    vm_args['template_name'] = template_name
    vm_args['volumeFormat'] = volume_format
    vm_args['volumeType'] = volume_type

    if hasattr(self, 'vm_args'):
        vm_args.update(self.vm_args)
    testflow.setup("Creating VM %s", self.vm_name)
    assert storage_helpers.create_vm_or_clone(**vm_args), (
        "Failed to create VM %s" % self.vm_name
    )


@pytest.fixture()
def add_disk_permutations(request, storage):
    """
    Creating all possible combinations of disks for test
    """
    self = request.node.cls

    self.shared = getattr(self, 'shared', None)
    disks_size = getattr(self, 'disks_size', config.DISK_SIZE)
    self.polarion_test_case = getattr(self, 'polarion_test_case', 'Test')
    testflow.setup("Creating all disk permutations")
    self.disks = storage_helpers.start_creating_disks_for_test(
        shared=self.shared, sd_name=self.storage_domain, disk_size=disks_size,
        interfaces=storage_helpers.INTERFACES
    )
    self.disk_names = [disk['disk_name'] for disk in self.disks]
    assert ll_disks.wait_for_disks_status(self.disk_names), (
        "At least one of the disks %s was not in the expected state 'OK"
        % self.disk_names
    )


@pytest.fixture()
def attach_and_activate_disks(request, storage):
    """
    Attach and activate disks to a VM
    """
    self = request.node.cls

    read_only = getattr(self, 'read_only', False)
    storage_helpers.prepare_disks_for_vm(
        self.vm_name, self.disk_names, read_only
    )


@pytest.fixture(scope='class')
def remove_vm(request, storage):
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
def start_vm(request, storage):
    """
    Start VM (on a specific host if has requested)
    """
    self = request.node.cls

    host = None
    wait_for_ip = getattr(self, 'vm_wait_for_ip', False)
    if hasattr(self, 'vm_run_on_spm'):
        run_on_spm = getattr(self, 'vm_run_on_spm', None)
        if run_on_spm:
            host = ll_hosts.get_spm_host(config.HOSTS)
        else:
            host = ll_hosts.get_hsm_host(config.HOSTS)
    if host is not None:
        testflow.setup("Starting VM %s", self.vm_name)
        assert ll_vms.runVmOnce(True, self.vm_name, config.VM_UP, host=host), (
            "Failed to start VM %s" % self.vm_name
        )
    else:
        testflow.setup("Starting VM %s", self.vm_name)
        assert ll_vms.startVm(True, self.vm_name, config.VM_UP, wait_for_ip), (
            "Failed to start VM %s" % self.vm_name
        )
    if hasattr(self, 'get_vm_ip'):
        self.vm_ip = storage_helpers.get_vm_ip(self.vm_name)


@pytest.fixture(scope='class')
def add_disk(request, storage):
    """
    Add disk and initialize parameters
    """
    self = request.node.cls

    disk_params = config.disk_args.copy()
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage
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
def delete_disk(request, storage):
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
        else:
            logger.error("Disk does not exists")
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def attach_disk(request, storage):
    """
    Attach a disk to VM
    """
    self = request.node.cls

    attach_kwargs = config.attach_disk_params.copy()
    if hasattr(self, 'update_attach_params'):
        attach_kwargs.update(self.update_attach_params)

    attach_to_vm = getattr(self, 'vm_to_attach_disk', self.vm_name)

    testflow.setup("Attach disk %s to VM %s", self.disk_name, attach_to_vm)
    assert ll_disks.attachDisk(
        True, alias=self.disk_name, vm_name=attach_to_vm, **attach_kwargs
    ), ("Failed to attach disk %s to VM %s" % (self.disk_name, attach_to_vm))
    ll_disks.wait_for_disks_status([self.disk_name])


@pytest.fixture(scope='class')
def update_vm(request, storage):
    """
    Update VM
    """
    self = request.node.cls

    if not ll_vms.updateVm(True, self.vm_name, **self.update_vm_params):
        assert "Failed to update vm %s with params %s" % (
            self.disk_name, self.update_vm_params
        )


@pytest.fixture(scope='class')
def create_snapshot(request, storage):
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
def preview_snapshot(request, storage):
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
def undo_snapshot(request, storage):
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
def delete_disks(request, storage):
    """
    Delete disks
    """
    self = request.node.cls

    def finalizer():
        if self.disks_to_remove:
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
        self.disks_to_remove = list()
    request.addfinalizer(finalizer)
    if not hasattr(self, 'disk_name'):
        self.disk_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_DISK
        )
    if not hasattr(self, 'disks_to_remove'):
        self.disks_to_remove = list()


@pytest.fixture()
def poweroff_vm(request, storage):
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
def poweroff_vm_setup(request, storage):
    """
    Power off VM
    """
    self = request.node.cls

    testflow.setup("Power off VM %s", self.vm_name)
    assert ll_vms.stop_vms_safely([self.vm_name]), (
        "Failed to power off VM %s" % self.vm_name
    )


@pytest.fixture(scope='class')
def create_template(request, storage):
    """
    Create a template from GE VM
    """
    self = request.node.cls

    def finalizer():
        if ll_templates.check_template_existence(self.template_name):
            testflow.teardown("Remove template %s", self.template_name)
            assert ll_templates.remove_template(True, self.template_name), (
                "Failed to remove template %s" % self.template_name
            )
    request.addfinalizer(finalizer)
    if not hasattr(self, 'template_name'):
        self.template_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_TEMPLATE
        )
    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage
        )[0]
    base_vm_for_snapshot = getattr(self, 'vm_name', config.VM_NAME[0])
    testflow.setup("Creating template %s", self.template_name)
    assert ll_templates.createTemplate(
        True, vm=base_vm_for_snapshot, name=self.template_name,
        cluster=config.CLUSTER_NAME, storagedomain=self.storage_domain
    ), (
        "Failed to create template %s from VM %s" % (
            self.template_name, base_vm_for_snapshot
        )
    )


@pytest.fixture(scope='class')
def remove_template(request, storage):
    """
    Remove a template
    """
    self = request.node.cls

    def finalizer():
        if ll_templates.check_template_existence(self.template_name):
            testflow.teardown("Remove template %s", self.template_name)
            assert ll_templates.remove_template(True, self.template_name), (
                "Failed to remove template %s" % self.template_name
            )
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_TEMPLATE])
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def initialize_storage_domains(request, storage):
    """
    Initialize storage domain parameters
    """
    self = request.node.cls

    self.storage_domains = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, storage
    )
    self.storage_domain = self.storage_domains[0]
    self.storage_domain_1 = self.storage_domains[1]
    self.storage_domain_2 = self.storage_domains[2]


@pytest.fixture()
def deactivate_domain(request, storage):
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

    if hasattr(self, 'sd_to_deactivate_index'):
        self.sd_to_deactivate = self.storage_domains[
            self.sd_to_deactivate_index
        ]
    else:
        self.sd_to_deactivate = getattr(
            self, 'sd_to_deactivate', ll_sd.getStorageDomainNamesForType(
                config.DATA_CENTER_NAME, storage
            )[0]
        )

    test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
    testflow.setup(
        "Deactivating storage domain %s", self.sd_to_deactivate
    )
    assert ll_sd.deactivateStorageDomain(
        True, config.DATA_CENTER_NAME, self.sd_to_deactivate
    ), ("Failed to deactivate storage domain %s" % self.sd_to_deactivate)


@pytest.fixture(scope='class')
def create_storage_domain(request, storage):
    """
    Create new storage domain
    """
    self = request.node.cls

    def finalizer():
        """
        Remove added storage domain
        """
        if getattr(self, 'new_dc_name', False):
            return
        testflow.teardown(
            "Remove storage domain %s", self.new_storage_domain
        )
        spm = hl_dc.get_spm_host(positive=True, datacenter=self.datacenter)
        assert spm, ("Failed to find SPM on data center %s" % self.datacenter)
        assert hl_sd.remove_storage_domain(
            self.new_storage_domain, self.datacenter,
            spm.get_name(), engine=config.ENGINE, format_disk=True
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
    self.datacenter = getattr(self, 'new_dc_name', config.DATA_CENTER_NAME)
    testflow.setup(
        "Create new storage domain %s", self.new_storage_domain
    )
    domain_kwargs = getattr(self, 'create_domain_kwargs', dict())
    storage_helpers.add_storage_domain(
        self.new_storage_domain, self.datacenter, self.index, storage,
        **domain_kwargs
    )


@pytest.fixture(scope='class')
def remove_storage_domain(request, storage):
    """
    Remove storage domain
    """
    self = request.node.cls

    def finalizer():
        self.spm = getattr(self, 'spm', ll_hosts.get_spm_host(config.HOSTS))
        if ll_sd.checkIfStorageDomainExist(True, self.storage_domain):
            testflow.teardown("Remove storage domain %s", self.storage_domain)
            assert hl_sd.remove_storage_domain(
                self.storage_domain, config.DATA_CENTER_NAME,
                host=self.spm, engine=config.ENGINE, format_disk=True
            ), ("Failed to remove storage domain %s", self.storage_domain)
    request.addfinalizer(finalizer)
    self.storage_domain = None


@pytest.fixture(scope='class')
def remove_vms(request, storage):
    """
    Remove VM
    """
    self = request.node.cls

    def finalizer():
        """
        Remove VMs created during the test
        """
        testflow.teardown("Remove VMs %s", ', '.join(self.vm_names))
        assert ll_vms.safely_remove_vms(self.vm_names), (
            "Failed to remove VM from %s" % self.vm_names
        )
    request.addfinalizer(finalizer)
    if not hasattr(self, 'vm_names'):
        self.vm_names = list()


@pytest.fixture()
def clean_export_domain(request, storage):
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
def set_spm_priorities(request, storage):
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
            result_list.append(ll_hosts.set_spm_priority(True, host, priority))
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
        if not ll_hosts.set_spm_priority(True, host, priority):
            raise exceptions.HostException(
                'Unable to set host %s priority' % host
            )
    ll_hosts.wait_for_spm(config.DATA_CENTER_NAME)
    self.spm_host = getattr(
        self, 'spm_host', ll_hosts.get_spm_host(config.HOSTS)
    )
    if not hasattr(self, 'hsm_hosts'):
        self.hsm_hosts = [
            host for host in config.HOSTS if host != self.spm_host
        ]
    testflow.setup("Ensuring SPM priority is for all hosts")
    for host, priority in zip(config.HOSTS, self.spm_priorities):
        if not ll_hosts.check_spm_priority(True, host, str(priority)):
            raise exceptions.HostException(
                'Unable to check host %s priority' % host
            )


@pytest.fixture()
def init_master_domain_params(request, storage):
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
def create_dc(request, storage):
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
        self, 'host_name', ll_hosts.get_hsm_host(config.HOSTS)
    )
    testflow.setup(
        "Create data-center %s with cluster %s and host %s", self.new_dc_name,
        self.cluster_name, self.host_name
    )

    storage_helpers.create_data_center(
        self.new_dc_name, self.cluster_name, self.host_name, self.dc_version
    )


@pytest.fixture(scope='class')
def clean_dc(request, storage):
    """
    Remove data-center from the the environment
    """
    self = request.node.cls

    def finalizer():
        master_domain = None
        new_storage_domain = getattr(self, 'new_storage_domain', False)
        new_dc_name = getattr(self, 'new_dc_name', config.DATA_CENTER_NAME)
        if new_storage_domain:
            master_domain = new_storage_domain
        else:
            master_domain = getattr(
                self, 'master_domain', config.MASTER_DOMAIN
            )
            found, storage_domain = ll_sd.findMasterStorageDomain(
                True, self.new_dc_name
            )
            if found:
                master_domain = storage_domain['masterDomain']

        testflow.teardown(
            "Clean data-center %s and remove it", self.new_dc_name
        )
        storage_helpers.clean_dc(
            self.new_dc_name, self.cluster_name, self.host_name,
            sd_name=master_domain
        )
        if new_storage_domain:
            testflow.teardown(
                "Removing storage domain %s", self.storage_domain
            )
            test_utils.wait_for_tasks(config.ENGINE, new_dc_name)
            assert ll_sd.removeStorageDomain(
                True, master_domain, self.host_name, format='true',
            )
    request.addfinalizer(finalizer)


@pytest.fixture()
def clean_mount_point(request, storage):
    """
    Clean storage domain mount point
    """

    def finalizer():

        spm_host = ll_hosts.get_spm_host(config.HOSTS)

        if storage == NFS or storage == POSIX:
            assert storage_resource.clean_mount_point(
                spm_host, config.NFS_DOMAINS_KWARGS[0]['address'],
                config.NFS_DOMAINS_KWARGS[0]['path'],
                rhevm_helpers.NFS_MNT_OPTS
            ), "Failed to clean mount point address %s, path %s" % (
                config.NFS_DOMAINS_KWARGS[0]['address'],
                config.NFS_DOMAINS_KWARGS[0]['path'],
            )
        elif storage == GLUSTER:
            assert storage_resource.clean_mount_point(
                spm_host, config.GLUSTER_DOMAINS_KWARGS[0]['address'],
                config.GLUSTER_DOMAINS_KWARGS[0]['path'],
                rhevm_helpers.GLUSTER_MNT_OPTS
            ), "Failed to clean mount point address %s, path %s" % (
                config.GLUSTER_DOMAINS_KWARGS[0]['address'],
                config.GLUSTER_DOMAINS_KWARGS[0]['path'],
            )
    request.addfinalizer(finalizer)


@pytest.fixture()
def remove_vm_from_export_domain(request, storage):
    """
    Remove VM from export domain
    """
    self = request.node.cls

    def finalizer():
        export_domain = getattr(
            self, 'export_domain', config.EXPORT_DOMAIN_NAME
        )

        testflow.teardown(
            "Removing VM %s from export domain %s", self.vm_name,
            export_domain
        )
        assert ll_vms.remove_vm_from_export_domain(
            positive=True, vm=self.vm_name, datacenter=config.DATA_CENTER_NAME,
            export_storagedomain=export_domain
        ), "Failed to remove VM %s from export domain %s" % (
            self.vm_name, export_domain
        )

    request.addfinalizer(finalizer)


@pytest.fixture()
def remove_template_from_export_domain(request, storage):
    """
    Remove template from export domain
    """
    self = request.node.cls

    def finalizer():
        export_domain = getattr(
            self, 'export_domain', config.EXPORT_DOMAIN_NAME
        )

        testflow.teardown(
            "Remove template %s from export domain %s",
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
def seal_vm(request, storage):
    """
    Seal VM
    """
    self = request.node.cls

    assert network_helper.seal_vm(self.vm_name, config.VM_PASSWORD), (
        "Failed to set a persistent network for VM '%s'" % self.vm_name
    )


@pytest.fixture()
def export_vm(request, storage):
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
def create_fs_on_disk(request, storage):
    """
    Creates a filesystem on a disk and mounts it in the vm
    """
    self = request.node.cls

    out, self.mount_point = storage_helpers.create_fs_on_disk(
        self.vm_name, self.disk_name
    )
    assert out, (
        "Unable to create a filesystem on disk: %s of VM %s" % (
            self.disk_name, self.vm_name
        )
    )


@pytest.fixture(scope='class')
def prepare_disks_with_fs_for_vm(request, storage):
    """
    Prepare disks with filesystem for vm
    """
    self = request.node.cls

    testflow.setup(
        "Creating disks with filesystem and attach to VM %s", self.vm_name,
    )
    disks, mount_points = storage_helpers.prepare_disks_with_fs_for_vm(
        self.storage_domain, self.vm_name,
        executor=getattr(self, 'vm_executor', None)
    )
    self.disks_to_remove = disks
    config.MOUNT_POINTS = mount_points


@pytest.fixture()
def wait_for_disks_and_snapshots(request, storage):
    """
    Wait for given VMs snapshots and disks status
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown(
            "Wait for VMs %s Disks and snapshots to be in 'OK' status",
            self.vms_to_wait
        )
        for vm_name in self.vms_to_wait:
            if ll_vms.does_vm_exist(vm_name):
                try:
                    disks = [d.get_id() for d in ll_vms.getVmDisks(vm_name)]
                    ll_disks.wait_for_disks_status(disks, key='id')
                    ll_vms.wait_for_vm_snapshots(vm_name, config.SNAPSHOT_OK)
                except APITimeout:
                    assert False, (
                        "Snapshots failed to reach OK state on VM '%s'" %
                        vm_name
                    )
            ll_jobs.wait_for_jobs([config.JOB_LIVE_MIGRATE_DISK])
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
    request.addfinalizer(finalizer)

    self.vms_to_wait = getattr(self, 'vms_to_wait', [self.vm_name])


@pytest.fixture()
def unblock_connectivity_storage_domain_teardown(request, storage):
    """
    Unblock connectivity from host to storage domain
    """
    self = request.node.cls

    def finalizer():
        assert storage_helpers.unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.storage_domain_ip
        ), "Failed to block connection from %s to %s" % (
            self.host_ip, self.storage_domain_ip
        )

    request.addfinalizer(finalizer)


@pytest.fixture()
def initialize_variables_block_domain(request, storage):
    """
    Initialize variables for blocking connection from the SPM to a
    storage domain
    """
    self = request.node.cls

    spm_host = getattr(self, 'block_spm_host', True)
    self.host = getattr(self, 'host', None)

    if self.host is None:
        self.host = ll_hosts.get_spm_host(config.HOSTS) if spm_host else (
            ll_hosts.get_hsm_host(config.HOSTS)
        )
    self.host_ip = ll_hosts.get_host_ip(self.host)
    found, address = ll_sd.getDomainAddress(True, self.storage_domain)
    assert found, "IP for storage domain %s not found" % self.storage_domain
    self.storage_domain_ip = address['address']


@pytest.fixture()
def add_nic(request, storage):
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
def export_template(request, storage):
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


@pytest.fixture(scope='class')
def remove_templates(request, storage):
    """
    Remove templates
    """
    self = request.node.cls

    def finalizer():
        for template in self.templates_names:
            if ll_templates.check_template_existence(template):
                testflow.teardown("Remove template %s", template)
                assert ll_templates.remove_template(True, template), (
                    "Failed to remove template %s" % template
                )

    request.addfinalizer(finalizer)
    if not hasattr(self, 'templates_names'):
        self.templates_names = list()


@pytest.fixture()
def clone_vm_from_template(request, storage):
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
def create_export_domain(request, storage):
    """
    Create and attach export domain
    """

    self = request.node.cls

    self.export_domain = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_SD
    )
    self.spm = getattr(self, 'spm', ll_hosts.get_spm_host(config.HOSTS))
    testflow.setup("Creating export domain %s", self.export_domain)
    assert ll_sd.addStorageDomain(
        True, name=self.export_domain, host=self.spm, type=config.EXPORT_TYPE,
        **self.storage_domain_kwargs
    ), "Unable to add export domain %s" % self.export_domain

    data_center = getattr(self, 'new_dc_name', config.DATA_CENTER_NAME)
    assert ll_sd.attachStorageDomain(
        True, data_center, self.export_domain
    ), "Unable to attach export domain %s to data center" % (
        self.export_domain
    )


@pytest.fixture(scope='class')
def remove_export_domain(request, storage):
    """
    Remove export domain
    """
    self = request.node.cls

    def finalizer():
        if ll_sd.checkIfStorageDomainExist(True, self.export_domain):
            testflow.teardown("Remove export domain %s", self.export_domain)
            data_center_id = ll_sd.get_storage_domain_obj(
                self.export_domain
            ).get_data_centers().get_data_center()[0].get_id()
            data_center_name = ll_dc.get_data_center(
                data_center_id, 'id'
            ).get_name()
            test_utils.wait_for_tasks(config.ENGINE, data_center_name)
            assert hl_sd.remove_storage_domain(
                self.export_domain, data_center_name, self.spm,
                engine=config.ENGINE, format_disk=True
            ), "Failed to remove export domain %s" % self.export_domain
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def remove_glance_image(request, storage):
    """
    Removes Glance image
    """
    self = request.node.cls

    def finalizer():
        image_found = False
        for image in ll_sd.get_storage_domain_images(config.GLANCE_DOMAIN):
            if self.disk.get_alias() == image.get_name():
                image_found = True
                assert ll_sd.remove_glance_image(
                    image.get_id(), config.GLANCE_HOSTNAME,
                    config.HOSTS_USER, config.HOSTS_PW
                ), "Failed to remove glance image %s" % self.disk.get_alias()
        assert image_found, (
            "Failed to find image %s in glance image repository %s" % (
                self.disk.get_alias(), self.glance_domain
            )
        )
        request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def move_host_to_another_cluster(request, storage):
    """
    Move host to another cluster
    """
    self = request.node.cls

    testflow.setup(
        "Move host %s into the newly created cluster", self.host_name
    )
    assert hl_hosts.move_host_to_another_cluster(
        self.host_name, self.cluster_name
    ), (
        "Could not move host '%s' into cluster '%s'" % (
            self.host_name, self.cluster_name
        )
    )


@pytest.fixture()
def update_vm_disk(request, storage):
    """
    Update VM disk
    """
    self = request.node.cls

    disk = self.disk_name if getattr(self, 'disk_name', None) else (
        getattr(self, 'disk_id', None)
    )
    disk_kwargs = getattr(self, 'disk_kwargs', None)
    testflow.setup("Update disk %s", disk)
    assert ll_disks.updateDisk(True, **disk_kwargs), (
        "Failed to update disk %s" % disk
    )


@pytest.fixture()
def restart_vdsmd(request, storage):
    """
    Restart VDSM
    """
    self = request.node.cls

    def finalizer():
        host = getattr(
            self, 'restart_vdsmd_host', ll_hosts.get_spm_host(config.HOSTS)
        )
        host_ip = ll_hosts.get_host_ip(host)
        testflow.teardown("Restart vdsmd on host %s", host)
        assert test_utils.restartVdsmd(host_ip, config.HOSTS_PW), (
            "Failed to restart VDSM on host %s" % host
        )
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.WAIT_FOR_SPM_INTERVAL
        ), "SPM host was not elected in data-center %s" % (
            config.DATA_CENTER_NAME
        )
        assert ll_hosts.wait_for_hosts_states(True, host), (
            "Host %s failed to reach status UP" % host
        )
    request.addfinalizer(finalizer)


@pytest.fixture()
def create_second_vm(request, storage):
    """
    Create second VM and initialize parameters
    """
    self = request.node.cls

    def finalizer():
        """
        Remove the second VM
        """
        testflow.teardown("Remove VM %s", self.vm_name_2)
        assert ll_vms.safely_remove_vms([self.vm_name_2]), (
            "Failed to power off and remove VM %s" % self.vm_name_2
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
    request.addfinalizer(finalizer)

    self.vm_name_2 = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    vm_args = config.create_vm_args.copy()
    vm_args['storageDomainName'] = self.storage_domain
    vm_args['vmName'] = self.vm_name_2
    testflow.setup("Creating VM %s", self.vm_name_2)
    assert storage_helpers.create_vm_or_clone(**vm_args), (
        "Failed to create VM %s" % self.vm_name_2
    )


@pytest.fixture(scope='class')
def init_host_or_engine_executor(request, storage):
    """
    Initialize executor later used for commands executions in the host or
    engine
    """
    self = request.node.cls

    executor_type = getattr(self, 'executor_type', 'host')
    self.executor = rhevm_helpers.get_host_executor(
        config.VDC, config.VDC_PASSWORD
    ) if executor_type is 'engine' else (
        rhevm_helpers.get_host_executor(self.host_ip, config.HOSTS_PW)
    )


@pytest.fixture(scope='class')
def init_host_resource(request, storage):
    """
    Initialize Host resource
    """
    self = request.node.cls

    self.host_resource = rhevm_helpers.get_host_resource(
        self.host_ip, config.HOSTS_PW
    )


@pytest.fixture(scope='class')
def init_vm_executor(request, storage):
    """
    Initialize VM executor later used for commands executions in the VM
    """
    self = request.node.cls

    self.vm_executor = storage_helpers.get_vm_executor(self.vm_name)


@pytest.fixture(scope='class')
def create_several_snapshots(request, storage):
    """
    Create several snapshot of VM
    """
    self = request.node.cls

    self.snapshot_list = []

    for snap in range(self.snap_count):

        snapshot_description = getattr(
            self, 'snapshot_description',
            storage_helpers.create_unique_object_name(
                self.__name__, config.OBJECT_TYPE_SNAPSHOT
            ) + '%s' % snap
        )
        testflow.setup(
            "Creating snapshot %s of VM %s",
            snapshot_description, self.vm_name
        )
        assert ll_vms.addSnapshot(
            True, self.vm_name, snapshot_description
        ), "Failed to create snapshot of VM %s" % self.vm_name
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], snapshot_description
        )
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])

        self.snapshot_list.append(snapshot_description)


@pytest.fixture(scope='class')
def import_image_from_glance(request, storage):
    """
    Import image from glance as template to new created domain
    """
    self = request.node.cls

    self.glance_template_name = getattr(
        self, 'glance_template_name',
        storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_TEMPLATE
        )
    )

    storage_domain = getattr(
        self, 'new_storage_domain', self.storage_domain
    )

    self.disk_alias = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DISK
    )

    import_as_template = getattr(self, 'import_as_template', True)
    cluster = getattr(self, 'cluster_name', config.CLUSTER_NAME)
    glance_image = getattr(self, 'image_name', config.GOLDEN_GLANCE_IMAGE)

    assert ll_sd.import_glance_image(
        config.GLANCE_DOMAIN, glance_image,
        target_storage_domain=storage_domain, target_cluster=cluster,
        new_disk_alias=self.disk_alias,
        new_template_name=self.glance_template_name,
        import_as_template=import_as_template, async=False
    ), """Importing glance image %s from repository %s to storage
       domain %s failed""" % (
        storage_domain, config.GOLDEN_GLANCE_IMAGE, config.GLANCE_DOMAIN
    )

    ll_jobs.wait_for_jobs([config.JOB_IMPORT_IMAGE])
    # initialize for remove_templates fixture
    self.templates_names.append(self.glance_template_name)


@pytest.fixture(scope='class')
def remove_hsm_host(request, storage):
    """
    Remove an hsm from the base data center and add it back
    """
    self = request.node.cls

    def finalizer():
        if self.hsm_host not in ll_hosts.get_host_names_list():
            testflow.teardown("Adding host %s back", self.hsm_host)
            assert ll_hosts.add_host(
                name=self.hsm_host, address=self.hsm_host_vds.fqdn,
                wait=True, cluster=config.CLUSTER_NAME,
                root_password=config.VDC_ROOT_PASSWORD,
                comment=self.hsm_host_vds.ip
            )

    request.addfinalizer(finalizer)
    self.hsm_host = ll_hosts.get_hsm_host(config.HOSTS)
    self.hsm_host_vds = config.VDS_HOSTS[config.HOSTS.index(self.hsm_host)]
    testflow.setup("Removing host %s from the env", self.hsm_host)
    assert ll_hosts.remove_host(True, self.hsm_host, deactivate=True)


@pytest.fixture(scope='class')
def copy_template_disk(request, storage):
    """
    Copy template disk to another storage domain
    """
    self = request.node.cls

    testflow.setup(
        "Copying template %s disks to storage domain %s",
        self.template, self.new_storage_domain
    )
    template_disks_objs = ll_templates.getTemplateDisks(self.template)
    template_disks = [disk.get_alias() for disk in template_disks_objs]
    assert template_disks, "Failed to get disks of template %s" % self.template
    for disk in template_disks:
        ll_templates.copyTemplateDisk(
            self.template, disk, self.new_storage_domain
        )
        ll_disks.wait_for_disks_status(
            disk, timeout=ll_templates.CREATE_TEMPLATE_TIMEOUT
        )


@pytest.fixture(scope='class')
def skip_invalid_storage_type(request, storage):
    """
    Skip the test case if the storage type is not valid for it
    """
    self = request.node.cls

    if storage not in self.storages:
        pytest.skip(
            "Storage type %s is not valid for testing this case" % storage
        )


@pytest.fixture()
def create_disks_with_fs(request, storage):
    """
    Create disks from all permutation and create filesystem on them,
    saves all the needed data in dict object with vm_name as keys
    and the value is dict (with keys: disks, mount_points, executor)
    """
    self = request.node.cls

    add_file_on_each_disk = getattr(self, 'add_file_on_each_disk', False)

    self.DISKS_MOUNTS_EXECUTOR = getattr(
        self, 'DISKS_MOUNTS_EXECUTOR', config.DISKS_MOUNTS_EXECUTOR.copy()
    )
    self.CHECKSUM_FILES_RESULTS = getattr(
        self, 'CHECKSUM_FILES_RESULTS', config.CHECKSUM_FILES.copy()
    )

    # verify storage value will not override in case of create few VMs
    if storage not in self.CHECKSUM_FILES_RESULTS.keys():
        self.CHECKSUM_FILES_RESULTS[storage] = dict()

    self.DISKS_MOUNTS_EXECUTOR[self.vm_name] = dict()

    storage_domain = getattr(self, 'new_storage_domain', self.storage_domain)

    started = False
    if ll_vms.get_vm_state(self.vm_name) == config.VM_DOWN:
        testflow.setup("Start VM %s", self.vm_name)
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name, wait_for_status=config.VM_UP
        )
        started = True

    testflow.setup("Fetch VM %s executor", self.vm_name)
    executor = storage_helpers.get_vm_executor(self.vm_name)

    testflow.setup("Create disks with filesystem on VM %s", self.vm_name)
    disk_ids, mount_points = (
        storage_helpers.prepare_disks_with_fs_for_vm(
            storage_domain, self.vm_name, executor=executor
        )
    )
    self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['disks'] = disk_ids
    self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['mount_points'] = mount_points
    self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['executor'] = executor

    if add_file_on_each_disk:
        file_name = getattr(self, 'file_name', 'test_file')
        testflow.setup("Create file on all the VM's %s disks", self.vm_name)
        for mount_point in mount_points:
            assert storage_helpers.create_file_on_vm(
                self.vm_name, file_name, mount_point, executor
            ), "Failed to create file %s on VM %s with path %s" % (
                file_name, self.vm_name, mount_point
            )
            full_path = os.path.join(mount_point, file_name)
            assert storage_helpers.write_content_to_file(
                vm_name=self.vm_name, file_name=full_path, vm_executor=executor
            ), "Failed to write content to file %s on VM %s" % (
                full_path, self.vm_name
            )
            testflow.setup("Save file %s checksum value", full_path)
            self.CHECKSUM_FILES_RESULTS[storage][full_path] = (
                storage_helpers.checksum_file(
                    self.vm_name, full_path, executor
                )
            )
        # verify the data will write to the backend
        rc, _, error = executor.run_cmd(cmd=shlex.split('sync'))
        if rc:
            logger.error(
                "Failed to run command 'sync' on %s, error: %s",
                self.vm_name, error
            )
    if started:
        testflow.setup("Stop VM %s", self.vm_name)
        assert ll_vms.stop_vms_safely([self.vm_name])


@pytest.fixture()
def create_vms(request, storage):
    """
    Add number of VMs to the environment according to num_on_vms attribute
    """
    self = request.node.cls

    if not hasattr(self, 'storage_domain'):
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

    num_of_vms = getattr(self, 'num_of_vms', 2)

    for index in range(num_of_vms):
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        create_vm(request, storage, remove_vm)
        self.vm_names.append(self.vm_name)


@pytest.fixture(scope="class")
def storage_cleanup(request, storage):
    """
    Clean up all storage domains which are not in GE yaml and direct LUNs
    """
    def finalizer():
        rhevm_helpers.storage_cleanup()
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def extend_storage_domain(request, storage):
    """
    Extend a block based storage domain
    """
    self = request.node.cls

    extend_indices = getattr(self, 'extend_indices', [1])
    self.domain_size = ll_sd.get_total_size(
        storagedomain=self.new_storage_domain,
        data_center=config.DATA_CENTER_NAME
    )
    testflow.setup(
        "Extending storage domain %s, current size is %s",
        self.new_storage_domain, self.domain_size
    )
    self.extension_luns = storage_helpers.extend_storage_domain(
        storage_domain=self.new_storage_domain, extend_indices=extend_indices
    )


@pytest.fixture()
def create_file_than_snapshot_several_times(request, storage):
    """
    Create file ,take checksum & than snapshot several times
    """

    self = request.node.cls

    self.snapshots_descriptions_list = list()

    out, self.mount_path = storage_helpers.create_fs_on_disk(
        self.vm_name, self.disk_name
    )

    assert out, (
        "Unable to create a filesystem on disk: %s of VM %s" %
        (self.disk_name, self.vm_name)
    )

    write_to_file_than_snapshot_number_of_times = getattr(
        self, 'write_to_file_than_snapshot_number_of_times', 1
    )
    self.vm_executor = getattr(
        self, 'vm_executor', storage_helpers.get_vm_executor(self.vm_name)
    )
    for time in range(write_to_file_than_snapshot_number_of_times):
        file_name = config.FILE_NAME + str(time)
        full_path = os.path.join(self.mount_path, file_name)

        storage_helpers.create_test_file_and_check_existance(
            self.vm_name, self.mount_path, file_name, self.vm_executor
        )

        checksum_file = storage_helpers.checksum_file(
            self.vm_name, full_path, vm_executor=self.vm_executor
        )
        self.checksum_file_list.append(checksum_file)
        self.full_path_list.append(full_path)

        self.snapshot_description = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        ) + str(time)
        testflow.setup(
            "Creating snapshot %s of VM %s",
            self.snapshot_description, self.vm_name
        )
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_description
        ), "Failed to create snapshot of VM %s" % self.vm_name
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, [config.SNAPSHOT_OK], self.snapshot_description
        )
        ll_jobs.wait_for_jobs([config.JOB_CREATE_SNAPSHOT])
        self.snapshots_descriptions_list.append(self.snapshot_description)


@pytest.fixture(scope='class')
def detach_disks(request, storage):
    """
    Detach disks from VM before removing them
    """

    self = request.node.cls

    def finalizer():
        for disk in self.disk_names:
            ll_disks.detachDisk(True, disk, self.vm_name)
            self.disks_to_remove.append(disk)

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def delete_snapshot(request, storage):
    """
    Delete the snapshot created in the test
    """

    self = request.node.cls

    def finalizer():
        testflow.teardown("Deleting snapshot %s", self.snapshot_description)
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshot_description
        ), "Failed to remove snapshot %s" % self.snapshot_description

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def deactivate_and_detach_export_domain(request, storage):
    """
    Deactivate and detach the export domain and add it back
    """
    def finalizer():
        testflow.teardown(
            "Attaching and activating export domain %s to data center %s",
            config.EXPORT_DOMAIN_NAME, config.DATA_CENTER_NAME
        )
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME
        )
    request.addfinalizer(finalizer)
    testflow.setup(
        "Deactivating and detaching export domain %s from data center %s",
        config.EXPORT_DOMAIN_NAME, config.DATA_CENTER_NAME
    )
    test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
    assert hl_sd.detach_and_deactivate_domain(
        config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME, config.ENGINE
    )


@pytest.fixture()
def copy_golden_template_disk(request, storage):
    """
    Copy golden environment template disk to another storage domain
    """

    self = request.node.cls

    golden_template_name = rhevm_helpers.get_golden_template_name(
        config.CLUSTER_NAME
    )
    template_disk_name = ll_templates.getTemplateDisks(
        golden_template_name
    )[0].get_name()

    sd_name = getattr(self, 'domain_to_copy_template', self.storage_domain)
    testflow.setup(
        "Copy template %s disk to storage domain %s",
        template_disk_name, sd_name
    )
    ll_templates.copyTemplateDisk(
        golden_template_name, template_disk_name, sd_name
    )
    ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])
    test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)


@pytest.fixture(scope='class')
def put_all_hsm_hosts_to_maintenance(request, storage):
    """
    Put all HSM hosts to maintenance
    """
    def finalizer():
        for host in non_spm:
            testflow.teardown("Activating Host %s", host)
            assert ll_hosts.activate_host(True, host), (
                "Failed to activate host %s" % host
            )
    request.addfinalizer(finalizer)

    non_spm = []

    for host, resource in zip(config.HOSTS, config.VDS_HOSTS):
        test_utils.wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
        if ll_hosts.check_host_spm_status(False, host):
            testflow.setup("Deactivating Host %s", host)
            assert hl_hosts.deactivate_host_if_up(host, resource), (
                "Failed to deactivate host %s" % host
            )
            non_spm.append(host)


@pytest.fixture(scope='class')
def remove_vms_pool(request, storage):
    """
    Detach and remove VMs pool
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Remove VMs pool: %s", self.pool_name)

        assert hl_vmpools.remove_whole_vm_pool(vmpool=self.pool_name), (
            "Failed to remove VMs pool %s" % self.vm_pool
        )

    request.addfinalizer(finalizer)
