import config
import pytest
from art.unittest_lib.common import testflow
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    vms as ll_vms
)
import rhevmtests.storage.helpers as storage_helpers


@pytest.fixture()
def initialize_attributes(request, storage):
    """
    Initialize attributes
    """
    self = request.node.cls

    self.host = ll_hosts.get_spm_host(config.HOSTS)
    self.host_ip = ll_hosts.get_host_ip(self.host)


@pytest.fixture()
def flush_ip_table(request):
    """
    Flush iptables
    """
    self = request.node.cls

    def finalizer():
        testflow.teardown("Flushing iptables on host %s", self.host_ip)
        assert storage_helpers.flushIptables(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW
        ), "Failed to flush iptables rules on host %s" % self.host_ip

    request.addfinalizer(finalizer)


@pytest.fixture()
def add_vm_with_disk(request, storage):
    """
    Create a new VM with a disk
    """
    self = request.node.cls

    def finalizer():
        assert ll_vms.safely_remove_vms(
            [self.test_vm_name]
        ), "Unable to remove VM %s" % self.test_vm_name

    request.addfinalizer(finalizer)
    self.vm_names = list()
    self.test_vm_name = storage_helpers.create_unique_object_name(
        self.__name__, config.OBJECT_TYPE_VM
    )
    vm_args = config.create_vm_args.copy()
    vm_args['vmName'] = self.test_vm_name
    vm_args['storageDomainName'] = self.storage_domain

    testflow.setup("Creating VM %s", self.test_vm_name)
    assert storage_helpers.create_vm_or_clone(**vm_args), (
        "Failed to create VM %s" % self.test_vm_name
    )
    self.vm_names.append(self.test_vm_name)

    testflow.setup(
        "Attaching disk %s to VM %s", self.disk_name, self.test_vm_name
    )
    assert ll_disks.attachDisk(True, self.disk_name, self.test_vm_name), (
        "Failed to attach disk %s to VM %s" %
        (self.disk_name, self.test_vm_name)
    )
    assert ll_disks.wait_for_disks_status(self.disk_name), (
        "Disk %s is not in the expected state 'OK" % self.disk_name
    )


@pytest.fixture()
def wait_for_disks_status_ok(request, storage):
    """
    Wait until disk status is OK for self.disk_name
    """
    self = request.node.cls

    def finalizer():
        assert ll_disks.wait_for_disks_status(self.disk_name), (
            "Failed to wait for disk %s to be in status OK" % self.disk_name
        )

    request.addfinalizer(finalizer)


@pytest.fixture()
def create_multiple_vms(request, storage):
    """
    Create multiple VMs
    """
    self = request.node.cls

    def finalizer():
        assert ll_vms.safely_remove_vms(
            self.vm_names
        ), "Unable to remove VMs %s" % self.vm_names
    request.addfinalizer(finalizer)

    testflow.setup("Creating %s VMs", self.vm_count)
    self.vm_names = list()
    vm_args = config.create_vm_args.copy()
    vm_args['installation'] = False

    sd_list = self.storage_domains[0:self.vm_count]
    if not self.multiple_sd:
        sd_list = [sd_list[0] for _ in range(self.vm_count)]

    for i, sd in zip(range(self.vm_count), sd_list):
        self.vm_name = storage_helpers.create_unique_object_name(
            self.__name__, config.OBJECT_TYPE_VM
        )
        vm_args['vmName'] = self.vm_name
        vm_args['storageDomainName'] = sd
        assert storage_helpers.create_vm_or_clone(**vm_args), (
            'Unable to create VM %s for test' % self.vm_name
        )
        self.vm_names.append(self.vm_name)
