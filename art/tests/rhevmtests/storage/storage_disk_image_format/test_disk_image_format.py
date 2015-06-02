"""
Storage Disk Image Format
"""
import config
import logging
from concurrent.futures import ThreadPoolExecutor
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.low_level import (
    disks, storagedomains, vms, templates,
)
from art.test_handler.tools import tcms
from rhevmtests.storage import helpers


TCMS_PLAN_ID = '8090'

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
    'os_type': config.ENUMS['rhel6'],
    'user': config.VM_USER,
    'password': config.VM_PASSWORD,
}


@attr(tier=1)
class BaseTestDiskImage(TestCase):
    """
    Base Test Class for test plan 8090:
    https://tcms.engineering.redhat.com/plan/8090
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
        cls.storage_domains = storagedomains.getStorageDomainNamesForType(
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

        :param disk_dict: dictionary str/bool with disk identifier and sparse
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

    def setUp(self):
        """
        Create one vm with thin provisioned disk and other one with
        preallocated disk
        """
        self.vm_thin = "vm_thin_%s" % TCMS_PLAN_ID
        self.vm_prealloc = "vm_prealloc_%s" % TCMS_PLAN_ID
        self.vms = [self.vm_thin, self.vm_prealloc]
        # Define the disk objects' retriever function
        self.retrieve_disk_obj = lambda x: vms.getVmDisks(x)

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
            assert vms.stop_vms_safely([self.vm_thin, self.vm_prealloc])

        self.disk_thin = vms.getVmDisks(self.vm_thin)[0].get_alias()
        self.disk_prealloc = vms.getVmDisks(self.vm_prealloc)[0].get_alias()
        self.snapshot_desc = "snapshot_{0}".format(TCMS_PLAN_ID)

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
            return vms.addSnapshot(True, vm, self.snapshot_desc)

        self.execute_concurrent_vms(addsnapshot)

    def export_vms(self, discard_snapshots=False):
        """
        Export vms in parallel
        """
        def exportVm(vm):
            return vms.exportVm(
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
            return vms.importVm(
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
            vms.get_vm_snapshots(self.vm_thin)
        ]
        vm_prealloc_snapshots = [
            snapshot.get_description() for snapshot in
            vms.get_vm_snapshots(self.vm_prealloc)
        ]
        self.assertTrue(self.snapshot_desc not in vm_thin_snapshots)
        self.assertTrue(self.snapshot_desc not in vm_prealloc_snapshots)

    def tearDown(self):
        """
        Remove created vms
        """
        vms.stop_vms_safely(self.vms)
        assert vms.removeVms(True, self.vms)


class TestCasesVms(BaseTestDiskImageVms):
    """
    Collection of tests which utilize BaseTestDiskImageVms
    """

    @tcms(TCMS_PLAN_ID, '232953')
    def test_format_and_snapshots(self):
        """
        TCMS case id: 232953
        Create a snapshot
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.check_disks()
        self.add_snapshots()
        self.check_disks({self.vm_prealloc: True})

    @tcms(TCMS_PLAN_ID, '232954')
    def test_move_disk_offline(self):
        """
        TCMS case id: 232954
        Move the disk
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        assert disks.move_disk(
            disk_name=self.disk_thin, target_domain=self.domain_1)
        assert disks.move_disk(
            disk_name=self.disk_prealloc, target_domain=self.domain_1)

        self.check_disks()

    @tcms(TCMS_PLAN_ID, '232955')
    def test_add_snapshot_and_move_disk(self):
        """
        TCMS case id: 232955
        Create a snapshot and move the disk
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.check_disks({self.vm_prealloc: True})

        assert disks.move_disk(
            disk_name=self.disk_thin, target_domain=self.domain_1)
        assert disks.move_disk(
            disk_name=self.disk_prealloc, target_domain=self.domain_1)

        self.check_disks({self.vm_prealloc: True})

    @tcms(TCMS_PLAN_ID, '232956')
    def test_live_move_disk(self):
        """
        TCMS case id: 232956
        Start a live disk migration
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        vms.start_vms([self.vm_prealloc, self.vm_thin], max_workers=2,
                      wait_for_status=config.VM_UP, wait_for_ip=False)

        assert disks.move_disk(
            disk_name=self.disk_thin, target_domain=self.domain_1)
        assert disks.move_disk(
            disk_name=self.disk_prealloc, target_domain=self.domain_1)

        self.check_disks({self.vm_prealloc: True})


class TestCasesVmsExport(BaseTestDiskImageVms):
    """
    Collection of test cases for export vms
    """

    @tcms(TCMS_PLAN_ID, '232957')
    def test_export_vm(self):
        """
        TCMS case id: 232957
        Export a vm
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.export_vms()

        self.retrieve_disk_obj = lambda w: vms.getVmDisks(
            w, storage_domain=self.export_domain)
        self.check_disks()

    @tcms(TCMS_PLAN_ID, '232958')
    def test_add_snapshot_and_export_vm(self):
        """
        TCMS case id: 232958
        Create a snapshot and export the vm
        * Thin provisioned disk in the export domain should remain the same
        * Preallocated disk in the export domain should change to thin
        provision
        """
        self.add_snapshots()
        self.export_vms()

        self.retrieve_disk_obj = lambda w: vms.getVmDisks(
            w, storage_domain=self.export_domain)
        self.check_disks({self.vm_prealloc: True})

    @tcms(TCMS_PLAN_ID, '232959')
    def test_add_snapshot_export_vm_with_discard_snapshots(self):
        """
        TCMS case id: 232959
        Create a snapshot and export the vm choosing to discard the existing
        snapshots.
        * Thin provisioned disk in the export domain should remain the same
        * Preallocated disk in the export domain should remain the same
        """
        self.add_snapshots()
        self.export_vms(discard_snapshots=True)

        self.retrieve_disk_obj = lambda w: vms.getVmDisks(
            w, storage_domain=self.export_domain)
        self.check_disks()

    @tcms(TCMS_PLAN_ID, '232960')
    def test_import_vm(self):
        """
        TCMS case id: 232960
        Export a vm and import it back
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.export_vms()
        assert vms.removeVms(True, [self.vm_thin, self.vm_prealloc])
        self.import_vms()

        self.check_disks()

    @tcms(TCMS_PLAN_ID, '232961')
    def test_export_vm_after_snapshot_and_import(self):
        """
        TCMS case id: 232961
        Create snapshot on vm, export the vm and import it back
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.export_vms()
        assert vms.removeVms(True, [self.vm_thin, self.vm_prealloc])
        self.import_vms()

        self.check_disks({self.vm_prealloc: True})

    @tcms(TCMS_PLAN_ID, '232962')
    def test_export_vm_with_collapse(self):
        """
        TCMS case id: 232962
        Create a snapshot to a vm, export the vm and import choosing to
        collapse the existing snapshots
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.add_snapshots()
        self.export_vms()
        assert vms.removeVms(True, [self.vm_thin, self.vm_prealloc])
        self.import_vms(collapse=True)
        self.check_snapshots_collapsed()
        self.check_disks({self.vm_prealloc: True})

    def tearDown(self):
        """
        Remove the vms from the export domain
        """
        for vm in self.vms:
            vms.removeVm(True, vm, stopVM='true')
        for vm in [self.vm_thin, self.vm_prealloc]:
            assert vms.removeVmFromExportDomain(
                True, vm, config.DATA_CENTER_NAME, self.export_domain)


class TestCasesImportVmLinked(BaseTestDiskImage):
    """
    Collection for test cases with one vm imported
    """
    retrieve_disk_obj = lambda self, x: vms.getVmDisks(x)

    def setUp(self):
        """
        Create a template
        """
        self.vm_name = "vm_%s" % TCMS_PLAN_ID
        self.template_name = "template_%s" % TCMS_PLAN_ID
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
        assert templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name)
        assert vms.removeVm(True, self.vm_name)

    @tcms(TCMS_PLAN_ID, '232963')
    def test_import_link_to_template(self):
        """
        TCMS case id: 232963
        Create a vm from a thin provisioned template, export the vm and
        re-import it back
        * Thin provisioned disk should remain the same
        """
        assert vms.cloneVmFromTemplate(
            True, self.vm_name, self.template_name, config.CLUSTER_NAME,
            clone=False, vol_sparse=True, vol_format=config.COW_DISK
        )
        assert vms.exportVm(True, self.vm_name, self.export_domain)
        assert vms.removeVm(True, self.vm_name)
        assert vms.importVm(True, self.vm_name, self.export_domain,
                            self.domain_0, config.CLUSTER_NAME)

        self.check_disks()

    @tcms(TCMS_PLAN_ID, '232964')
    def test_import_link_to_template_collapse(self):
        """
        TCMS case id: 232964
        Create a vm from a thin provisioned template, export the vm and the
        template, remove both of them and import the vm back
        * Thin provisioned disk should remain the same
        """
        assert vms.cloneVmFromTemplate(
            True, self.vm_name, self.template_name, config.CLUSTER_NAME,
            clone=False, vol_sparse=True, vol_format=config.COW_DISK
        )
        assert templates.exportTemplate(True, self.template_name,
                                        self.export_domain, wait=True)
        self.remove_exported_template = True
        assert vms.exportVm(True, self.vm_name, self.export_domain)

        assert vms.removeVm(True, self.vm_name)
        assert templates.removeTemplate(True, self.template_name)

        assert vms.importVm(True, self.vm_name, self.export_domain,
                            self.domain_0, config.CLUSTER_NAME,
                            collapse=True)

        self.check_disks()

    def tearDown(self):
        """
        Remove all templates and vms created
        """
        assert vms.removeVm(True, self.vm_name)
        if templates.validateTemplate(True, self.template_name):
            assert templates.removeTemplate(True, self.template_name)
        assert vms.removeVmFromExportDomain(
            True, self.vm_name, config.DATA_CENTER_NAME, self.export_domain,
        )
        if self.remove_exported_template:
            assert templates.removeTemplateFromExportDomain(
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
        assert vms.importVm(True, self.vm_thin, self.export_domain,
                            self.domain_0, config.CLUSTER_NAME,
                            name=self.new_vm_thin)
        assert vms.importVm(True, self.vm_prealloc, self.export_domain,
                            self.domain_0, config.CLUSTER_NAME,
                            name=self.new_vm_prealloc)

    @tcms(TCMS_PLAN_ID, '232965')
    def test_import_vm_without_removing_old_vm(self):
        """
        TCMS case id: 232965
        Import a vm without removing the original vm used in the export
        process
        * Thin provisioned disk should remain the same
        * Preallocated disk should change to thin provisioned
        """
        self.import_vm_with_new_name()

    @tcms(TCMS_PLAN_ID, '232966')
    def test_import_vm_without_removing_old_vm_with_snapshot(self):
        """
        TCMS case id: 232966
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
        assert vms.removeVms(True, [self.new_vm_thin, self.new_vm_prealloc])
        for vm in [self.vm_thin, self.vm_prealloc]:
            assert vms.removeVmFromExportDomain(
                True, vm, config.DATA_CENTER_NAME, self.export_domain)


class TestCasesCreateTemplate(BaseTestDiskImageVms):
    """
    Verify the disk images' format of a template
    """
    template_thin = "template_thin"
    template_preallocated = "template_preallocated"

    def create_template_from_vm(self):
        """
        Create one template from a vm with a thin provisioned disk and one from
        a vm with a preallocated disk. Check templates' disks image format
        """
        assert templates.createTemplate(
            True, vm=self.vm_thin, name=self.template_thin,
            cluster=config.CLUSTER_NAME
        )

        assert templates.createTemplate(
            True, vm=self.vm_prealloc, name=self.template_preallocated,
            cluster=config.CLUSTER_NAME
        )

        self.retrieve_disk_obj = templates.getTemplateDisks
        self.default_disks = {
            self.template_thin: True,
            self.template_preallocated: False,
        }
        self.check_disks()

    @tcms(TCMS_PLAN_ID, '232967')
    def test_create_template_from_vm(self):
        """
        TCMS case id: 232967
        Create a template from a vm
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.create_template_from_vm()

    @tcms(TCMS_PLAN_ID, '232968')
    def test_create_template_from_vm_with_snapshots(self):
        """
        TCMS case id: 232968
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
            assert templates.removeTemplate(True, template)


class TestCase232969(BaseTestDiskImage):
    """
    Test vm with both disk formats
    """
    tcms_test_id = '232969'

    def setUp(self):
        """
        Create a vm with a thin provisioned disk and a preallocated disk
         """
        self.vm_name = "vm_%s" % TCMS_PLAN_ID
        self.template_name = "template_%s" % TCMS_PLAN_ID

        # First disk is thin provisioned
        vm_args = VM_ARGS.copy()
        vm_args.update(self.disk_keywords)
        vm_args.update({
            'vmName': self.vm_name,
            'volumeType': True,
            'volumeFormat': config.COW_DISK,
        })
        assert helpers.create_vm_or_clone(**vm_args)
        self.thin_disk_alias = vms.getVmDisks(self.vm_name)[0].get_alias()

        self.preallocated_disk_alias = "{0}_prealloc".format(self.vm_name)
        # Adding a prealloacted disk
        assert vms.addDisk(
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
                (disks.getTemplateDisk, self.template_name),
                (disks.getVmDisk, self.vm_name)]:

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
        assert vms.exportVm(True, self.vm_name, self.export_domain)
        assert vms.removeVm(True, self.vm_name)

        assert vms.importVm(True, self.vm_name, self.export_domain,
                            self.domain_0, config.CLUSTER_NAME,
                            collapse=collapse)

        assert templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name)

    @tcms(TCMS_PLAN_ID, tcms_test_id)
    def test_different_format_same_vm(self):
        """
        TCMS case id: 232969 - no snapshot
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        self.action_test()
        self.check_disks()

    @tcms(TCMS_PLAN_ID, tcms_test_id)
    def test_different_format_same_vm_with_snapshot(self):
        """
        TCMS case id: 232969 - with snapshot
        * Thin provisioned disk should remain the same
        * Preallocated disk should remain the same
        """
        assert vms.addSnapshot(True, self.vm_name, "another snapshot")
        self.action_test(collapse=True)

    def tearDown(self):
        """
        Remove created vm, exported vm and template
        """
        assert vms.removeVm(True, self.vm_name)
        assert vms.removeVmFromExportDomain(
            True, self.vm_name, config.DATA_CENTER_NAME, self.export_domain)
        assert templates.removeTemplate(True, self.template_name)


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


class TestCase232969VIRTIO(TestCase232969):
    """"""
    __test__ = True
    disk_interface = config.INTERFACE_VIRTIO


class TestCase232969IDE(TestCase232969):
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