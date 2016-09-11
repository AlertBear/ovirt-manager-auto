#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Networking fixtures
"""

import pytest
import re

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
from art.unittest_lib import testflow
from rhevmtests.networking import helper as network_helper


class NetworkFixtures(object):
    """
    Class for networking fixtures
    """
    def __init__(self):
        conf.VDS_0_HOST = conf.VDS_HOSTS[0]
        conf.VDS_1_HOST = conf.VDS_HOSTS[1]
        conf.HOST_0_NAME = conf.HOSTS[0]
        conf.HOST_1_NAME = conf.HOSTS[1]
        conf.HOST_0_IP = conf.VDS_0_HOST.ip
        conf.HOST_1_IP = conf.VDS_1_HOST.ip
        conf.HOST_0_NICS = conf.VDS_0_HOST.nics
        conf.HOST_1_NICS = conf.VDS_1_HOST.nics
        self.vds_0_host = conf.VDS_0_HOST
        self.vds_1_host = conf.VDS_1_HOST
        self.vds_list = [self.vds_0_host, self.vds_1_host]
        self.host_0_name = conf.HOST_0_NAME
        self.host_1_name = conf.HOST_1_NAME
        self.hosts_list = [self.host_0_name, self.host_1_name]
        self.host_0_ip = conf.HOST_0_IP
        self.host_1_ip = conf.HOST_1_IP
        self.host_0_nics = conf.HOST_0_NICS
        self.host_1_nics = conf.HOST_1_NICS
        self.dc_0 = conf.DC_0
        self.cluster_0 = conf.CL_0
        self.cluster_1 = conf.CL_1
        self.bond_0 = conf.BOND[0]
        self.bond_1 = conf.BOND[1]
        self.vm_0 = conf.VM_0
        self.vm_1 = conf.VM_1
        self.num_dummies = conf.NUM_DUMMYS
        self.mgmt_bridge = conf.MGMT_BRIDGE
        conf.HOSTS_LIST = self.hosts_list
        conf.VDS_HOSTS_LIST = self.vds_list

    def prepare_networks_on_setup(self, networks_dict, dc=None, cluster=None):
        """
        Create networks on setup

        Args:
            networks_dict (dict): Networks to create
            dc (str): Datacenter name
            cluster (str): Cluster name
        """
        network_helper.prepare_networks_on_setup(
            networks_dict=networks_dict, dc=dc, cluster=cluster
        )

    def remove_networks_from_setup(self, hosts):
        """
        Remove network from setup

        Args:
            hosts (list or str): Host name or hosts list
        """
        network_helper.remove_networks_from_setup(hosts=hosts)

    def run_vm_once_specific_host(self, vm, host, wait_for_up_status):
        """
        Run VM once on specific host

        Args:
            vm (str): VM name.
            host (str): Host name.
            wait_for_up_status (bool): Wait for VM to be up

        Returns:
            bool: True if action succeeded, False otherwise
        """
        return network_helper.run_vm_once_specific_host(
            vm=vm, host=host, wait_for_up_status=wait_for_up_status
        )

    def stop_vm(self, positive, vm):
        """
        Stop VM

        Args:
            positive (bool): Expected status.
            vm (str): Name of vm.
        """
        ll_vms.stopVm(positive=positive, vm=vm)


@pytest.fixture(scope="class")
def clean_host_interfaces(request):
    """
    Clean hosts interfaces.
    """
    NetworkFixtures()
    hosts_nets_nic_dict = request.node.cls.hosts_nets_nic_dict

    def fin():
        """
        Clean hosts interfaces
        """
        for key in hosts_nets_nic_dict.iterkeys():
            host_name = conf.HOSTS[key]
            testflow.teardown("Clean host %s interface", host_name)
            hl_host_network.clean_host_interfaces(host_name=host_name)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def setup_networks_fixture(request, clean_host_interfaces):
    """
    perform network operation to host via setup network
    """
    NetworkFixtures()
    hosts_nets_nic_dict = request.node.cls.hosts_nets_nic_dict
    ethtool_opts_str = "ethtool_opts"

    sn_dict = {
        "add": {}
    }

    for key, val in hosts_nets_nic_dict.iteritems():
        host = conf.HOSTS[key]
        host_resource = conf.VDS_HOSTS[key]
        for net, value in val.iteritems():
            slaves_list = list()
            slaves = value.get("slaves")
            nic = value.get("nic")
            network = value.get("network")
            datacenter = value.get("datacenter")
            ip_dict = value.get("ip")
            mode = value.get("mode")
            properties = value.get("properties")
            if properties and ethtool_opts_str in properties.keys():
                val = properties.get(ethtool_opts_str)
                match = re.findall(r'\d', val)
                if match:
                    host_nic_idx = match[0]
                    properties[ethtool_opts_str] = val.replace(
                        host_nic_idx, host_resource.nics[int(host_nic_idx)]
                    )
            if slaves:
                for nic_ in slaves:
                    slaves_list.append(host_resource.nics[nic_])

            if isinstance(nic, int):
                nic = host_resource.nics[nic]

            sn_dict["add"][net] = {
                "network": network,
                "nic": nic,
                "datacenter": datacenter,
                "slaves": slaves_list,
                "mode": mode,
                "properties": properties
            }
            if ip_dict:
                for k, v in ip_dict.iteritems():
                    ip_dict[k]["netmask"] = v.get("netmask", "24")
                    ip_dict[k]["boot_protocol"] = v.get(
                        "boot_protocol", "static"
                    )
                    sn_dict["add"][net]["ip"] = ip_dict

        testflow.setup("Create %s via setup_network on host %s", sn_dict, host)
        assert hl_host_network.setup_networks(host_name=host, **sn_dict)
        sn_dict["add"] = dict()
