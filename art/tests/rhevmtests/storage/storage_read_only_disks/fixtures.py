import pytest
import config
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from rhevmtests.storage import helpers as storage_helpers
from rhevmtests.storage.fixtures import (  # noqa: F401
    unblock_connectivity_storage_domain_teardown
)


@pytest.fixture(scope='class')
def initialize_template_name(request, storage):
    """
    Initialize template name for test
    """

    self = request.node.cls

    self.template_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_TEMPLATE
    )


@pytest.fixture()  # noqa: F811
def initialize_params_for_unblock(
    request, unblock_connectivity_storage_domain_teardown
):
    """
    Initialize parameters for unblock connectivity finalizer
    """
    self = request.node.cls

    self.blocked = getattr(self, 'blocked', True)

    def finalizer():
        if self.blocked:
            vm_host = ll_hosts.get_vm_host(self.vm_name)
            self.host_ip = ll_hosts.get_host_ip(vm_host)

            storage_domain_name = (
                ll_vms.get_vms_disks_storage_domain_name(self.vm_name)
            )
            self.storage_domain_ip = ll_sd.getDomainAddress(
                True, storage_domain_name
            )[1]

    request.addfinalizer(finalizer)
