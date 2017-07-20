"""
This module implements mac2ip conventor.
It simply run tcpdump on hosts and waiting for DHCP leases.
"""
import time
import logging
import art.test_handler.settings as settings
from art.test_handler.exceptions import CanNotFindIP
from art.rhevm_api.utils.mac2ip import (
    DHCPLeasesCatcher, TCPDumpParser, SSHProducer,
)
from art.rhevm_api.resources import Host, RootUser


logger = logging.getLogger("pytest.art.mac2ip")


__all__ = [
    'pytest_artconf_ready',
]

PARAMETERS = 'PARAMETERS'
VDS_PASSWORD = 'vds_password'
VDS = 'vds'
CONF_SECTION = "MAC_TO_IP_CONV"
ENABLED = 'enabled'
DEBUG = 'debug'
TIMEOUT = 'timeout'
ATTEMPTS = 'attempts'
WAIT_INT = 'wait_interval'

DEFAULT_TIMEOUT = 10
DEFAULT_ATTEMPTS = 120
DEFAULT_WAIT = 1


class Mac2IpConvertor(object):
    """
    It holds mac2ip mapper and bind it to convertMacToIp function.
    """
    def __init__(self, hosts, attempts, tcp_timeout, wait_interval, debug):
        self.leases = DHCPLeasesCatcher()
        self.hosts = hosts
        self.attempts = attempts
        self.tcp_timeout = tcp_timeout
        self.wait_interval = wait_interval
        self.debug = debug

    def pytest_art_ensure_resources(self):
        parser = TCPDumpParser(self.leases.cache, debug=self.debug)
        for host in self.hosts:
            reader = SSHProducer(parser, host, self.tcp_timeout)
            self.leases.add_reader(reader)
        self._wrap_original_function()

    def pytest_art_release_resources(self):
        self.leases.stop()

    def _wrap_original_function(self):
        # binding convertMacToIp function to cache
        def wrapper(mac=None, subnetClass=None, vlan=None):
            for _ in range(my_self.attempts):  # noqa
                try:
                    ip = my_self.leases.get_ip(mac)  # noqa
                    if ip:
                        return ip
                except Exception as e:
                    logger.warn("Caught exception: %s", e)
                time.sleep(my_self.wait_interval)  # noqa
            else:
                raise CanNotFindIP(mac)

        from utilities.utils import convertMacToIp
        convertMacToIp.func_code = wrapper.func_code
        convertMacToIp.func_globals['my_self'] = self
        convertMacToIp.func_globals['CanNotFindIP'] = CanNotFindIP


def get_int_option(name, default):
    return int(settings.ART_CONFIG[CONF_SECTION].get(name, default))


def pytest_artconf_ready(config):
    """
    Register AutoDevices plugin.
    """
    hosts = []
    user = RootUser(
        settings.ART_CONFIG[PARAMETERS].get(VDS_PASSWORD)[0]
    )
    for ip in settings.ART_CONFIG[PARAMETERS].get(VDS):
        h = Host(ip)
        h.users.append(user)
        hosts.append(h)
    if hosts:
        debug = str(
            settings.ART_CONFIG[CONF_SECTION].get(DEBUG, "False")
        )
        debug = debug.lower() in ('1', 'yes', 'true')
        config.pluginmanager.register(
            Mac2IpConvertor(
                hosts,
                get_int_option(ATTEMPTS, DEFAULT_ATTEMPTS),
                get_int_option(TIMEOUT, DEFAULT_TIMEOUT),
                get_int_option(WAIT_INT, DEFAULT_WAIT),
                debug,
            )
        )
