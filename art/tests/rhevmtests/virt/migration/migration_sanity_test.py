#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt sanity testing for migration feature.
"""

import pytest
import logging
from art.unittest_lib import common
from art.test_handler import exceptions
from art.test_handler.tools import polarion
import art.unittest_lib.network as network_lib
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.jobs as ll_jobs
import rhevmtests.networking.helper as net_helper
from rhevmtests.virt import config


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
class TestMigrationVirtSanityCase1(common.VirtTest):
    """
    Virt Migration sanity case:
    Check migration of one VM
    """

    __test__ = True

    @classmethod
    def teardown_class(cls):
        """
        Stop vm
        """
        assert ll_vms.stop_vms_safely([config.MIGRATION_VM])

    @polarion("RHEVM3-3847")
    def test_migration(self):
        """
        Check migration of one VM
        """
        assert ll_vms.migrateVm(
            positive=True,
            vm=config.MIGRATION_VM
        ), "Failed to migrate VM: %s " % config.VM_NAME[0]


@common.attr(tier=1)
class TestMigrationVirtSanityCase2(common.VirtTest):
    """
    Virt Migration sanity case:
    Check maintenance on SPM host with one VM
     """
    __test__ = True

    @classmethod
    def setup_class(cls):
        if not net_helper.run_vm_once_specific_host(
            vm=config.VM_NAME[1], host=config.HOSTS[1],
            wait_for_up_status=True
        ):
            raise exceptions.VMException(
                "Cannot start VM %s on host %s" %
                (config.VM_NAME[1], config.HOSTS[1])
            )

    @classmethod
    def teardown_class(cls):
        """
        Stop VM
        """
        if not ll_vms.stopVm(
            True,
            config.VM_NAME[1]
        ):
            logger.error('Failed to stop vm %s', config.VM_NAME[1])

    @polarion("RHEVM3-12332")
    def test_maintenance_of_spm(self):
        """
        Check migration VM by putting host into maintenance
        """
        assert hl_vms.migrate_by_maintenance(
            vms_list=[config.VM_NAME[1]],
            src_host=network_lib.get_host(config.VM_NAME[1]),
            vm_os_type=config.RHEL_OS_TYPE_FOR_MIGRATION,
            vm_user=config.VMS_LINUX_USER,
            vm_password=config.VMS_LINUX_PW,
            connectivity_check=config.CONNECTIVITY_CHECK
        ), "Maintenance test failed"


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
@common.attr(tier=1)
class TestMigrationVirtSanityCase3(common.VirtTest):
    """
    Check cancel VM migration.
    Start migrate vm in different thread and cancel migration
    """

    __test__ = True
    cancel_vm_migrate = None

    @classmethod
    def setup_class(cls):
        cls.cancel_vm_migrate = False
        assert ll_vms.startVm(
            True, config.MIGRATION_VM, wait_for_status=config.VM_UP
        )

    @classmethod
    def teardown_class(cls):
        """
        If Cancel migration failed, remove migration job
        """
        if not cls.cancel_vm_migrate:
            remove_migration_job()

    @polarion("RHEVM3-14032")
    def test_cancel_migration(self):
        """
        Start migration VM using thread , cancel migration
        check the cancel succeed and VM stay on the source host.
        """

        logger.info("Start migration for VM: %s ", config.MIGRATION_VM)
        assert ll_vms.migrateVm(True, config.MIGRATION_VM, wait=False)
        ll_vms.wait_for_vm_states(
            config.MIGRATION_VM, states=[
                config.ENUMS['vm_state_migrating'],
                config.ENUMS['vm_state_migrating_from'],
                config.ENUMS['vm_state_migrating_to']
            ]
        )
        self.cancel_vm_migrate = hl_vms.cancel_vm_migrate(
            vm=config.MIGRATION_VM,
        )
        assert self.cancel_vm_migrate, (
            "Cancel migration didn't succeed for VM:%s " % config.MIGRATION_VM
        )
