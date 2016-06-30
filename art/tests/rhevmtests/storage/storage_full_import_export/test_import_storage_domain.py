"""
RHEVM3-10951 - Import export domain
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
workitem?id=RHEVM3-10951
"""
import logging
from art.rhevm_api.tests_lib.low_level import (
    templates as ll_templates,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.utils.test_utils import wait_for_tasks
from art.test_handler import exceptions
from art.test_handler.tools import polarion
from art.test_handler.settings import opts
from art.unittest_lib import attr
from art.unittest_lib.common import StorageTest as TestCase
from rhevmtests.storage import config
from rhevmtests import helpers as rhevm_helpers
import rhevmtests.storage.helpers as storage_helpers

logger = logging.getLogger(__name__)


def setup_module():
    """
    Deactivae and detach export domain
    """
    # This should not be asserted becuase of the deactivate storage domain
    # issue
    wait_for_tasks(config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
    hl_sd.detach_and_deactivate_domain(
        config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME
    )


def teardown_module():
    """
    Attach and active export domain
    """
    if not hl_sd.attach_and_activate_domain(
        config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME
    ):
        raise exceptions.StorageDomainException(
            "Unable to attach and activate storage domain %s" %
            config.EXPORT_DOMAIN_NAME
        )


@attr(tier=2)
class BaseTestCase(TestCase):
    """
    Base class handle import of a export domain
    """

    def setUp(self):
        """
        Create an export domain and export a vm
        """
        self.export_domain_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_SD
        )
        self.imported_vm = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]

        if not ll_sd.addStorageDomain(
            True, name=self.export_domain_name, host=config.HOSTS[0],
            type=config.EXPORT_TYPE,
            **self.storage_domain_kwargs
        ):
            raise exceptions.StorageDomainException(
                "Unable to add storage domain %s with kwars %s" % (
                    self.export_domain_name, self.storage_domain_kwargs
                )
            )
        if not ll_sd.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.export_domain_name
        ):
            raise exceptions.StorageDomainException(
                "Unable to attach storage domain %s to datacenter %s" % (
                    self.export_domain_name, config.DATA_CENTER_NAME
                )
            )
        self.template_name = rhevm_helpers.get_golden_template_name(
            config.CLUSTER_NAME
        )
        if not ll_templates.exportTemplate(
            True, self.template_name, self.export_domain_name,
            exclusive='true', wait=True
        ):
            raise exceptions.TemplateException(
                "Unable to export template %s to domain %s" % (
                    self.template_name, self.export_domain_name
                )
            )
        if not ll_vms.exportVm(
            True, config.VM_NAME[0], self.export_domain_name
        ):
            raise exceptions.VMException(
                "Unable to export vm %s to domain %s" % (
                    config.VM_NAME[0], self.export_domain_name
                )
            )
        if not ll_sd.removeStorageDomains(
            True, self.export_domain_name, config.HOSTS[0], format='false'
        ):
            raise exceptions.StorageDomainException(
                "Unable to remove storage domain %s" % self.export_domain_name
            )

    @polarion("RHEVM3-10951")
    def test_import_export_storage_domain(self):
        """
        Import an export storage domain
        Import the vm
        """
        self.assertTrue(
            ll_sd.addStorageDomain(
                True, host=config.HOSTS[0], type=config.EXPORT_TYPE,
                **self.storage_domain_kwargs
            ), "Unable to import an export domain %s" % self.export_domain_name
        )
        self.assertTrue(
            ll_sd.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.export_domain_name
            ), "Unable to attach export domain %s to data center %s" % (
                self.export_domain_name, config.DATA_CENTER_NAME
            )
        )
        self.assertTrue(
            ll_vms.importVm(
                True, config.VM_NAME[0], self.export_domain_name,
                self.storage_domain, config.CLUSTER_NAME, self.imported_vm
            ), "Unable to import vm %s from storage domain %s" % (
                config.VM_NAME[0], self.export_domain_name
            )
        )
        self.assertTrue(
            ll_vms.startVm(True, self.imported_vm, config.VM_UP),
            "Unable to start vm %s after been imported from an imported "
            " storage domain" % self.imported_vm
        )

    def tearDown(self):
        """
        Remove export domain and created vm
        """
        if not ll_sd.removeStorageDomains(
            True, self.export_domain_name, config.HOSTS[0], format='true'
        ):
            logger.error(
                "Unable to remove storage domain %s", self.export_domain_name
            )
            BaseTestCase.test_failed = True
        if not ll_vms.safely_remove_vms([self.imported_vm]):
            logger.error("Unable to remove vm %s", self.imported_vm)
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()


class TestCase10951_GLUSTER(BaseTestCase):
    __test__ = config.STORAGE_TYPE_GLUSTER in opts['storages']
    storages = set([config.STORAGE_TYPE_GLUSTER])

    def setUp(self):
        """
        Prepare gluster storage domain
        """
        self.storage_domain_kwargs = {
            'storage_type': config.STORAGE_TYPE_GLUSTER,
            'vfs_type': config.ENUMS['vfs_type_glusterfs'],
            'address': config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
            'path': config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0]
        }
        super(TestCase10951_GLUSTER, self).setUp()


class TestCase10951_POSIX(BaseTestCase):
    # Since we don't run with POSIX make sure this test runs in NFS
    __test__ = config.STORAGE_TYPE_NFS in opts['storages']
    storages = set([config.STORAGE_TYPE_NFS])

    def setUp(self):
        """
        Prepare gluster storage domain
        """
        self.storage_domain_kwargs = {
            'storage_type': config.STORAGE_TYPE_POSIX,
            'vfs_type': config.STORAGE_TYPE_NFS,
            'address': config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
            'path': config.UNUSED_DATA_DOMAIN_PATHS[0]
        }
        super(TestCase10951_POSIX, self).setUp()
