"""
Improve HA failover, so that even when power fencing is not available,
automatic HA will work without manual confirmation on host rebooted
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage_4_0/4_1_Storage_Improve_HA_failover_even_when_power_fencing_not_available_aut
"""
import config
from config import NFS
import pytest
import re
import shlex
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    jobs as ll_jobs,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)
from art.rhevm_api.utils.test_utils import restart_engine, wait_for_tasks
from art.test_handler.settings import ART_CONFIG
from art.test_handler.tools import bz, polarion
from art.unittest_lib import (
    tier2,
    tier3,
    tier4,
)
from art.unittest_lib import StorageTest, testflow, storages

from rhevmtests.storage import helpers as storage_helpers
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage.fixtures import (
    remove_vms, remove_template, create_storage_domain, create_dc,
    create_export_domain, clean_dc, remove_export_domain,
    deactivate_and_detach_export_domain
)
from fixtures import (
    unblock_engine_to_host, unblock_host_to_storage_domain,
    finalizer_wait_for_host_up, initialize_params
)

# BZ1459865 is leaving the env in a bad status if this tests are run with
# ISCSI or GLUSTERFS. After is fixed enable tests for all storage domain types


class BaseStorageVMLeaseTest(StorageTest):

    vm_lease = True
    ssh_vm = True
    vm_args = dict()

    def create_vms(self):
        for vm_name in self.vm_names:
            vm_args = config.create_vm_args.copy()
            vm_args['storageDomainName'] = self.storage_domain
            vm_args['cluster'] = getattr(
                self, 'cluster_name', config.CLUSTER_NAME
            )
            vm_args['vmName'] = vm_name
            if self.vm_lease:
                vm_args['lease'] = self.storage_domain
                vm_args['highly_available'] = True
                lease_msg = (
                    "with lease in storage domain %s" % self.storage_domain
                )
            else:
                lease_msg = "without lease"
            vm_args.update(self.vm_args)
            testflow.step("Creating VM %s %s", vm_name, lease_msg)
            assert storage_helpers.create_vm_or_clone(**vm_args), (
                "Failed to create VM %s" % vm_name
            )
        wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)

    def start_vms(self, set_placement_host_value=True, wait_for_ip=True):
        for vm_name in self.vm_names:
            wait_for_tasks(config.ENGINE, config.DATA_CENTER_NAME)
            testflow.step("Start VM %s", vm_name)
            assert ll_vms.startVm(
                True, vm_name, config.VM_UP, wait_for_ip=wait_for_ip
            )
            host = ll_vms.get_vm_host(vm_name=vm_name)
            host_ip = ll_hosts.get_host_ip_from_engine(
                host=host
            )
            if set_placement_host_value:
                config.PLACEMENT_HOST = host
                config.PLACEMENT_HOST_IP = host_ip

            self.host_executor = rhevm_helpers.get_host_executor(
                ip=host_ip, password=config.HOSTS_PW
            )
            rc, output, error = self.host_executor.run_cmd(
                shlex.split("sanlock client status")
            )
            assert not rc, (
                "Failed to execute sanlock client command %s" % error
            )
            regex = re.search(
                "%s:.*xleases" % (
                    ll_vms.get_vm_obj(vm_name).get_id(),
                ), output
            )
            assert self.vm_lease == bool(regex), (
                "Lease volume for VM %s was expected to %sexist, "
                "sanlock output %s"
                % (vm_name, '' if self.vm_lease else 'not ', output)
            )

    def block_connection_engine_to_host(self, wait_for_nonresponsive=True):
        testflow.step(
            "Blocking connection from the engine to host %s",
            config.PLACEMENT_HOST
        )
        assert storage_helpers.blockOutgoingConnection(
            config.ENGINE.host.ip, config.HOSTS_USER, config.HOSTS_PW,
            config.PLACEMENT_HOST_IP
        )
        if wait_for_nonresponsive:
            testflow.step(
                "Waiting for host %s to be non-responsive",
                config.PLACEMENT_HOST
            )
            assert ll_hosts.wait_for_hosts_states(
                True, [config.PLACEMENT_HOST], config.HOST_NONRESPONSIVE,
                timeout=config.TIMEOUT_GENERAL_LEASES
            )
            for vm_name in self.vm_names:
                testflow.step(
                    "Waiting for VM %s to be in state UNKNOWN", vm_name
                )
                assert ll_vms.waitForVMState(
                    vm_name, config.VM_UNKNOWN,
                    timeout=config.TIMEOUT_GENERAL_LEASES
                )

    def block_connection_host_to_storage(self):
        testflow.step(
            "Blocking connection from host %s to storage domain %s",
            config.PLACEMENT_HOST, self.storage_domain
        )
        for ip in self.storage_domain_ips:
            assert storage_helpers.blockOutgoingConnection(
                config.PLACEMENT_HOST_IP, config.HOSTS_USER, config.HOSTS_PW,
                ip
            )

    def verify_vm_is_running_on_different_host(self):
        for vm_name in self.vm_names:
            testflow.step(
                "Wait until VM %s is back up", vm_name
            )
            assert ll_vms.waitForVMState(vm_name, timeout=600)
            current_running_host = ll_vms.get_vm_host(vm_name)
            assert config.PLACEMENT_HOST != current_running_host, (
                "VM %s is running on host %s, before was running on host %s"
                % (vm_name, current_running_host, config.PLACEMENT_HOST)
            )
            testflow.step(
                "VM %s successfully started on host %s", self.vm_name,
                current_running_host
            )
            if self.ssh_vm:
                self.vm_executor = storage_helpers.get_vm_executor(vm_name)
                rc, _, error = self.vm_executor.run_cmd(
                    shlex.split(config.SYNC_CMD)
                )
                assert not rc, (
                    "Failed to connect to vm %s and execute sync: %s" % (
                        self.vm_name, error
                    )
                )


@pytest.mark.usefixtures(
    initialize_params.__name__,
    remove_vms.__name__,
    finalizer_wait_for_host_up.__name__,
    unblock_engine_to_host.__name__,
    unblock_host_to_storage_domain.__name__,
)
class BaseStorageVmLeaseTestWithFixtures(BaseStorageVMLeaseTest):
    pass


# This test needs power manager enabled in the host to be able to
# bring it back up, but in this case the host should be power on
# automatically so no failover lease should occur.
class TestCase17616(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Power-off the host
    4. Access the vm after it's active on the other host
    """
    __test__ = False

    @polarion("RHEVM-17616")
    @tier4
    def test_ha_failover_unreachable_host_loosing_power(self):
        # TODO: write test
        return


@storages((NFS,))
class TestCase17618(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Block connection from engine to host
    4. Block connection from storage to host
    5. Access the vm after it's active on the other host
    """

    @polarion("RHEVM-17618")
    @tier2
    def test_ha_failove_unreachable_host_storage_inaccesible(self):
        self.create_vms()
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()


@storages((NFS,))
class TestCase17619(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Block connection from engine to host
    4. Manually power off the VM
    5. Access the vm after it's active on the other host
    """

    @polarion("RHEVM-17619")
    @tier2
    def test_ha_failover_unreachable_host_vm_terminated(self):
        self.create_vms()
        self.start_vms()
        host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=config.PLACEMENT_HOST
        )
        self.block_connection_engine_to_host()
        testflow.step("Killing qemu process")
        assert ll_hosts.kill_vm_process(host_resource, self.vm_name)
        self.verify_vm_is_running_on_different_host()


class TestCase17620(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Block connection engine to the host -> VM will become UNKNOWN and
       won't failover to another host
    """
    # Is that test case is supposed to run only on NFS? Ask Raz.
    __test__ = config.STORAGE_TYPE_NFS in ART_CONFIG['RUN']['storages']

    @polarion("RHEVM-17620")
    @tier2
    def test_ha_failover_unreachable_host_storage_accessible(self):
        self.create_vms()
        self.start_vms()
        self.block_connection_engine_to_host()
        assert not ll_vms.waitForVMState(
            self.vm_name, config.VM_UP, timeout=config.TIMEOUT_GENERAL_LEASES
        )


@storages((NFS,))
class TestCase17621(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Block connection from all hosts in the DC to the storage domain.
    4. Block connection from engine to the host -> VM will become UNKNOWN and
        won't failover to another host
    """

    @polarion("RHEVM-17621")
    @tier3
    def test_ha_failover_storage_innaccessible_all_hosts(self):
        self.create_vms()
        self.start_vms()
        hosts_ips = list()
        try:
            testflow.step(
                "Blocking connection from engine to rest of the hosts"
            )
            for host in config.HOSTS:
                host_ip = ll_hosts.get_host_ip(host)
                hosts_ips.append(host_ip)
                for storage_ip in self.storage_domain_ips:
                    assert storage_helpers.blockOutgoingConnection(
                        host_ip, config.HOSTS_USER,
                        config.HOSTS_PW, storage_ip
                    )
            self.block_connection_engine_to_host()
            assert ll_vms.waitForVMState(
                self.vm_name, config.VM_UNKNOWN,
                timeout=config.TIMEOUT_GENERAL_LEASES
            )
            assert not ll_vms.waitForVMState(
                self.vm_name, config.VM_UP,
                timeout=config.TIMEOUT_GENERAL_LEASES
            )
        finally:
            for host_ip in hosts_ips:
                for storage_domain_ip in self.storage_domain_ips:
                    storage_helpers.unblockOutgoingConnection(
                        host_ip, config.HOSTS_USER,
                        config.HOSTS_PW, storage_domain_ip
                    )


@storages((NFS,))
class TestCase17623(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM without storage lease
    2. Edit the VM, create a new lease
    3. Start the VM
    4. Block connection from engine to host
    5. Block connection from storage to host
    6. Access the vm after it's active on the other host
    """
    vm_lease = False

    @polarion("RHEVM-17623")
    @tier2
    def test_ha_failover_existing_ha_vm(self):
        self.create_vms()
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domain,
            highly_available=True
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.vm_lease = True
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()


@storages((NFS,))
class TestCase17624(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Edit the VM and remove the lease
    3. Start the VM
    4. Block connection from engine to host
    5. Block connection from storage to hos  -> VM has no lease so the VM
        stays in status UNKNOWN
    """

    @polarion("RHEVM-17624")
    @tier3
    def test_ha_failover_removing_vm_lease(self):
        self.create_vms()
        assert ll_vms.updateVm(True, self.vm_name, lease='')
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.vm_lease = False
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        assert not ll_vms.waitForVMState(
            self.vm_name, config.VM_UP, timeout=config.TIMEOUT_GENERAL_LEASES
        )


@storages((NFS,))
class TestCase18184(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM without storage lease
    2. Start the VM
    3. Edit the VM, create a new lease
    4. VM needs to be restarted for the lease to change
    """
    vm_lease = False

    @bz({'1484053': {}})
    @polarion("RHEVM-18184")
    @tier3
    def test_create_lease_while_vm_up(self):
        self.create_vms()
        self.start_vms()
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domain,
            highly_available=True
        )
        self.vm_lease = True
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        testflow.step("Stop VM %s", self.vm_name)
        assert ll_vms.stopVm(True, self.vm_name)
        assert ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.start_vms()


@storages((NFS,))
class TestCase18185(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Edit the VM, remove the lease
    4. VM needs to be restarted for the lease to change
    """

    @bz({'1484053': {}})
    @polarion("RHEVM-18185")
    @tier3
    def test_ha_remove_lease_while_vm_up(self):
        self.create_vms()
        self.start_vms()
        assert ll_vms.updateVm(True, self.vm_name, lease='')
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.vm_lease = False
        assert ll_vms.stopVm(True, self.vm_name)
        assert ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.start_vms()


@storages((NFS,))
class TestCase18186(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. While the create lease process is in progress, block connnection from
        engine to the SPM host.
    3. Start the VM -> VM fails to start
    4. Wait until other host has the SPM role
    5. Start the VM
    6. Block connection from engine to host
    7. Block connection from storage to host
    8. Access the vm after it's active on the other host
    """
    vm_lease = False

    @polarion("RHEVM-18186")
    @tier4
    def test_ha_spm_unreachable(self):
        self.spm = ll_hosts.get_spm_host(config.HOSTS)
        self.spm_ip = ll_hosts.get_host_ip(self.spm)
        self.create_vms()
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domains[1],
            highly_available=True
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        try:
            assert storage_helpers.blockOutgoingConnection(
                config.ENGINE.host.ip, config.HOSTS_USER, config.HOSTS_PW,
                self.spm_ip
            )
            assert ll_hosts.wait_for_spm(
                config.DATA_CENTER_NAME, config.WAIT_FOR_SPM_TIMEOUT,
                config.WAIT_FOR_SPM_INTERVAL
            )
        finally:
            storage_helpers.unblockOutgoingConnection(
                config.ENGINE.host.ip, config.HOSTS_USER, config.HOSTS_PW,
                self.spm_ip
            )
        self.vm_lease = True
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domains[2]
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()


@storages((NFS,))
class TestCase17625(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Block connection from engine to all the hosts in the DC except one
    4. Block connection from storage to host
    5. Access the vm after it's active on the other host
    """

    @bz({'1484053': {}})
    @polarion("RHEVM-17625")
    @tier4
    def test_ha_failover_multiple_hosts_unreachable(self):
        self.create_vms()
        self.start_vms()
        self.block_connection_engine_to_host()
        second_host = None
        for host in config.HOSTS:
            if (
                host != config.PLACEMENT_HOST and
                not ll_hosts.check_host_spm_status(True, host)
            ):
                second_host = host
                break
        second_host_ip = ll_hosts.get_host_ip(second_host)
        try:
            testflow.step(
                "Block connection to the other hsm host %s", second_host
            )
            assert storage_helpers.blockOutgoingConnection(
                config.ENGINE.host.ip, config.HOSTS_USER, config.HOSTS_PW,
                second_host_ip
            )
            assert ll_hosts.wait_for_hosts_states(
                True, [second_host], config.HOST_NONRESPONSIVE,
                timeout=config.TIMEOUT_GENERAL_LEASES
            )
            self.block_connection_host_to_storage()
            self.verify_vm_is_running_on_different_host()
            assert second_host != ll_vms.get_vm_host(self.vm_name), (
                "VM %s is running on a non responsive host" % self.vm_name
            )
        finally:
            storage_helpers.unblockOutgoingConnection(
                config.ENGINE.host.ip, config.HOSTS_USER, config.HOSTS_PW,
                second_host_ip
            )


@storages((NFS,))
class TestCase17629(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Block connection from engine to host
    4. Block connection from storage to host
    5. Restart the engine
    6. Access the vm after it's active on the other host
    """

    @polarion("RHEVM-17629")
    @tier4
    def test_ha_failover_host_unreachable_engine_restart(self):
        self.create_vms()
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        testflow.step("Restaring the engine")
        restart_engine(config.ENGINE, 10, 75)
        self.verify_vm_is_running_on_different_host()


@storages((NFS,))
class TestCase17630(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Block connection from engine to host
    4. Block connection from storage to host
    5. Restart sanlock -> VM lease is release and VM starts in another host
    """

    @polarion("RHEVM-17630")
    @tier4
    def test_ha_failover_while_sanlock_restart(self):
        self.create_vms()
        self.start_vms()
        self.block_connection_engine_to_host(wait_for_nonresponsive=False)
        self.block_connection_host_to_storage()
        testflow.step("Restart sanlock")
        rc, output, error = self.host_executor.run_cmd(
            shlex.split("killall -9 sanlock")
        )
        assert not rc, (
            "Failed to restart sanlock service %s" % error
        )
        ll_hosts.wait_for_hosts_states(
            True, [config.PLACEMENT_HOST], states=config.HOST_NONRESPONSIVE
        )
        self.verify_vm_is_running_on_different_host()


@storages((NFS,))
class TestCase17634(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease
    2. Start the VM
    3. Block connection from engine to host to master domain
    4. Block connection from storage to host
    5. Access the vm after it's active on the other host
    """
    vm_lease = False

    @polarion("RHEVM-17634")
    @tier4
    def test_ha_failover_master_storage_domain_inaccessible(self):
        self.create_vms()
        _, master = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        master_storage_domain = master['masterDomain']
        activate_domains = list()
        try:
            while master_storage_domain not in self.storage_domains:
                assert hl_sd.deactivate_domain(
                    config.DATA_CENTER_NAME, master_storage_domain,
                    config.ENGINE
                )
                activate_domains.append(master_storage_domain)
                _, master = ll_sd.findMasterStorageDomain(
                    True, config.DATA_CENTER_NAME
                )
                master_storage_domain = master['masterDomain']
        finally:
            for domain in activate_domains:
                ll_sd.activateStorageDomain(
                    True, config.DATA_CENTER_NAME, domain
                )
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domain,
            highly_available=True
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.storage_domain_ips = hl_sd.get_storage_domain_addresses(
            master_storage_domain
        )
        self.vm_lease = True
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()


class TestCase17635(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create multiple HA VMs with storage lease
    2. Start the VMs
    3. Block connection from engine to host
    4. Block connection from storage to host
    5. Access the VMs after it's active on the other host
    """
    # Disable until BZ1437056 is working, modify the create_vms() function
    __test__ = False
    num_of_vms = 2

    @polarion("RHEVM-17635")
    @tier4
    def test_ha_failover_multiple_ha_vms(self):
        self.create_vms()
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()


class TestCase17637(BaseStorageVmLeaseTestWithFixtures):
    __test__ = False

    @polarion("RHEVM-17637")
    @tier4
    def test_ha_failover_upgrade_storage_domain_v4(self):
        # TODO: write test
        return


@storages((NFS,))
@pytest.mark.usefixtures(
    create_storage_domain.__name__,
    initialize_params.__name__,
    remove_vms.__name__,
    finalizer_wait_for_host_up.__name__,
    unblock_engine_to_host.__name__,
    unblock_host_to_storage_domain.__name__,
)
class TestCase18333(BaseStorageVMLeaseTest):
    """
    1. Atttach an unattached v3 storage to the DC.
    2. Create new HA VM with storage lease
    3. Start the VM
    4. Block connection from engine to host
    5. Block connection from storage to host
    6. Access the vm after it's active on the other host
    """
    domain_kwargs = {'storage_format': 'v3'}
    vm_args = {'clone_from_template': False}
    vm_lease = False

    @polarion("RHEVM-18333")
    @tier4
    def test_ha_failover_attach_v3_storage_domain(self):
        self.create_vms()
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.new_storage_domain,
            highly_available=True
        )
        self.vm_lease = True
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.start_vms(wait_for_ip=False)
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()


class TestCase17638(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Change the name of the xleases volume in the storage domain
    2. Start the VM -> VM won't start without a lease
    3. Change the name back to xleases
    4. Start the VM -> VM should start
    """
    __test__ = False

    @polarion("RHEVM-17638")
    @tier4
    def test_ha_failover_xleases_corrupted(self):
        # TODO: write test
        return


class TestCase17639(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Remove all permissions from the xleases volume
    2. Start the VM -> VM won't start without a lease
    3. Add the original file permissions back
    4. Start the VM -> VM should start
    """
    __test__ = False

    @polarion("RHEVM-17639")
    @tier4
    def test_ha_failover_wiouth_rw_permissions_xleases_volume(self):
        # TODO: write test
        return


@storages((NFS,))
class TestCase18187(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Start the VM
    2. Take snapsoht of the VM
    3. Stop the vm
    4. Edit the vm and remove the lease from it
    5. Preview the first snapshot and start the VM -> VM won't start
    """

    @bz({'1484053': {}})
    @polarion("RHEVM-18187")
    @tier3
    def test_take_snapshot_vm_with_lease(self):
        self.create_vms()
        self.start_vms()
        self.snapshot_desc = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        testflow.step("Add snapshot to VM %s", self.vm_name)
        assert ll_vms.addSnapshot(True, self.vm_name, self.snapshot_desc)
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        assert ll_vms.stopVm(True, self.vm_name)
        testflow.step("Remove lease for VM %s", self.vm_name)
        assert ll_vms.updateVm(True, self.vm_name, lease='')
        self.vm_lease = False
        testflow.step(
            "Preview snapshot %s snapshot %s", self.snapshot_desc,
            self.vm_name
        )
        assert ll_vms.preview_snapshot(True, self.vm_name, self.snapshot_desc)
        assert not ll_vms.startVm(True, self.vm_name, timeout=10), (
            "VM %s started when the lease is missing" % self.vm_name
        )
        assert ll_vms.get_vm_obj(self.vm_name).get_lease(), (
            "Lease configuration for VM %s should be there"
        )


class TestCaseBaseSnapshot(BaseStorageVmLeaseTestWithFixtures):
    """
    General flow for snapshot tests
    """
    file_path = '/root/test_vm_lease'
    live_snapshot = False

    def snapshot_failover_flow(self):
        self.create_vms()
        self.snapshot_desc = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_SNAPSHOT
        )
        if self.live_snapshot:
            self.start_vms()
        testflow.step("Add snapshot to vm %s", self.vm_name)
        assert ll_vms.addSnapshot(
            True, self.vm_name, self.snapshot_desc,
            persist_memory=self.live_snapshot
        )
        ll_vms.wait_for_vm_snapshots(self.vm_name, config.SNAPSHOT_OK)
        if not self.live_snapshot:
            self.start_vms()
        testflow.step("Write files to VM %s", self.vm_name)
        self.vm_executor = storage_helpers.get_vm_executor(self.vm_name)
        assert storage_helpers.write_content_to_file(
            self.vm_name, self.file_path, vm_executor=self.vm_executor
        )
        checksum = storage_helpers.checksum_file(
            self.vm_name, self.file_path, vm_executor=self.vm_executor
        )
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()
        checksum_after_failover = storage_helpers.checksum_file(
            self.vm_name, self.file_path, vm_executor=self.vm_executor
        )
        assert checksum == checksum_after_failover, (
            "File %s content after the failover is not the same %s - %s"
            % (self.file_path, checksum, checksum_after_failover)
        )
        assert ll_vms.stopVm(True, self.vm_name)
        testflow.step(
            "Preview %s snapshot %s", self.vm_name, self.snapshot_desc
        )
        assert ll_vms.preview_snapshot(True, self.vm_name, self.snapshot_desc)
        self.start_vms(set_placement_host_value=False)
        assert not storage_helpers.does_file_exist(
            self.vm_name, self.file_path, vm_executor=self.vm_executor
        )


@storages((NFS,))
class TestCase18162(TestCaseBaseSnapshot):
    """
    1. Take a snapshot of the VM
    2. Start the VM
    3. Access the VM and create files with data
    4. Block connection from engine to host
    5. Block connection from storage to host
    6. When the VM is active again, files should be there
    7. Preview the snapshot -> Files should be gone
    """

    @bz({'1484863': {}})
    @polarion("RHEVM-18162")
    @tier3
    def test_ha_failover_with_preview_snapshot(self):
        self.snapshot_failover_flow()


@storages((NFS,))
class TestCase17641(TestCaseBaseSnapshot):
    """
    1. Start the VM
    2. Take a live snapshot of the VM
    3. Access the VM and create files with data
    4. Block connection from engine to host
    5. Block connection from storage to host
    6. When the VM is active again, files should be there
    7. Preview the snapshot -> Files should be gone
    """
    live_snapshot = True

    @bz({'1484863': {}})
    @polarion("RHEVM-17641")
    @tier3
    def test_ha_failover_with_live_preview_snapshot(self):
        self.snapshot_failover_flow()


@storages((NFS,))
@pytest.mark.usefixtures(
    deactivate_and_detach_export_domain.__name__,
    create_dc.__name__,
    clean_dc.__name__,
    create_storage_domain.__name__,
    initialize_params.__name__,
    create_export_domain.__name__,
    remove_export_domain.__name__,
    remove_vms.__name__,
    finalizer_wait_for_host_up.__name__,
    unblock_engine_to_host.__name__,
    unblock_host_to_storage_domain.__name__,
)
class TestCase17644(BaseStorageVMLeaseTest):
    """
    1. Start the VM
    2. Stop the VM, remove the lease, and export to the export domain
    3. Detach the export domain and attach it to the other DC
    4. Import the Vm, edit and create a new lease, and start the VM in a new DC
    5. Block connection from engine to host
    6. Block connection from storage to host
    7. Access the vm after it's active on the other host
    """
    vm_args = {'clone_from_template': False}

    @polarion("RHEVM-17644")
    @tier4
    def test_ha_failover_imported_vm_from_another_dc(self):
        self.create_vms()
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domain,
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.start_vms(wait_for_ip=False)
        assert ll_vms.stopVm(True, self.vm_name)
        testflow.step("Remove lease from VM %s", self.vm_name)
        assert ll_vms.updateVm(True, self.vm_name, lease='')
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        testflow.step("Export VM %s", self.vm_name)
        assert ll_vms.exportVm(True, self.vm_name, self.export_domain)
        assert ll_vms.safely_remove_vms([self.vm_name])
        testflow.step(
            "Deactivate and detach export domain %s from data center "
            "%s and attach it to data center %s", self.export_domain,
            self.new_dc_name, config.DATA_CENTER_NAME
        )
        wait_for_tasks(config.ENGINE, self.new_dc_name)
        assert hl_sd.detach_and_deactivate_domain(
            self.new_dc_name, self.export_domain, config.ENGINE
        )
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.export_domain
        )
        testflow.step("Import VM %s", self.vm_name)
        assert ll_vms.importVm(
            True, self.vm_name, self.export_domain,
            self.storage_domains[0], config.CLUSTER_NAME
        )
        found_hsm_host, hosts = ll_hosts.get_any_non_spm_host(
            config.HOSTS, config.HOST_UP, config.CLUSTER_NAME
        )
        testflow.step("Add lease to VM %s", self.vm_name)
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domains[0],
            highly_available=True
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.storage_domain_ips = hl_sd.get_storage_domain_addresses(
            self.storage_domains[0]
        )
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()


@storages((NFS,))
@pytest.mark.usefixtures(
    create_storage_domain.__name__,
    initialize_params.__name__,
    remove_vms.__name__,
    finalizer_wait_for_host_up.__name__,
    unblock_engine_to_host.__name__,
    unblock_host_to_storage_domain.__name__,
)
class TestCase18217(BaseStorageVMLeaseTest):
    """
    1. Start the VM
    2. Stop the VM and remove the lease
    3. Move the storage domain where the VM is located to maintenance mode
    4. Detach the storage domain
    5. Remove the storage domain from the DC
    6. Import again the storage domain to the DC and activate it
    7. Import the VM from the imported storage domain
    8. Start the VM
    """
    vm_args = {'clone_from_template': False}

    @polarion("RHEVM-18217")
    @tier4
    def test_ha_failover_attached_storage_domain(self):
        self.create_vms()
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domain,
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.start_vms()
        assert ll_vms.stopVm(True, self.vm_name)
        assert ll_vms.updateVm(True, self.vm_name, lease='')
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        testflow.step(
            "Detach and remove data storage domain %s",
            self.storage_domain
        )
        wait_for_tasks(config.ENGINE, self.new_dc_name)
        assert hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, self.storage_domain, config.ENGINE
        )
        assert ll_sd.removeStorageDomain(
            True, self.storage_domain, config.PLACEMENT_HOST, format='false'
        )
        testflow.step("Import data storage doamin %s", self.storage_domain)
        storage_helpers.import_storage_domain(
            config.PLACEMENT_HOST, self.storage
        )
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.storage_domain
        )
        testflow.step("Register VM %s", self.vm_name)
        hl_sd.register_vm_from_data_domain(
            self.storage_domain, self.vm_name, config.CLUSTER_NAME
        )
        testflow.step("Start VM %s", self.vm_name)
        assert ll_vms.startVm(True, self.vm_name, config.VM_UP)
        assert ll_vms.waitForVMState(self.vm_name, config.VM_UP)


@storages((NFS,))
class TestCase17665(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease and disks from different storage
        domains
    2. Start the VM
    3. Block connection from engine to host
    4. Block connection from storage domain of one of the disks to the host
    5. VM cannot start on any host since the disk in the specific storage
        storage domain becomes innaccessible
    """
    vm_lease = False

    @bz({'1459156': {}})
    @polarion("RHEVM-17665")
    @tier4
    def test_ha_failover_disk_different_storage_domains(self):
        self.create_vms()
        disks_ids = [
            disk.get_id() for disk in
            ll_disks.getObjDisks(self.vm_name, get_href=False)
        ]
        storage_domain = ll_disks.get_other_storage_domain(
            disks_ids[0], self.vm_name, force_type=False, key='id'
        )
        assert ll_vms.updateVm(
            True, self.vm_name, lease=storage_domain,
            highly_available=True
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.vm_lease = True
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        assert not ll_vms.waitForVMState(
            self.vm_name, config.VM_UP, timeout=config.TIMEOUT_GENERAL_LEASES
        )


@storages((NFS,))
class TestCase18188(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Create new HA VM with storage lease and without disks
    2. Start the VM
    3. Block connection from engine to host
    4. Block connection from storage to host
    5. Access the vm after it's active on the other host
    """
    ssh_vm = False

    @bz({'1484053': {}})
    @polarion("RHEVM-18188")
    @tier3
    def test_ha_failover_diskless(self):
        assert ll_vms.addVm(
            True, name=self.vm_name, cluster=config.CLUSTER_NAME,
            boot=config.ENUMS['boot_sequence_network'],
        )
        assert ll_vms.addNic(
            True, vm=self.vm_name, name=config.NIC_NAME[0],
            network=config.MGMT_BRIDGE, vnic_profile=config.MGMT_BRIDGE,
            plugged='true', linked='true'
        )
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domain,
            highly_available=True
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.start_vms(wait_for_ip=False)
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()


@storages((NFS,))
@pytest.mark.usefixtures(
    initialize_params.__name__,
    remove_template.__name__,
    remove_vms.__name__,
    finalizer_wait_for_host_up.__name__,
    unblock_engine_to_host.__name__,
    unblock_host_to_storage_domain.__name__,
)
class TestCase18216(BaseStorageVMLeaseTest):
    """
    1. Create template from the HA VM
    2. When the template is complate, create a new VM from the template
    3. Start the VM
    4. Block connection from engine to host
    5. Block connection from storage to host
    6. Access the vm after it's active on the other host
    """

    @bz({'1481691': {}})
    @polarion("RHEVM-18216")
    @tier3
    def test_ha_failover_from_template_with_lease(self):
        self.create_vms()
        self.start_vms()
        assert ll_vms.stopVm(True, self.vm_name)
        testflow.step(
            "Create template %s from vm %s", self.template_name, self.vm_name
        )
        assert ll_templates.createTemplate(
            True, vm=self.vm_name, name=self.template_name,
            cluster=config.CLUSTER_NAME, storagedomain=self.storage_domain,
        )
        assert ll_vms.removeVm(True, self.vm_name)
        storage_domain_id = ll_templates.get_template_obj(
            self.template_name
        ).get_lease().get_storage_domain().get_id()
        assert self.storage_domain == ll_sd.get_storage_domain_obj(
            storage_domain_id, 'id'
        ).get_name()
        assert ll_vms.cloneVmFromTemplate(
            True, name=self.vm_name, cluster=config.CLUSTER_NAME,
            storagedomain=self.storage_domain, template=self.template_name,
            clone='true', lease=self.storage_domain,
            highly_available=True
        )
        self.start_vms()
        self.block_connection_engine_to_host()
        self.block_connection_host_to_storage()
        self.verify_vm_is_running_on_different_host()


@storages((NFS,))
class TestCase18218(BaseStorageVmLeaseTestWithFixtures):
    """
    1. Locate the storage domain where the VM's lease is located, and move
        this storage domain to maintenance
    2. Try to detach the storage domain -> Can't detach the storage domain
    """
    vm_leases = False

    @polarion("RHEVM-18218")
    @tier4
    def test_detach_storage_domain_with_leases(self):
        self.create_vms()
        assert ll_vms.updateVm(
            True, self.vm_name, lease=self.storage_domains[1],
            highly_available=True
        )
        ll_jobs.wait_for_jobs([config.JOB_UPDATE_VM])
        self.start_vms()
        assert ll_vms.stopVm(True, self.vm_name)
        testflow.step(
            "Trying to detach storage domain %s while is holding "
            "leases for VM %s", self.storage_domains[1], self.vm_name
        )
        wait_for_tasks(config.ENGINE, self.new_dc_name)
        assert hl_sd.deactivate_domain(
            config.DATA_CENTER_NAME, self.storage_domains[1], config.ENGINE
        )
        domain_detached = ll_sd.detachStorageDomain(
            False, config.DATA_CENTER_NAME, self.storage_domains[1]
        )
        if not domain_detached:
            assert ll_sd.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.storage_domains[1]
            )
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.storage_domains[1]
        )
        assert domain_detached, (
            "Was possible to detach a storage domain %s while is holding "
            "vm leases", self.storage_domains[1]
        )
