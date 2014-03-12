"""
Test exposing BZ 1000789, checks that creating a vm
from a template with no disks is working
"""
import logging
from art.unittest_lib import BaseTestCase as TestCase

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import disks
from art.test_handler.tools import tcms, bz
import art.test_handler.exceptions as errors

import config

LOGGER = logging.getLogger(__name__)

ENUMS = config.ENUMS
STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')

VM_NO_DISKS = 'no_disk_vm'
TEMPLATE_NO_DISKS = 'no_disks_template'
VM_SHARED_DISK = 'shared_disk_vm'
TEMPLATE_SHARED_DISK = 'shared_disk_template'
VM_DIRECT_LUN = 'direct_lun_vm'
TEMPLATE_DIRECT_LUN = 'direct_lun_template'

def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    # Backup all luns info
    lun_address_backup = config.PARAMETERS.as_list('lun_address')
    lun_target_backup = config.PARAMETERS.as_list('lun_target')
    lun_backup = config.PARAMETERS.as_list('lun')

    # Keep only one lun in the config, so build setup won't use both luns
    config.PARAMETERS['lun_address'] = config.PARAMETERS.as_list(
        'lun_address')[0]
    config.PARAMETERS['lun_target'] = config.PARAMETERS.as_list(
        'lun_target')[0]
    config.PARAMETERS['lun'] = config.PARAMETERS.as_list('lun')[0]

    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.DATA_CENTER_TYPE, basename=config.BASENAME)

    #Restore second lun
    config.PARAMETERS['lun_address'] = lun_address_backup
    config.PARAMETERS['lun_target'] = lun_target_backup
    config.PARAMETERS['lun'] = lun_backup

    # Add a VM without disks
    if not ll_vms.addVm(True, name=VM_NO_DISKS,
                        storagedomain=config.DOMAIN_NAME_1,
                        cluster=config.CLUSTER_NAME):
        raise errors.VMException("Cannot create vm %s" % VM_NO_DISKS)

    # Create a template from vm without disks
    template_kwargs = {"vm": VM_NO_DISKS,
                       "name": TEMPLATE_NO_DISKS}

    if not templates.createTemplate(True, **template_kwargs):
        raise errors.TemplateException("Can't create template "
                                       "from vm %s" % VM_NO_DISKS)

    # Add a VM with shared disk
    if not ll_vms.addVm(True, name=VM_SHARED_DISK,
                        storagedomain=config.DOMAIN_NAME_1,
                        cluster=config.CLUSTER_NAME):
        raise errors.VMException("Cannot create vm %s" % VM_SHARED_DISK)

    # Add a shared disk
    shared_disk_kwargs = {"interface": "virtio",
                          "alias": "shared_disk",
                          "format": "raw",
                          "size": config.DISK_SIZE,
                          "bootable": True,
                          "storagedomain": config.DOMAIN_NAME_1,
                          "shareable": True,
                          "sparse": False,
                          "type_": "nfs"
                          }

    if not disks.addDisk(True, **shared_disk_kwargs):
        raise errors.DiskException("Cannot add direct lun disk to vm %s"
                                   % VM_DIRECT_LUN)

    # Create a template from vm with shared disk
    template_kwargs = {"vm": VM_SHARED_DISK,
                       "name": TEMPLATE_SHARED_DISK}

    if not templates.createTemplate(True, **template_kwargs):
        raise errors.TemplateException("Can't create template "
                                       "from vm %s" % VM_SHARED_DISK)

    # Add a VM with direct lun disk
    if not ll_vms.addVm(True, name=VM_DIRECT_LUN,
                        storagedomain=config.DOMAIN_NAME_1,
                        cluster=config.CLUSTER_NAME):
        raise errors.VMException("Cannot create vm %s" % VM_DIRECT_LUN)

    lun_address = config.PARAMETERS['lun_address'][1] if \
        len(config.PARAMETERS['lun_address']) > 1 \
        else config.PARAMETERS['lun_address'][0]
    lun_target = config.PARAMETERS['lun_target'][1] if \
        len(config.PARAMETERS['lun_target']) > 1 \
        else config.PARAMETERS['lun_target'][0]
    # Add a direct lun disk
    direct_lun_disk_kwargs = {"interface": "virtio",
                              "alias": "direct_lun_disk",
                              "format": "cow",
                              "size": config.DISK_SIZE,
                              "bootable": True,
                              "storagedomain": config.DOMAIN_NAME_1,
                              "lun_address": lun_address,
                              "lun_target": lun_target,
                              "lun_id": config.PARAMETERS['lun'][1],
                              "type_": "iscsi"
                              }

    if not disks.addDisk(True, **direct_lun_disk_kwargs):
        raise errors.DiskException("Cannot add direct lun disk to vm %s"
                                   % VM_DIRECT_LUN)

    # Create a template from vm without disks
    template_kwargs = {"vm": VM_DIRECT_LUN,
                       "name": TEMPLATE_DIRECT_LUN}

    if not templates.createTemplate(True, **template_kwargs):
        raise errors.TemplateException("Can't create template "
                                       "from vm %s" % VM_DIRECT_LUN)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME,
                                   vdc=config.VDC,
                                   vdc_password=config.VDC_PASSWORD)


class TestCase305452(TestCase):
    """
    test exposing https://bugzilla.redhat.com/show_bug.cgi?id=1000789
    scenario:
    * create a VM from a template without disks

    https://tcms.engineering.redhat.com/case/231819/?from_plan=2339
    """
    __test__ = True
    tcms_plan_id = '2339'
    tcms_test_case = '231819'

    @bz(1000789)
    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_vm_from_template(self):
        """ creates vms from templates
        """
        LOGGER.info("Creating vm from template without disks")
        new_vm_name = "%s_new" % VM_NO_DISKS
        self.assertTrue(ll_vms.createVm(True, new_vm_name,
                                        "VM for bug 1000789",
                                        template=TEMPLATE_NO_DISKS,
                                        cluster=config.CLUSTER_NAME))

        LOGGER.info("Creating vm from template with shared disk")
        new_vm_name = "%s_new" % VM_SHARED_DISK
        self.assertTrue(ll_vms.createVm(True, new_vm_name,
                                        "VM for bug 1000789",
                                        template=TEMPLATE_SHARED_DISK,
                                        cluster=config.CLUSTER_NAME))

        LOGGER.info("Creating vm from template with direct lun")
        new_vm_name = "%s_new" % VM_DIRECT_LUN
        self.assertTrue(ll_vms.createVm(True, new_vm_name,
                                        "VM for bug 1000789",
                                        template=TEMPLATE_DIRECT_LUN,
                                        cluster=config.CLUSTER_NAME))


    @classmethod
    def teardown_class(cls):
        """
        Wait for un-finished tasks
        """
        test_utils.wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                                  config.DEFAULT_DATA_CENTER_NAME)
