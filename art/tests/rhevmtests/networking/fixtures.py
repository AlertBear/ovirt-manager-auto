#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Networking fixtures
"""

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
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
