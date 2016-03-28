#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for MAC pool per DC
"""
import pytest

import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
from art.rhevm_api.utils import test_utils
from rhevmtests import networking


class MacPoolPrepareSetup(object):
    """
    Prepare setup
    """
    def __init__(self):
        """
        Initialize params
        """
        self.nic0 = conf.NIC_NAME_0
        self.nic1 = conf.NIC_NAME_1
        self.nic2 = conf.NIC_NAME_2
        self.nic3 = conf.NIC_NAME_3
        self.pool_0 = conf.MAC_POOL_NAME_0
        self.pool_1 = conf.MAC_POOL_NAME_1
        self.vm_0 = conf.VM_0
        self.mp_vm = conf.MP_VM
        self.mp_vm_1 = conf.MP_VM_NAMES[1]
        self.mp_template = conf.MP_TEMPLATE
        self.dc_0 = conf.DC_0
        self.ext_dc = conf.EXT_DC_0
        self.def_mac_pool = conf.DEFAULT_MAC_POOL
        self.mac_pool_cl = conf.MAC_POOL_CL
        self.range_list = conf.MAC_POOL_RANGE_LIST
        self.mgmt = conf.MGMT_BRIDGE
        self.ver_35 = conf.VERSION[5]
        self.comp_ver = conf.COMP_VERSION

    def create_basic_setup(self):
        """
        Create basic setup (DC/Cluster)
        """
        if not hl_networks.create_basic_setup(
            datacenter=self.ext_dc, storage_type=conf.STORAGE_TYPE,
            version=self.comp_ver, cluster=self.mac_pool_cl,
            cpu=conf.CPU_NAME
        ):
            raise conf.NET_EXCEPTION()

    def move_host_to_new_cluster(self):
        """
        Move host to new cluster
        """
        if not hl_hosts.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=self.mac_pool_cl
        ):
            raise conf.NET_EXCEPTION()

    def add_storage(self):
        """
        Add storage
        """
        if not hl_storagedomains.addNFSDomain(
            host=conf.HOST_1_NAME, storage=conf.MP_STORAGE,
            data_center=self.ext_dc, path=conf.UNUSED_DATA_DOMAIN_PATHS[0],
            address=conf.UNUSED_DATA_DOMAIN_ADDRESSES[0]
        ):
            raise conf.NET_EXCEPTION()

    def create_vm(self):
        """
        Create VM
        """
        if not ll_vms.createVm(
            positive=True, vmName=self.mp_vm, cluster=self.mac_pool_cl,
            storageDomainName=conf.MP_STORAGE, size=conf.VM_DISK_SIZE
        ):
            raise conf.NET_EXCEPTION()

    def create_template(self):
        """
        Create template
        """
        if not ll_templates.createTemplate(
            positive=True, vm=self.mp_vm, cluster=self.mac_pool_cl,
            name=self.mp_template
        ):
            raise conf.NET_EXCEPTION()

    def remove_vm(self, vm=None):
        """
        Remove VM

        Args:
            vm (str): VM name
        """
        vm = self.mp_vm if not vm else vm
        ll_vms.removeVm(positive=True, vm=vm)

    def deactivate_storage(self):
        """
        Deactivate storage
        """
        test_utils.wait_for_tasks(
            vdc=conf.VDC_HOST, vdc_password=conf.VDC_ROOT_PASSWORD,
            datacenter=self.ext_dc
        )
        ll_storagedomains.deactivate_master_storage_domain(
            positive=True, datacenter=self.ext_dc
        )

    def remove_dc(self):
        """
        Remove DC
        """
        ll_datacenters.remove_datacenter(positive=True, datacenter=self.ext_dc)

    def remove_storage(self):
        """
        Remove storage
        """
        hl_storagedomains.remove_storage_domain(
            name=conf.MP_STORAGE, datacenter=None, host=conf.HOST_1_NAME
        )

    def move_host_to_original_cluster(self):
        """
        Move host to original cluster
        """
        hl_hosts.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=conf.CL_0
        )

    def remove_cluster(self):
        """
        Remove cluster
        """
        ll_clusters.removeCluster(positive=True, cluster=self.mac_pool_cl)

    def update_mac_pool_to_default(self):
        """
        Update MAC pool to default
        """
        curr_mac_pool_values = ll_mac_pool.get_mac_range_values(
            ll_mac_pool.get_mac_pool(pool_name=self.def_mac_pool)
        )
        if not curr_mac_pool_values == conf.DEFAULT_MAC_POOL_VALUES:
            hl_mac_pool.update_default_mac_pool()

    def update_dc_mac_pool_default(self):
        """
        Update DCs MAC pool to default MAC pool
        """
        ll_dc.update_datacenter(
            positive=True, datacenter=self.dc_0,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=self.def_mac_pool)
        )

    def remove_non_default_mac_pool(self):
        """
        Remove all non-default MAC pools from setup if any
        """
        networking.remove_unneeded_mac_pools()

    def create_mac_pools(self, pools):
        """
        Create MAC pools

        Args:
            pools (list): List of tuple of pools names and allow_duplicates
        """
        for pool, dup in pools:
            if not ll_mac_pool.create_mac_pool(
                name=pool, ranges=[self.range_list[0]], allow_duplicates=dup
            ):
                raise conf.NET_EXCEPTION()

    def update_dcs_mac_pools(self, dcs):
        """
        Update DCs with created MAC pools

        Args:
            dcs (list): List of tuple [(DC, pool)] to update
        """
        for dc, pool in dcs:
            if not ll_dc.update_datacenter(
                positive=True, datacenter=dc,
                mac_pool=ll_mac_pool.get_mac_pool(pool_name=pool)
            ):
                raise conf.NET_EXCEPTION()


class Case06Fixture(MacPoolPrepareSetup):
    """
    Fixture functions for TestMacPoolRange06 case
    """
    def __init__(self):
        """
        Call base class __init__
        """
        super(Case06Fixture, self).__init__()

    def create_mac_pools_case_06(self):
        """
        Create MAC pools
        """
        pools = [(self.pool_0, False), (self.pool_1, True)]
        self.create_mac_pools(pools=pools)

    def update_dcs_mac_pools_case_06(self):
        """
        Update DCs with created MAC pools
        """
        dcs = [(self.dc_0, self.pool_0), (self.ext_dc, self.pool_0)]
        self.update_dcs_mac_pools(dcs=dcs)

    def remove_nics_from_vm(self):
        """
        Remove vNICs from VM
        """
        for nic in (self.nic1, self.nic2, self.nic3):
            for vm in (self.vm_0, self.mp_vm):
                if nic == self.nic3 and vm == self.vm_0:
                    continue
                ll_vms.removeNic(positive=True, vm=vm, nic=nic)

    def update_mac_pool_dcs_to_default_case_06(self):
        """
        Update DCs with default MAC pool
        """
        dcs = [
            (self.dc_0, self.def_mac_pool), (self.ext_dc, self.def_mac_pool)
        ]
        self.update_dcs_mac_pools(dcs=dcs)


class Case08Fixture(MacPoolPrepareSetup):
    def __init__(self):
        super(Case08Fixture, self).__init__()

    def create_mac_pool_case_08(self):
        """
        Create MAC pool
        """
        pool = [(self.pool_0, False)]
        self.create_mac_pools(pools=pool)

    def update_dcs_mac_pools_case_08(self):
        """
        Update DCs with created MAC pools
        """
        dcs = [(self.ext_dc, self.pool_0)]
        self.update_dcs_mac_pools(dcs=dcs)

    def update_template_nic(self):
        """
        Update template NICs
        """
        for nic in [self.nic0, self.nic1]:
            if not ll_templates.addTemplateNic(
                positive=True, template=self.mp_template, name=nic,
                data_center=self.ext_dc
            ):
                raise conf.NET_EXCEPTION()

    def create_vm_from_template(self):
        """
        Create VM
        """
        if not ll_vms.createVm(
            positive=True, vmName=self.mp_vm_1, cluster=self.mac_pool_cl,
            template=self.mp_template, network=self.mgmt
        ):
            raise conf.NET_EXCEPTION()

    def remove_template(self):
        """
        Remove template
        """
        if not ll_templates.removeTemplate(
            positive=True, template=self.mp_template
        ):
            raise conf.NET_EXCEPTION()

    def update_mac_pool_dcs_to_default_case_08(self):
        """
        Update DC with default MAC pool
        """
        dc = [(self.ext_dc, self.def_mac_pool)]
        self.update_dcs_mac_pools(dcs=dc)

    def remove_vm_case_08(self):
        """
        Remove VM for case 08
        """
        self.remove_vm(vm=self.mp_vm_1)


class Case11Fixture(MacPoolPrepareSetup):
    def __init__(self):
        super(Case11Fixture, self).__init__()

    def update_dc_version(self, version):
        """
        Update DC version
        """
        if not ll_dc.update_datacenter(
            positive=True, datacenter=self.ext_dc, version=version
        ):
            raise conf.NET_EXCEPTION()

    def update_dc_version_35(self):
        """
        Update DC version to 3.5
        """
        self.update_dc_version(version=self.ver_35)

    def update_mac_pool_range(self):
        """
        Update MAC poll range
        """
        if not ll_mac_pool.create_mac_pool(
            name=self.pool_0, ranges=[self.range_list[0]]
        ):
            raise conf.NET_EXCEPTION()

    def update_dcs_mac_pools_case_11(self):
        """
        Update DCs with created MAC pools
        """
        dcs = [(self.dc_0, self.pool_0), (self.ext_dc, self.pool_0)]
        self.update_dcs_mac_pools(dcs=dcs)

    def add_nic_to_vm(self):
        """
        Add NIC to VM
        """
        if not ll_vms.addNic(positive=True, vm=self.mp_vm, name=self.nic1):
            raise conf.NET_EXCEPTION()

    def update_dc_version_original(self):
        """
        Update DC version to original version
        """
        self.update_dc_version(version=self.comp_ver)

    def remove_nics_from_vm(self):
        """
        Remove NIC from VM
        """
        for vm in (self.vm_0, self.mp_vm):
            ll_vms.removeNic(positive=True, vm=vm, nic=self.nic1)

    def update_mac_pool_dcs_to_default_case_11(self):
        """
        Update DCs with default MAC pool
        """
        dcs = [
            (self.dc_0, self.def_mac_pool), (self.ext_dc, self.def_mac_pool)
        ]
        self.update_dcs_mac_pools(dcs=dcs)


@pytest.fixture(scope="module")
def mac_pool_prepare_setup(request):
    """
    Prepare setup for MAC pool per DC tests

    Create basic setup -> None
    Move host to new cluster -> Move host back to original cluster
    Add storage -> Remove storage
    Create VM -> Remove DC
              -> Remove storage
              -> Move host back to original cluster
              -> Remove cluster
              -> Remove VM
    Create template -> Update default MAC pool for DC
    """
    ps = MacPoolPrepareSetup()

    @networking.ignore_exception
    def fin8():
        """
        Finalizer for remove non default MAC pools
        """
        ps.remove_non_default_mac_pool()
    request.addfinalizer(fin8)

    @networking.ignore_exception
    def fin7():
        """
        Finalizer for set default MAC pools for DCs
        """
        ps.update_mac_pool_to_default()
    request.addfinalizer(fin7)

    @networking.ignore_exception
    def fin6():
        """
        Finalizer for remove clister
        """
        ps.remove_cluster()
    request.addfinalizer(fin6)

    @networking.ignore_exception
    def fin5():
        ps.move_host_to_original_cluster()
    request.addfinalizer(fin5)

    @networking.ignore_exception
    def fin4():
        """
        Finalizer for remove storage
        """
        ps.remove_storage()
    request.addfinalizer(fin4)

    @networking.ignore_exception
    def fin3():
        ps.remove_dc()
    request.addfinalizer(fin3)

    @networking.ignore_exception
    def fin2():
        """
        Finalizer for remove DC
        """
        ps.deactivate_storage()
    request.addfinalizer(fin2)

    @networking.ignore_exception
    def fin1():
        """
        Finalizer for remove VM
        """
        ps.remove_vm()
    request.addfinalizer(fin1)

    ps.create_basic_setup()
    ps.move_host_to_new_cluster()
    ps.add_storage()
    ps.create_vm()
    ps.create_template()


@pytest.fixture(scope="class")
def mac_pool_range_06_fixture(request, mac_pool_prepare_setup):
    """
    Setup and teardown for TestMacPoolRange06

    Create MAC pool -> Remove MAC pool
    Update DCs MAC pools -> Update DCs MAC pool to default
                         -> Remove vNICs from VM
    -> Remove non-default pools
    """
    ps = Case06Fixture()

    def fin3():
        """
        Finalizer for remove non default MAC pools
        """
        ps.remove_non_default_mac_pool()
    request.addfinalizer(fin3)

    def fin2():
        """
        Finalizer for set default MAC pools for DCs
        """
        ps.update_mac_pool_dcs_to_default_case_06()
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove NICs from VM
        """
        ps.remove_nics_from_vm()
    request.addfinalizer(fin1)

    ps.create_mac_pools_case_06()
    ps.update_dcs_mac_pools_case_06()


@pytest.fixture(scope="class")
def mac_pool_range_08_fixture(request, mac_pool_prepare_setup):
    """
    Setup and teardown for TestMacPoolRange07

    Create MAC pool -> Remove MAC pool
    Update DCs MAC pools -> Update DCs MAC pool to default
    Update template NICs - > Remove template
    Create VM -> remove VM
    -> Remove non-default pools
    """
    ps = Case08Fixture()

    def fin4():
        """
        Finalizer for remove non default MAC pools
        """
        ps.remove_non_default_mac_pool()
    request.addfinalizer(fin4)

    def fin3():
        """
        Finalizer for set default MAC pools for DCs
        """
        ps.update_mac_pool_dcs_to_default_case_08()
    request.addfinalizer(fin3)

    def fin2():
        """
        Finalizer for remove template
        """
        ps.remove_template()
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for remove VM
        """
        ps.remove_vm_case_08()
    request.addfinalizer(fin1)

    ps.create_mac_pool_case_08()
    ps.update_dcs_mac_pools_case_08()
    ps.update_template_nic()
    ps.create_vm_from_template()


@pytest.fixture(scope="class")
def mac_pool_range_11_fixture(request, mac_pool_prepare_setup):
    """
    Setup and teardown for TestMacPoolRange11

    Update DC version to 3.5 -> Update DC version to original version
    Update MAC pool range
    Update DCs MAC pool -> Update DCs MAC pool to default
    Add NIC to VM -> Remove NIC from VM
    -> Remove non-default pools
    """
    ps = Case11Fixture()

    def fin4():
        """
        Finalizer for remove non default MAC pools
        """
        ps.remove_non_default_mac_pool()
    request.addfinalizer(fin4)

    def fin3():
        """
        Finalizer for set default MAC pools for DCs
        """
        ps.update_mac_pool_dcs_to_default_case_11()
    request.addfinalizer(fin3)

    def fin2():
        """
        Finalizer for remove NICs from VM
        """
        ps.remove_nics_from_vm()
    request.addfinalizer(fin2)

    def fin1():
        """
        Finalizer for update DC version
        """
        ps.update_dc_version_original()
    request.addfinalizer(fin1)

    ps.update_dc_version_35()
    ps.update_mac_pool_range()
    ps.update_dcs_mac_pools_case_11()
    ps.add_nic_to_vm()
