""" 4.1 Cold merge
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Cold_Merge
"""
from rhevmtests.storage import config
from multiprocessing.dummy import Pool
from multiprocessing import Process, Queue

import pytest
from art.rhevm_api.utils.log_listener import watch_logs
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    hosts as ll_hosts,
    jobs as ll_jobs,
)
import remove_snapshot_base as basePlan
from rhevmtests.storage.fixtures import remove_vm   # noqa F401
from fixtures import initialize_params, initialize_params_new_dc
from rhevmtests.storage.fixtures import (
    create_dc, clean_dc, remove_hsm_host, delete_disks, create_vm,
    wait_for_disks_and_snapshots, prepare_disks_with_fs_for_vm,
    create_storage_domain, start_vm, init_vm_executor,
)
from art.test_handler.tools import polarion, bz
from art.unittest_lib import (
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib import testflow

TEST_FILE_TEMPLATE = 'test_file_%s'
REGEX_COLD_MERGE_CMD = r"ColdMergeVDSCommand\(HostName\ =\ (?P<host_name>\w+)"
REGEX_SDM_MERGE_CMD = "sdm_merge"
TIMEOUT_COLD_MERGE_CMD = 60


class ColdMergeBaseClass(basePlan.BasicEnvironment):
    """
    Set live merge parameter to False
    """
    live_merge = False
    command_sdm_merge = None

    def remove_snapshot_with_verify_cold_merge(self, snapshot_idx):
        """
        Removes the snapshot with `idx snapshot_idx` and checks on engine.log
        and on each host vdsm.log for the proper commands with regex

        Since all tests has multiple disks and multiple snapshots including
        all disks we have to assert that at least an HSM host executes the
        cold merge command
        """
        self.hosts = {}
        for host in ll_hosts.get_cluster_hosts(config.CLUSTER_NAME):
            self.hosts[host] = ll_hosts.get_host_ip(host)

        def get_cold_merge_host_from_engine(q):
            """
            Matches the REGEX_COLD_MERGE_CMD on the engine.log and returns
            it to find which host is actually executing the sdm_merge command
            """
            found_regex, _ = watch_logs(
                files_to_watch=config.ENGINE_LOG, regex=REGEX_COLD_MERGE_CMD,
                time_out=TIMEOUT_COLD_MERGE_CMD,
                ip_for_files=config.ENGINE.host.ip,
                username=config.HOSTS_USER,
                password=config.VDC_ROOT_PASSWORD
            )
            if found_regex:
                q.put_nowait(found_regex.group('host_name'))
                return
            q.put_nowait(False)

        def get_cold_merge_host_from_vdsm(q):
            """
            Create multiple processes to look for the merge command on all the
            hosts in the cluster
            """
            pool = Pool(len(self.hosts))

            def check_vdsm(host_name):
                """
                Matches REGEX_SDM_MERGE_CMD on the vdsm.log of `host_name`,
                and in case it is found executes the self.command_sdm_merge()
                """
                found_regex, _ = watch_logs(
                    files_to_watch=config.VDSM_LOG, regex=REGEX_SDM_MERGE_CMD,
                    command_to_exec=self.command_sdm_merge,
                    time_out=TIMEOUT_COLD_MERGE_CMD,
                    ip_for_files=self.hosts[host_name],
                    username=config.HOSTS_USER,
                    password=config.VDC_ROOT_PASSWORD
                )
                if found_regex:
                    return host_name
                return False
            q.put_nowait(pool.map(check_vdsm, self.hosts.keys()))

        q1, q2 = Queue(), Queue()
        testflow.step("Looking for expected regex on engine and VDSM logs")
        p1 = Process(target=get_cold_merge_host_from_engine, args=(q1,))
        p2 = Process(target=get_cold_merge_host_from_vdsm, args=(q2,))
        p1.start()
        p2.start()
        try:
            testflow.step(
                "Remove snapshot %s", self.snapshot_list[snapshot_idx]
            )
            assert ll_vms.removeSnapshot(
                True, self.vm_name, self.snapshot_list[snapshot_idx],
                timeout=-1
            )
            host = q1.get(timeout=TIMEOUT_COLD_MERGE_CMD)
            hosts_executed_sdm_merge = filter(
                lambda w: w, q2.get(timeout=TIMEOUT_COLD_MERGE_CMD)
            )
            p1.join(timeout=TIMEOUT_COLD_MERGE_CMD)
            p2.join(timeout=TIMEOUT_COLD_MERGE_CMD)
            testflow.step(
                "Hosts executed sdm_merge %s", hosts_executed_sdm_merge
            )
            # The host that the engine.log reported was executing the
            # cold merge should be in list of hosts that executed the
            # cold merge
            assert host in hosts_executed_sdm_merge, (
                "Couldn't find command %s executed in any of the hosts vdsm"
                % REGEX_SDM_MERGE_CMD
            )
            # With the massive permutation of disks and snapshots for
            # the test cases at least one of the cold merge commands should
            # be executed in an HSM host
            assert any(
                ll_hosts.get_host_object(host).get_spm().get_status() == 'none'
                for host in hosts_executed_sdm_merge
            )
        finally:
            if self.command_sdm_merge:
                self.wait_for_command()
            ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)

    def wait_for_command(self):
        """
        Function to be instanciated which will execute instructions
        after the remove snapshot operations has started
        """
        return


@bz({'1509629': {}})
class TestCase18894(ColdMergeBaseClass, basePlan.TestCase6038):
    """
    Basic offline delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6038
    """
    __test__ = True
    test_case = '18894'


class TestCase18923(ColdMergeBaseClass, basePlan.TestCase16287):
    """
    Basic offline delete and merge of a single snapshot's disk

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM/workitem?id=RHEVM3-16287
    """
    __test__ = True
    test_case = '18923'


class TestCase18912(ColdMergeBaseClass, basePlan.TestCase12215):
    """
    Deleting all snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-12215
    """
    __test__ = True
    test_case = '18912'


class TestCase18900(ColdMergeBaseClass, basePlan.TestCase6044):
    """
    Offline delete and merge after deleting the base snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6044
    """
    __test__ = True
    test_case = '18900'


class TestCase18901(ColdMergeBaseClass, basePlan.TestCase6045):
    """
    Offline snapshot delete and merge with restart of vdsm

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6045
    """
    __test__ = True
    test_case = '18901'


class TestCase18899(ColdMergeBaseClass, basePlan.TestCase6043):
    """
    Offline delete and merge after deleting the last created snapshot

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6043
    """
    __test__ = True
    test_case = '18899'


class TestCase18902(ColdMergeBaseClass, basePlan.TestCase6046):
    """
    Offline delete and merge of snapshot while stopping the engine

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6046
    """
    __test__ = True
    test_case = '18902'


class TestCase18904(ColdMergeBaseClass, basePlan.TestCase6048):
    """
    Consecutive delete and merge of snapshots

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6048
    """
    __test__ = True
    test_case = '18904'


class TestCase18906(ColdMergeBaseClass, basePlan.TestCase6050):
    """
    Delete a 2nd offline snapshot during a delete and merge of another
    snapshot within the same VM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM3-6050
    """
    __test__ = True
    test_case = '18906'


class TestCase18920(ColdMergeBaseClass, basePlan.TestCase12216):
    """
    Basic offline merge after disk with snapshot is extended

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=12216
    """
    __test__ = True
    test_case = '18920'


class TestCase18975(ColdMergeBaseClass):
    """
    Cold Merge with SPM and several HSMs

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM-18975
    """
    __test__ = True
    test_case = '18975'

    @polarion("RHEVM-18975")
    @tier2
    def test_basic_snapshot_cold_merge_sdm_merge_by_hsm(self):
        self.basic_flow()
        self.remove_snapshot_with_verify_cold_merge(1)
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in range(3)]
        )


@pytest.mark.usefixtures(
    remove_hsm_host.__name__,
    delete_disks.__name__,
    create_vm.__name__,
    start_vm.__name__,
    init_vm_executor.__name__,
    prepare_disks_with_fs_for_vm.__name__,
    initialize_params.__name__,
    wait_for_disks_and_snapshots.__name__,
)
class TestCase18976(ColdMergeBaseClass):
    """
    Verfiy that the new added HSM is used

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM-18976
    """
    __test__ = True
    test_case = '18976'

    @polarion("RHEVM-18976")
    @tier2
    def test_basic_snapshot_merge_after_adding_hsm(self):
        self.basic_flow(4)
        self.remove_snapshot_with_verify_cold_merge(1)
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in range(3)]
        )
        hosts_activate = []
        try:
            testflow.step("Deactivate all hsm hosts")
            for host in ll_hosts.get_cluster_hosts(config.CLUSTER_NAME):
                host_obj = ll_hosts.get_host_object(host)
                if host_obj.get_spm().get_status() == 'none':
                    assert ll_hosts.deactivate_host(True, host)
                    hosts_activate.append(host)
            testflow.step("Add host %s back to the cluster", self.hsm_host)
            assert ll_hosts.add_host(
                name=self.hsm_host, address=self.hsm_host_vds.fqdn,
                wait=True, cluster=config.CLUSTER_NAME,
                root_password=config.VDC_ROOT_PASSWORD,
                comment=self.hsm_host_vds.ip
            )
            self.remove_snapshot_with_verify_cold_merge(2)
            self.verify_snapshot_files(
                self.snapshot_list[3],
                [TEST_FILE_TEMPLATE % i for i in range(4)]
            )
        finally:
            for host in hosts_activate:
                assert ll_hosts.activate_host(True, host)


@pytest.mark.usefixtures(
    create_dc.__name__,
    create_storage_domain.__name__,
    initialize_params_new_dc.__name__,
    clean_dc.__name__,
    delete_disks.__name__,
    create_vm.__name__,
    start_vm.__name__,
    init_vm_executor.__name__,
    prepare_disks_with_fs_for_vm.__name__,
    initialize_params.__name__,
    wait_for_disks_and_snapshots.__name__,
)
class TestCase18932(basePlan.BaseTestCase):
    """
    Cold Merge with previous compatibility version

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM-18932
    """
    __test__ = True
    clone_from_template = False
    test_case = '18932'
    dc_verison = "4.0"

    @polarion("RHEVM-18932")
    @tier3
    def test_basic_flow_with_previous_compatibility_version(self):
        self.basic_flow()
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1],
        )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in range(3)]
        )


class TestCase18972(ColdMergeBaseClass):
    """
    Cold merge with failure DURING PrepareMerge on SPM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM-18972
    """
    __test__ = True
    test_case = '18972'

    @polarion("RHEVM-18972")
    @tier4
    def test_basic_flow_restart_vdsm_during_prepare_merge(self):
        self.basic_flow()
        _, spm_dict = ll_hosts.get_host(
            True, config.DATA_CENTER_NAME, spm=True
        )
        self.spm = spm_dict['host']
        self.spm_ip = ll_hosts.get_host_ip(self.spm)
        testflow.step("Removing snapshot %s", self.snapshot_list[1])
        assert ll_vms.removeSnapshot(
            True, self.vm_name, self.snapshot_list[1], timeout=-1
        )
        testflow.step("Waiting for PrepareMerge command")
        found_regex, _ = watch_logs(
            config.ENGINE_LOG, regex='PrepareMerge',
            time_out=TIMEOUT_COLD_MERGE_CMD,
            command_to_exec=config.KILL_VDSM,
            ip_for_files=config.ENGINE.host.ip,
            username=config.HOSTS_USER, password=config.VDC_ROOT_PASSWORD,
            ip_for_execute_command=self.spm_ip,
            remote_username=config.HOSTS_USER,
            remote_password=config.HOSTS_PW
        )
        assert found_regex, (
            "'PrepareImage' expression was not found on %s log"
            % config.ENGINE_LOG
        )
        testflow.step("Waiting for the host and the data center for be UP")
        assert ll_hosts.wait_for_hosts_states(True, self.spm), (
            "Host %s failed to reach status UP" % self.spm
        )
        assert ll_hosts.wait_for_spm(
            config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
            config.WAIT_FOR_SPM_INTERVAL
        )
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        snapshots = [
            snap.get_description() for snap in
            ll_vms.get_vm_snapshots(self.vm_name)
        ]
        if self.snapshot_list[1] in snapshots:
            testflow.step(
                "Remove operation rolled back, removing snapshot %s",
                self.snapshot_list[1]
            )
            assert ll_vms.removeSnapshot(
                True, self.vm_name, self.snapshot_list[1]
            )
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in range(3)]
        )


class TestCase18974(ColdMergeBaseClass):
    """
    Verify failure when HSM goes down after SDMMerge starts on HSM

    https://polarion.engineering.redhat.com/polarion/#/project
    /RHEVM3/workitem?id=RHEVM-18974
    """
    __test__ = True
    test_case = '18974'
    command_sdm_merge = config.KILL_VDSM

    def wait_for_command(self):
        """
        Vdsm restart could happen in any HSM host, wait for all hosts
        to be up
        """
        for host in self.hosts:
            assert ll_hosts.wait_for_hosts_states(True, host), (
                "Host %s failed to reach status UP" % host
            )

    @polarion("RHEVM-18974")
    @tier4
    def test_basic_flow_restart_vdsm_after_sdm_merge_starts(self):
        self.basic_flow()
        self.remove_snapshot_with_verify_cold_merge(1)
        ll_jobs.wait_for_jobs([config.JOB_REMOVE_SNAPSHOT])
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        self.verify_snapshot_files(
            self.snapshot_list[2], [TEST_FILE_TEMPLATE % i for i in range(3)]
        )
