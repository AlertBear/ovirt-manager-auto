#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Cloud init - init class
"""
import logging
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import config

logger = logging.getLogger("Virt_cloud_init")


def setup_package():
    if not config.PPC_ARCH:
        logger.info("Cloud init setup")
        logger.info("Find NFS storage domain to import template")
        sd_name = ll_sd.getStorageDomainNamesForType(
            datacenter_name=config.DC_NAME,
            storage_type=config.STORAGE_TYPE
        )[0]
        logger.info("Storage domain name: %s", sd_name)
        logger.info("Create template from rhel-guest-image in glance")
        if not ll_sd.import_glance_image(
            glance_repository=config.GLANCE_DOMAIN,
            glance_image=config.RHEL_IMAGE_GLANCE_IMAGE,
            target_storage_domain=sd_name,
            target_cluster=config.CLUSTER_NAME[0],
            new_disk_alias='cloud_init',
            new_template_name=config.CLOUD_INIT_TEMPLATE,
            import_as_template=True
        ):
            raise errors.TemplateException(
                "Failed to create template %s from glance" %
                config.CLOUD_INIT_TEMPLATE
            )
        else:
            logger.info("skip since PPC arch")


def teardown_package():
    if not config.PPC_ARCH:
        logger.info("Cloud init teardown")
        logger.info("Remove template %s", config.CLOUD_INIT_TEMPLATE)
        if not ll_templates.removeTemplate(
            positive=True, template=config.CLOUD_INIT_TEMPLATE
        ):
            logger.error(
                "Failed to remove template %s", config.CLOUD_INIT_TEMPLATE
            )
        else:
            logger.info("Successfully removed %s.", config.CLOUD_INIT_TEMPLATE)
    else:
        logger.info("skip since PPC arch")
