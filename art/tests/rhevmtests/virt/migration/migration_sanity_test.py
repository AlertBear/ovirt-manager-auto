#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt sanity testing for migration feature.
"""

import logging
import threading as thread
import time
from art.unittest_lib import common
from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.unittest_lib.network as network_lib
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.jobs as ll_jobs
from rhevmtests.virt import config
import rhevmtests.virt.helper as virt_helper


logger = logging.getLogger("Virt_Migration_Cases")
RHEL_OS_TYPE_FOR_MIGRATION = "rhel"


def remove_migration_job():
    """
    Remove migration job
    """

    remove_migration_job_query = (
        "UPDATE job SET status = 'FINISHED' WHERE status = 'STARTED' "
        "and action_type='MigrateVM'"
    )
    logger.info('Check for unfinished migration jobs in DB')
    active_jobs = ll_jobs.get_active_jobs()
    if active_jobs:
        for job in active_jobs:
            if 'Migrating VM' in job.description:
                logger.warning(
                    'There is unfinished migration job : %s', job.description
                )
                logger.info("Remove migration job")
                config.ENGINE.db.psql(remove_migration_job_query)


@common.attr(tier=1)
class TestMigrationVirtSanityCase(common.VirtTest):
    """
    Virt sanity cases:
    1. Check migration of one VM
    2. Check maintenance with one VM
    """

    __test__ = True

    @polarion("RHEVM3-3847")
    def test_migration(self):
        """
        Check migration of one VM
        """
        self.assertTrue(
            ll_vms.migrateVm(
                positive=True,
                vm=config.VM_NAME[0]
            ),
            "Failed to migrate VM: %s " % config.VM_NAME[0]
        )

    @polarion("RHEVM3-12332")
    def test_migration_maintenance(self):
        """
        Check migration for one VM
        by putting host into maintenance
        """

        logger.info(
            "Check that migration for one VM "
            "by putting the host into maintenance succeed"
        )
        self.assertTrue(
            hl_vms.migrate_by_maintenance(
                vms_list=[config.VM_NAME[0]],
                src_host=network_lib.get_host(config.VM_NAME[0]),
                vm_os_type=config.RHEL_OS_TYPE_FOR_MIGRATION,
                vm_user=config.VMS_LINUX_USER,
                vm_password=config.VMS_LINUX_PW
            ),
            "Maintenance test with one VM failed"
        )


@common.attr(tier=1)
class TestCancelVMMigration(common.VirtTest):
    """
    Check cancel VM migration.
    Start migrate vm in different thread and cancel migration
    Note: VM running memory load to in increase migration time
    """

    __test__ = True
    cancel_vm_migrate = None

    @classmethod
    def setup_class(cls):
        cls.cancel_vm_migrate = False
        logger.info('Start vm %s', config.VM_NAME[1])
        if not ll_vms.startVm(
            True,
            config.VM_NAME[1],
            wait_for_ip=True
        ):
            raise exceptions.VMException(
                'Failed to start vm %s' %
                config.VM_NAME[1]
            )
        if not virt_helper.load_vm_memory(
            config.VM_NAME[1],
            memory_size='0.5',
            reuse_memory='False'
        ):
            raise exceptions.VMException("Failed to load VM memory")

    @classmethod
    def teardown_class(cls):
        """
        1. If Cancel migration failed, remove migration job
        2. Stop VM
        """
        if not cls.cancel_vm_migrate:
            remove_migration_job()
        logger.info('Stop vm: %s', config.VM_NAME[1])
        if not ll_vms.stopVm(
            True,
            config.VM_NAME[1]
        ):
            logger.error('Failed to stop vm %s', config.VM_NAME[1])

    @polarion("RHEVM3-14032")
    def test_cancel_migration(self):
        """
        Start migration VM using thread , VM running memory load
        to add delay to migration. And cancel migration
        check the cancel succeed and VM stay on the source host.
        """

        logger.info("Start migration for VM: %s ", config.VM_NAME[1])
        migration_thread = thread.Thread(
            name='migration_thread', target=ll_vms.migrateVm, args=(
                False, config.VM_NAME[1], False, False)
        )
        migration_thread.run()
        time.sleep(5)
        logger.info("Cancel migration for VM: %s ", config.VM_NAME[1])
        self.cancel_vm_migrate = hl_vms.cancel_vm_migrate(
            vm=config.VM_NAME[1],
            wait=True
        )
        self.assertTrue(
            self.cancel_vm_migrate,
            "Cancel migration didn't succeed for VM:%s " % config.VM_NAME[1]
        )
