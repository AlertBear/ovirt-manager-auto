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
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as mac_pool_conf
import helper
import rhevmtests.helpers as global_helper
import rhevmtests.networking.config as conf
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains
from art.rhevm_api.resources.storage import clean_mount_point
from rhevmtests import networking
from rhevmtests.networking.fixtures import NetworkFixtures


class MacPool(NetworkFixtures):
    """
    Prepare setup
    """
    def __init__(self):
        """
        Initialize params
        """
        super(MacPool, self).__init__()
        self.nic0 = mac_pool_conf.NIC_NAME_0
        self.nic1 = mac_pool_conf.NIC_NAME_1
        self.nic2 = mac_pool_conf.NIC_NAME_2
        self.nic3 = mac_pool_conf.NIC_NAME_3
        self.pool_0 = mac_pool_conf.MAC_POOL_NAME_0
        self.pool_1 = mac_pool_conf.MAC_POOL_NAME_1
        self.mp_vm = mac_pool_conf.MP_VM
        self.mp_vm_1 = mac_pool_conf.MP_VM_NAMES[1]
        self.mp_template = mac_pool_conf.MP_TEMPLATE
        self.ext_dc = mac_pool_conf.EXT_DC_0
        self.def_mac_pool = conf.DEFAULT_MAC_POOL
        self.mac_pool_cl = mac_pool_conf.MAC_POOL_CL
        self.range_list = mac_pool_conf.MAC_POOL_RANGE_LIST
        self.ver_35 = conf.VERSION[5]
        self.comp_ver = conf.COMP_VERSION

    def create_basic_setup(self):
        """
        Create basic setup (DC/Cluster)
        """
        assert hl_networks.create_basic_setup(
            datacenter=self.ext_dc, version=self.comp_ver,
            cluster=self.mac_pool_cl, cpu=conf.CPU_NAME
        )

    def move_host_to_new_cluster(self):
        """
        Move host to new cluster
        """
        assert hl_hosts.move_host_to_another_cluster(
            host=conf.HOST_1_NAME, cluster=self.mac_pool_cl
        )

    def add_storage(self):
        """
        Add storage
        """
        assert hl_storagedomains.addNFSDomain(
            host=self.host_0_name, storage=mac_pool_conf.MP_STORAGE,
            data_center=self.ext_dc, path=conf.UNUSED_DATA_DOMAIN_PATHS[0],
            address=conf.UNUSED_DATA_DOMAIN_ADDRESSES[0]
        )

    def create_vm(self):
        """
        Create VM
        """
        assert ll_vms.createVm(
            positive=True, vmName=self.mp_vm, cluster=self.mac_pool_cl,
            storageDomainName=mac_pool_conf.MP_STORAGE,
            provisioned_size=conf.VM_DISK_SIZE,
        )

    def create_template(self):
        """
        Create template
        """
        assert ll_templates.createTemplate(
            positive=True, vm=self.mp_vm, cluster=self.mac_pool_cl,
            name=self.mp_template
        )

    def remove_vm(self, vm=None):
        """
        Remove VM

        Args:
            vm (str): VM name
        """
        vm = self.mp_vm if not vm else vm
        ll_vms.removeVm(positive=True, vm=vm)

    def remove_dc(self):
        """
        Remove DC
        """
        ll_datacenters.remove_datacenter(
            positive=True, datacenter=self.ext_dc, force=True
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
        if not curr_mac_pool_values == mac_pool_conf.DEFAULT_MAC_POOL_VALUES:
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
            assert ll_mac_pool.create_mac_pool(
                name=pool, ranges=[self.range_list[0]], allow_duplicates=dup
            )

    def update_dcs_mac_pools(self, dcs):
        """
        Update DCs with created MAC pools

        Args:
            dcs (list): List of tuple [(DC, pool)] to update
        """
        for dc, pool in dcs:
            assert ll_dc.update_datacenter(
                positive=True, datacenter=dc,
                mac_pool=ll_mac_pool.get_mac_pool(pool_name=pool)
            )


class Case06Fixture(MacPool):
    """
    Fixture functions for TestMacPoolRange06 case
    """
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


class Case08Fixture(MacPool):
    """
    Fixture functions for TestMacPoolRange08 case
    """
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
            assert ll_templates.addTemplateNic(
                positive=True, template=self.mp_template, name=nic,
                data_center=self.ext_dc
            )

    def create_vm_from_template(self):
        """
        Create VM
        """
        assert ll_vms.createVm(
            positive=True, vmName=self.mp_vm_1, cluster=self.mac_pool_cl,
            template=self.mp_template, network=self.mgmt_bridge
        )

    def remove_template(self):
        """
        Remove template
        """
        assert ll_templates.removeTemplate(
            positive=True, template=self.mp_template
        )

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


class Case11Fixture(MacPool):
    """
    Fixture functions for TestMacPoolRange11 case
    """
    def update_dc_version(self, version):
        """
        Update DC version
        """
        assert ll_dc.update_datacenter(
            positive=True, datacenter=self.ext_dc, version=version
        )

    def update_dc_version_35(self):
        """
        Update DC version to 3.5
        """
        self.update_dc_version(version=self.ver_35)

    def update_mac_pool_range(self):
        """
        Update MAC poll range
        """
        assert ll_mac_pool.create_mac_pool(
            name=self.pool_0, ranges=[self.range_list[0]]
        )

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
        assert ll_vms.addNic(positive=True, vm=self.mp_vm, name=self.nic1)

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
    ps = MacPool()

    @networking.ignore_exception
    def fin8():
        """
        Clean storage domain
        """
        clean_mount_point(
            host=ps.host_0_name, src_ip=conf.UNUSED_DATA_DOMAIN_ADDRESSES[0],
            src_path=conf.UNUSED_DATA_DOMAIN_PATHS[0],
            opts=global_helper.NFS_MNT_OPTS
        )
    request.addfinalizer(fin8)

    @networking.ignore_exception
    def fin7():
        """
        Remove storage
        """
        ll_storagedomains.removeStorageDomain(
            positive=True, storagedomain=mac_pool_conf.MP_STORAGE,
            host=ps.host_0_name, force=True
        )
    request.addfinalizer(fin7)

    @networking.ignore_exception
    def fin6():
        """
        Finalizer for remove non default MAC pools
        """
        ps.remove_non_default_mac_pool()
    request.addfinalizer(fin6)

    @networking.ignore_exception
    def fin5():
        """
        Finalizer for set default MAC pools for DCs
        """
        ps.update_mac_pool_to_default()
    request.addfinalizer(fin5)

    @networking.ignore_exception
    def fin4():
        """
        Finalizer for remove cluster
        """
        ps.remove_cluster()
    request.addfinalizer(fin4)

    @networking.ignore_exception
    def fin3():
        """
        Remove datacenter
        """
        ps.remove_dc()
    request.addfinalizer(fin3)

    @networking.ignore_exception
    def fin2():
        """
        Move host to original cluster
        """
        ps.move_host_to_original_cluster()
    request.addfinalizer(fin2)

    @global_helper.wait_for_jobs_deco(["Removing VM"])
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
    Setup and teardown for TestMacPoolRange08

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
def fixture_mac_pool_range_case_02(request, mac_pool_prepare_setup):
    """
    Create MAC pool
    Create a new DC with MAC pool
    Remove a created DC
    """
    MacPool()
    mac_pool = request.node.cls.mac_pool
    range_ = request.node.cls.range
    ext_dc = request.node.cls.ext_dc

    def fin2():
        """
        Remove MAC pool
        """
        ll_mac_pool.remove_mac_pool(mac_pool_name=mac_pool)
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove DC
        """
        ll_dc.remove_datacenter(positive=True, datacenter=ext_dc)
    request.addfinalizer(fin1)

    assert ll_mac_pool.create_mac_pool(name=mac_pool, ranges=[range_])
    helper.create_dc()
    assert ll_dc.remove_datacenter(positive=True, datacenter=ext_dc)


@pytest.fixture(scope="class")
def fixture_mac_pool_range_case_03(request, mac_pool_prepare_setup):
    """
    Create 1 MAC pool
    Update DC with 1 of created MAC pool
    """
    ps = MacPool()
    pool_name_0 = request.node.cls.pool_name_0
    pool_name_1 = request.node.cls.pool_name_1
    pool_name_2 = request.node.cls.pool_name_2
    range_list = request.node.cls.range_list

    @networking.ignore_exception
    def fin2():
        """
        Remove MAC pools
        """
        for mac_pool in (pool_name_0, pool_name_1, pool_name_2):
            ll_mac_pool.remove_mac_pool(mac_pool_name=mac_pool)
    request.addfinalizer(fin2)

    def fin1():
        """
        Update MAC pool in DC
        """
        ll_dc.update_datacenter(
            positive=True, datacenter=ps.dc_0,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=ps.def_mac_pool)
        )
    request.addfinalizer(fin1)

    assert ll_mac_pool.create_mac_pool(
        name=pool_name_0, ranges=[range_list[0]]
    )
    assert ll_dc.update_datacenter(
        positive=True, datacenter=ps.dc_0,
        mac_pool=ll_mac_pool.get_mac_pool(pool_name=pool_name_0)
    )


@pytest.fixture(scope="class")
def fixture_mac_pool_range_case_04(request, mac_pool_prepare_setup):
    """
    Create a new MAC pool
    Update DC with this MAC pool
    """
    ps = MacPool()
    vm = request.node.cls.vm
    pool_name = request.node.cls.pool_name
    range_list = request.node.cls.range_list

    def fin3():
        """
        Remove MAC pool
        """
        ll_mac_pool.remove_mac_pool(mac_pool_name=pool_name)
    request.addfinalizer(fin3)

    def fin2():
        """
        Update MACpoll in DC
        """
        ll_dc.update_datacenter(
            positive=True, datacenter=ps.dc_0,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=ps.def_mac_pool)
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove vNICs from VM
        """
        for nic in mac_pool_conf.NICS_NAME[1:5]:
            ll_vms.removeNic(positive=True, vm=vm, nic=nic)
    request.addfinalizer(fin1)

    assert ll_mac_pool.create_mac_pool(name=pool_name, ranges=[range_list[1]])
    assert ll_dc.update_datacenter(
        positive=True, datacenter=ps.dc_0,
        mac_pool=ll_mac_pool.get_mac_pool(pool_name)
    )


@pytest.fixture(scope="class")
def fixture_mac_pool_range_case_05(request, mac_pool_prepare_setup):
    """
    Create a new MAC pool
    Update DC with this MAC pool
    """
    ps = MacPool()
    vm = request.node.cls.vm
    pool_name = request.node.cls.pool_name
    mac_pool_ranges = request.node.cls.mac_pool_ranges

    def fin3():
        """
        Remove MAC pool
        """
        ll_mac_pool.remove_mac_pool(mac_pool_name=pool_name)
    request.addfinalizer(fin3)

    def fin2():
        """
        Update MAC pool in DC
        """
        ll_dc.update_datacenter(
            positive=True, datacenter=ps.dc_0,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=ps.def_mac_pool)
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove vNICs from VM
        """
        for nic in mac_pool_conf.NICS_NAME[1:7]:
            ll_vms.removeNic(positive=True, vm=vm, nic=nic)
    request.addfinalizer(fin1)

    assert ll_mac_pool.create_mac_pool(
        name=pool_name, ranges=mac_pool_ranges[:3]
    )
    assert ll_dc.update_datacenter(
        positive=True, datacenter=conf.DC_0,
        mac_pool=ll_mac_pool.get_mac_pool(pool_name=pool_name)
    )
    for i in range(3):
        assert ll_vms.addNic(
            positive=True, vm=vm, name=mac_pool_conf.NICS_NAME[i + 1]
        )


@pytest.fixture(scope="class")
def fixture_mac_pool_range_case_09(request, mac_pool_prepare_setup):
    """
     Create MAC pool
    Create 2 new DCs with MAC pool
    """
    MacPool()
    ext_dc_1 = request.node.cls.ext_dc_1
    ext_dc_2 = request.node.cls.ext_dc_2
    pool_name_0 = request.node.cls.pool_name_0
    range_list = request.node.cls.range_list

    def fin():
        """
        Remove MAC pool
        """
        ll_mac_pool.remove_mac_pool(mac_pool_name=pool_name_0)
    request.addfinalizer(fin)

    assert ll_mac_pool.create_mac_pool(
        name=pool_name_0, ranges=[range_list[0]]
    )
    for dc in [ext_dc_1, ext_dc_2]:
        helper.create_dc(dc_name=dc)
