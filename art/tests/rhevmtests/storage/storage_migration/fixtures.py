import pytest
import config
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
    jobs as ll_jobs,
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.utils import test_utils
from rhevmtests.storage.fixtures import create_disks_with_fs
import rhevmtests.storage.helpers as storage_helpers

DEFAULT_DISK_TIMEOUT = 180
STORAGE_DOMAIN_NUM_FOR_TYPE = 3


@pytest.fixture()
def initialize_params(request, storage):
    """
    Initialize parameters
    """
    self = request.node.cls

    self.vm_disk_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_DISK
    )


@pytest.fixture()
def add_disk(request, storage):
    """
    Create shareable disk
    """
    self = request.node.cls

    self.new_disk_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_DISK
    )
    shareable = getattr(self, 'shareable', False)
    large_disk = getattr(self, 'large_disk', False)

    disk_params = config.disk_args.copy()
    timeout = DEFAULT_DISK_TIMEOUT

    if shareable:
        disk_params['shareable'] = True
        disk_params['format'] = config.DISK_FORMAT_RAW
        disk_params['sparse'] = False
    if large_disk:
        disk_params['provisioned_size'] = (60 * config.GB)
        disk_params['format'] = config.DISK_FORMAT_RAW
        disk_params['sparse'] = False
        timeout = DEFAULT_DISK_TIMEOUT * 10

    disk_params['active'] = getattr(self, 'active', False)
    disk_params['wipe_after_delete'] = getattr(
        self, 'wipe_after_delete', False
    )

    disk_params['storagedomain'] = getattr(
        self, 'disk_storage_domains', self.storage_domains[0]
    )
    disk_params['alias'] = self.new_disk_name
    testflow.setup("Add disk %s", self.new_disk_name)
    assert ll_disks.addDisk(True, **disk_params), (
        "Can't create disk with params: %s" % disk_params
    )
    assert ll_disks.wait_for_disks_status(
        disk_params['alias'], timeout=timeout), (
        "Disk '%s' has not reached state 'OK'" % disk_params['alias']
    )

    # initialize for delete_disks fixture
    self.disks_to_remove.append(self.new_disk_name)


@pytest.fixture()
def attach_disk_to_vm(request, storage):
    """
    Attach disk to VM, if disk is shareable, attach it to another VM
    """
    self = request.node.cls

    shareable = getattr(self, 'shareable', False)
    active = getattr(self, 'active', True)
    testflow.setup(
        "Attach disk %s to VM %s", self.new_disk_name, self.vm_name
    )
    vms_to_attach = [self.vm_name, self.vm_name_2] if shareable else (
        [self.vm_name]
    )
    for vm in vms_to_attach:
        assert ll_disks.attachDisk(
            positive=True, alias=self.new_disk_name,
            vm_name=vm, active=active
        ), "Unable to attach disk %s to VM %s" % (self.new_disk_name, vm)


@pytest.fixture()
def initialize_domain_to_deactivate(request, storage):
    """
    Initialize storage domain to deactivate
    """
    self = request.node.cls

    self.vm_disk = ll_vms.getVmDisks(self.vm_name)[0]

    self.target_sd = ll_disks.get_other_storage_domain(
        self.vm_disk.get_alias(), self.vm_name,
        force_type=config.MIGRATE_SAME_TYPE
    )

    # Initialize for deactivate_domain fixture
    self.sd_to_deactivate = self.target_sd


@pytest.fixture()
def create_disks_for_vm(request, storage):
    """
    Prepares disks for given VM
    """
    self = request.node.cls

    self.disk_names = getattr(self, 'disk_names', list())
    create_on_same_domain = getattr(self, 'create_on_same_domain', False)
    disks_size = getattr(self, 'disks_size', config.DISK_SIZE)
    inactive_disk_index = getattr(self, 'inactive_disk_index', None)

    disk_params = config.disk_args.copy()
    disk_params['format'] = config.RAW_DISK
    disk_params['sparse'] = False
    disk_params['provisioned_size'] = disks_size

    for index in range(self.disk_count):
        disk_params['alias'] = (
            storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_DISK
            )
        )

        disk_params['storagedomain'] = (
            self.storage_domain if create_on_same_domain else
            self.storage_domains[index % STORAGE_DOMAIN_NUM_FOR_TYPE]
        )

        if index == inactive_disk_index:
            disk_params['active'] = False
        assert ll_disks.addDisk(True, **disk_params), (
            "Failed to create disk with params %s" % disk_params
        )
        ll_disks.wait_for_disks_status(disk_params['alias'])
        self.disk_names.append(disk_params['alias'])
        testflow.setup(
            "Add disk %s to VM %s", disk_params['alias'], self.vm_name
        )
        assert ll_disks.attachDisk(
            True, disk_params['alias'], self.vm_name, disk_params['active']
        )


@pytest.fixture()
def prepare_disks_for_vm(request, storage):
    """
    Attach disks to VM
    """
    self = request.node.cls

    config.DISK_NAMES[storage] = self.disk_names

    testflow.setup(
        "Add disks %s to VM %s", config.DISK_NAMES[storage], self.vm_name
    )
    disk_interfaces = [disk['disk_interface'] for disk in self.disks]
    assert storage_helpers.prepare_disks_for_vm(
        self.vm_name, config.DISK_NAMES[storage],
        interfaces=disk_interfaces
    ), "Failed to attach disks to VM %s" % self.vm_name


@pytest.fixture()
def initialize_vm_and_template_names(request, storage):
    """
    Create unique names for test
    """
    self = request.node.cls

    self.test_templates = [
        "{0}_{1}".format(
            storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
            )[:33], "single"
        ),
        "{0}_{1}".format(
            storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
            )[:35], "both"
        )
    ]
    self.vm_names = [
        "{0}_{1}".format(
            storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_VM
            ), "from_single"
        ),
        "{0}_{1}".format(
            storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_VM
            ), "from_both"
        )
    ]


@pytest.fixture()
def create_templates(request, storage):
    """
    Create two templates, first with one disk and the second with two disks on
    different storage domains
    """
    self = request.node.cls

    disks_objs = ll_disks.getObjDisks(self.vm_name, get_href=False)

    target_domain = ll_disks.get_disk_storage_domain_name(
        disks_objs[0].get_alias(), self.vm_name
    )

    testflow.setup(
        "Creating template %s from VM %s to storage domain %s",
        self.test_templates[0], self.vm_name, target_domain
    )
    assert ll_templates.createTemplate(
        True, True, vm=self.vm_name, name=self.test_templates[0],
        cluster=config.CLUSTER_NAME, storagedomain=target_domain,
    ), "Failed to create template '%s'" % self.test_templates[0]

    # initialize for remove_templates fixture
    self.templates_names.append(self.test_templates[0])

    self.second_domain = ll_disks.get_other_storage_domain(
        disk=disks_objs[0].get_id(), force_type=config.MIGRATE_SAME_TYPE,
        key='id'
    )
    target_domain = filter(
        lambda w: w != self.second_domain, self.storage_domains
    )[0]

    testflow.setup(
        "Creating second template %s from VM %s to storage domain %s",
        self.test_templates[1], self.vm_name, target_domain
    )
    assert ll_templates.createTemplate(
        True, True, vm=self.vm_name, name=self.test_templates[1],
        cluster=config.CLUSTER_NAME, storagedomain=target_domain
    ), "Failed to create template '%s'" % self.test_templates[1]

    self.templates_names.append(self.test_templates[1])

    ll_templates.copy_template_disks(
        self.test_templates[1], [self.second_domain]
    )
    assert ll_templates.waitForTemplatesStates(
        names=",".join(self.test_templates)
    ), "Template '%s' failed to reach OK status" % self.test_templates

    for template in self.test_templates:
        ll_templates.wait_for_template_disks_state(template)


@pytest.fixture()
def create_vms_from_templates(request, storage):
    """
    Create two VMs from templates
    """
    self = request.node.cls

    for template, vm_name in zip(self.test_templates, self.vm_names):
        template_disks = ll_disks.getObjDisks(
            template, get_href=False, is_template=True
        )
        sd_obj = ll_sd.get_storage_domain_obj(
            template_disks[0].storage_domains.storage_domain[0].get_id(),
            key='id'
        )
        target_sd = sd_obj.get_name()
        if target_sd == self.second_domain:
            sd_obj = ll_sd.get_storage_domain_obj(
                (template_disks[0].storage_domains.storage_domain[1].get_id()),
                key='id')
            target_sd = sd_obj.get_name()

        testflow.setup(
            "Create VM %s from template %s on storage domain %s",
            vm_name, template, target_sd
        )

        assert ll_vms.addVm(
            True, name=vm_name, cluster=config.CLUSTER_NAME,
            storagedomain=target_sd, template=template
        ), "Cannot create VM %s from template %s on storage domain %s" % (
            vm_name, template, target_sd
        )
        self.vms_to_wait.append(vm_name)
    ll_vms.start_vms(self.vm_names, 2, config.VM_UP, False)


@pytest.fixture()
def add_two_storage_domains(request, storage):
    """
    Add two storage-domains in order to extend them
    """
    self = request.node.cls

    def finalizer():
        """
        Remove the storage domains
        """
        testflow.teardown(
            "Remove storage domains %s", [self.sd_src, self.sd_target]
        )
        for sd in [self.sd_src, self.sd_target]:
            assert hl_sd.remove_storage_domain(
                name=sd, datacenter=config.DATA_CENTER_NAME, host=self.spm,
                engine=config.ENGINE
            ), "Failed to Remove storage domains %s" % (
                [self.sd_src, self.sd_target]
            )
            ll_jobs.wait_for_jobs([config.JOB_REMOVE_DOMAIN])
        test_utils.wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
    request.addfinalizer(finalizer)
    self.spm = ll_hosts.get_spm_host(config.HOSTS)
    self.sd_src = "{0}_{1}".format(
        "source_domain_", storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
    )
    self.sd_target = "{0}_{1}".format(
        "target_domain_", storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
    )
    for index, sd_name in zip(xrange(2), [self.sd_src, self.sd_target]):
        testflow.setup("Add ISCSI storage domain %s", sd_name)
        assert hl_sd.add_iscsi_data_domain(
            host=self.spm, storage=sd_name,
            data_center=config.DATA_CENTER_NAME,
            lun=config.ISCSI_DOMAINS_KWARGS[index]['lun'],
            lun_address=config.ISCSI_DOMAINS_KWARGS[index]['lun_address'],
            lun_target=config.ISCSI_DOMAINS_KWARGS[index]['lun_target'],
            override_luns=True
        ), "Failed to add storage domain %s" % sd_name

        test_utils.wait_for_tasks(
            config.ENGINE, config.DATA_CENTER_NAME
        )
    self.storage_domain = self.disk_storage_domains = self.sd_src


@pytest.fixture()
def create_vm_on_different_sd(request, storage):
    """
    Create VM on storage domain in a different data center
    """
    self = request.node.cls

    def finalizer():
        """
        Remove the VM
        """
        testflow.teardown("Remove VM %s", self.vm_name)
        assert ll_vms.safely_remove_vms([self.vm_name]), (
            "Failed to power off and remove VM %s" % self.vm_name_2
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_VM])
    request.addfinalizer(finalizer)

    self.vm_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    vm_args = config.clone_vm_args.copy()
    vm_args['storageDomainName'] = self.new_storage_domain
    vm_args['name'] = self.vm_name
    vm_args['cluster'] = self.cluster_name
    vm_args['template'] = self.glance_template_name
    vm_args['clone'] = True
    testflow.setup("Creating VM %s", self.vm_name)
    assert ll_vms.cloneVmFromTemplate(**vm_args), (
        "Failed to create VM %s" % self.vm_name
    )
    # TODO: mark the boot disk as workaround for bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1303320
    disks_obj = ll_vms.getVmDisks(self.vm_name)
    assert ll_disks.updateDisk(
        positive=True, vmName=self.vm_name, id=disks_obj[0].get_id(),
        bootable=True
    )
    assert ll_vms.addNic(
            positive=True, vm=self.vm_name, name=config.NIC_NAME[0],
            network=config.MGMT_BRIDGE
    )


@pytest.fixture(scope='class')
def remove_storage_domain(request, storage):
    """
    Remove storage domain
    """
    self = request.node.cls

    def finalizer():
        dc_name = getattr(self, 'new_dc_name', config.DATA_CENTER_NAME)
        if ll_sd.checkIfStorageDomainExist(
            True, self.second_storage_domain_name
        ):
            testflow.teardown(
                "Remove storage domain %s", self.second_storage_domain_name
            )
            assert hl_sd.remove_storage_domain(
                self.second_storage_domain_name, dc_name, self.host_name,
                engine=config.ENGINE, format_disk=True
            ), "Failed to remove storage domain %s" % (
                self.second_storage_domain_name
            )
    request.addfinalizer(finalizer)
    self.second_storage_domain_name = (
        storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
    )


@pytest.fixture()
def create_disks_with_fs_for_vms(request, storage):
    """
    Create disks from all permutation and create filesystem on them for each VM
    in vm_names, saves all the needed data in dict object with vm_names as keys
    and the value is dict (with keys: disks, mount_points, executor)
    """
    self = request.node.cls

    ll_vms.start_vms(
        vm_list=self.vm_names, max_workers=4, wait_for_status=config.VM_UP
    )
    for vm_name in self.vm_names:
        self.vm_name = vm_name
        create_disks_with_fs(request, storage)
    assert ll_vms.stop_vms_safely(vms_list=self.vm_names)


@pytest.fixture()
def unblock_connectivity_teardown(request, storage):
    """
    Verify connection unblocked from host to target in case test failed
    """

    def finalizer():
        testflow.teardown(
            "Unblock connection from host %s to target %s",
            config.SOURCE, config.TARGET
        )
        storage_helpers.unblockOutgoingConnection(
            config.SOURCE, config.HOSTS_USER, config.HOSTS_PW, config.TARGET
        )
    request.addfinalizer(finalizer)
