import config
import pytest
import helpers
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
)
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    datacenters as ll_dc,
    vms as ll_vms,
    hosts as ll_hosts,
)
from art.unittest_lib.common import testflow
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import helpers as storage_helpers


@pytest.fixture(scope='class')
def initialize_variables(request, storage):
    """
    Initialize variables needed for the test
    """
    self = request.node.cls

    self.ovf_store = helpers.get_first_ovf_store_id_and_obj(
        self.storage_domain
    )
    spm = ll_hosts.get_spm_host(config.HOSTS)
    self.spm_host = rhevm_helpers.get_host_resource_by_name(spm)
    data_center_obj = ll_dc.get_data_center(config.DATA_CENTER_NAME)
    self.sp_id = storage_helpers.get_spuuid(data_center_obj)
    if not hasattr(self, 'diskless_vm'):
        self.disk_name = ll_vms.get_vm_bootable_disk(self.vm_name)


@pytest.fixture(scope='class')
def initialize_storage_domains_for_test(request, storage):
    """
    Initialize storage domain variable as needed for test
    """
    self = request.node.cls

    if hasattr(self, 'disk_on_master'):
        found, storage_domain = ll_sd.findMasterStorageDomain(
            True, datacenter=config.DATA_CENTER_NAME
        )
        self.storage_domain = storage_domain.get('masterDomain')
    elif hasattr(self, 'disk_on_non_master'):
        found, storage_domain = ll_sd.findNonMasterStorageDomains(
            True, datacenter=config.DATA_CENTER_NAME
        )
        self.storage_domain = storage_domain.get('nonMasterDomains')[0]
    else:
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.storage_domain = self.storage_domains[0]
        self.storage_domain_1 = self.storage_domains[1]


@pytest.fixture(scope='class')
def initialize_new_disk_params(request, storage):
    """
    Initialize new disk parameters
    """
    self = request.node.cls

    self.new_disk_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DISK
    )

    self.disk_args = config.disk_args.copy()
    self.disk_args['alias'] = self.new_disk_name


@pytest.fixture(scope='class')
def initialize_direct_lun_params(request, storage):
    """
    Initialize direct LUN parameters
    """
    self = request.node.cls

    self.direct_lun_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_DIRECT_LUN
    )

    self.direct_lun_args = config.disk_args.copy()
    self.direct_lun_args['alias'] = self.direct_lun_name
    self.direct_lun_args['lun_address'] = config.EXTEND_LUN_ADDRESS[0]
    self.direct_lun_args['lun_target'] = config.EXTEND_LUN_TARGET[0]
    self.direct_lun_args['lun_id'] = config.EXTEND_LUN[0]
    self.direct_lun_args['type_'] = config.STORAGE_TYPE_ISCSI


@pytest.fixture(scope='class')
def init_params_for_diskless_test(request, storage):
    """
    Initiazlie parameters for diskless VM tests
    """
    self = request.node.cls

    self.vm_id = ll_vms.get_vm_obj(self.vm_name).get_id()
    self.sd_id = ll_sd.get_storage_domain_obj(self.storage_domain).get_id()
    self.is_block_storage = (
        True if self.storage in config.BLOCK_TYPES else False
    )
    self.ovf_store = helpers.get_first_ovf_store_id_and_obj(
        self.storage_domain
    )


@pytest.fixture(scope='class')
def initialize_template_params(request, storage):
    """
    Initialize template parameteres
    """
    self = request.node.cls

    self.template_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_TEMPLATE
    )


@pytest.fixture(scope='module')
def set_ovf_store_count(request):
    """
    Update the number of OVF stores and restart engine
    """
    def finalizer():
        testflow.teardown(
            "Restoring the ovirt-engine service with "
            "StorageDomainOvfStoreCount set to %s, restarting engine",
            config.DEFAULT_NUM_OVF_STORES_PER_SD
        )
        cmd = config.UPDATE_OVF_NUM_OVF_STORES_CMD % {
            'num_ovf_stores': config.DEFAULT_NUM_OVF_STORES_PER_SD
        }
        assert config.ENGINE.engine_config(action='set', param=cmd).get(
            'results'
        ), "Update number of OVF stores failed to execute on '%s'" % config.VDC
        hl_dc.ensure_data_center_and_sd_are_active(config.DATA_CENTER_NAME)

    request.addfinalizer(finalizer)

    testflow.setup(
        "Changing the ovirt-engine service with StorageDomainOvfStoreCount set"
        " to %s, restarting engine", config.UPDATED_NUM_OVF_STORES_PER_SD
    )
    cmd = config.UPDATE_OVF_NUM_OVF_STORES_CMD % {
        'num_ovf_stores': config.UPDATED_NUM_OVF_STORES_PER_SD
    }
    assert config.ENGINE.engine_config(
        action='set', param=cmd
    ).get('results'), (
        "Update number of OVF stores failed to execute on '%s'" % config.VDC
    )
    hl_dc.ensure_data_center_and_sd_are_active(config.DATA_CENTER_NAME)


@pytest.fixture(scope='class')
def initalize_vm_to_remove(request, storage):
    """
    Initialize VM to remove when the test is finished
    """
    self = request.node.cls

    def finalizer():
        self.vm_name = self.new_vm_name

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def remove_ovf_store_from_glance_domain(request, storage):
    """
    Remove OVF store files from Glance domain
    """
    def finalizer():
        glance_images = ll_sd.get_storage_domain_images(config.GLANCE_DOMAIN)
        for image in glance_images:
            if image.get_name() == config.OVF_STORE_DISK_NAME:
                assert ll_sd.remove_glance_image(
                    image.get_id(), config.GLANCE_HOSTNAME, config.HOSTS_USER,
                    config.HOSTS_PW
                ), "Failed to remove OVF store image from Glance domain"

    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def initialize_vm_pool_name(request, storage):
    """
    Initialize VM pool name for test
    """
    self = request.node.cls

    self.pool_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_POOL
    )
