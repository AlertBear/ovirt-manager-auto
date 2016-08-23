"""
4.0 Storage Ability to choose qcow2 disk format when creating a VM from
template
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_0_Storage_Ability_to_choose_qcow2_disk_format_when_creating
_a_VM_from_%20template
"""
import config
import logging
import pytest

from art.test_handler import exceptions
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import polarion, bz
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_datacenters,
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.unittest_lib import (
    StorageTest as TestCase,
    tier2,
    tier3,
)
from rhevmtests.storage.fixtures import (
    create_vm,
)
from rhevmtests.storage.fixtures import remove_vm  # flake8: noqa
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import helpers as storage_helpers

ENUMS = config.ENUMS
QCOW2 = 'qcow2'

logger = logging.getLogger(__name__)


class BaseTestCase(TestCase):

    template_disks_format = None
    create_snapshot = False

    @pytest.fixture(scope='function')
    def initializer_BaseTestCase(self, request, storage):
        """
        Creates a vm with one preallocated and one thin provisioned disk
        Creates a snapshot if `create_snapshot` attribute is True.
        Then creates a template from the vm with the disk format as set
        in `template_disks_format` attribute.
        """
        request.addfinalizer(self.finalizer_BaseTestCase)
        self.vms, self.templates = list(), list()
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.template_name = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        self.storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )[0]
        self.storage_domain_id = ll_sd.get_storage_domain_obj(
            self.storage_domain
        ).get_id()
        self.data_center_id = ll_datacenters.get_data_center(
            config.DATA_CENTER_NAME
        ).get_id()

        vm_args_copy = config.create_vm_args.copy()
        vm_args_copy['vmName'] = self.vm_name
        vm_args_copy['volumeFormat'] = config.DISK_FORMAT_COW
        vm_args_copy['volumeType'] = True
        vm_args_copy['installation'] = False
        vm_args_copy['storageDomainName'] = self.storage_domain
        if not storage_helpers.create_vm_or_clone(**vm_args_copy):
            raise exceptions.VMException(
                "Unable to create vm %s" % self.vm_name
            )

        self.vms.append(self.vm_name)
        if not ll_vms.addDisk(
            True, self.vm_name, provisioned_size=config.GB,
            format=config.DISK_FORMAT_RAW, sparse=False,
            active=True, interface=config.INTERFACE_VIRTIO,
            storagedomain=self.storage_domain
        ):
            raise exceptions.DiskException(
                "Unable to create and attach disk to vm %s" %
                self.vm_name
            )

        if self.create_snapshot:
            self.snapshot_name = storage_helpers.create_unique_object_name(
                self.__class__.__name__, config.OBJECT_TYPE_SNAPSHOT
            )
            if not ll_vms.addSnapshot(
                True, self.vm_name, self.snapshot_name,
            ):
                raise exceptions.SnapshotException(
                    "Unable to create snapshot on vm %s" % self.vm_name
                )

        sparse = True
        if (self.template_disks_format == config.DISK_FORMAT_RAW and
           self.storage in config.BLOCK_TYPES):
            # For block storage domains and RAW format the sparse has to be
            # set explicitly
            sparse = False
        disks = {}
        for disk in ll_vms.getVmDisks(self.vm_name):
            disks[disk.get_id()] = {
                'format': self.template_disks_format,
                'storagedomain': self.storage_domain,
                'sparse': sparse,
            }

        if not ll_templates.createTemplate(
            True, True, vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME, storagedomain=self.storage_domain,
            disks=disks
        ):
            raise exceptions.TemplateException(
                "Unable to create template %s" % self.template_name
            )
        self.templates.append(self.template_name)

        host = ll_hosts.get_spm_host(config.HOSTS)
        self.host_resource = rhevm_helpers.get_host_resource_by_name(host)

    def verify_object_disks_format(self, name, _format, object_type):
        """
        Verify with qemu-img that disks attached to an object are of an
        specific format

        Arguments:
            name (str): Name of the object
            _format (str): Expected format of the disks attached to the object,
            can be 'raw' or 'cow'
            object_type (str): Object type of name, can be 'vm' or 'template'
        """
        if _format == config.DISK_FORMAT_COW:
            _format = QCOW2
        disks = ll_disks.get_disk_attachments(name, object_type=object_type)
        for disk in disks:
            vol_id = ll_disks.get_disk_obj(disk.get_id(), 'id').get_image_id()
            args = {
                "storagepoolID": self.data_center_id,
                "storagedomainID": self.storage_domain_id,
                "imageID": disk.get_id(),
                "volumeID": vol_id,
            }
            if self.storage in config.BLOCK_TYPES:
                self.host_resource.vds_client(cmd="Image.prepare", args=args)
            try:
                # Verify the disk format
                vol_format = self.host_resource.vds_client(
                    cmd="Volume.getQemuImageInfo", args=args
                ).get("format")
            finally:
                if self.storage in config.BLOCK_TYPES:
                    if self.storage in config.BLOCK_TYPES:
                        self.host_resource.vds_client(
                            cmd="Image.teardown", args=args
                        )
            assert vol_format == _format, (
                "Disk %s format is %s, expected format is %s"
                % (disk.get_id(), vol_format, _format)
            )

    def finalizer_BaseTestCase(self):
        """
        Remove all vms and templates
        """
        if not ll_vms.safely_remove_vms(self.vms):
            TestCase.test_failed = True
            logger.error("Failed to remove VMs %s", self.vms)
        if not ll_templates.remove_templates(True, self.templates):
            TestCase.test_failed = True
            logger.error("Failed to remove templates %s", self.templates)
        TestCase.teardown_exception()


class TestCase16405(BaseTestCase):
    """
    Create a template with QCOW2 format disks
    """
    __test__ = True
    template_disks_format = config.DISK_FORMAT_COW

    @pytest.mark.usefixtures("initializer_BaseTestCase")
    @tier2
    @polarion("RHEVM-16405")
    def test_create_template_qcow2(self):
        """
        Test setup:
        - VM with 2 attached disks: one preallocated and one thin provision

        Test flow:
        - Create a template from the VM. Create the template disks as QCOW2
        - Verify that for both disks, the disks format is QCOW2 with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        """
        self.verify_object_disks_format(
            self.template_name, self.template_disks_format, 'template'
        )


class TestCase16407(BaseTestCase):
    """
    Create a VM from a QCOW2 template as QCOW2
    """
    __test__ = True
    template_disks_format = config.DISK_FORMAT_COW

    @pytest.mark.usefixtures("initializer_BaseTestCase")
    @polarion("RHEVM-16407")
    @tier3
    def test_create_vm_from_a_qcow2_template_as_qcow2(self):
        """
        Test setup:
        - VM with 2 attached disks: one preallocated and one thin provision

        Test flow:
        - Create a template from the VM. Create the template disks as QCOW2
        - Create a VM from the template. Create a VM disks as QCOW2
        - Verify that for both disks, the disks format is QCOW2 with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        """
        self.vm_name_2 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name_2, self.template_name, config.CLUSTER_NAME,
            vol_format=config.DISK_FORMAT_COW, vol_sparse=True, clone=False,
        ), "Unable to create vm from template %s" % self.template_name
        self.vms.append(self.vm_name_2)
        self.verify_object_disks_format(
            self.vm_name_2, self.template_disks_format, 'vm'
        )


class TestCase16408(BaseTestCase):
    """
    Create a VM from QCOW2 template as RAW
    """
    __test__ = True
    template_disks_format = config.DISK_FORMAT_COW

    @polarion("RHEVM-16408")
    @tier3
    @pytest.mark.usefixtures("initializer_BaseTestCase")
    def test_create_vm_from_a_qcow2_template_as_raw(self):
        """
        Test setup:
        - VM with 2 attached disks: one preallocated and one thin provision

        Test flow:
        - Create a template from the VM. Create the template disks as QCOW2
        - Try to create a VM from the template. Create a VM disks as RAW
        -> Operation should not be allowed
        """
        self.vm_name_3 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        assert ll_vms.cloneVmFromTemplate(
            False, self.vm_name_3, self.template_name, config.CLUSTER_NAME,
            vol_format=config.DISK_FORMAT_RAW, vol_sparse=False, clone=False,
        ), (
            "Able to create vm with RAW disk format from a template %s "
            "with COW disk format" % self.template_name
        )
        self.vms.append(self.vm_name_3)


class TestCase16406(BaseTestCase):
    """
    Create a template with RAW format disks
    """
    __test__ = True
    template_disks_format = config.DISK_FORMAT_RAW

    @pytest.mark.usefixtures("initializer_BaseTestCase")
    @polarion("RHEVM-16406")
    @tier3
    def test_create_template_raw(self):
        """
        Test setup:
        - VM with 2 attached disks: one preallocated and one thin provision

        Test flow:
        - Create a template from the VM. Create the template disks as RAW
        - Verify that for both disks, the disks format is RAW with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        """
        self.verify_object_disks_format(
            self.template_name, self.template_disks_format, 'template'
        )


class TestCase16410(BaseTestCase):
    """
    Create a VM from a RAW template as RAW
    """
    __test__ = True
    template_disks_format = config.DISK_FORMAT_RAW

    @pytest.mark.usefixtures("initializer_BaseTestCase")
    @polarion("RHEVM-16410")
    @tier3
    def test_create_vm_from_raw_template_as_raw(self):
        """
        Test setup:
        - VM with 2 attached disks: one preallocated and one thin provision

        Test flow:
        - Create a template from the VM. Create the template disks as RAW
        - Create a VM from the template. Create the VM disks as RAW
        - Verify that for both disks, the disks format is RAW with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        """
        self.vm_name_2 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name_2, self.template_name, config.CLUSTER_NAME,
            vol_format=config.DISK_FORMAT_RAW, vol_sparse=False,
        ), "Unable to create vm from template %s" % self.template_name
        self.vms.append(self.vm_name_2)
        self.verify_object_disks_format(
            self.vm_name_2, self.template_disks_format, 'vm'
        )


class TestCase16411(BaseTestCase):
    """
    Create a VM from a RAW template as QCOW2
    """
    __test__ = True
    template_disks_format = config.DISK_FORMAT_RAW

    @pytest.mark.usefixtures("initializer_BaseTestCase")
    @polarion("RHEVM-16411")
    @tier3
    def test_create_vm_from_a_raw_template_as_qcow2(self):
        """
        Test setup:
        - VM with 2 attached disks: one preallocated and one thin provision

        Test flow:
        - Create a template from the VM. Create the template disks as RAW
        - Create a VM from the template. Create the VM disks as COW2
        - Verify that for both disks, the disks format is QCOW2 with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        """
        self.vm_name_3 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name_3, self.template_name, config.CLUSTER_NAME,
            vol_format=config.DISK_FORMAT_COW, vol_sparse=True, clone=False,
        ), "Unable to create vm from template %s" % self.template_name
        self.vms.append(self.vm_name_3)
        self.verify_object_disks_format(
            self.vm_name_3, config.DISK_FORMAT_COW, 'vm'
        )


class TestCase16409(BaseTestCase):
    """
    Create a template with RAW disk from a VM with a asnapshot.
    Then create VMs from the template
    """
    __test__ = True
    template_disks_format = config.DISK_FORMAT_RAW
    create_snapshot = True

    @polarion("RHEVM-16409")
    @tier3
    @pytest.mark.usefixtures("initializer_BaseTestCase")
    def test_create_template_raw_from_vm_with_snapshots(self):
        """
        Test setup:
        - VM with 2 attached disks: one preallocated and one thin provision

        Test flow:
        - Create a snapshot for the VM that includes disks and configuration
        - Create a template from the VM. Create the template disks as RAW
        - Verify that for both disks, the disks format is RAW with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        - Create a VM from the template with QCOW2 disk -> Should succeed
        - Verify that for both disks, the disks format is QCOW2 with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        - Create a VM from the template with RAW disk -> Should succeed
        - Verify that for both disks, the disks format is RAW with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        """
        self.verify_object_disks_format(
            self.template_name, self.template_disks_format, 'template'
        )
        self.vm_name_2 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name_2, self.template_name, config.CLUSTER_NAME,
            vol_format=config.DISK_FORMAT_RAW, vol_sparse=False,
        ), "Unable to create vm from template %s" % self.template_name
        self.vms.append(self.vm_name_2)
        self.verify_object_disks_format(
            self.vm_name_2, self.template_disks_format, 'vm'
        )
        self.vm_name_3 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name_3, self.template_name, config.CLUSTER_NAME,
            vol_format=config.DISK_FORMAT_COW, vol_sparse=True,
            clone=False,
        ), "Unable to create vm from template %s" % self.template_name
        self.vms.append(self.vm_name_3)
        self.verify_object_disks_format(
            self.vm_name_3, config.DISK_FORMAT_COW, 'vm'
        )


class TestCase16412(BaseTestCase):
    """
    Create a template with QCOW2 disk from a VM with snapshot.
    Then create VMs from the template
    """
    __test__ = True
    template_disks_format = config.DISK_FORMAT_COW
    create_snapshot = True

    @polarion("RHEVM-16412")
    @tier3
    @pytest.mark.usefixtures("initializer_BaseTestCase")
    def test_create_template_qcow2_from_vm_with_snapshot(self):
        """
        Test setup:
        - VM with 2 attached disks: one preallocated and one thin provision

        Test flow:
        - Create a snapshot for the VM that includes disks and configuration
        - Create a template from the VM. Create the template disks as QCOW2
        - Verify that for both disks, the disks format is QCOW2 with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        - Create a template from the VM. Create the template disks as QCOW2
        - Verify that for both disks, the disks format is QCOW2 with:
        vdsm-client Volume getQemuImageInfo storagepoolID=<SPUUID>
        storagedomainID=<SDUUID> imageID=<IMGUUID> volumeID=<VOLUUID>
        - Create a VM from the template with RAW disk -> Should not be allowed
        """
        self.verify_object_disks_format(
            self.template_name, self.template_disks_format, 'template'
        )
        self.vm_name_2 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name_2, self.template_name, config.CLUSTER_NAME,
            vol_format=config.DISK_FORMAT_COW, vol_sparse=True, clone=False,
        ), "Unable to create vm from template %s" % self.template_name
        self.vms.append(self.vm_name_2)
        self.verify_object_disks_format(
            self.vm_name_2, self.template_disks_format, 'vm'
        )

        self.vm_name_3 = storage_helpers.create_unique_object_name(
            self.__class__.__name__, config.OBJECT_TYPE_VM
        )
        assert ll_vms.cloneVmFromTemplate(
            False, self.vm_name_3, self.template_name, config.CLUSTER_NAME,
            vol_format=config.DISK_FORMAT_RAW, vol_sparse=False, clone=False,
        ), (
            "Able to create vm with RAW disk format from a template %s "
            " with COW disk format" % self.template_name
        )
        self.vms.append(self.vm_name_3)


@pytest.mark.usefixtures(
    create_vm.__name__
)
class TestCase16968(TestCase):
    """
    Creating VMs from templates as clones and verify actual and virtual size
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_0_Storage_Templates
    """
    __test__ = (
        config.STORAGE_TYPE_ISCSI in ART_CONFIG['RUN']['storages'] or
        config.STORAGE_TYPE_FCP in ART_CONFIG['RUN']['storages']
    )
    storages = set([config.STORAGE_TYPE_ISCSI, config.STORAGE_TYPE_FCP])
    polarion_test_case = '16968'

    deep_copy = True
    volume_format = config.DISK_FORMAT_COW

    @polarion("RHEVM3-16968")
    @bz({'1459455': {}})
    @tier2
    def test_virtual_actual_disk_size_block(self):
        """
        - Create VM with disk format "QCOW2" from template as clone on block
        based domain

        Expected results:
            - Disk virtual size should be larger than disk actual size
        """
        vm_disk = ll_vms.get_vm_bootable_disk_id(self.vm_name)
        disk_virtual_size = ll_disks.get_disk_obj(
            vm_disk
        ).get_provisioned_size()
        disk_actual_size = ll_disks.get_disk_obj(vm_disk).get_actual_size()
        assert disk_actual_size < disk_virtual_size, (
            "Disk %s actual size: %s, virtual size: %s" % (
                vm_disk, disk_actual_size, disk_virtual_size
            )
        )
