#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
This is a helper module for run_once test
"""

import logging
import re

from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sd,
)
from rhevmtests.compute.virt import config

logger = logging.getLogger(__name__)


def run_once_with_boot_dev(boot_device, cdrom_image=None):
    """
    run once with chosen boot device

    :param boot_device: boot device
    :type boot_device: str
    :param cdrom_image: cdrom image name if device is cdrom
    :type cdrom_image: str
    :return: True, if succeeded to run once with boot device
    :rtype: bool
    """
    logger.info("Run once vm %s boot from %s", config.VM_RUN_ONCE, boot_device)
    if not ll_vms.runVmOnce(
        positive=True, vm=config.VM_RUN_ONCE, cdrom_image=cdrom_image,
        boot_dev=boot_device
    ):
        logger.error(
            "Failed to run once vm %s to boot from %s",
            config.VM_RUN_ONCE, boot_device
        )
        return False
    boot_list = ll_vms.get_vm_boot_sequence(config.VM_RUN_ONCE)
    if boot_list[0] == boot_device:
        logger.info("Succeeded to run once with %s", boot_device)
        return True
    logger.error(
        "Run once succeeded but with the wrong boot device. "
        "Expected: %s, got: %s", boot_device, boot_list[0]
    )
    return False


def set_iso_images_names():
    """
    Initializes images names from iso domain to use in run_once_test.py
    """
    iso_domain_files_obj = ll_sd.get_iso_domain_files(
        config.SHARED_ISO_DOMAIN_NAME
    )
    if not iso_domain_files_obj:
        logger.error("Iso domain: %s is empty", config.SHARED_ISO_DOMAIN_NAME)
        return
    iso_domain_files = [f.get_name() for f in iso_domain_files_obj]
    for f in iso_domain_files:
        if re.findall(config.CD_PATTERN, f):
            if not config.CDROM_IMAGE_1:
                config.CDROM_IMAGE_1 = f
            elif not config.CDROM_IMAGE_2:
                config.CDROM_IMAGE_2 = f
        elif re.findall(config.FLOPPY_PATTERN, f):
            if not config.FLOPPY_IMAGE:
                config.FLOPPY_IMAGE = f

    if None in [
        config.CDROM_IMAGE_1, config.CDROM_IMAGE_2, config.FLOPPY_IMAGE
    ]:
        logger.error(
            "Couldn't find 1 or more images required for this test in :%s "
            "iso doamin:", config.SHARED_ISO_DOMAIN_NAME
        )
        config.CDROM_IMAGE_2 = config.CDROM_IMAGE_1
