#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Global fixtures
"""

import pytest

import art.rhevm_api.tests_lib.high_level.storagedomains as hl_sd
import config
import fixtures_helper
import helpers
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_datacenters,
    vms as ll_vms,
    storagedomains as ll_sd
)
from art.unittest_lib import testflow
from rhevmtests.storage import config as stconfig


@pytest.fixture()
def stop_vms_fixture_function(request):
    """
    Stop VM(s).
    """
    vms_dict = request.getfixturevalue("start_vms_dict")
    vms_dict = vms_dict or dict()
    vms_to_stop = fixtures_helper.get_fixture_val(
        request=request, attr_name="vms_to_stop", default_value=vms_dict.keys()
    )

    def fin():
        """
        Stop VM(s).
        """
        testflow.teardown("Stop VMs %s", vms_to_stop)
        assert ll_vms.stop_vms_safely(vms_list=vms_to_stop)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def start_vm(request):
    """
    Run VM once.
    """
    vms_dict = getattr(request.node.cls, "start_vms_dict", dict())
    vms_to_stop = getattr(request.node.cls, 'vms_to_stop', vms_dict.keys())

    def fin():
        """
        Stop VM(s).
        """
        testflow.teardown("Stop VMs %s", vms_to_stop)
        assert ll_vms.stop_vms_safely(vms_list=vms_to_stop)
    request.addfinalizer(fin)

    if vms_dict:
        fixtures_helper.start_vm_helper(vms_dict=vms_dict)


@pytest.fixture()
def start_vms_fixture_function(request, stop_vms_fixture_function):
    """
    Run VMs once.
    """
    vms_dict = request.getfixturevalue("start_vms_dict") or dict()
    if vms_dict:
        fixtures_helper.start_vm_helper(vms_dict=vms_dict)


@pytest.fixture(scope="class")
def create_clusters(request):
    """
    Add cluster(s).

    Example:
        clusters_dict = {
            ext_cls_1: {
                "name": ext_cls_1,
                "data_center": dc,
                "cpu": conf.CPU_NAME,
                "version": conf.COMP_VERSION,
                "management_network": net_1
            },
            ext_cls_2: {
                "name": ext_cls_2,
                "data_center": dc,
                "cpu": conf.CPU_NAME,
                "version": conf.COMP_VERSION,
                "management_network": net_2
            },
        }
    """
    clusters_dict = getattr(request.node.cls, "clusters_dict", dict())
    clusters_to_remove = getattr(
        request.node.cls, 'clusters_to_remove', clusters_dict.keys()
    )
    result_list = list()

    def fin():
        """
        Remove clusters
        """
        for cluster in clusters_to_remove:
            result_list.append(
                ll_clusters.removeCluster(positive=True, cluster=cluster)
            )
        assert all(result_list)
    request.addfinalizer(fin)

    for cluster_name, params in clusters_dict.iteritems():
        testflow.setup("Add cluster %s with %s", cluster_name, params)
        assert ll_clusters.addCluster(positive=True, **params)


@pytest.fixture(scope="class")
def create_datacenters(request):
    """
    Add datacenter(s).
    """
    datacenters_dict = getattr(request.node.cls, "datacenters_dict", dict())
    dcs_to_remove = getattr(
        request.node.cls, 'dcs_to_remove', datacenters_dict.keys()
    )
    result_list = list()

    def fin():
        """
        Remove datacenter(s).
        """
        for dc in dcs_to_remove:
            testflow.teardown("Remove datacenter %s", dc)
            result_list.append(
                ll_datacenters.remove_datacenter(positive=True, datacenter=dc)
            )
        assert all(result_list)
    request.addfinalizer(fin)

    for dc_params in datacenters_dict.itervalues():
        testflow.setup("Add datacenter with %s", dc_params)
        assert ll_datacenters.addDataCenter(positive=True, **dc_params)


@pytest.fixture(scope='class')
def init_storage_manager(request, storage):
    """
    Initialize storage manager instance
    """

    self = request.node.cls
    self.manager = config.ISCSI_STORAGE_MANAGER if storage == (
        config.STORAGE_TYPE_ISCSI
    ) else config.FCP_STORAGE_MANAGER

    # Initialize the storage manager with iscsi as the storage type since
    # storage_api has only iscsi manager which is good also for fc
    self.storage_manager = (
        helpers.get_storage_manager(
            config.STORAGE_TYPE_ISCSI, self.manager, config.STORAGE_CONFIG
        )
    )
    self.storage_server = config.STORAGE_SERVER[self.manager]
    assert self.storage_manager, (
        "Failed to retrieve storage server" % self.new_storage_domain
    )


@pytest.fixture(scope='class')
def create_lun_on_storage_server(request, storage):
    """
    Create a LUN on storage server and refresh hosts LUNs list by maintenance
    and activate them
    """
    self = request.node.cls

    testflow.setup(
        "Creating a new LUN in storage server %s", self.storage_server
    )
    lun_name = 'lun_%s' % self.__name__
    new_lun_size = getattr(self, 'new_lun_size', '60')
    existing_sd = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, storage
    )[0]
    existing_lun = helpers.get_lun_id(
        existing_sd, self.storage_manager, self.storage_server
    )
    self.new_lun_id, self.new_lun_identifier = (
        self.storage_manager.create_and_map_lun(
            lun_name, new_lun_size, existing_lun
        )
    )
    assert self.new_lun_id, "Failed to get LUN ID"
    assert self.new_lun_identifier, "Failed to get LUN identifier"
    if hasattr(self, 'lun_params'):
        if self.storage_server == config.STORAGE_SERVER_NETAPP:
            self.storage_manager.modify_lun(
                self.new_lun_id, **self.lun_params
            )

    if storage == config.STORAGE_TYPE_ISCSI:
        config.UNUSED_LUNS.append(self.new_lun_identifier)
        config.UNUSED_LUN_ADDRESSES.append(config.UNUSED_LUN_ADDRESSES[0])
        config.UNUSED_LUN_TARGETS.append(config.UNUSED_LUN_TARGETS[0])
        self.index = len(config.UNUSED_LUNS)-1
    elif storage == config.STORAGE_TYPE_FCP:
        config.UNUSED_FC_LUNS.append(self.new_lun_identifier)
        self.index = len(config.UNUSED_FC_LUNS)-1
    testflow.setup(
        "Deactivating and activating hosts %s after LUN creation", config.HOSTS
    )
    helpers.maintenance_and_activate_hosts()


@pytest.fixture(scope='class')
def remove_lun_from_storage_server(request, storage):
    """
    Remove the LUN from storage server. Refresh the hosts LUNs list by
    maintenance and activate them for iSCSI and maintenance, reboot and
    activate for FC
    """
    self = request.node.cls

    def finalizer():
        if self.new_lun_id:
            testflow.teardown(
                "Removing LUN %s from storage server %s", self.new_lun_id,
                self.storage_server
            )
            self.storage_manager.removeLun(self.new_lun_id)
            if storage == config.STORAGE_TYPE_ISCSI:
                config.UNUSED_LUNS.pop(self.index)
                config.UNUSED_LUN_ADDRESSES.pop(self.index)
                config.UNUSED_LUN_TARGETS.pop(self.index)
                testflow.teardown(
                    "Deactivating and activating hosts %s after LUN removal",
                    config.HOSTS
                )
                helpers.maintenance_and_activate_hosts()
            elif storage == config.STORAGE_TYPE_FCP:
                config.UNUSED_FC_LUNS.pop(self.index)
                testflow.teardown(
                    "Rebooting hosts %s after LUN removal", config.HOSTS
                )
                helpers.reboot_hosts(config.VDS_HOSTS)
            self.index -= 1
    request.addfinalizer(finalizer)


@pytest.fixture(scope='module')
def register_windows_templates(request):
    """
    Import preconfigured nfs-windows data nfs storage that contains
    windows templates and register the templates that reside in it
    """
    def fin():
        testflow.teardown(
            "Detach and deactivate %s storage domain" %
            config.WINDOWS_DATASD_NAME
        )
        hl_sd.remove_storage_domain(
            name=config.WINDOWS_DATASD_NAME,
            datacenter=config.WINDOWS_DATASD_DC,
            host=config.HOSTS[0],
            engine=config.ENGINE
        )
    request.addfinalizer(fin)

    testflow.setup(
        "Add storage domain %s, attach to date-center %s and activate",
        config.WINDOWS_DATASD_NAME, config.WINDOWS_DATASD_DC
    )
    assert ll_sd.importStorageDomain(
        True, stconfig.TYPE_DATA,
        config.STORAGE_TYPE_NFS,
        config.WINDOWS_DATASD_ADDR,
        config.WINDOWS_DATASD_PATH,
        config.WINDOWS_DATASD_HOST,
    ), "Storage domain %s can not be imported" % config.WINDOWS_DATASD_NAME

    assert ll_sd.attachStorageDomain(
        True, config.WINDOWS_DATASD_DC, config.WINDOWS_DATASD_NAME
    ), 'Unable to attach domain %s to dc %s' % (
        config.WINDOWS_DATASD_DC, config.WINDOWS_DATASD_NAME
    )

    unregistered_templates = ll_sd.get_unregistered_templates(
        config.WINDOWS_DATASD_NAME
    )
    template_names = [
        template.get_name() for template in unregistered_templates
    ]
    testflow.setup(
        "Registering templates: %s", ", ".join(template_names)
    )
    for template in unregistered_templates:
        assert ll_sd.register_object(
            template, cluster=config.CLUSTER_NAME[0],
        ), "Template %s registration failed" % (template.name)


@pytest.fixture(scope="class")
def stop_vms_fixture(request):
    """
    Stop VM(s).
    """
    vms_to_stop = fixtures_helper.get_fixture_val(
        request=request, attr_name="vms_to_stop", default_value=[]
    )

    def fin():
        """
        Stop VM(s).
        """
        testflow.teardown("Stop VMs %s", vms_to_stop)
        assert ll_vms.stop_vms_safely(vms_list=vms_to_stop)
    request.addfinalizer(fin)
