#! /usr/bin/python
# -*- coding: utf-8 -*-

import copy
import logging

import pytest

import art.rhevm_api.data_struct.data_structures as data_struct
import config
import helper
import rhevmtests.helpers as gen_helper
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms
)
from art.unittest_lib.common import testflow

logger = logging.getLogger("rhel_guest_image_fixture")


@pytest.fixture(scope="module")
def module_setup(request):
    """
    Setup: Create templates from glance with rhel guest images
    Teardown: Remove templates from engine
    """

    def fin():
        """
        Remove template
        """
        testflow.teardown("Remove templates")
        ll_templates.remove_templates(
            positive=True, templates=config.TEMPLATES_NAMES
        )

    request.addfinalizer(fin)

    testflow.setup("Import rhel guest images from glance")
    sd_name = ll_sd.get_master_storage_domain_name(
        datacenter_name=config.DC_NAME[0],
    )
    logger.info("Storage domain name: %s", sd_name)
    for image in config.RHEL_IMG_LIST:
        template_name = config.IMG_TO_TEMPLATE_NAME[image]
        disk_name = '%s_%s' % (template_name, 'disk')
        logger.info("Create template from rhel-guest-image in glance")
        assert ll_sd.import_glance_image(
            glance_repository=config.GLANCE_DOMAIN,
            glance_image=image,
            target_storage_domain=sd_name,
            target_cluster=config.CLUSTER_NAME[0],
            new_disk_alias=disk_name,
            new_template_name=template_name,
            import_as_template=True
        )
        assert ll_disks.wait_for_disks_status([disk_name])
        assert ll_templates.waitForTemplatesStates(
            [config.IMG_TO_TEMPLATE_NAME[image]]
        )
        assert ll_templates.addTemplateNic(
            positive=True,
            template=template_name,
            name=config.NIC_NAME[0],
            network=config.MGMT_BRIDGE,
        )


@pytest.fixture(scope="class")
def class_setup_vm_cases(request, module_setup):
    """
    Create VM for each guest image template with initialization parameters in
    order to run it using cloud init.
    """

    def fin():
        """

        1. Update use private ssh key to false
        2. Restore initialization to none
        3. Restore user to default(cloud_user)
        4. Remove vms
        """
        testflow.teardown("Reset parameters and remove VM")
        config.USER_PKEY = False
        request.node.cls.initialization = None
        config.VM_USER_CLOUD_INIT = config.VM_USER_CLOUD_INIT_1
        assert ll_vms.safely_remove_vms(vms=config.TESTED_VMS_NAMES)

    request.addfinalizer(fin)

    initialization = data_struct.Initialization(
        **copy.deepcopy(helper.initialization_params)
    )

    for vm_name in config.TESTED_VMS_NAMES:
        testflow.step(
            "Create new vm %s from template with initialization"
            "parameters", vm_name
        )
        assert ll_vms.createVm(
            positive=True, vmName=vm_name,
            vmDescription=vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=config.TAMPLATE_TO_VM_NAME[vm_name],
            os_type=config.VM_OS_TYPE,
            display_type=config.VM_DISPLAY_TYPE,
            initialization=initialization,
            memory=config.GB,
            max_memory=gen_helper.get_gb(4),
            ballooning=False
        )
        logger.info("update disk to bootable")
        disk_id = ll_disks.getObjDisks(
            name=vm_name, get_href=False
        )[0].id
        assert ll_disks.updateDisk(
            positive=True, vmName=vm_name,
            id=disk_id, bootable=True
        )
