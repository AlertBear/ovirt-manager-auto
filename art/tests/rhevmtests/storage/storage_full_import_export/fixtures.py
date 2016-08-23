import pytest
from rhevmtests.storage import config
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from rhevmtests import helpers as rhevm_helpers
import rhevmtests.storage.helpers as storage_helpers


@pytest.fixture(scope='class')
def initialize_export_domain_param(request, storage):
    """
    Extract export domain name
    """
    self = request.node.cls

    export_domains = ll_sd.findExportStorageDomains(config.DATA_CENTER_NAME)
    assert export_domains, (
        "No Export storage domains were found in Data center %s" %
        config.DATA_CENTER_NAME
    )

    self.export_domain = export_domains[0]


@pytest.fixture(scope='class')
def initialize_vm_and_template_names(request, storage):
    """
    Create unique name for VMs and templates
    """
    self = request.node.cls

    self.vm_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    ) + '_original'
    self.from_vm1 = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    ) + '_1'
    self.from_vm2 = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    ) + '_2'
    self.vm_cloned1 = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    ) + '_cloned_1'
    self.vm_cloned2 = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_VM
    ) + '_cloned_2'
    self.from_template1 = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
    ) + '_1'
    self.from_template2 = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
    ) + '_2'


@pytest.fixture()
def remove_template_setup(request, storage):
    """
    Remove template
    """
    self = request.node.cls

    testflow.setup("Remove template %s" % self.template_name)
    assert ll_templates.remove_template(
        positive=True, template=self.template_name
    ), "Failed to remove template %s" % self.template_name


@pytest.fixture()
def remove_second_vm_from_export_domain(request, storage):
    """
    Remove second VM from export domain
    """
    self = request.node.cls

    def finalizer():
        export_domain = getattr(
            self, 'export_domain', config.EXPORT_DOMAIN_NAME
        )

        testflow.teardown(
            "Removing VM %s from export domain %s", self.vm_from_template,
            export_domain
        )
        assert ll_vms.remove_vm_from_export_domain(
            positive=True, vm=self.vm_from_template,
            datacenter=config.DATA_CENTER_NAME,
            export_storagedomain=export_domain
        ), "Failed to remove VM %s from export domain %s" % (
            self.vm_from_template, export_domain
        )

    request.addfinalizer(finalizer)


@pytest.fixture()
def remove_export_domain_setup(request, storage):
    """
    Remove export domain
    """
    self = request.node.cls

    testflow.teardown("Remove export domain %s", self.export_domain)

    self.spm = getattr(self, 'spm', ll_hosts.get_spm_host(config.HOSTS))

    assert hl_sd.remove_storage_domain(
        self.export_domain, config.DATA_CENTER_NAME, self.spm,
        engine=config.ENGINE
    ), "Failed to detach and remove export-domain %s" % self.export_domain


@pytest.fixture()
def fetch_golden_template_name(request, storage):
    """
    Fetch golden template name
    """
    self = request.node.cls

    self.template_name = rhevm_helpers.get_golden_template_name(
        config.CLUSTER_NAME
    )


@pytest.fixture(scope='class')
def initialize_first_template_name(request, storage):
    """
    Create unique name for first template
    """
    self = request.node.cls

    self.template_name = storage_helpers.create_unique_object_name(
        self.__class__.__name__, config.OBJECT_TYPE_TEMPLATE
    ) + '_template_original'
