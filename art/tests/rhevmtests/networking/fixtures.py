#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Networking fixtures
"""

import logging
import os

import pytest

import art.core_api.apis_exceptions as exceptions
import config as conf
import rhevmtests.networking.sr_iov.config as sriov_conf
import fixtures_helper as network_fixture_helper
import rhevmtests.coresystem.aaa.ldap.common as aaa_common
import rhevmtests.helpers as global_helper
from art.rhevm_api.tests_lib.high_level import (
    vms as hl_vms,
    networks as hl_networks
)
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    hosts as ll_hosts,
    vms as ll_vms,
    clusters as ll_clusters,
    sriov as ll_sriov
)
from rhevmtests.networking import config_handler
from art.unittest_lib import testflow
from rhevmtests import fixtures_helper

logger = logging.getLogger(__name__)


class NetworkFixtures(object):
    """
    Class for networking fixtures
    """
    def __init__(self):
        conf.VDS_0_HOST = conf.VDS_HOSTS[0]
        conf.VDS_1_HOST = conf.VDS_HOSTS[1]
        conf.VDS_2_HOST = (
            conf.VDS_HOSTS[2] if len(conf.VDS_HOSTS) > 2 else None
        )
        conf.HOST_0_NAME = conf.HOSTS[0]
        conf.HOST_1_NAME = conf.HOSTS[1]
        conf.HOST_2_NAME = conf.HOSTS[2] if len(conf.HOSTS) > 2 else None
        conf.HOST_0_IP = conf.VDS_0_HOST.ip
        conf.HOST_1_IP = conf.VDS_1_HOST.ip
        conf.HOST_0_NICS = conf.VDS_0_HOST.nics
        conf.HOST_1_NICS = conf.VDS_1_HOST.nics
        conf.HOST_2_NICS = conf.VDS_2_HOST.nics
        self.vds_0_host = conf.VDS_0_HOST
        self.vds_1_host = conf.VDS_1_HOST
        self.vds_2_host = conf.VDS_2_HOST
        self.vds_list = [
            v for v in [self.vds_0_host, self.vds_1_host, self.vds_2_host]
            if v
        ]
        self.host_0_name = conf.HOST_0_NAME
        self.host_1_name = conf.HOST_1_NAME
        self.host_2_name = conf.HOST_2_NAME
        self.hosts_list = [
            h for h in [self.host_0_name, self.host_1_name, self.host_2_name]
            if h
        ]
        self.host_0_ip = conf.HOST_0_IP
        self.host_1_ip = conf.HOST_1_IP
        self.host_0_nics = conf.HOST_0_NICS
        self.host_1_nics = conf.HOST_1_NICS
        self.host_2_nics = conf.HOST_2_NICS
        self.dc_0 = conf.DC_0
        self.cluster_0 = conf.CL_0
        self.cluster_1 = conf.CL_1
        self.bond_0 = conf.BOND[0]
        self.bond_1 = conf.BOND[1]
        self.vm_0 = conf.VM_0
        self.vm_1 = conf.VM_1
        self.vms_list = [self.vm_0, self.vm_1]
        self.mgmt_bridge = conf.MGMT_BRIDGE
        conf.HOSTS_LIST = self.hosts_list
        conf.VDS_HOSTS_LIST = self.vds_list
        self.exclude_gluster_network_from_nics()
        if not conf.NO_SEMI_SRIOV_SUPPORT:
            # Create SR-IOV host NIC class instances to work with SR-IOV
            # interfaces
            sriov_conf.HOST_0_SRIOV_NICS_OBJ = (
                ll_sriov.SriovHostNics(conf.HOST_0_NAME)
            )
            sriov_conf.HOST_1_SRIOV_NICS_OBJ = (
                ll_sriov.SriovHostNics(conf.HOST_1_NAME)
            )

            # Get all SR-IOV host NIC objects
            sriov_conf.HOST_0_PF_LIST = (
                sriov_conf.HOST_0_SRIOV_NICS_OBJ.get_all_pf_nics_objects()
            )
            sriov_conf.HOST_1_PF_LIST = (
                sriov_conf.HOST_1_SRIOV_NICS_OBJ.get_all_pf_nics_objects()
            )

            # Get all SR-IOV host NIC names
            host_0_pf_nics = (
                sriov_conf.HOST_0_SRIOV_NICS_OBJ.get_all_pf_nics_names()
            )
            sriov_conf.HOST_0_PF_NAMES = [
                i for i in conf.HOST_0_NICS if i in host_0_pf_nics
            ]

            host_1_pf_nics = (
                sriov_conf.HOST_1_SRIOV_NICS_OBJ.get_all_pf_nics_names()
            )
            sriov_conf.HOST_1_PF_NAMES = [
                i for i in conf.HOST_1_NICS if i in host_1_pf_nics
            ]

            # Get all PF objects according to PF NIC names
            sriov_conf.HOST_0_PF_OBJECTS = [
                ll_sriov.SriovNicPF(host=conf.HOST_0_NAME, nic=nic_name)
                for nic_name in sriov_conf.HOST_0_PF_NAMES
            ]
            sriov_conf.HOST_1_PF_OBJECTS = [
                ll_sriov.SriovNicPF(host=conf.HOST_1_NAME, nic=nic_name)
                for nic_name in sriov_conf.HOST_1_PF_NAMES
            ]

            # Store specific PF objects for use in tests
            # Assuming more then one SR-IOV NIC per host is available
            sriov_conf.HOST_0_PF_OBJECT_1 = sriov_conf.HOST_0_PF_OBJECTS[0]
            sriov_conf.HOST_0_PF_OBJECT_2 = sriov_conf.HOST_0_PF_OBJECTS[1]
            sriov_conf.HOST_1_PF_OBJECT_1 = sriov_conf.HOST_1_PF_OBJECTS[0]

    def exclude_gluster_network_from_nics(self):
        """
        Exclude gluster network from host NICs list
        """
        for host, vds, nics in zip(
            self.hosts_list, self.vds_list, [
                conf.HOST_0_NICS, conf.HOST_1_NICS, conf.HOST_2_NICS]
        ):
            host_obj = ll_hosts.get_host_object(host_name=host)
            host_nics = ll_hosts.get_host_nics_list(host=host_obj)
            for nic in host_nics:
                nic_name = nic.name
                if "dummy" in nic_name or nic_name not in nics:
                    continue

                try:
                    network = ll_networks.get_network_on_host_nic(
                        host=host, nic=nic_name
                    )
                    if ll_networks.is_gluster_network(
                        network=network, cluster=host_obj.get_cluster()
                    ):
                        logger.debug(
                            "Found Gluster network (%s) on host %s NIC %s. "
                            "Excluding the network from the host NICs list",
                            network, host, nic_name
                        )
                        nics.pop(nics.index(nic_name))
                        break
                except (AttributeError, exceptions.EntityNotFound):
                    # In case no network on NIC or in case host have VLAN
                    # on host NIC
                    continue


@pytest.fixture(scope="class")
def clean_host_interfaces(request):
    """
    Clean host(s) interfaces networks (except the management network)
    """
    hosts_nets_nic_dict = request.node.cls.hosts_nets_nic_dict

    def fin():
        """
        Clean host(s) interfaces networks (except the management network)
        """
        assert network_fixture_helper.clean_host_interfaces_helper(
            hosts_nets_nic_dict=hosts_nets_nic_dict
        )
    request.addfinalizer(fin)


@pytest.fixture()
def clean_host_interfaces_fixture_function(request):
    """
    Clean host(s) interfaces networks (except the management network)
    """
    hosts_nets_nic_dict = fixtures_helper.get_fixture_val(
        request=request, attr_name="hosts_nets_nic_dict"
    )

    def fin():
        """
        Clean host(s) interfaces networks (except the management network)
        """
        network_fixture_helper.clean_host_interfaces_helper(
            hosts_nets_nic_dict=hosts_nets_nic_dict
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def setup_networks_fixture(request, clean_host_interfaces):
    """
    Perform network operation on host via setup network
    """
    NetworkFixtures()
    hosts_nets_nic_dict = request.node.cls.hosts_nets_nic_dict
    sriov_nics = getattr(request.node.cls, "sriov_nics", False)
    persist = getattr(request.node.cls, "persist", False)
    network_fixture_helper.setup_network_helper(
        hosts_nets_nic_dict=hosts_nets_nic_dict, sriov_nics=sriov_nics,
        persist=persist
    )


@pytest.fixture()
def setup_networks_fixture_function(
    request, clean_host_interfaces_fixture_function
):
    """
    Perform network operation on host via setup network
    """
    sriov_nics = fixtures_helper.get_fixture_val(
        request=request, attr_name="sriov_nics", default_value=False
    )
    persist = fixtures_helper.get_fixture_val(
        request=request, attr_name="persist", default_value=False
    )
    hosts_nets_nic_dict = request.getfixturevalue("hosts_nets_nic_dict")
    network_fixture_helper.setup_network_helper(
        hosts_nets_nic_dict=hosts_nets_nic_dict, sriov_nics=sriov_nics,
        persist=persist
    )


@pytest.fixture(scope="class")
def store_vms_params(request):
    """
    Store VM params (IP, resource) into config variable
    """
    vms = getattr(request.node.cls, "vms_to_store", list())
    for vm in vms:
        ip = hl_vms.get_vm_ip(vm_name=vm)
        resource = global_helper.get_host_resource(
            ip=ip, password=conf.VDC_ROOT_PASSWORD
        )
        conf.VMS_TO_STORE[vm] = dict()
        conf.VMS_TO_STORE[vm]["ip"] = ip
        conf.VMS_TO_STORE[vm]["resource"] = resource


@pytest.fixture(scope="class")
def update_cluster_network_usages(request):
    """
    Update cluster network usages
    """
    cluster = request.cls.update_cluster
    network = request.cls.update_cluster_network
    usages = request.cls.update_cluster_network_usages

    cluster_obj = ll_clusters.get_cluster_object(cluster_name=cluster)
    assert ll_networks.update_cluster_network(
        positive=True, cluster=cluster_obj, network=network, usages=usages
    )


@pytest.fixture(scope="class")
def create_and_attach_networks(request, remove_all_networks):
    """
    Create and attach network to Data-Centers and clusters
    """
    create_network_dict = request.cls.create_networks
    for val in create_network_dict.values():
        assert hl_networks.create_and_attach_networks(**val)


@pytest.fixture(scope="class")
def remove_all_networks(request):
    """
    Remove all networks from Data-Centers
    """
    dcs = getattr(request.node.cls, "remove_dcs_networks", list())

    def fin():
        """
        Remove all networks from Data-Centers
        """
        results = [
            hl_networks.remove_all_networks(datacenter=dc) for dc in dcs
        ]
        assert all(results)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def restore_network_usage(request):
    """
    Set management network as default route
    """
    network = request.cls.network_usage
    cluster = request.cls.cluster_usage

    def fin():
        """
        Set management network as default route
        """
        cluster_obj = ll_clusters.get_cluster_object(cluster_name=cluster)
        assert ll_networks.update_cluster_network(
            positive=True, cluster=cluster_obj, network=network,
            usages=conf.ALL_NETWORK_USAGES
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def add_vnic_profiles(request):
    """
    Add vNIC profiles with properties
    """
    vnics_profiles = getattr(
        request.node.cls, "add_vnic_profile_params", dict()
    )
    for values in vnics_profiles.values():
        assert ll_networks.add_vnic_profile(positive=True, **values)


@pytest.fixture(scope="class")
def remove_vnic_profiles(request):
    """
    Remove vNICs profiles
    """
    results = list()
    vnics_profiles = getattr(
        request.node.cls, "remove_vnic_profile_params", dict()
    )

    def fin2():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove vNIC profile
        """
        for values in vnics_profiles.values():
            kwargs = {
                "vnic_profile_name": values.get("name"),
                "network": values.get("network"),
                "cluster": values.get("cluster"),
                "data_center": values.get("data_center")
            }
            results.append(
                (
                    ll_networks.remove_vnic_profile(positive=True, **kwargs),
                    "fin1: ll_networks.remove_vnic_profile {kwargs}".format(
                        kwargs=kwargs
                    )
                )
            )
    request.addfinalizer(fin1)


@pytest.fixture(scope="class")
def add_vnics_to_vms(request):
    """
    Add vNIC(s) with properties to a VM(s)
    """
    vms_and_vnics = getattr(request.node.cls, "add_vnics_vms_params", dict())
    for vm_name, vnics_properties in vms_and_vnics.items():
        for values in vnics_properties.values():
            assert ll_vms.addNic(positive=True, vm=vm_name, **values)


@pytest.fixture(scope="class")
def remove_vnics_from_vms(request):
    """
    Remove vNICs from VMs
    """
    results = list()
    vms_and_vnics = getattr(
        request.node.cls, "remove_vnics_vms_params", dict()
    )

    def fin2():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove vNIC(s) from a VM(s)
        """
        for vm_name, vnics_properties in vms_and_vnics.items():
            for values in vnics_properties.values():
                nic_name = values.get("name")
                if ll_vms.get_vm_state(vm_name=vm_name) == conf.VM_UP:
                    results.append(
                        (
                            ll_vms.updateNic(
                                positive=True, vm=vm_name, nic=nic_name,
                                plugged=False
                            ), "fin1: ll_vms.updateNic {vm} {nic}".format(
                                vm=vm_name, nic=nic_name
                            )
                        )
                    )

                results.append(
                    (
                        ll_vms.removeNic(
                            positive=True, vm=vm_name, nic=nic_name
                        ),
                        "fin1: ll_vms.removeNic {vm} {nic}".format(
                            vm=vm_name, nic=nic_name
                        )
                    )
                )
    request.addfinalizer(fin1)


@pytest.fixture(scope="class")
def update_vnic_profiles(request):
    """
    Update vNICs profiles.
    """
    results = list()
    update_vnics_profiles = getattr(
        request.node.cls, "update_vnics_profiles", dict()
    )
    restore_vnics_profiles = getattr(
        request.node.cls, "restore_vnics_profiles", dict()
    )

    def fin2():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin2)

    def fin1():
        """
        Update vNICs proflies
        """
        for vnic, val in restore_vnics_profiles.iteritems():
            if "network" not in val.keys():
                val["network"] = vnic
            results.append(
                (
                    ll_networks.update_vnic_profile(name=vnic, **val),
                    "fin1: ll_networks.update_vnic_profile {val}".format(
                        val=val
                    )
                )
            )
    request.addfinalizer(fin1)

    for vnic, val in update_vnics_profiles.iteritems():
        if "network" not in val.keys():
            val["network"] = vnic
        assert ll_networks.update_vnic_profile(name=vnic, **val)


@pytest.fixture(scope="class")
def setup_ldap_integration(request):
    """
    Setup LDAP service(s) integration in oVirt engine
    """
    ldap_params = getattr(request.cls, "ldap_services", list())
    ldap_params_answer_files = [
        conf.AAA_LDAP_ANSWER_FILES[srv] for srv in ldap_params
    ]

    def fin():
        """
        Removes non-default LDAP services from oVirt engine
        """
        for aaa_dir in (
            conf.ENGINE_EXTENSIONS_DIR, conf.AAA_PROFILES_DIR
        ):
            testflow.teardown("Cleaning AAA directory: %s", aaa_dir)
            aaa_common.cleanExtDirectory(ext_dir=aaa_dir)

        testflow.setup("Restarting ovirt-engine service")
        conf.ENGINE.restart()
    request.addfinalizer(fin)

    answers_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        conf.AAA_ART_ANSWER_FILES_RELATIVE_PATH
    )

    testflow.setup("Setting up LDAP(s) services")
    for answer_file in ldap_params_answer_files:
        assert aaa_common.setup_ldap(
            host=conf.ENGINE_HOST,
            conf_file=os.path.join(answers_dir, answer_file)
        )

        if "w2k12r2" in answer_file:
            # In AD profile additional properties are needed
            conf_handler = config_handler.HostConfigFileHandler(
                host=conf.ENGINE_HOST, path=conf.AAA_AD_PROFILE
            )
            assert conf_handler.set_options(parameters=conf.AAA_AD_PROPERTIES)

    testflow.setup("Restarting ovirt-engine service")
    conf.ENGINE.restart()
