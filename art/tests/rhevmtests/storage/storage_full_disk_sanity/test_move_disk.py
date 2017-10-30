"""
Move Disk Plan
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_3_6/3_6_Storage_Disk_General
"""
import config
import pytest
import logging
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    templates as ll_templates,
    vms as ll_vms,
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    StorageTest as TestCase,
    tier3,
)
from rhevmtests.storage.fixtures import (
    add_disk, create_vm, create_template, create_storage_domain,
    deactivate_domain, delete_disks, initialize_storage_domains, delete_disk
)
from rhevmtests.storage.fixtures import remove_vm  # noqa
logger = logging.getLogger(__name__)


@pytest.mark.usefixtures(
    add_disk.__name__,
    delete_disk.__name__
)
class TestCase16757(TestCase):
    """
    Move disk from storage domain A to storage domain A - should fail
    """
    __test__ = True

    @polarion("RHEVM-16757")
    @tier3
    def test_move_disk_to_source_domain(self):
        """
        Move disk from source domain to source domain
        """
        assert not ll_disks.move_disk(
            disk_name=self.disk_name, target_domain=self.storage_domain
        ), "Succeeded to move disk from source domain to source domain"


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    delete_disks.__name__,
)
class TestCase16758(TestCase):
    """
    Move locked disk - should fail
    """
    __test__ = True
    disk_size = 10 * config.GB

    @polarion("RHEVM-16758")
    @tier3
    def test_move_locked_disk(self):
        """
        Move locked disk
        """
        assert ll_disks.addDisk(
            True, alias=self.disk_name, provisioned_size=self.disk_size,
            format=config.RAW_DISK, storagedomain=self.storage_domain,
            sparse=False
        ), "Failed to create shared disk %s" % self.disk_name
        self.disks_to_remove.append(self.disk_name)
        ll_disks.wait_for_disks_status(
            [self.disk_name], status=config.DISK_LOCKED
        )
        assert not ll_disks.move_disk(
            disk_name=self.disk_name, target_domain=self.storage_domain_1
        ), "Succeeded to move locked disk %s" % self.disk_name


@pytest.mark.usefixtures(
    create_template.__name__,
)
class TestCase16759(TestCase):
    """
    Move template disk - should fail
    """
    __test__ = True

    @polarion("RHEVM-16759")
    @tier3
    def test_move_template_disk(self):
        """
        Move template disk
        """
        template_disk = ll_templates.getTemplateDisks(
            self.template_name)[0]
        target_sd = ll_disks.get_other_storage_domain(
            template_disk.get_id(), key='id'
        )
        assert not ll_disks.move_disk(
            disk_id=template_disk.get_id(), target_domain=target_sd
        ), "Succeeded to move template's disk %s" % template_disk.get_alias()


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    add_disk.__name__,
    delete_disk.__name__,
    deactivate_domain.__name__,
)
class TestCase16760(TestCase):
    """
    Move disk to deactivated storage domain - should fail
    """
    __test__ = True
    sd_to_deactivate_index = 1

    @polarion("RHEVM-16760")
    @tier3
    def test_move_disk_to_deactivated_sd(self):
        """
        Move disk to storage domain in maintenance
        """
        assert not ll_disks.move_disk(
            disk_name=self.disk_name, target_domain=self.sd_to_deactivate
        ), (
            "Succeeded to move disk %s to deactivated storage domain"
            % self.disk_name
        )


@pytest.mark.usefixtures(
    create_vm.__name__,
    create_storage_domain.__name__,
)
class TestCase16762(TestCase):
    """
    Move disk based on template to storage domain without a copy of it -
    should fail
    """
    __test__ = True

    @polarion("RHEVM-16762")
    @tier3
    def test_move_disk_based_on_template_to_sd_without_a_copy(self):
        """
        Move disk based on template to storage domain without a copy of it
        """
        vm_disk = ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        assert not ll_disks.move_disk(
            disk_name=vm_disk, target_domain=self.new_storage_domain
        ), (
            "Succeeded to move disk %s based on template to storage domain "
            "that doesn't contain copy of the template's disk"
            % vm_disk
        )
