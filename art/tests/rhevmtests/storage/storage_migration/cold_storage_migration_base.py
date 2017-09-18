"""
Storage cold migration sanity test
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_Live_Storage_Migration
"""
from threading import Thread
from time import sleep
import os
import logging
import pytest
import config
import shlex
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_dc,
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.utils.log_listener import watch_logs
from art.test_handler import exceptions
from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib.common import StorageTest, testflow
from art.rhevm_api.utils import test_utils
import rhevmtests.storage.helpers as storage_helpers
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from rhevmtests.storage.fixtures import (
    create_snapshot, remove_templates, remove_vms, initialize_storage_domains,
    create_disks_with_fs, create_dc, create_storage_domain, clean_dc,
    import_image_from_glance, create_vms,
)
from rhevmtests.storage.storage_migration.fixtures import (
    create_vm_on_different_sd, remove_storage_domain,
    create_disks_with_fs_for_vms, unblock_connectivity_teardown,
)
from rhevmtests.storage.fixtures import remove_vm  # noqa F401

import storage_migration_base as basePlan

LIVE_MIGRATION_TIMEOUT = 5 * 60

logger = logging.getLogger(__name__)


class ColdMoveBase(StorageTest):
    """
    Base class for all destructive cases for cold move
    """
    file_name = 'test_file'
    add_file_on_each_disk = True
    regex = None
    target_sd = None

    def cold_migrate_vm_and_verify(self, source=None, target=None):
        """
        Cold migrate VM disks and verify migration
        """
        testflow.step("Migrate VM %s disks", self.vm_name)

        for vm, disks_and_mounts in self.DISKS_MOUNTS_EXECUTOR.iteritems():
            for disk_id in disks_and_mounts['disks']:
                disk_name = ll_disks.get_disk_obj(
                    disk_id, attribute='id'
                ).get_alias()
                source_sd = ll_disks.get_disk_storage_domain_name(
                    disk_name=disk_name, vm_name=vm
                ) if source is None else source
                target_sd = ll_disks.get_other_storage_domain(
                    disk=disk_name, vm_name=vm,
                    force_type=config.MIGRATE_SAME_TYPE
                ) if target is None else target
                testflow.step(
                    "Migrate disk %s of VM %s to %s", disk_name, vm, target_sd
                )
                ll_vms.migrate_vm_disk(
                    vm_name=vm, disk_name=disk_name, target_sd=target_sd
                )
                storage_helpers.wait_for_disks_and_snapshots(
                    [self.vm_name], live_operation=config.LIVE_MOVE
                )
                testflow.step(
                    "Verify disk %s of VM %s moved to %s",
                    disk_name, vm, target_sd
                )
                assert ll_vms.verify_vm_disk_moved(
                    vm_name=vm, disk_name=disk_name, source_sd=source_sd,
                    target_sd=target_sd
                ), "Failed to move %s attached to %s from %s to %s" % (
                    disk_name, vm, target_sd, source_sd
                )
        assert self.check_files_after_operation(), (
            "Files doesn't found or match on VM %s disks" % self.vm_name
        )

    def check_if_disk_moved(self, disk_name, vm, source_sd, moved):
        """
        Check whether disk moved or not and return status according to 'moved'
        parameter

        Args:
            disk_name (str): Name of the disk
            vm (str): Name of the VM disk
            source_sd (str): Name of the source storage domain
            moved (bool): specified if migration should succeed

        Returns:
            bool: True if disk status is according to 'moved', False otherwise
        """
        testflow.step(
            "Verify disk %s of VM %s moved from %s", disk_name, vm, source_sd
        )
        return moved != ll_vms.verify_vm_disk_moved(vm, disk_name, source_sd)

    def verify_cold_move(self, source_sd, moved=True):
        """
        Verifies if the disks have been moved

        Args:
            source_sd (str): Name of the source storage domain
            moved (bool): specified if migration should succeed

        Returns:
            unsatisfied_disks (List): List of disks_names that failed/succeeded
                to move according to 'moved' parameter, None if verification
                succeeded
        """
        unsatisfied_disks = list()

        for vm, disk_and_mounts in self.DISKS_MOUNTS_EXECUTOR.iteritems():
            for disk in disk_and_mounts['disks']:
                disk_name = (
                    ll_disks.get_disk_obj(disk, attribute='id').get_alias()
                )
                if self.check_if_disk_moved(disk_name, vm, source_sd, moved):
                    logging.info(
                        "%s to move disk %s",
                        "Failed" if moved else "Succeed", disk_name
                    )
                    unsatisfied_disks.append(disk_name)
        return None if not unsatisfied_disks else unsatisfied_disks

    def verify_cold_move_different_sources(self, source_sds, moved=True):
        """
        Verifies if disks from different storage domains have been moved

        Args:
            source_sds (str): Name of the source storage domains
            moved (bool): Specified if migration should succeed

        Returns:
            unsatisfied_disks (List): List of disks_names that failed/succeeded
                to move according to 'moved' parameter, None if verification
                succeeded
        """
        unsatisfied_disks = list()

        for vm, disk_and_mounts in self.DISKS_MOUNTS_EXECUTOR.iteritems():
            for disk, source_sd in zip(disk_and_mounts['disks'], source_sds):
                disk_name = (
                    ll_disks.get_disk_obj(disk, attribute='id').get_alias()
                )
                if self.check_if_disk_moved(disk_name, vm, source_sd, moved):
                    logging.info(
                        "%s to move disk %s",
                        "Failed" if moved else "Succeed", disk_name
                    )
                    unsatisfied_disks.append(disk_name)
        return None if not unsatisfied_disks else unsatisfied_disks

    def check_files_after_operation(self):
        """
        Verify file existence and checksum after operation performed
        """
        testflow.step("Start VMs %s", self.DISKS_MOUNTS_EXECUTOR.keys())
        ll_vms.start_vms(
            vm_list=self.DISKS_MOUNTS_EXECUTOR.keys(), max_workers=4,
            wait_for_status=config.VM_UP
        )
        for vm, disk_and_mounts in self.DISKS_MOUNTS_EXECUTOR.iteritems():
            for mount_point in disk_and_mounts['mount_points']:
                full_path = os.path.join(mount_point, self.file_name)
                executor = disk_and_mounts['executor']
                testflow.step("Verify file %s exists", full_path)
                if not storage_helpers.does_file_exist(
                    vm, full_path, vm_executor=executor
                ):
                    logger.error("File %s not found on VM %s", full_path, vm)
                    return False
                testflow.step("Verify file %s checksum", full_path)
                checksum = storage_helpers.checksum_file(
                    vm, full_path, vm_executor=executor
                )
                if checksum != (
                    self.CHECKSUM_FILES_RESULTS[self.storage][full_path]
                ):
                    logger.error(
                        "Checksum of file %s doesn't match original"
                        " checksum: %s, current checksum: %s", full_path,
                        self.CHECKSUM_FILES_RESULTS[self.storage][full_path],
                        checksum
                    )
                    return False
        return True

    def check_volumes_after_operation(self, disks_ids, initial_vol_count):
        """
        Verify that the number of volumes after preforming cold storage
        migration is equal to the volume number before it (cleanup preformed)

        Args:
            disks_ids (list): List of disk ids to count the volumes for
            initial_vol_count (int): Volume count before preforming cold
                storage migration

        Raises:
            AssertionError: In case the current volume count not equal to
                initial volume count
        """
        current_vol_count = storage_helpers.get_disks_volume_count(disks_ids)
        assert current_vol_count == initial_vol_count, (
            """Leftovers found, initial volume count: %s,
             current volume count: %s""" % (
                initial_vol_count, current_vol_count
            )
        )


@pytest.mark.usefixtures(
    create_disks_with_fs.__name__,
)
class BaseKillSpmVdsm(basePlan.BaseTestCase, ColdMoveBase):
    """
    Base class for Kill SPM VDSM tests
    """
    exception = False

    def basic_flow(self, migration_succeed=True):
        disk_ids = self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['disks']

        initial_vol_count = storage_helpers.get_disks_volume_count(disk_ids)
        spm_host = ll_hosts.get_spm_host(config.HOSTS)
        spm_ip = ll_hosts.get_host_ip(spm_host)
        self.target_sd = ll_disks.get_other_storage_domain(
            disk_ids[0], self.vm_name, force_type=config.MIGRATE_SAME_TYPE,
            key='id'
        )

        t = Thread(
            target=watch_logs, args=(
                config.ENGINE_LOG, self.regex, config.KILL_VDSM,
                LIVE_MIGRATION_TIMEOUT, config.VDC, config.HOSTS_USER,
                config.VDC_ROOT_PASSWORD, spm_ip, config.HOSTS_USER,
                config.HOSTS_PW
            )
        )
        t.start()
        sleep(5)

        testflow.step("Migrate VM %s", self.vm_name)
        try:

            ll_vms.migrate_vm_disks(
                self.vm_name, wait=False,
                same_type=config.MIGRATE_SAME_TYPE,
                ensure_on=config.LIVE_MOVE,
                target_domain=self.target_sd
            )
        except exceptions.DiskException:
            testflow.step("Exception raised during first storage migration")
            self.exception = True
        finally:
            wait_for_jobs([config.JOB_MOVE_COPY_DISK])

        t.join()
        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_name], live_operation=config.LIVE_MOVE
        )
        testflow.step(
            "Verify if migration succeeded after kill SPM VDSM process"
        )
        unsetisfied_disks = self.verify_cold_move(
            source_sd=self.storage_domain, moved=not self.exception
        )
        if unsetisfied_disks is not None:
            for disk in unsetisfied_disks:
                assert (
                    ll_disks.get_disk_obj(disk).get_status() == config.DISK_OK
                ), "Disk %s is not in state 'OK'" % disk
        self.check_volumes_after_operation(disk_ids, initial_vol_count)
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.WAIT_FOR_SPM_INTERVAL
        ), 'SPM was not elected on data-center %s' % config.DATA_CENTER_NAME

        assert ll_hosts.wait_for_hosts_states(True, spm_host), (
            "Host %s failed to reach status UP" % spm_host
        )


class TestCase18995(BaseKillSpmVdsm):
    """
    Kill VDSM on SPM before completing CopyImageGroupVolumesDataCommand
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False
    regex = "CreateVolumeContainerCommand"

    @polarion("RHEVM3-118995")
    @tier4
    def test_kill_spm_vdsm_before_copy_image_cmd(self):
        """
        Actions:
            - Create VM with disks and files on them
            - Cold move the disks
            - Kill VDSM on the SPM host before CopyImageGroupVolumesDataCommand
            - Restart VDSM
            - Cold move the VM disks again
        Expected Results:
            - We should fail in migrating all disks for the first time
            - We should succeed in migrating all disks for the second time
            - Data on the disks should remain
        """
        self.basic_flow()
        if self.exception:
            self.cold_migrate_vm_and_verify()


class TestCase19059(BaseKillSpmVdsm):
    """
    Kill VDSM on SPM during CopyDataCommand on HSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False
    regex = "CopyDataCommand"

    @polarion("RHEVM-19059")
    @tier4
    def test_kill_spm_vdsm_during_copy_data_cmd(self):
        """
        Actions:
            - Create VM with disks and files on them
            - Cold move the disks
            - Kill VDSM on the SPM host during CopyDataCommand
        Expected Results:
            - We should succeed in migrating all disks
            - Data on the disks should remain
        """
        self.basic_flow()
        assert self.check_files_after_operation()


@pytest.mark.usefixtures(
    create_disks_with_fs.__name__,
)
@bz({'1488015': {}})
class BaseRestartEngine(basePlan.BaseTestCase, ColdMoveBase):
    """
    Base class for restart engine tests
    """
    def basic_flow(self):
        """
        - Check initial volume count before migrating the disks
        - Move each disk to different storage domain
        - When the regex appears on the log -> restart the engine
        - Verify move ended successfully for the disks who manage to complete
          the move before the restart of the engine
        - Verify volume count remains the same
        """
        disk_ids = self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['disks']
        target_domains = list()
        src_domains = list()
        initial_vol_count = storage_helpers.get_disks_volume_count(disk_ids)

        for disk_id in disk_ids:
            disk_name = ll_disks.get_disk_obj(
                disk_id, attribute='id'
            ).get_alias()
            ll_disks.get_disk_storage_domain_name(disk_name)
            src_domains.append(
                ll_disks.get_disk_storage_domain_name(disk_name)
            )
            disk_sd = ll_disks.get_other_storage_domain(
                disk_id, self.vm_name,
                force_type=config.MIGRATE_SAME_TYPE, key='id'
            )
            target_domains.append(disk_sd)

        t = Thread(
            target=watch_logs, args=(
                config.ENGINE_LOG, self.regex, None, LIVE_MIGRATION_TIMEOUT,
                config.VDC, config.VDC_ROOT_USER, config.VDC_ROOT_PASSWORD,
            )
        )
        t.start()
        sleep(5)

        testflow.step("Migrate VM %s disks", self.vm_name)
        for disk_id, target_sd in zip(disk_ids, target_domains):
            disk_name = ll_disks.get_disk_obj(
                disk_id, attribute='id'
            ).get_alias()
            ll_vms.migrate_vm_disk(
                vm_name=self.vm_name, disk_name=disk_name, target_sd=target_sd,
                wait=False
            )

        testflow.step(
            "Wait for command %s to appear on the engine log", self.regex
        )
        t.join()
        test_utils.restart_engine(config.ENGINE, 5, 30)

        hl_dc.ensure_data_center_and_sd_are_active(config.DATA_CENTER_NAME)
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.WAIT_FOR_SPM_INTERVAL
        ), 'SPM was not elected on data-center %s' % config.DATA_CENTER_NAME

        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_name], live_operation=config.LIVE_MOVE
        )

        unsatisfied_disks = self.verify_cold_move_different_sources(
            source_sds=src_domains, moved=False
        )
        if unsatisfied_disks is not None:
            for disk in unsatisfied_disks:
                assert (
                    ll_disks.get_disk_obj(disk).get_status() == config.DISK_OK
                ), "Disk %s is not in state 'OK'" % disk
        self.check_volumes_after_operation(disk_ids, initial_vol_count)


class TestCase19060_during_CopyImageGroupWithDataCmd(BaseRestartEngine):
    """
    Restart Engine during 3 different operations on the engine
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False
    regex = "CopyImageGroupWithDataCommand"

    @polarion("RHEVM-19060")
    @tier4
    def test_restart_engine_during_copy_image_group_with_data_cmd(self):
        self.basic_flow()
        self.cold_migrate_vm_and_verify()


class TestCase19060_during_CloneImageGroupVolumesStructureCmd(
    BaseRestartEngine
):
    """
    Restart Engine during 3 different operations on the engine
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False
    regex = "CloneImageGroupVolumesStructureCommand"

    @polarion("RHEVM-19060")
    @tier4
    def test_restart_enigne_during_clone_image_group_vol_structure_cmd(self):
        self.basic_flow()
        self.cold_migrate_vm_and_verify()


class TestCase19060_during_CreateVolumeContainerCommand(BaseRestartEngine):
    """
    Restart Engine during 3 different operations on the engine
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False
    regex = "CreateVolumeContainerCommand"

    @polarion("RHEVM-19060")
    @tier4
    def test_restart_engine_during_create_vol_container_cmd(self):
        self.basic_flow()
        self.cold_migrate_vm_and_verify()


class TestCase19061(BaseRestartEngine):
    """
    Restart Engine during 2 different move operations on SPM and HSM
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False
    regex = "CopyImageGroupVolumesDataCommand"

    @polarion("RHEVM-19061")
    @tier4
    def test_restart_engine_during_two_commands(self):
        self.basic_flow()
        self.regex = "CopyDataCommand"
        self.basic_flow()
        self.cold_migrate_vm_and_verify()


@pytest.mark.usefixtures(
    create_disks_with_fs.__name__,
    unblock_connectivity_teardown.__name__,
)
class BaseBlockConnection(basePlan.BaseTestCase, ColdMoveBase):
    """
    Base class for block connection tests
    """
    __test__ = False

    hsm_host = None
    host_ip = None
    regex = "CopyVolumeDataVDSCommand"

    def basic_flow(self, target, source=None, migration_succeed=False):
        """
        - Cold migrate VM disks to target domain
        - Block connection from the host which execute the regex command
          to given target
        - Un-block the connection
        - Cold migrate the VM disks again
        """
        disk_ids = self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['disks']
        initial_vol_count = storage_helpers.get_disks_volume_count(disk_ids)

        def f():
            """
            Function that searches for the first occurrence of the hsm host and
            initialize a Host resource object
            """
            watch_logs(
                files_to_watch=config.ENGINE_LOG, regex=self.regex,
                time_out=LIVE_MIGRATION_TIMEOUT, ip_for_files=config.VDC,
                username=config.HOSTS_USER, password=config.VDC_ROOT_PASSWORD,
            )
            if source is None:
                self.hsm_host = storage_helpers.get_hsm_host(
                    config.JOB_MOVE_COPY_DISK, config.COPY_VOLUME_VERB, True
                )
            testflow.step(
                "HSM host %s found for %s verb", config.SOURCE,
                config.COPY_VOLUME_VERB
            )
        t = Thread(target=f, args=())
        t.start()
        sleep(5)
        testflow.step("Migrate VM %s", self.vm_name)
        ll_vms.migrate_vm_disks(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE,
            ensure_on=config.LIVE_MOVE, target_domain=self.target_sd
        )
        testflow.step(
            "Wait for command %s to appear on the engine log", self.regex
        )
        t.join()

        if source is None:
            assert self.hsm_host, "HSM host was not found"
            self.host_ip = self.hsm_host.ip
        else:
            self.host_ip = source
        config.SOURCE = self.host_ip

        assert config.SOURCE, "HSM host was not found"

        try:
            testflow.step(
                "Block connection between %s to %s", config.SOURCE, target
            )
            assert storage_helpers.setup_iptables(
                config.SOURCE, target, block=True
            ), "Failed to block connection"

            hl_dc.ensure_data_center_and_sd_are_active(config.DATA_CENTER_NAME)
            assert ll_hosts.wait_for_spm(
                config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
                config.WAIT_FOR_SPM_INTERVAL
            ), (
                'SPM was not elected on data-center %s' % (
                    config.DATA_CENTER_NAME
                )
            )
            testflow.step(
                "Unblock connection from %s to %s", config.SOURCE, target
            )
            assert storage_helpers.setup_iptables(
                config.SOURCE, target, block=False
            ), "Failed to unblock connection from host %s to %s" % (
                config.SOURCE, target
            )
        finally:
            wait_for_jobs([config.JOB_MOVE_COPY_DISK])
            storage_helpers.wait_for_disks_and_snapshots(
                [self.vm_name], live_operation=config.LIVE_MOVE
            )
        unsetisfied_disks = self.verify_cold_move(
            source_sd=self.storage_domain, moved=migration_succeed
        )
        if unsetisfied_disks is not None:
            logger.info(
                "Disks %s %s to move to storage domain %s",
                unsetisfied_disks,
                "Failed" if migration_succeed else "Succeed", self.target_sd
            )
            testflow.step("Verify disks %s status is 'OK'", unsetisfied_disks)
            for disk in unsetisfied_disks:
                assert (
                    ll_disks.get_disk_obj(disk).get_status() == config.DISK_OK
                ), "Disk %s is not in state 'OK'" % disk

        self.check_volumes_after_operation(disk_ids, initial_vol_count)
        assert self.check_files_after_operation()
        assert ll_vms.stop_vms_safely([self.vm_name])
        self.cold_migrate_vm_and_verify()


class TestCase19095(BaseBlockConnection):
    """
    Cold Move with disconnection of network between engine and
    HSM running CopyVolumeDataVDSCommand
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False

    @polarion("RHEVM-19095")
    @tier4
    def test_disconnect_engine_and_hsm_during_CopyVolumeDataVDSCommand(self):
        """
        Actions:
            - Create VM with block based disks and files on them
            - Cold move the VM disks to another block based storage domain
            - Disconnect the network between the engine and HSM running
              the CopyDataCommand
        Expected Results:
            - We should succeed in migrating all disks
            - Data on the disks should remain
        """
        self.target_sd = ll_disks.get_other_storage_domain(
            self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['disks'][0],
            self.vm_name, force_type=config.MIGRATE_SAME_TYPE, key='id'
        )
        config.TARGET = {'address': [config.ENGINE.host.ip]}
        self.basic_flow(target=config.TARGET, migration_succeed=True)


class TestCase19028(BaseBlockConnection):
    """
    Storage connectivity issues between hosts and source domain
    HSM running CopyVolumeDataVDSCommand
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False

    @polarion("RHEVM-19028")
    @tier4
    def test_disconnect_source_domain_and_hsm_during_CopyVolumeDataVDSCommand(
        self
    ):
        """
        Actions:
            - Create VM with disks and files on them
            - Cold move the VM disks
            - During the move operation block the source domain
              using iptables on the HSM
        Expected Results:
            - We should fail in migrating all disks
            - Data on the disks should remain
        """
        self.target_sd = ll_disks.get_other_storage_domain(
            self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['disks'][0],
            self.vm_name, force_type=config.MIGRATE_SAME_TYPE, key='id'
        )
        found, address = ll_sd.getDomainAddress(True, self.storage_domain)
        assert found, "IP for storage domain %s not found" % (
            self.storage_domain
        )
        config.TARGET = address
        self.basic_flow(target=config.TARGET)


class TestCase19007(BaseBlockConnection):
    """
    Storage connectivity issues between hosts and source domain
    HSM running CopyVolumeDataVDSCommand
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False

    regex = 'CloneImageGroupVolumesStructureCommand'

    @polarion("RHEVM-19007")
    @tier4
    def test_disconnect_spm_host_and_hsm_during_CopyVolumeDataVDSCommand(self):
        """
        Actions:
            - Create VM with disks and files on them
            - Cold move the VM disks
            - During the move operation block the connection from the SPM host
             using iptables to the target storage domain
        Expected Results:
            - We should fail in migrating all disks
            - Data on the disks should remain
        """
        self.target_sd = ll_disks.get_other_storage_domain(
            self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['disks'][0],
            self.vm_name, force_type=config.MIGRATE_SAME_TYPE, key='id'
        )
        found, address = ll_sd.getDomainAddress(True, self.target_sd)
        assert found, "IP for storage domain %s not found" % (
            self.target_sd
        )
        config.TARGET = address
        spm_host = ll_hosts.get_spm_host(config.HOSTS)
        config.SOURCE = ll_hosts.get_host_ip(spm_host)
        self.basic_flow(target=config.TARGET, source=config.SOURCE)


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    remove_vms.__name__,
    create_vms.__name__,
    create_disks_with_fs_for_vms.__name__,
)
class TestCase19012(ColdMoveBase):
    """
    Cold Move multiple VM's disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False
    num_of_vms = 4

    @polarion("RHEVM-19012")
    @tier3
    def test_move_multiple_vms_with_multiple_disks(self):
        """
        Actions:
            - Create multiple VMs with disks and files on them
            - Cold move the VMs disks
        Expected Results:
            - We should succeed in migrating all disks
            - Data on the disks should remain
        """
        vms_names = self.DISKS_MOUNTS_EXECUTOR.keys()
        for vm, disks_and_mounts in self.DISKS_MOUNTS_EXECUTOR.iteritems():
            target_sd = ll_disks.get_other_storage_domain(
                disks_and_mounts['disks'][0],
                force_type=config.MIGRATE_SAME_TYPE, key='id'
            )
            testflow.step("Migrate VM %s", vm)
            ll_vms.migrate_vm_disks(
                vm, wait=False, same_type=config.MIGRATE_SAME_TYPE,
                ensure_on=config.LIVE_MOVE, target_domain=target_sd
            )
        storage_helpers.wait_for_disks_and_snapshots(
            vms_to_wait_for=vms_names, live_operation=config.LIVE_MOVE
        )
        assert not self.verify_cold_move(source_sd=self.storage_domain)
        assert self.check_files_after_operation()


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    create_dc.__name__,
    create_storage_domain.__name__,
    clean_dc.__name__,
    import_image_from_glance.__name__,
    remove_templates.__name__,
    remove_storage_domain.__name__,
    create_vm_on_different_sd.__name__,
    create_disks_with_fs.__name__,
)
class TestCase19016(ColdMoveBase):
    """
    Domain upgraded to 4.1
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False

    vm_names = list()
    dc_version = "4.0"
    dc_upgrade_version = "4.1"
    templates_names = list()
    image_name = config.GLANCE_QCOW2v2_IMAGE_NAME

    def get_other_type_of_storage_domain(self):
        """
        Return required storage domain type in order to create new domain
        """
        if self.storage == (
                config.STORAGE_TYPE_NFS or config.STORAGE_TYPE_GLUSTER
        ):
            return config.STORAGE_TYPE_ISCSI
        else:
            return config.STORAGE_TYPE_NFS

    @polarion("RHEVM-19016")
    @tier3
    def test_move_to_upgraded_domain(self):
        """
        Actions:
            - Create VM with disks and files on them in 4.0 data center
            - Upgrade the data center to 4.1
            - Create new storage domain
            - Cold move VM disks to the new storage domain
        Expected Results:
            - We should succeed in migrating all disks
            - Data on the disks should remain
        """
        testflow.step(
            "Update cluster %s to version %s",
            self.cluster_name, self.dc_upgrade_version
        )
        assert ll_clusters.updateCluster(
            True, self.cluster_name,
            version=self.dc_upgrade_version,
        ), "Failed to upgrade compatibility version of cluster"

        testflow.step(
            "Update data center %s to version %s",
            self.new_dc_name, self.dc_upgrade_version
        )
        assert ll_dc.update_datacenter(
            positive=True, datacenter=self.new_dc_name,
            version=self.dc_upgrade_version
        ), "Failed to upgrade data center %s to version %s" % (
            self.new_dc_name, self.dc_upgrade_version
        )

        testflow.step(
            "Add storage domain to data center %s" % self.new_dc_name
        )
        storage_type = self.storage if config.MIGRATE_SAME_TYPE else (
            self.get_other_type_of_storage_domain()
        )
        storage_helpers.add_storage_domain(
            storage_domain=self.second_storage_domain_name,
            data_center=self.new_dc_name,
            index=1, storage_type=storage_type
        )

        self.cold_migrate_vm_and_verify(
            source=self.new_storage_domain,
            target=self.second_storage_domain_name
        )


@pytest.mark.usefixtures(
    create_disks_with_fs.__name__,
    create_snapshot.__name__,
)
class TestCase19035(basePlan.BaseTestCase, ColdMoveBase):
    """
    Cold move a disk containing a snapshot, which has been extended
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """

    @polarion("RHEVM-19035")
    @tier2
    def test_move_vm_with_extended_snapshot(self):
        """
        Actions:
            - Create VM with disks and files on them
            - Create snapshot to the disks
            - Extend VM disks
            - Cold move VM disks
        Expected Results:
            - We should succeed in migrating all disks
            - Data on the disks should remain
        """
        vm_disks_names = [
            disk.get_alias() for disk in ll_vms.getVmDisks(vm=self.vm_name)
            ]

        testflow.step("Extend VM %s disks", self.vm_name)
        for disk in vm_disks_names:
            if not ll_vms.is_bootable_disk(
                vm=self.vm_name, disk=disk, attr='name'
            ):
                assert ll_vms.extend_vm_disk_size(
                    True, self.vm_name, disk=disk,
                    provisioned_size=3 * config.GB
                ), "Failed to extend disk %s" % disk

        assert ll_disks.wait_for_disks_status(vm_disks_names)

        self.target_sd = ll_disks.get_other_storage_domain(
            vm_disks_names[0], self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE
        )
        self.cold_migrate_vm_and_verify()


@pytest.mark.usefixtures(
    initialize_storage_domains.__name__,
    create_disks_with_fs.__name__,
    create_snapshot.__name__,
)
class TestCase19020(basePlan.BaseTestCase, ColdMoveBase):
    """
    Cold move of VM with multiple snapshots
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage_4_0/4_1_Storage_Cold_Move
    """
    __test__ = False
    second_file_name = 'test_file_2'

    checksum_res = dict()

    def create_file_after_snapshot(self, executor):
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name, wait_for_status=config.VM_UP,
            wait_for_ip=True
        )
        for mount_point in (
            self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['mount_points']
        ):
            assert storage_helpers.create_file_on_vm(
                self.vm_name, self.second_file_name, mount_point, executor
            ), "Failed to create file %s on VM %s with path %s" % (
                self.second_file_name, self.vm_name, mount_point
            )
            full_path = os.path.join(mount_point, self.second_file_name)
            assert storage_helpers.write_content_to_file(
                self.vm_name, full_path, vm_executor=executor
            ), "Failed to write content to file %s on VM %s" % (
                full_path, self.vm_name
            )
            self.checksum_res[full_path] = (
                storage_helpers.checksum_file(
                    self.vm_name, full_path, executor
                )
            )
            rc, _, error = executor.run_cmd(cmd=shlex.split('sync'))
            if rc:
                logger.error(
                    "Failed to run command 'sync' on %s, error: %s",
                    self.vm_name, error
                )
        assert ll_vms.stop_vms_safely(vms_list=[self.vm_name])

    @polarion("RHEVM-19020")
    @tier2
    def test_move_vm_with_multiple_snapshots(self):
        """
        Actions:
            - Create VM with disks and files on them
            - Create snapshot with all the VM's disks
            - Create another file on each disk
            - Cold move VM disks
            - Preview the snapshot
        Expected Results:
            - We should succeed in migrating all disks
            - Data on the disks should remain
        """
        vm_executor = self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['executor']
        testflow.step(
            "Create another file on each disk of VM %s after snapshot added",
            self.vm_name
        )
        self.create_file_after_snapshot(vm_executor)
        vm_disk_objects = ll_vms.getVmDisks(vm=self.vm_name)

        testflow.step("Migrate VM %s", self.vm_name)
        target_sd = ll_disks.get_other_storage_domain(
            vm_disk_objects[0].get_alias(), self.vm_name,
            force_type=config.MIGRATE_SAME_TYPE
        )
        ll_vms.migrate_vm_disks(
            self.vm_name, wait=False, same_type=config.MIGRATE_SAME_TYPE,
            ensure_on=config.LIVE_MOVE, target_domain=target_sd
        )
        storage_helpers.wait_for_disks_and_snapshots(
            [self.vm_name], config.LIVE_MOVE
        )

        testflow.step(
            "Preview VM %s snapshot %s", self.vm_name,
            self.snapshot_description
        )
        assert ll_vms.preview_snapshot(
            positive=True, vm=self.vm_name,
            description=self.snapshot_description
        ), "Failed to preview snapshot %s" % self.snapshot_description

        assert not self.verify_cold_move(source_sd=self.storage_domain)
        assert self.check_files_after_operation()

        testflow.step("Stop VM %s", self.vm_name)
        assert ll_vms.stop_vms_safely([self.vm_name])

        testflow.step(
            "Undo VM %s snapshot %s preview", self.vm_name,
            self.snapshot_description
        )
        assert ll_vms.undo_snapshot_preview(positive=True, vm=self.vm_name), (
            "Failed to undo snapshot %s preview" % self.snapshot_description
        )
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name, wait_for_status=config.VM_UP,
            wait_for_ip=True
        )
        for mount_point in (
            self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['mount_points']
        ):
            full_path = os.path.join(mount_point, self.second_file_name)
            assert (
                self.checksum_res[full_path] == storage_helpers.checksum_file(
                    self.vm_name, full_path, vm_executor
                )
            ), """File %s changed after disk migration and snapshot
                %s preview""" % (full_path, self.snapshot_description)
