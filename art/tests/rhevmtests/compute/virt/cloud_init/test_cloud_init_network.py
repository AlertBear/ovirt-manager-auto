#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - Cloud init networking Test
Check network IPv4 and IPv6 cases with cloud init
"""
import logging
import pytest
from rhevmtests.compute.virt import config, helper
from rhevmtests.compute.virt.fixtures import start_vm_with_parameters
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, tier2, testflow
from fixtures import add_nic_to_vm

logger = logging.getLogger("cloud_init_networking")
init_mark = pytest.mark.initialization_param

net_confs, ids = helper.generate_network_configs(config.NETWORKING_OPTIONS)
# Generates all  expected_config combinations, for instance this dictionary
# {
# 'ip': art.rhevm_api.data_struct.data_structures.Ip,
#  'boot_protocol': 'static',
#  'ipv6_boot_protocol': 'static',
#  'name': 'eth1',
#  'ipv6': art.rhevm_api.data_struct.data_structures.Ip
# } in form of data_struct.NicConfigurations object which is passed as
# initialization param
params = [
    polarion("RHEVM-19608")(init_mark(**helper.get_nic_config(conf))(
        conf)) for conf in net_confs
]


@pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
class TestCloudInitNetworking(VirtTest):
    """
    Cloud init networking test cases
    """
    vm_name = config.CLOUD_INIT_VM_NAME
    initialization = None
    start_vm_parameters = {
        "wait_for_ip": True,
        "use_cloud_init": True,
        "wait_for_status": config.VM_UP
    }

    @pytest.mark.parametrize('expected_config', params, ids=ids)
    @tier2
    @pytest.mark.usefixtures(
        add_nic_to_vm.__name__,
        start_vm_with_parameters.__name__
    )
    def test_cloud_init_network(self, expected_config):
        testflow.step('Compare NIC configurations')
        status, result = helper.compare_nic_configs(
            self.vm_name, expected_config
        )
        assert status, 'NIC config differs from expected in {}'.format(
            [
                (key, val['actual'], val['expected']) for
                key, val in result.iteritems() if val['status'] is False
            ]
        )
