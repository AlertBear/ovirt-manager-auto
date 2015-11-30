"""
Storage Disk Image Format
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_2_Storage_Disk_Image_Format
"""
import config
import logging
from concurrent.futures import ThreadPoolExecutor
from art.unittest_lib import attr, StorageTest as TestCase
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
    vms as ll_vms,
    templates as ll_templates,
)
from art.test_handler.tools import polarion  # pylint: disable=E0611
from rhevmtests.storage import helpers

ENUMS = config.ENUMS

logger = logging.getLogger(__name__)

VM_ARGS = {
    'positive': True,
    'vmName': "",
    'vmDescription': "",
    'cluster': config.CLUSTER_NAME,
    'size': config.DISK_SIZE,
    'nic': config.NIC_NAME[0],
    'image': config.COBBLER_PROFILE,
    'useAgent': True,
    'os_type': ENUMS['rhel6'],
    'user': config.VM_USER,
    'password': config.VM_PASSWORD,
    'network': config.MGMT_BRIDGE,
}


@attr(tier=2)
class BaseTestDiskImage(TestCase):
    """
    Base Test Class for test plan:
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_2_Storage_Disk_Image_Format
    """
    installation = False
    disk_interface = None

    default_disks = {}
    retrieve_disk_obj = None
    storage_domains = []

    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Retrieve environment's data
        """
        cls.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage,
        )
        cls.domain_0 = cls.storage_domains[0]
        cls.domain_1 = cls.storage_domains[1]

        cls.disk_keywords = {
            "diskInterface": cls.disk_interface,
            "installation": cls.installation,
            "storageDomainName": cls.domain_0,
        }
        cls.export_domain = config.EXPORT_DOMAIN_NAME

    def check_disks(self, disks_dict={}):
        """
        Make sure the vm's disks have the expected values. If the parameter
        disks_dict is passed in,  the default dictionary is updated. Also make
        sure there's at least one disk in the vm

        :param disks_dict: dictionary str/bool with disk identifier and sparse
        value
        :type disks_dict: dict
        """
        check_disks = self.default_disks.copy()
        check_disks.update(disks_dict)

        for key, sparse in check_disks.iteritems():
            logger.info("Checking disks format for %s", key)
            vm_disks = self.retrieve_disk_obj(key)
            # Make sure there's at least one disk
            assert vm_disks
            for disk in vm_disks:
                self.assertEqual(
                    disk.get_sparse(), sparse,
                    "Wrong sparse value for disk %s (disk id: %s)"
                    "expected %s" % (
                        disk.get_alias(), disk.get_id(), str(sparse)
                    )
                )


class BaseTestDiskImageVms(BaseTestDiskImage):
    """
    Base Test Case with two vms created, with thin and pre-allocated disks
    """
    vm_thin = None
    vm_prealloc = None

    default_disks = {}

    disk_thin = None
    disk_prealloc = None
    polarion_test_id = None

    def setUp(self):
        """
        Create one vm with thin provisioned disk and other one with
        preallocated disk
        """
        self.vm_thin = "vm_thin_disk_image"
        self.vm_prealloc = "vm_prealloc_disk_image"
        self.vms = [self.vm_thin, self.vm_prealloc]
        # Define the disk objects' retriever function
        self.retrieve_disk_obj = lambda x: ll_vms.getVmDisks(x)

        vm_thin_args = VM_ARGS.copy()
        vm_prealloc_args = VM_ARGS.copy()
        self.default_disks = {
            self.vm_thin: True,
            self.vm_prealloc: False,
        }
        thin_keywords = {
            "vmName": self.vm_thin,
            "volumeFormat": config.COW_DISK,
            "volumeType": True,  # sparse
        }
        vm_thin_args.update(thin_keywords)
        vm_thin_args.update(self.disk_keywords)

        prealloc_keywords = {
            "vmName": self.vm_prealloc,
            "volumeFormat": config.RAW_DISK,
            "volumeType": False,  # preallocated
        }
        vm_prealloc_args.update(prealloc_keywords)
        vm_prealloc_args.update(self.disk_keywords)

        assert helpers.create_vm_or_clone(**vm_thin_args)
        assert helpers.create_vm_or_clone(**vm_prealloc_args)

        if self.installation:
            assert ll_vms.stop_vms_safely([self.vm_thin, self.vm_prealloc])

        self.disk_thin = ll_vms.getVmDisks(self.vm_thin)[0].get_alias()
        self.disk_prealloc = ll_vms.getVmDisks(self.vm_prealloc)[0].get_alias()
        self.snapshot_desc = "snapshot_disk_image_format"

    def execute_concurrent_vms(self, fn):
        """
        Concurrent execute function for self.vms

        :param fn: function to submit to ThreadPoolExecutor. The function must
        accept only one parameter, the name of the vm
        :type fn: function
        """
        excecutions = list()
        with ThreadPoolExecutor(max_workers=2) as executor:
            for vm in self.vms:
                excecutions.append(executor.submit(fn, **{"vm": vm}))

        for excecution in excecutions:
            if not excecution.result():
                if excecution.exception():
                    raise excecution.exception()
                else:
                    raise Exception("Error executing %s" % excecution)

    def add_snapshots(self):
        """
        Create a snapshot for each vm in parallel
        """
        logger.info("Adding snapshots for %s", ", ".join(self.vms))

        def addsnapshot(vm):
            return ll_vms.addSnapshot(True, vm, self.snapshot_desc)

        self.execute_concurrent_vms(addsnapshot)

    def export_vms(self, discard_snapshots=False):
        """
        Export vms in parallel
        """
        def exportVm(vm):
            return ll_vms.exportVm(
                True, vm, self.export_domain,
                discard_snapshots=discard_snapshots
            )

        logger.info("Export vms %s", ", ".join(self.vms))
        self.execute_concurrent_vms(exportVm)

    def import_vms(self, collapse=False):
        """
        Import vms in parallel
        """
        logger.info("Import vms %s", ", ".join(self.vms))

        def importVm(vm):
            return ll_vms.importVm(
                True, vm, self.export_domain, self.domain_0,
                config.CLUSTER_NAME, collapse=collapse
            )

        self.execute_concurrent_vms(importVm)

    def check_snapshots_collapsed(self):
        """
        Ensure that the snapshots are removed after the import process
        """
        vm_thin_snapshots = [
            snapshot.get_description() for snapshot in
            ll_vms.get_vm_snapshots(self.vm_thin)
        ]
        vm_prealloc_snapshots = [
            snapshot.get_description() for snapshot in
            ll_vms.get_vm_snapshots(self.vm_prealloc)
        ]
        self.assertTrue(self.snapshot_desc not in vm_thin_snapshots)
        self.assertTrue(self.snapshot_desc not in vm_prealloc_snapshots)

    def tearDown(self):
        """
        Remove created vms
        """
        ll_vms.stop_vms_safely(self.vms)
        assert ll_vms.removeVms(True, self.vms)


class TestCasesVms(BaseTestDiskImageVms):
    """
    Collection of tests which utilize BaseTestDiskImageVms
    """
    bz = {
        '1251956': {'engine': None, 'version': ['3.6']},
        '1259785': {'engine': None, 'version': ['3.6']},
    }

    @polarion("RHEVM3-11604")
    def test_format_and_snapshots(self):
        """
        Polarion case id: 11604
        Create a snapshot
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.check_disks()
        self.add_snapshots()
        self.check_disks({self.vm_prealloc: True})

    @polarion("RHEVM3-11621")
    def test_move_disk_offline(self):
        """
        Polarion case id: 11621
        Move the disk
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        assert ll_disks.move_disk(
            disk_name=self.disk_thin, target_domain=self.domain_1
        )
        assert ll_disks.move_disk(
            disk_name=self.disk_prealloc, target_domain=self.domain_1
        )

        self.check_disks()

    @polarion("RHEVM3-11620")
    def test_add_snapshot_and_move_disk(self):
        """
        Polarion case id: 11620
        Create a snapshot and move the disk
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.check_disks({self.vm_prealloc: True})

        assert ll_disks.move_disk(
            disk_name=self.disk_thin, target_domain=self.domain_1
        )
        assert ll_disks.move_disk(
            disk_name=self.disk_prealloc, target_domain=self.domain_1
        )

        self.check_disks({self.vm_prealloc: True})

    @polarion("RHEVM3-11619")
    def test_live_move_disk(self):
        """
        Polarion case id: 11619
        Start a live disk migration
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        ll_vms.start_vms(
            [self.vm_prealloc, self.vm_thin], max_workers=2,
            wait_for_status=config.VM_UP, wait_for_ip=False
        )

        assert ll_disks.move_disk(
            disk_name=self.disk_thin, target_domain=self.domain_1
        )
        assert ll_disks.move_disk(
            disk_name=self.disk_prealloc, target_domain=self.domain_1
        )

        self.check_disks({self.vm_prealloc: True})


class TestCasesVmsExport(BaseTestDiskImageVms):
    """
    Collection of test cases for export vms
    """

    @polarion("RHEVM3-11618")
    def test_export_vm(self):
        """
        Polarion case id: 11618
        Export a vm
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.export_vms()

        self.retrieve_disk_obj = lambda w: ll_vms.getVmDisks(
            w, storage_domain=self.export_domain)
        self.check_disks()

    @polarion("RHEVM3-11617")
    def test_add_snapshot_and_export_vm(self):
        """
        Polarion case id: 11617
        Create a snapshot and export the vm
        * Thin provisioned disk in the export domain should remain the same
        * Preallocated disk in the export domain should change to thin
        provision
        """
        self.add_snapshots()
        self.export_vms()

        self.retrieve_disk_obj = lambda w: ll_vms.getVmDisks(
            w, storage_domain=self.export_domain)
        self.check_disks({self.vm_prealloc: True})

    @polarion("RHEVM3-11616")
    def test_add_snapshot_export_vm_with_discard_snapshots(self):
        """
        Polarion case id: 11616
        Create a snapshot and export the vm choosing to discard the existing
        snapshots.
        * Thin provisioned disk in the export domain should remain the same
        * Preallocated disk in the export domain should remain the same
        """
        self.add_snapshots()
        self.export_vms(discard_snapshots=True)

        self.retrieve_disk_obj = lambda w: ll_vms.getVmDisks(
            w, storage_domain=self.export_domain
        )
        self.check_disks()

    @polarion("RHEVM3-11615")
    def test_import_vm(self):
        """
        Polarion case id: 11615
        Export a vm and import it back
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.export_vms()
        assert ll_vms.removeVms(True, [self.vm_thin, self.vm_prealloc])
        self.import_vms()

        self.check_disks()

    @polarion("RHEVM3-11614")
    def test_export_vm_after_snapshot_and_import(self):
        """
        Polarion case id: 11614
        Create snapshot on vm, export the vm and import it back
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.export_vms()
        assert ll_vms.removeVms(True, [self.vm_thin, self.vm_prealloc])
        self.import_vms()

        self.check_disks({self.vm_prealloc: True})

    @polarion("RHEVM3-11613")
    def test_export_vm_with_collapse(self):
        """
        Polarion case id: 11613
        Create a snapshot to a vm, export the vm and import choosing to
        collapse the existing snapshots
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.export_vms()
        assert ll_vms.removeVms(True, [self.vm_thin, self.vm_prealloc])
        self.import_vms(collapse=True)
        self.check_snapshots_collapsed()
        self.check_disks({self.vm_prealloc: True})

    def tearDown(self):
        """
        Remove the vms from the export domain
        """
        for vm in self.vms:
            ll_vms.removeVm(True, vm, stopVM='true')
        for vm in [self.vm_thin, self.vm_prealloc]:
            assert ll_vms.removeVmFromExportDomain(
                True, vm, config.DATA_CENTER_NAME, self.export_domain
            )


class TestCasesImportVmLinked(BaseTestDiskImage):
    """
    Collection for test cases with one vm imported
    """
    retrieve_disk_obj = lambda self, x: ll_vms.getVmDisks(x)
    # Bugzilla history:
    # 1254230: Operation of exporting template to Export domain stucks

    def setUp(self):
        """
        Create a template
        """
        self.vm_name = "vm_disk_image_format"
        self.template_name = "template_disk_image_format"
        self.default_disks = {
            self.vm_name: True,
        }
        self.remove_exported_template = False
        vm_args = VM_ARGS.copy()
        vm_args.update(self.disk_keywords)
        vm_args.update({
            'vmName': self.vm_name,
            'volumeType': True,
            'volumeFormat': config.COW_DISK,
        })
        assert helpers.create_vm_or_clone(**vm_args)
        assert ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name
        )
        assert ll_vms.removeVm(True, self.vm_name)

    @polarion("RHEVM3-11612")
    def test_import_link_to_template(self):
        """
        Polarion case id: 11612
        Create a vm from a thin provisioned template, export the vm and
        re-import it back
        * Thin provisioned disk should remain the same
        """
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name, self.template_name, config.CLUSTER_NAME,
            clone=False, vol_sparse=True, vol_format=config.COW_DISK
        )
        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)
        assert ll_vms.removeVm(True, self.vm_name)
        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain, self.domain_0,
            config.CLUSTER_NAME
        )

        self.check_disks()

    @polarion("RHEVM3-11611")
    def test_import_link_to_template_collapse(self):
        """
        Polarion case id: 11611
        Create a vm from a thin provisioned template, export the vm and the
        template, remove both of them and import the vm back
        * Thin provisioned disk should remain the same
        """
        assert ll_vms.cloneVmFromTemplate(
            True, self.vm_name, self.template_name, config.CLUSTER_NAME,
            clone=False, vol_sparse=True, vol_format=config.COW_DISK
        )
        assert ll_templates.exportTemplate(
            True, self.template_name, self.export_domain, wait=True
        )
        self.remove_exported_template = True
        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)

        assert ll_vms.removeVm(True, self.vm_name)
        assert ll_templates.removeTemplate(True, self.template_name)

        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain, self.domain_0,
            config.CLUSTER_NAME, collapse=True
        )

        self.check_disks()

    def tearDown(self):
        """
        Remove all templates and vms created
        """
        assert ll_vms.removeVm(True, self.vm_name)
        if ll_templates.validateTemplate(True, self.template_name):
            assert ll_templates.removeTemplate(True, self.template_name)
        assert ll_vms.removeVmFromExportDomain(
            True, self.vm_name, config.DATA_CENTER_NAME, self.export_domain,
        )
        if self.remove_exported_template:
            assert ll_templates.removeTemplateFromExportDomain(
                True, self.template_name, config.DATA_CENTER_NAME,
                self.export_domain,
            )


class TestCasesImportVmWithNewName(BaseTestDiskImageVms):
    """
    Check disk images' format after importing the vm without removing the
    original vm used in the export process
    """

    def import_vm_with_new_name(self):
        """
        Export the thin provisioned and preallocated disk vms, then import them
        with a new name
        """
        self.new_vm_thin = "new_%s" % self.vm_thin
        self.new_vm_prealloc = "new_%s" % self.vm_prealloc

        self.export_vms()
        assert ll_vms.importVm(
            True, self.vm_thin, self.export_domain, self.domain_0,
            config.CLUSTER_NAME, name=self.new_vm_thin
        )
        assert ll_vms.importVm(
            True, self.vm_prealloc, self.export_domain, self.domain_0,
            config.CLUSTER_NAME, name=self.new_vm_prealloc
        )

    @polarion("RHEVM3-11610")
    def test_import_vm_without_removing_old_vm(self):
        """
        Polarion case id: 11610
        Import a vm without removing the original vm used in the export
        process
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.import_vm_with_new_name()

    @polarion("RHEVM3-11609")
    def test_import_vm_without_removing_old_vm_with_snapshot(self):
        """
        Polarion case id: 11609
        Create a snapshot to a vm, export the vm and import without removing
        the original vm used in the export process
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.import_vm_with_new_name()
        self.check_disks({self.vm_prealloc: True})

    def tearDown(self):
        """
        Remove new created vms
        """
        super(TestCasesImportVmWithNewName, self).tearDown()
        assert ll_vms.removeVms(True, [self.new_vm_thin, self.new_vm_prealloc])
        for vm in [self.vm_thin, self.vm_prealloc]:
            assert ll_vms.removeVmFromExportDomain(
                True, vm, config.DATA_CENTER_NAME, self.export_domain
            )


class TestCasesCreateTemplate(BaseTestDiskImageVms):
    """
    Verify the disk images' format of a template
    """
    template_thin = "template_thin"
    template_preallocated = "template_preallocated"
    bz = {'1257240': {'engine': None, 'version': ['3.6']}}

    def create_template_from_vm(self):
        """
        Create one template from a vm with a thin provisioned disk and one from
        a vm with a preallocated disk. Check templates' disks image format
        """
        assert ll_templates.createTemplate(
            True, vm=self.vm_thin, name=self.template_thin,
            cluster=config.CLUSTER_NAME
        )

        assert ll_templates.createTemplate(
            True, vm=self.vm_prealloc, name=self.template_preallocated,
            cluster=config.CLUSTER_NAME
        )

        self.retrieve_disk_obj = ll_templates.getTemplateDisks
        self.default_disks = {
            self.template_thin: True,
            self.template_preallocated: False,
        }
        self.check_disks()

    @polarion("RHEVM3-11608")
    def test_create_template_from_vm(self):
        """
        Polarion case id: 11608
        Create a template from a vm
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.create_template_from_vm()

    @polarion("RHEVM3-11607")
    def test_create_template_from_vm_with_snapshots(self):
        """
        Polarion case id: 11607
        Create a snapshot to the vm and create a template
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.add_snapshots()
        self.create_template_from_vm()

    def tearDown(self):
        """
        Remove the created templates
        """
        super(TestCasesCreateTemplate, self).tearDown()
        for template in [self.template_thin, self.template_preallocated]:
            assert ll_templates.removeTemplate(True, template)


class TestCase11606(BaseTestDiskImage):
    """
    Test vm with both disk formats
    """
    polarion_test_id = '11606'

    def setUp(self):
        """
        Create a vm with a thin provisioned disk and a preallocated disk
         """
        self.vm_name = "vm_%s" % self.polarion_test_id
        self.template_name = "template_%s" % self.polarion_test_id

        # First disk is thin provisioned
        vm_args = VM_ARGS.copy()
        vm_args.update(self.disk_keywords)
        vm_args.update({
            'vmName': self.vm_name,
            'volumeType': True,
            'volumeFormat': config.COW_DISK,
        })
        assert helpers.create_vm_or_clone(**vm_args)
        self.thin_disk_alias = ll_vms.getVmDisks(self.vm_name)[0].get_alias()

        self.preallocated_disk_alias = "{0}_prealloc".format(self.vm_name)
        # Adding a prealloacted disk
        assert ll_vms.addDisk(
            True, self.vm_name, config.DISK_SIZE, bootable=False,
            storagedomain=self.domain_0, interface=self.disk_interface,
            format=config.RAW_DISK, sparse=False,
            alias=self.preallocated_disk_alias,
        )

    def check_disks(self):
        """
        Verify the vm and template disks' format
        """
        for function, object_name in [
                (ll_disks.getTemplateDisk, self.template_name),
                (ll_disks.getVmDisk, self.vm_name)]:

            thin_disk = function(object_name, self.thin_disk_alias)
            preallocated_disk = function(
                object_name, self.preallocated_disk_alias,
            )
            self.assertEqual(
                thin_disk.get_sparse(), True,
                "%s disk %s should be thin provisioned" %
                (object_name, thin_disk.get_alias()),
            )
            self.assertEqual(
                preallocated_disk.get_sparse(), False,
                "%s disk %s should be preallocated" %
                (object_name, preallocated_disk.get_alias()),
            )

    def action_test(self, collapse=False):
        """
        Export the vm, import it and create a template
        """
        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)
        assert ll_vms.removeVm(True, self.vm_name)

        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain, self.domain_0,
            config.CLUSTER_NAME, collapse=collapse
        )

        assert ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name
        )

    @polarion("RHEVM3-11606")
    def test_different_format_same_vm(self):
        """
        Polarion case id: 11606 - no snapshot
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.action_test()
        self.check_disks()

    @polarion("RHEVM3-11606")
    def test_different_format_same_vm_with_snapshot(self):
        """
        Polarion case id: 11606 - with snapshot
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        assert ll_vms.addSnapshot(True, self.vm_name, "another snapshot")
        self.action_test(collapse=True)

    def tearDown(self):
        """
        Remove created vm, exported vm and template
        """
        assert ll_vms.removeVm(True, self.vm_name)
        assert ll_vms.removeVmFromExportDomain(
            True, self.vm_name, config.DATA_CENTER_NAME, self.export_domain
        )
        assert ll_templates.removeTemplate(True, self.template_name)


class TestCasesVmsVIRTIO(TestCasesVms):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_VIRTIO


class TestCasesVmsIDE(TestCasesVms):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_IDE


class TestCasesVmsExportVIRTIO(TestCasesVmsExport):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_VIRTIO


class TestCasesVmsExportIDE(TestCasesVmsExport):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_IDE


class TestCasesImportVmLinkedVIRTIO(TestCasesImportVmLinked):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_VIRTIO


class TestCasesImportVmLinkedIDE(TestCasesImportVmLinked):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_IDE


class TestCasesCreateTemplateVIRTIO(TestCasesCreateTemplate):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_VIRTIO


class TestCasesCreateTemplateIDE(TestCasesCreateTemplate):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_IDE


class TestCase11606VIRTIO(TestCase11606):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_VIRTIO


class TestCase11606IDE(TestCase11606):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_IDE


class TestCasesImportVmWithNewNameVIRTIO(TestCasesImportVmWithNewName):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_VIRTIO


class TestCasesImportVmWithNewNameIDE(TestCasesImportVmWithNewName):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_IDE
