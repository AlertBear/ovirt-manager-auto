#! /usr/bin/python
# -*- coding: utf-8 -*-


import copy
import logging
import pytest
from art.unittest_lib.common import testflow
import art.rhevm_api.data_struct.data_structures as data_struct
import rhevmtests.helpers as gen_helper
import rhevmtests.virt.helper as helper
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms
)
import rhevmtests.virt.config as config


logger = logging.getLogger("cloud_init_fixture")


@pytest.fixture(scope="module")
def cloud_init_setup(request):
    """
    Cloud init setup module
    Setup: Create template from glance with rhel guest image
    Teardown: Remove template from engine
    """

    def fin():
        """
        Remove template
        """
        testflow.teardown("Remove template")
        ll_templates.remove_template(
            positive=True, template=config.CLOUD_INIT_TEMPLATE
        )

    request.addfinalizer(fin)

    testflow.setup("Import image from glance")
    logger.info("Import image to master storage domain")
    sd_name = ll_sd.get_master_storage_domain_name(
        datacenter_name=config.DC_NAME[0],
    )
    logger.info("Storage domain name: %s", sd_name)
    logger.info("Create template from rhel-guest-image in glance")
    ll_sd.import_glance_image(
        glance_repository=config.GLANCE_DOMAIN,
        glance_image=config.CLOUD_INIT_IMAGE,
        target_storage_domain=sd_name,
        target_cluster=config.CLUSTER_NAME[0],
        new_disk_alias=config.CLOUD_INIT_VM_DISK_NAME,
        new_template_name=config.CLOUD_INIT_TEMPLATE,
        import_as_template=True
    )
    assert ll_disks.wait_for_disks_status([config.CLOUD_INIT_VM_DISK_NAME])
    assert ll_templates.waitForTemplatesStates([config.CLOUD_INIT_TEMPLATE])


@pytest.fixture()
def case_setup(request, cloud_init_setup):
    args = request.node.get_marker("initialization_param")
    args_per_condition = request.node.get_marker("per_condition")
    initialization_params = args.kwargs if args else {}
    args_per_condition_params = (
        args_per_condition.kwargs if args_per_condition else {}
    )

    def fin():
        """

        1. Update use private ssh key to false
        2. Restore initialization to none
        3. Restore user to default(cloud_user)
        4. Remove vm
        """
        testflow.teardown("Reset parameters and remove VM")
        config.USER_PKEY = False
        request.node.cls.initialization = None
        config.VM_USER_CLOUD_INIT = config.VM_USER_CLOUD_INIT_1
        ll_vms.safely_remove_vms(vms=[config.CLOUD_INIT_VM_NAME])

    request.addfinalizer(fin)

    testflow.setup("Init parameters and create VM")
    init_dict = init_parameters(
        args_per_condition_params, initialization_params
    )
    initialization = init_dict["initialization"]
    request.node.cls.initialization = init_dict["initialization"]
    if init_dict["per_condition"]["set_authorized_ssh_keys"]:
        logger.info("Set authorized ssh keys")
        config.VM_USER_CLOUD_INIT = config.VM_USER_CLOUD_INIT_1
        initialization.set_authorized_ssh_keys(
            config.SLAVE_HOST.get_ssh_public_key()
        )
        config.USER_PKEY = True

    logger.info(
        "Create new vm %s from cloud init template with initialization %s"
        "parameters", config.CLOUD_INIT_VM_NAME, vars(initialization)
    )

    assert ll_vms.createVm(
        positive=True, vmName=config.CLOUD_INIT_VM_NAME,
        vmDescription=config.CLOUD_INIT_VM_NAME,
        cluster=config.CLUSTER_NAME[0],
        template=config.CLOUD_INIT_TEMPLATE, os_type=config.VM_OS_TYPE,
        display_type=config.VM_DISPLAY_TYPE,
        initialization=initialization,
        nic=config.NIC_NAME[0],
        network=config.MGMT_BRIDGE,
        memory=2 * config.GB,
        max_memory=gen_helper.get_gb(4)
    )
    logger.info("update disk to bootable")
    disk_id = ll_disks.getObjDisks(
        name=config.CLOUD_INIT_VM_NAME, get_href=False
    )[0].id
    ll_disks.updateDisk(
        positive=True, vmName=config.CLOUD_INIT_VM_NAME,
        id=disk_id, bootable=True
    )


def init_parameters(args_per_condition, initialization_params):
    """
    initialize test parameters
    Args:
    args_per_condition(dict): dict with per conditions for the test
    initialization_params (dict): dict with update parameter of
    initialization obj

    Returns:
         dict: return dictionary with test parameters
    """
    res = {}
    update_params = copy.deepcopy(helper.initialization_params)
    for key, val in initialization_params.iteritems():
        if key == "user_name":
            config.VM_USER_CLOUD_INIT = val
        update_params[key] = val
    res["initialization"] = data_struct.Initialization(**update_params)

    args_per_condition_params = copy.deepcopy(config.PRE_CASE_CONDITIONS)
    for key, val in args_per_condition.iteritems():
        args_per_condition_params[key] = val
    res["per_condition"] = args_per_condition_params
    return res
