"""
Fixture file for mac_addr tests
"""

import pytest

import config as macaddr_config
from rhevmtests.networking import config as network_config
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network


@pytest.fixture()
def reset_host_nics(request):
    """
    Reset host NICs to VDSM default values
    """
    def fin():
        """
        Attach network to host NIC and remove it to get VDSM defalt values
        """
        add_sn_dict = {
            "add": {
                "1": {
                    "network": macaddr_config.RESET_NETS[1][0],
                    "nic": network_config.VDS_0_HOST.nics[1],
                },
                "2": {
                    "network": macaddr_config.RESET_NETS[1][1],
                    "nic": network_config.VDS_0_HOST.nics[2],
                },
                "3": {
                    "network": macaddr_config.RESET_NETS[1][2],
                    "nic": network_config.VDS_0_HOST.nics[3],
                }
            }
        }

        assert hl_host_network.setup_networks(
            host_name=network_config.HOST_0_NAME, **add_sn_dict
        )

        hl_host_network.clean_host_interfaces(
            host_name=network_config.HOST_0_NAME
        )
    request.addfinalizer(fin)
