"""
3.4 Glance sanity
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_4_Storage_Import_Template_Entities
"""
import logging
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms
)
from art.test_handler import exceptions as errors
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as BaseTestCase, SkipTest
from rhevmtests.storage import config, helpers as storage_helpers

logger = logging.getLogger(__name__)
POLL_PERIOD = 10

# Clone a vm from a template with the correct parameters
args_for_clone = {
    'positive': True,
    'name': None,
    'cluster': config.CLUSTER_NAME,
    'template': None,
    'clone': True,  # Always clone
    'vol_sparse': True,
    'vol_format': config.COW_DISK,
    'storagedomain': None,
    'virtio_scsi': True,
}


class BasicEnvironment(BaseTestCase):
    """
    This class implements the base setUp and tearDown functions as well
    as common functions used by the various tests
    """
    __test__ = False
    test_case = None
    glance_image = None
    vm_name = None

    def setUp(self):
        """
        Prepare the environment for test
        """
        # Disable glance tests for PPC architecture
        if config.PPC_ARCH:
            raise SkipTest("Glance is not supported on PPC")
        self.storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        self.vms_to_remove = list()
        self.templates_to_remove = list()
        self.storage_domain = self.storage_domains[0]
        self.new_disk_alias = self.create_unique_object_name(
            config.OBJECT_TYPE_DISK
        )
        self.new_template_name = self.create_unique_object_name(
            config.OBJECT_TYPE_TEMPLATE
        )[0:40]
        self.clone_vm_args = args_for_clone.copy()

    def tearDown(self):
        """
        Clean the environment at the end of each test case
        """
        self.teardown_remove_vms()
        self.teardown_remove_templates()
        self.teardown_exception()

    def teardown_remove_vms(self):
        if not ll_vms.safely_remove_vms(self.vms_to_remove):
            self.test_failed = True
            logger.error(
                "Failed to remove vms %s for test", self.vms_to_remove
            )

    def teardown_remove_templates(self):
        for template in self.templates_to_remove:
            if ll_templates.validateTemplate(True, template):
                logger.info("Removing template %s", template)
                if not ll_templates.removeTemplate(True, template):
                    self.test_failed = True
                    logger.error(
                        "Failed to remove template %s", template
                    )

    def add_nic_to_vm(self, vm_name):
        if not ll_vms.addNic(
                True, vm=vm_name, name=config.NIC_NAME[0],
                network=config.MGMT_BRIDGE, vnic_profile=config.MGMT_BRIDGE,
                plugged='true', linked='true'
        ):
            raise errors.NetworkException(
                'Unable to add nic to vm %s' % self.vm_name
            )

    def set_glance_image(self, sparse):
        """
        Choose the correct image from the glance repository based on the
        allocation policy
        """
        storage_domains = ll_sd.get_storagedomain_names()
        if config.GLANCE_DOMAIN in storage_domains:
            self.glance_image = config.GOLDEN_GLANCE_IMAGE
            if not sparse:
                self.glance_image = config.GLANCE_IMAGE_RAW

    def basic_flow_import_image_as_disk(self, disk_alias, sparse, wait=True):
        self.set_glance_image(sparse)
        if not ll_sd.import_glance_image(
            config.GLANCE_DOMAIN, self.glance_image,
            self.storage_domain, config.CLUSTER_NAME,
            new_disk_alias=disk_alias, async=(not wait)
        ):
            raise errors.GlanceRepositoryException(
                "Importing glance image from repository %s failed"
                % config.GLANCE_DOMAIN
            )
        ll_jobs.wait_for_jobs(
            [config.JOB_IMPORT_IMAGE], sleep=POLL_PERIOD
        )

    def basic_flow_import_image_as_template(
            self, template_name, sparse, storage_domain,
            new_disk_alias=None, wait=True
    ):
        """
        Basic flow: Covering importing a glance image as a template
        """
        self.set_glance_image(sparse)
        if not ll_sd.import_glance_image(
            config.GLANCE_DOMAIN, self.glance_image,
            storage_domain, config.CLUSTER_NAME,
            new_disk_alias=new_disk_alias,
            new_template_name=template_name,
            import_as_template=True, async=(not wait)
        ):
            raise errors.GlanceRepositoryException(
                "Importing glance image from repository %s failed"
                % config.GLANCE_DOMAIN
            )
        ll_jobs.wait_for_jobs(
            [config.JOB_IMPORT_IMAGE], sleep=POLL_PERIOD
        )
        self.templates_to_remove.append(template_name)

    def basic_flow_clone_vm_from_template(
            self, vm_name, template_name, storage_domain, wait=True,
            start_vm=True
    ):
        self.vm_name = vm_name
        self.clone_vm_args['storagedomain'] = storage_domain
        self.clone_vm_args['name'] = self.vm_name
        self.clone_vm_args['template'] = template_name
        self.clone_vm_args['wait'] = wait

        if not ll_vms.cloneVmFromTemplate(**self.clone_vm_args):
            raise errors.VMException(
                'Unable to create vm %s for test' % self.vm_name
            )
        ll_jobs.wait_for_jobs([config.JOB_ADD_VM_FROM_TEMPLATE])
        self.vms_to_remove.append(self.vm_name)
        self.add_nic_to_vm(self.vm_name)
        if start_vm:
            self.assertTrue(
                ll_vms.startVm(True, self.vm_name, wait_for_ip=True),
                "Unable to start vm %s cloned from template %s" % (
                    self.vm_name, template_name
                )
            )


@attr(tier=1)
class TestCase5734(BasicEnvironment):
    """
    Import a glance image as a template, then create a VM from this template
    """
    __test__ = True
    test_case = '5734'

    @polarion("RHEVM3-5734")
    def test_basic_import_glance_image(self):
        """
        - Import an image from the glance domain as a template
        - Create a VM from the template as thin copy
        - Create a VM from the template as cloned
        """
        self.basic_flow_import_image_as_template(
            self.new_template_name, True, self.storage_domain
        )
        vm_name = self.create_unique_object_name(
            config.OBJECT_TYPE_VM
        )
        self.basic_flow_clone_vm_from_template(
            vm_name, self.new_template_name,
            self.storage_domain
        )


@attr(tier=2)
class TestCase5735(BasicEnvironment):
    """
    Import multiple disks as templates
    """
    __test__ = True
    test_case = '5735'

    def setUp(self):
        super(TestCase5735, self).setUp()
        self.vm_names = list()
        self.templates = list()
        self.vm_names.append('vm_1_%s_%s' % (self.test_case, self.storage))
        self.vm_names.append('vm_2_%s_%s' % (self.test_case, self.storage))
        self.templates.append('template_sparse_%s' % self.test_case)
        self.templates.append('template_preallocated_%s' % self.test_case)

    @polarion("RHEVM3-5735")
    def test_import_multiple_images_as_template(self):
        """
        - Select multiple glance images from the glance domain
        - Import all of them as templates
        - Try to create VMs from the templates
        """
        for template_name, allocation_policy in zip(
                self.templates, [True, False]
        ):
            self.basic_flow_import_image_as_template(
                template_name, allocation_policy, self.storage_domain
            )
        for template_name, vm_name in zip(self.templates, self.vm_names):
            self.basic_flow_clone_vm_from_template(
                vm_name, template_name, self.storage_domain
            )


@attr(tier=2)
class TestCase5736(BasicEnvironment):
    """
    Import a glance template multiple times
    """
    __test__ = True
    test_case = '5736'
    templates = ["first_template", "second_template"]

    @polarion("RHEVM3-5736")
    def test_import_glance_image_more_than_once(self):
        """
        - Import an image from glance domain as a template
        - Import the same image again
        """
        for template_name in self.templates:
            self.basic_flow_import_image_as_template(
                template_name, True, self.storage_domain
            )


@attr(tier=2)
class TestCase5738(BasicEnvironment):
    """
    Import the same image both as a template and as disk
    """
    __test__ = True
    test_case = '5738'

    def setUp(self):
        super(TestCase5738, self).setUp()

    @polarion("RHEVM3-5738")
    def test_import_image_as_template_and_disk(self):
        """
        - Import an image from glance domain as a template
        - Import the same image as disk
        - Create a VM from the template
        - Attach the imported disk to a VM
        """
        self.basic_flow_import_image_as_template(
            self.new_template_name, True, self.storage_domain
        )
        self.vm_name_from_template = self.create_unique_object_name(
            config.OBJECT_TYPE_VM
        )
        self.basic_flow_clone_vm_from_template(
            self.vm_name_from_template, self.new_template_name,
            self.storage_domain, start_vm=False
        )
        vm_disk = ll_vms.getVmDisks(self.vm_name_from_template)[0].get_alias()
        ll_disks.updateDisk(
            True, vmName=self.vm_name_from_template, alias=vm_disk,
            bootable=True
        )

        self.basic_flow_import_image_as_disk(self.new_disk_alias, True)
        ll_jobs.wait_for_jobs([config.JOB_ADD_VM_FROM_TEMPLATE])
        self.assertTrue(
            ll_disks.attachDisk(
                True, self.new_disk_alias, self.vm_name_from_template
            ), "Failed to attach disk %s to vm %s" %
               (self.new_disk_alias, self.vm_name_from_template)
        )
        ll_vms.startVm(True, self.vm_name_from_template, config.VM_UP, True)
        status, output = storage_helpers.perform_dd_to_disk(
            self.vm_name_from_template, self.new_disk_alias
        )
        if not status:
            raise errors.DiskException(
                "Failed to write to imported image %s - %s" %
                (self.new_disk_alias, output)
            )
        logger.info(
            "Write operation to imported image from glance "
            "repository succeeded"
        )


@attr(tier=2)
class TestCase5739(BasicEnvironment):
    """
    Import glance image multiple times as a template
    (each on a different storage domain)
    """
    __test__ = True
    test_case = '5739'
    templates = ["template_sparse", "template_pre_allocated"]

    @polarion("RHEVM3-5739")
    def test_import_multiple_images_to_different_storages(self):
        """
        - Import multiple images from glance domain to different
        storage domains
        """
        for template_name, storage in zip(
                self.templates, self.storage_domains[:2]
        ):
            self.basic_flow_import_image_as_template(
                template_name, True, storage
            )


@attr(tier=2)
class TestCase5741(BasicEnvironment):
    """
    Create multiple VMs using import from a glance template
    """
    __test__ = True
    test_case = '5741'

    def setUp(self):
        super(TestCase5741, self).setUp()
        self.vm_names = list()
        self.vm_names.append('vm_1_%s_%s' % (self.test_case, self.storage))
        self.vm_names.append('vm_2_%s_%s' % (self.test_case, self.storage))

    @polarion("RHEVM3-5741")
    def test_create_multiple_vms_from_imported_template(self):
        """
        - Import an image from glance domain as template
        - Create several VMs in parallel as clone from imported glance
        template
        """
        self.basic_flow_import_image_as_template(
            self.new_template_name, True, self.storage_domain
        )
        for vm_name in self.vm_names:
            self.basic_flow_clone_vm_from_template(
                vm_name, self.new_template_name, self.storage_domain,
                wait=False
            )
            if ll_templates.get_template_state(self.new_template_name) \
                    == config.TEMPLATE_LOCKED:
                raise errors.TemplateException(
                    "Template %s should not be in locked state while "
                    "creating a VM from it" % self.new_template_name
                )


@attr(tier=2)
class TestCase5743(BasicEnvironment):
    """
    Copy image of imported template image
    """
    __test__ = True
    test_case = '5743'

    @polarion("RHEVM3-5743")
    def test_copy_imported_image(self):
        """
        - Import an image from glance domain as template
        - Copy the disk of the template to another data domain
        - Try to create a VM from the template with the copied disk
        """
        self.basic_flow_import_image_as_template(
            self.new_template_name, True, self.storage_domains[0],
            self.new_disk_alias
        )
        self.assertTrue(
            ll_disks.copy_disk(
                disk_name=self.new_disk_alias,
                target_domain=self.storage_domains[1]
            ), "Unable to copy disk %s to target domain %s" % (
                self.new_disk_alias, self.storage_domains[1]
            )
        )
        self.vm_name = self.create_unique_object_name(
            config.OBJECT_TYPE_VM
        )
        self.basic_flow_clone_vm_from_template(
            self.vm_name, self.new_template_name, self.storage_domains[1]
        )


@attr(tier=2)
class TestCase5746(BasicEnvironment):
    """
    Change disk interface
    """
    __test__ = True
    test_case = '5746'

    @polarion("RHEVM3-5746")
    def test_Change_disk_interface(self):
        """
        - Import an image from glance domain as template
        - Create a VM from the template
        - Try to change the disk interface of the VM
        (from Virt-IO to Virt-IO-SCSI)
        """
        self.basic_flow_import_image_as_template(
            self.new_template_name, True, self.storage_domain,
            self.new_disk_alias
        )
        self.vm_name = self.create_unique_object_name(
            config.OBJECT_TYPE_VM
        )
        self.clone_vm_args['storagedomain'] = self.storage_domain
        self.clone_vm_args['name'] = self.vm_name
        self.clone_vm_args['template'] = self.new_template_name

        self.basic_flow_clone_vm_from_template(
            self.vm_name, self.new_template_name, self.storage_domain,
            start_vm=False
        )
        self.assertTrue(
            ll_vms.updateVmDisk(
                True, self.vm_name, self.new_disk_alias,
                interface=config.VIRTIO_SCSI
            ), "Unable to change vm %s interface to interface %s" % (
                self.vm_name, config.VIRTIO_SCSI
            )
        )


@attr(tier=2)
class TestCase5683(BaseTestCase):
    """
    Export a template disk to glance repository
    """
    __test__ = True

    def setUp(self):
        """
        Create a template from a vm to export
        """
        # TODO: template name only allows 40 character length,
        # implement a proper solution for all occurences
        self.template_name = self.create_unique_object_name(
            config.OBJECT_TYPE_TEMPLATE
        )[0:40]
        storage_domains = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, self.storage
        )
        # Use one of the already created vms and export it to the
        # storage domain type of the test multiplier
        if not ll_templates.createTemplate(
            True, vm=config.VM_NAME[0], name=self.template_name,
            storagedomain=storage_domains[0]
        ):
            raise errors.TemplateException(
                "Unable to create template % from vm %s" %
                (self.template_name, config.VM_NAME[0])

            )
        self.disk = ll_templates.getTemplateDisks(self.template_name)[0]

    @polarion("RHEVM3-5683")
    def test_export_template_disk(self):
        """
        Export template disk to glance domain
        """
        self.assertTrue(
            ll_disks.export_disk_to_glance(
                True, self.disk.get_id(), config.GLANCE_DOMAIN
            ), "Unable to export disk %s to glance domain %s" %
            (self.disk.get_id(), config.GLANCE_DOMAIN)
        )

    def tearDown(self):
        """
        Remove the template and glance image
        """
        ll_disks.wait_for_disks_status([self.disk.get_id], key='id')
        if not ll_templates.removeTemplate(True, self.template_name):
            BaseTestCase.test_failed = True
            logger.error(
                "Failed to remove template %s", self.vms_to_remove
            )
        image_found = False
        for image in ll_sd.get_storage_domain_images(
            config.GLANCE_DOMAIN
        ):
            if self.disk.get_alias() == image.get_name():
                image_found = True
                if not ll_sd.remove_glance_image(
                    image.get_id(), config.GLANCE_HOSTNAME,
                    config.HOSTS_USER, config.HOSTS_PW
                ):
                    BaseTestCase.test_failed = True
                    logger.error(
                        "Failed to remove glance image %s",
                        self.disk.get_alias()
                    )
        if not image_found:
            BaseTestCase.test_failed = True
            logger.error(
                "Failed to find image in glance image %s repository %s",
                self.disk.get_alias(), self.glance_domain
                )
        BaseTestCase.teardown_exception()


@attr(tier=2)
class TestCase10696(BasicEnvironment):
    """
    Import a glance image as template
    """
    __test__ = True
    test_case = '2'
    template_name = 'glance_template_10696'
    disk_alias = 'glance_image_10697'

    @polarion("RHEVM3-10696")
    def test_import_glance_image_as_template(self):
        """
        - Import an image from glance domain as a template
        - Import the same image again
        """
        response_body = ll_sd.import_glance_image(
            config.GLANCE_DOMAIN, config.GOLDEN_GLANCE_IMAGE,
            self.storage_domain, config.CLUSTER_NAME,
            new_disk_alias=self.disk_alias,
            new_template_name=self.template_name,
            import_as_template=True, async=False, return_response_body=True
        )
        ll_jobs.wait_for_jobs([config.JOB_IMPORT_IMAGE], sleep=POLL_PERIOD)
        self.templates_to_remove.append(self.template_name)
        disk_id = ll_disks.get_disk_obj(self.disk_alias).get_id()
        self.assertTrue(
            disk_id in response_body,
            "Imported image's ID is not part of the import request "
            "response's body"
        )


@attr(tier=2)
class TestCase10697(BasicEnvironment):
    """
    Import a glance image as disk
    """
    __test__ = True
    test_case = '10697'
    disk_alias = 'glance_image_10697'
    disk_id = None

    @polarion("RHEVM3-10697")
    def test_import_glance_image_as_disk(self):
        """
        - Import an image from glance domain as a disk
        """
        response_body = ll_sd.import_glance_image(
            config.GLANCE_DOMAIN, config.GOLDEN_GLANCE_IMAGE,
            self.storage_domain, config.CLUSTER_NAME,
            new_disk_alias=self.disk_alias, async=False,
            return_response_body=True
        )
        ll_jobs.wait_for_jobs([config.JOB_IMPORT_IMAGE], sleep=POLL_PERIOD)
        self.disk_id = ll_disks.get_disk_obj(self.disk_alias).get_id()
        self.assertTrue(
            self.disk_id in response_body,
            "Imported image's ID is not part of the import request "
            "response's body"
        )

    def tearDown(self):
        super(TestCase10697, self).tearDown()
        if not ll_disks.deleteDisk(True, disk_id=self.disk_id):
            BaseTestCase.test_failed = True
        BaseTestCase.teardown_exception()
