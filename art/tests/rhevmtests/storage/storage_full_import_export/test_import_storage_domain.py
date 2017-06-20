"""
RHEVM3-10951 - Import export domain
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
workitem?id=RHEVM3-10951
"""
import pytest
from rhevmtests.storage import config
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from art.test_handler.tools import polarion
from art.test_handler.settings import opts
from art.unittest_lib import (
    tier2,
)
from art.unittest_lib.common import StorageTest as TestCase, testflow
import rhevmtests.storage.helpers as storage_helpers
from rhevmtests.storage.storage_full_import_export.fixtures import (
    remove_export_domain_setup, fetch_golden_template_name
)
from rhevmtests.storage.fixtures import (
    export_template, export_vm, create_vm, remove_vms, create_export_domain,
    remove_export_domain,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa


@pytest.fixture(scope='module', autouse=True)
def deactivate_and_detach_export_domain(request):
    """
    Deactivate and detach storage domain
    """
    def finalizer():
        """
        Attach and active export domain
        """
        testflow.teardown("Attach export domain %s", config.EXPORT_DOMAIN_NAME)
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME
        ), "Unable to attach and activate export domain %s" % (
            config.EXPORT_DOMAIN_NAME
        )

    request.addfinalizer(finalizer)
    testflow.teardown("Detach export domain %s", config.EXPORT_DOMAIN_NAME)
    assert hl_sd.detach_and_deactivate_domain(
        config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME,
        engine=config.ENGINE
    ), "Failed to detach export domain %s" % config.EXPORT_DOMAIN_NAME


@pytest.mark.usefixtures(
    create_vm.__name__,
    remove_vms.__name__,
    create_export_domain.__name__,
    remove_export_domain.__name__,
    fetch_golden_template_name.__name__,
    export_template.__name__,
    export_vm.__name__,
    remove_export_domain_setup.__name__,
)
class BaseTestCase(TestCase):
    """
    Base class handle import of a export domain
    """
    exclusive = 'true'

    @pytest.mark.skipif(
        not len(config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS),
        reason="Not defined unused gluster domains"
    )
    @polarion("RHEVM3-10951")
    @tier2
    def test_import_export_storage_domain(self):
        """
        Import an export storage domain
        Import the vm
        """
        testflow.step("Import export domain %s", self.export_domain)
        assert ll_sd.addStorageDomain(
            True, host=self.spm, type=config.EXPORT_TYPE,
            **self.storage_domain_kwargs
        ), "Unable to import an export domain %s" % self.export_domain
        testflow.step(
            "Attach export domain %s to data-center %s",
            self.export_domain, config.DATA_CENTER_NAME
        )
        assert ll_sd.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.export_domain
        ), "Unable to attach export domain %s to data center %s" % (
            self.export_domain, config.DATA_CENTER_NAME
        )
        imported_vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        testflow.step(
            "Import VM %s with name %s",
            self.vm_name, imported_vm_name
        )
        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain,
            self.storage_domain, config.CLUSTER_NAME, imported_vm_name
        ), "Unable to import VM %s from storage domain %s" % (
            self.vm_name, self.export_domain
        )
        self.vm_names.append(imported_vm_name)
        testflow.step("Start VM %s", imported_vm_name)
        assert ll_vms.startVm(True, imported_vm_name, config.VM_UP), (
            "Unable to start VM %s after been imported from an imported "
            "storage domain" % imported_vm_name
        )


class TestCase10951_GLUSTER(BaseTestCase):
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    storages = set([config.STORAGE_TYPE_GLUSTER])
    gl_add = config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES
    gl_path = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS

    storage_domain_kwargs = {
        'storage_type': config.STORAGE_TYPE_GLUSTER,
        'vfs_type': config.ENUMS['vfs_type_glusterfs'],
        'address': gl_add[0] if len(gl_add) else None,
        'path': gl_path[0] if len(gl_path) else None
    }


class TestCase10951_POSIX(BaseTestCase):
    # Since we don't run with POSIX make sure this test runs in NFS
    __test__ = config.STORAGE_TYPE_NFS in opts['storages']
    storages = set([config.STORAGE_TYPE_NFS])
    nfs_add = config.UNUSED_DATA_DOMAIN_ADDRESSES
    nfs_path = config.UNUSED_DATA_DOMAIN_PATHS

    storage_domain_kwargs = {
        'storage_type': config.STORAGE_TYPE_POSIX,
        'vfs_type': config.STORAGE_TYPE_NFS,
        'address': nfs_add[0] if len(nfs_add) else None,
        'path': nfs_path[0] if len(nfs_path) else None
    }
