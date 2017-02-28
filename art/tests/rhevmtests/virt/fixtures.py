#! /usr/bin/python
# -*- coding: utf-8 -*-


import pytest
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.unittest_lib import testflow
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains
from rhevmtests.storage.helpers import (
    create_data_center, clean_dc, add_storage_domain
)
import config


@pytest.fixture(scope="class")
def remove_vm(request):
    """
    Remove vm safely
    """

    vm_name = request.cls.vm_name

    def fin():
        testflow.teardown("Remove vm %s", vm_name)
        ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def start_vms(request):
    """
    Start VM's
    """
    vms = request.node.cls.vm_name
    wait_for_vms_ip = getattr(request.node.cls, "wait_for_vms_ip", True)

    def fin():
        """
        Stop VM's
        """
        testflow.teardown("Stop vms %s", vms)
        ll_vms.stop_vms_safely(vms_list=[vms])
    request.addfinalizer(fin)

    testflow.setup("Start vms %s", vms)
    ll_vms.start_vms(vm_list=[vms], wait_for_ip=wait_for_vms_ip)


@pytest.fixture()
def create_dc(request):
    """
    create data center with one host to the environment and a storage domain
    """
    comp_version = request.cls.comp_version
    host = config.HOSTS[request.cls.host_index]
    dc_name = "DC_%s" % comp_version.replace(".", "_")
    cluster_name = "Cluster_%s" % comp_version.replace(".", "_")
    sd_name = "SD_%s" % comp_version.replace(".", "_")

    def fin():
        """
        Clean DC- remove storage-domain & attach the host back to GE DC
        """
        testflow.setup("Clean DC and remove storage Domain")
        clean_dc(
            dc_name=dc_name,
            cluster_name=cluster_name,
            dc_host=host, sd_name=sd_name
        )
        assert hl_storagedomains.remove_storage_domain(
            name=sd_name,
            datacenter=config.DC_NAME[0],
            host=host,
            engine=config.ENGINE,
            format_disk=True
        )

    request.addfinalizer(fin)
    testflow.setup(
        "Create Data Center %s with compatibility version: %s "
        "and storage domain %s",
        dc_name, comp_version, sd_name
    )
    create_data_center(
        dc_name=dc_name,
        cluster_name=cluster_name,
        host_name=host,
        comp_version=comp_version
    )
    add_storage_domain(
        storage_domain=sd_name,
        data_center=dc_name,
        index=0,
        storage_type=config.STORAGE_TYPE_NFS
    )
