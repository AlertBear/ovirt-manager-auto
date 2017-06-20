"""
3.4 Glance sanity
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_4_Storage_Import_Template_Entities
"""
import logging

import pytest
from art.unittest_lib.common import testflow

from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms
)
from art.test_handler import exceptions as errors
from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    tier2,
    tier3,
)
from art.unittest_lib import StorageTest as BaseTestCase
from rhevmtests.storage import config, helpers as storage_helpers

from fixtures import (initializer_class, extract_template_disks)

from rhevmtests.storage.fixtures import (
    remove_vms, remove_templates, create_template, remove_glance_image,
    delete_disks
)

logger = logging.getLogger(__name__)
POLL_PERIOD = 10


@pytest.mark.usefixtures(
    initializer_class.__name__,
    remove_vms.__name__,
    delete_disks.__name__,
    remove_templates.__name__,
)
class BasicEnvironment(BaseTestCase):
    """
    This class implements the base setUp and tearDown functions as well
    as common functions used by the various tests
    """
    __test__ = False
    test_case = None
    glance_image = None
    vm_name = None

    def add_nic_to_vm(self, vm_name):
        if not ll_vms.addNic(
                True, vm=vm_name, name=config.NIC_NAME[0],
                network=config.MGMT_BRIDGE, vnic_profile=config.MGMT_BRIDGE,
                plugged='true', linked='true'
        ):
            raise errors.NetworkException(
                'Unable to add nic to vm %s' % vm_name
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
        if wait:
            ll_jobs.wait_for_jobs(
                [config.JOB_IMPORT_IMAGE], sleep=POLL_PERIOD
            )
            if new_disk_alias is not None:
                ll_disks.wait_for_disks_status(
                    [new_disk_alias]
                )
            if not ll_templates.check_template_existence(template_name):
                raise errors.TemplateException(
                    "Failed to import image from glance as template"
                )
            ll_templates.waitForTemplatesStates(template_name)

    def basic_flow_clone_vm_from_template(
        self, vm_name, template_name, storage_domain, wait=True, start_vm=True
    ):
        self.clone_vm_args['storagedomain'] = storage_domain
        self.clone_vm_args['name'] = vm_name
        self.clone_vm_args['template'] = template_name
        self.clone_vm_args['wait'] = wait

        assert ll_vms.cloneVmFromTemplate(**self.clone_vm_args), (
            'Unable to create VM %s for test' % vm_name
        )
        ll_jobs.wait_for_jobs([config.JOB_ADD_VM_FROM_TEMPLATE])
        self.add_nic_to_vm(vm_name)
        ll_vms.wait_for_vm_states(vm_name, [config.VM_DOWN])
        if start_vm:
            assert ll_vms.startVm(True, vm_name, config.VM_UP, True), (
                "Unable to start VM %s cloned from template %s" % (
                    vm_name, template_name
                )
            )


class TestCase5734(BasicEnvironment):
    """
    Import a glance image as a template, then create a VM from this template
    """
    __test__ = True
    test_case = '5734'

    @polarion("RHEVM3-5734")
    @tier3
    def test_basic_import_glance_image(self):
        """
        - Import an image from the glance domain as a template
        - Create a VM from the template as thin copy
        - Create a VM from the template as cloned
        """
        self.basic_flow_import_image_as_template(
            self.templates_names[0], True, self.storage_domain,
            self.disks_to_remove[0]
        )
        self.basic_flow_clone_vm_from_template(
            self.vm_names[0], self.templates_names[0],
            self.storage_domain
        )


class TestCase10689(BasicEnvironment):
    """
    RHEVM3-10689 - Override template name when importing an image from glance
    """
    __test__ = True
    test_case = '10689'

    @polarion("RHEVM3-10689")
    @tier3
    def test_override_template_name(self):
        """
        Test flow:
        - Import an image from Glance to RHEV as a template, using a new name
        -> Template should be imported with the new name
        """
        # Ensure there's no template with the same name in the system
        assert not bool(
            ll_templates.get_template_obj(self.templates_names[0])
        ), "Template with name %s exists already in the environment" % (
            self.templates_names[0]
        )
        self.basic_flow_import_image_as_template(
            self.templates_names[0], True, self.storage_domain,
            self.disks_to_remove[0]
        )
        assert ll_templates.get_template_obj(
            self.templates_names[0]
        ), "Template with name %s does not exist" % self.templates_names[0]


class TestCase5735(BasicEnvironment):
    """
    Import multiple disks as templates
    """
    __test__ = True
    test_case = '5735'

    @polarion("RHEVM3-5735")
    @tier3
    def test_import_multiple_images_as_template(self):
        """
        - Select multiple glance images from the glance domain
        - Import all of them as templates
        - Try to create VMs from the templates
        """
        for template_name, allocation_policy in zip(
                self.templates_names, [True, False]
        ):
            self.basic_flow_import_image_as_template(
                template_name, allocation_policy, self.storage_domain,
                self.disks_to_remove[0]
            )
        for template_name, vm_name in zip(self.templates_names, self.vm_names):
            self.basic_flow_clone_vm_from_template(
                vm_name, template_name, self.storage_domain
            )


class TestCase5736(BasicEnvironment):
    """
    Import a glance template multiple times
    """
    __test__ = True
    test_case = '5736'

    @polarion("RHEVM3-5736")
    @tier3
    def test_import_glance_image_more_than_once(self):
        """
        - Import an image from glance domain as a template
        - Import the same image again
        """
        for template_name, disk_alias in zip(
            self.templates_names, [
                                   self.disks_to_remove[0],
                                   self.disks_to_remove[1]
                                   ]
        ):
            self.basic_flow_import_image_as_template(
                template_name, True, self.storage_domain, disk_alias
            )


class TestCase5738(BasicEnvironment):
    """
    Import the same image both as a template and as disk
    """
    __test__ = True
    test_case = '5738'

    @polarion("RHEVM3-5738")
    @tier3
    def test_import_image_as_template_and_disk(self):
        """
        - Import an image from glance domain as a template
        - Import the same image as disk
        - Create a VM from the template
        - Attach the imported disk to a VM
        """
        self.basic_flow_import_image_as_template(
            self.templates_names[0], True, self.storage_domain,
            self.disks_to_remove[0]
        )
        self.basic_flow_clone_vm_from_template(
            self.vm_names[0], self.templates_names[0],
            self.storage_domain, start_vm=False
        )
        vm_disk = ll_vms.getVmDisks(self.vm_names[0])[0].get_alias()
        ll_disks.updateDisk(
            True, vmName=self.vm_names[0], alias=vm_disk, bootable=True
        )
        self.basic_flow_import_image_as_disk(self.disks_to_remove[1], True)
        ll_jobs.wait_for_jobs([config.JOB_ADD_VM_FROM_TEMPLATE])
        assert ll_disks.attachDisk(
            True, self.disks_to_remove[1], self.vm_names[0]
        ), "Failed to attach disk %s to vm %s" % (
            self.disks_to_remove[1], self.vm_names[0]
        )
        ll_vms.startVm(True, self.vm_names[0], config.VM_UP, True)
        status, output = storage_helpers.perform_dd_to_disk(
            self.vm_names[0], self.disks_to_remove[1]
        )
        if not status:
            raise errors.DiskException(
                "Failed to write to imported image %s - %s" %
                (self.disks_to_remove[1], output)
            )
        logger.info(
            "Write operation to imported image from glance "
            "repository succeeded"
        )


class TestCase5739(BasicEnvironment):
    """
    Import glance image multiple times as a template
    (each on a different storage domain)
    """
    __test__ = True
    test_case = '5739'
    templates_names = ["template_sparse", "template_pre_allocated"]

    @polarion("RHEVM3-5739")
    @tier3
    def test_import_multiple_images_to_different_storages(self):
        """
        - Import multiple images from glance domain to different
        storage domains
        """
        for template_name, storage, second_disk_alias in zip(
                self.templates_names, self.storage_domains[:2],
                [self.disks_to_remove[0], self.disks_to_remove[1]]
        ):
            self.basic_flow_import_image_as_template(
                template_name, True, storage, second_disk_alias
            )


class TestCase5741(BasicEnvironment):
    """
    Create multiple VMs using import from a glance template
    """
    __test__ = True
    test_case = '5741'

    @polarion("RHEVM3-5741")
    @tier3
    def test_create_multiple_vms_from_imported_template(self):
        """
        - Import an image from glance domain as template
        - Create several VMs in parallel as clone from imported glance
        template
        """
        self.basic_flow_import_image_as_template(
            self.templates_names[0], True, self.storage_domain,
            self.disks_to_remove[0]
        )
        for vm_name in self.vm_names:
            self.basic_flow_clone_vm_from_template(
                vm_name, self.templates_names[0], self.storage_domain,
                wait=False
            )
            if ll_templates.get_template_state(
                self.templates_names[0]
            ) == config.TEMPLATE_LOCKED:
                raise errors.TemplateException(
                    "Template %s should not be in locked state while"
                    "creating a VM from it" % self.templates_names[0]
                )


class TestCase5743(BasicEnvironment):
    """
    Copy image of imported template image
    """
    __test__ = True
    test_case = '5743'

    @polarion("RHEVM3-5743")
    @tier2
    def test_copy_imported_image(self):
        """
        - Import an image from glance domain as template
        - Copy the disk of the template to another data domain
        - Try to create a VM from the template with the copied disk
        """
        self.basic_flow_import_image_as_template(
            self.templates_names[0], True, self.storage_domains[0],
            self.disks_to_remove[0]
        )
        testflow.setup(
            "Copying template disk %s to storage domains %s",
            self.disks_to_remove[0], self.storage_domains[1]
        )
        assert ll_disks.copy_disk(
            disk_name=self.disks_to_remove[0],
            target_domain=self.storage_domains[1]
        ), "Unable to copy disk %s to target domain %s" % (
            self.disks_to_remove[0], self.storage_domains[1]
        )
        assert ll_disks.wait_for_disks_status(
            self.disks_to_remove[0], timeout=240
        ), (
            "Disk %s was not in the expected state 'OK" %
            self.disks_to_remove[0]
        )
        ll_jobs.wait_for_jobs([config.JOB_MOVE_COPY_DISK])

        self.basic_flow_clone_vm_from_template(
            self.vm_names[0], self.templates_names[0], self.storage_domains[1]
        )


@bz({'1349594': {}})
class TestCase5746(BasicEnvironment):
    """
    Change disk interface
    """
    __test__ = True
    test_case = '5746'

    @polarion("RHEVM3-5746")
    @tier3
    def test_Change_disk_interface(self):
        """
        - Import an image from glance domain as template
        - Create a VM from the template
        - Try to change the disk interface of the VM
        (from Virt-IO to Virt-IO-SCSI)
        """
        self.basic_flow_import_image_as_template(
            self.templates_names[0], True, self.storage_domain,
            self.disks_to_remove[0]
        )
        self.clone_vm_args['storagedomain'] = self.storage_domain
        self.clone_vm_args['name'] = self.vm_names[0]
        self.clone_vm_args['template'] = self.templates_names[0]

        self.basic_flow_clone_vm_from_template(
            self.vm_names[0], self.templates_names[0], self.storage_domain,
            start_vm=False
        )
        assert ll_disks.updateDisk(
            True, vmName=self.vm_names[0], alias=self.disks_to_remove[0],
            interface=config.VIRTIO_SCSI
        ), "Unable to change vm %s interface to interface %s" % (
            self.vm_names[0], config.VIRTIO_SCSI
        )


@bz({'1411123': {}})
@pytest.mark.usefixtures(
    create_template.__name__,
    extract_template_disks.__name__,
    remove_glance_image.__name__
)
class TestCase5683(BaseTestCase):
    """
    Export a template disk to glance repository
    """
    __test__ = True

    @polarion("RHEVM3-5683")
    @tier2
    def test_export_template_disk(self):
        """
        Export template disk to glance domain
        """
        assert ll_disks.export_disk_to_glance(
            True, self.disk.get_id(), config.GLANCE_DOMAIN
        ), "Unable to export disk %s to glance domain %s" % (
            self.disk.get_id(), config.GLANCE_DOMAIN
        )


@bz({'1411123': {}})
class TestCase10696(BasicEnvironment):
    """
    Import a glance image as template
    """
    __test__ = True
    test_case = '10696'
    template_name = 'glance_template_10696'
    disk_alias = 'glance_image_10696'

    @polarion("RHEVM3-10696")
    @tier3
    def test_import_glance_image_as_template(self):
        """
        - Import an image from glance domain as a template
        - Import the same image again
        """
        response_body = ll_sd.import_glance_image(
            config.GLANCE_DOMAIN, config.GOLDEN_GLANCE_IMAGE,
            self.storage_domain, config.CLUSTER_NAME,
            new_disk_alias=self.disks_to_remove[0],
            new_template_name=self.templates_names[0],
            import_as_template=True, async=False, return_response_body=True
        )
        ll_jobs.wait_for_jobs([config.JOB_IMPORT_IMAGE], sleep=POLL_PERIOD)
        self.templates_names.append(self.templates_names[0])
        disk_id = ll_disks.get_disk_obj(self.disks_to_remove[0]).get_id()
        assert disk_id in response_body, (
            "Imported image's ID is not part of the import request "
            "response's body"
        )


@bz({'1411123': {}})
class TestCase10697(BasicEnvironment):
    """
    Import a glance image as disk
    """
    __test__ = True
    test_case = '10697'
    disk_name = 'glance_image_10697'
    disk_id = None

    @polarion("RHEVM3-10697")
    @tier2
    def test_import_glance_image_as_disk(self):
        """
        - Import an image from glance domain as a disk
        """
        response_body = ll_sd.import_glance_image(
            config.GLANCE_DOMAIN, config.GOLDEN_GLANCE_IMAGE,
            self.storage_domain, config.CLUSTER_NAME,
            new_disk_alias=self.disks_to_remove[0], async=False,
            return_response_body=True
        )
        ll_jobs.wait_for_jobs([config.JOB_IMPORT_IMAGE], sleep=POLL_PERIOD)
        self.disk_id = ll_disks.get_disk_obj(self.disks_to_remove[0]).get_id()
        assert self.disk_id in response_body, (
            "Imported image's ID is not part of the import request "
            "response's body"
        )
