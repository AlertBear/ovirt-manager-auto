"""
--------------------
Mac Converter Plugin
--------------------

Plugin captures DHCP leases on VDS hosts, which means you are able to get
IP address of VM according to MAC address.
ART provides function convertMacToIp which maps MAC to IP according to
RHEVM QA lab definitions.
Plugin rebinds this function to converter, so you don't need to use
two different functions and don't need to change your tests.

CLI Options:
------------
    --with-mac-ip-conv  Enable the plugin

Configuration Options:
----------------------
    | **[MAC_TO_IP_CONV]**
    | **enabled** - to enable plugin (true/false)
    | **timeout** - timeout in seconds for reading DHCP leases, default: 10
    | **attempts** - number of attempts for retry, default: 60
    | **wait_interval** - seconds to sleep between attempts, default: 1
    | **debug** - enables debugging output, bool(default=False)
"""

import re
import select
import time
from threading import Thread
from subprocess import list2cmdline
from utilities.sshConnection import SSHSession
from utilities.machine import Machine, LINUX
from art.test_handler.exceptions import CanNotFindIP

from art.test_handler.plmanagement import Component, implements, get_logger,\
    PluginError
from art.test_handler.plmanagement.interfaces.application import\
    IConfigurable, IApplicationListener
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation


logger = get_logger('mac_to_ip_conv')


PARAMETERS = 'PARAMETERS'
VDS_PASSWORD = 'vds_password'
VDS = 'vds'
MAC_TO_IP_CONV = "MAC_TO_IP_CONV"
DEFAULT_STATE = False
DEFAULT_DEBUG = False
ENABLED = 'enabled'
DEBUG = 'debug'
TIMEOUT = 'timeout'
ATTEMPTS = 'attempts'
WAIT_INT = 'wait_interval'
DEFAULT_TIMEOUT = 10
DEFAULT_ATTEMPTS = 60
DEFAULT_WAIT = 1


class MacToIpConverterError(PluginError):
    pass


class CanNotTranslateMacToIP(CanNotFindIP):
    pass


class ReaderIsNotReady(MacToIpConverterError):
    pass


def unify_mac_format(mac):
    if not isinstance(mac, basestring):
        raise ValueError("Expected string, got %s" % type(mac))
    return mac.upper().replace('-', ':')


class TCPDumpParser(object):
    """
    Final automata used for parsing purposes
    """
    S_UNKNOWN = 0
    S_REPLY = 1
    S_CL_IP = 2
    S_SER_IP = 3
    S_GW_IP = 4
    S_MAC_ADDR = 5
    S_MSG = 6

    P_REPLY = 'BOOTP/DHCP, Reply'
    P_YOUR_IP = 'Your-IP (?P<ip>([0-9]+[.]){3}[0-9]+)'
    P_SERVER_IP = 'Server-IP'
    P_GW_IP = 'Gateway-IP'
    P_MAC = 'Client-Ethernet-Address (?P<mac>([0-9a-f]+[-:]){5}[0-9a-f]+)'
    P_MSG = 'DHCP-Message Option [0-9]+, length [0-9]+: (?P<msg>[a-z]+)'

    EXPECT = {
        S_UNKNOWN: (P_REPLY,),
        S_REPLY: (P_YOUR_IP,),
        S_CL_IP: (P_SERVER_IP,),
        S_SER_IP: (P_GW_IP, P_MAC),
        S_GW_IP: (P_MAC,),
        S_MAC_ADDR: (P_MSG,),
        S_MSG: (P_MSG,),
    }

    def __init__(self, cache, debug=False):
        super(TCPDumpParser, self).__init__()
        self.c = cache
        self.st = self.S_UNKNOWN
        self.ip = None
        self.mac = None
        self.debug = debug

    def parse_line(self, line):
        """
        Accepts output from tcpdump, line-by-line
        """
        if self.debug:
            expect = " OR ".join(["'%s'" % x for x in self.EXPECT[self.st]])
            logger.debug("EXPECT %s GOT %s", expect, line)

        if self.st == self.S_UNKNOWN:
            if re.search(self.P_REPLY, line):
                # saw reply -> waiting for IP
                self.st = self.S_REPLY
                return
        elif self.st == self.S_REPLY:
            # saw IP -> waiting for server IP
            m = re.search(self.P_YOUR_IP, line)
            if m:
                self.ip = m.group('ip')
                self.st = self.S_CL_IP
                return
        elif self.st == self.S_CL_IP:
            # saw server IP -> waiting for GW
            if re.search(self.P_SERVER_IP, line):
                self.st = self.S_SER_IP
                return
        elif self.st == self.S_SER_IP:
            if re.search(self.P_GW_IP, line):
                # saw GW -> waiting for MAC
                self.st = self.S_GW_IP
                return
            if self.__read_mac(line):
                # saw MAC -> waiting for MESSAGE_TYPE
                return
        elif self.st == self.S_GW_IP:
            # saw MAC -> wating for MESSAGE_TYPE
            if self.__read_mac(line):
                return
        elif self.st == self.S_MSG:
            m = re.search(self.P_MSG, line, re.I)
            if m:
                # saw MESSAGE -> check if it is ACK
                msg = m.group('msg').lower()
                if msg == 'ack':
                    self.__store_mac()
                # else -> don't care about this lease -> wait for REPLY
            else:  # stay in this state and wait for MESSAGE line
                return

        # no expected match -> waiting for REPLY
        self.st = self.S_UNKNOWN

    def __read_mac(self, line):
        m = re.search(self.P_MAC, line, re.I)
        if m:
            self.mac = unify_mac_format(m.group('mac'))
            self.st = self.S_MSG
            return True
        return False

    def __store_mac(self):
        old_ip = None
        with self.c:
            old_ip = self.c.get(self.mac, None)
            self.c[self.mac] = self.ip
        if old_ip != self.ip:
            logger.info("Caught %s for %s", self.ip, self.mac)


class Producer(Thread):
    """
    Reads lines from specific stream and pass them into parser
    """

    def __init__(self, parser, stream, start=True):
        super(Producer, self).__init__()
        self.p = parser
        self.s = stream
        self.ready = False
        if start:
            self.start()

    def __iter__(self):
        while True:
            line = self.s.readline()
            if not line:
                raise StopIteration()
            yield line

    def run(self):
        with self.s:
            for line in self:
                self.p.parse_line(line)
        self.s = None

    def stop(self):
        if self.s is not None:
            self.s.close()
            self.s = None


class SSHProducer(Producer):
    """
    Connect to host, run tcpdump on it, read output which is passed into parser
    """

    IOBUFF = 512

    def __init__(self, parser, host, passwd, start=True, timeout=10):
        super(SSHProducer, self).__init__(parser, None, False)
        self.setName("tcpdump-%s" % host)
        self.hostname = host
        self.password = passwd
        self.m = None
        self.out = ''
        self.timeout = timeout
        self.ch = None
        self.exit = False
        if start:
            self.start()

    def parse(self):
        data = self.out.splitlines(True)
        if not data:
            return
        if data[-1].endswith('\n'):
            self.out = ''
        else:
            data, self.out = data[:-1], data[-1]
        for line in data:
            self.p.parse_line(line)

    def run(self):
        while not self.exit:
            try:
                self.collecting()
            except Exception as ex:
                # closed by remote host, it could be caused by reboot of host
                logger.warn("Collecting failed: %s", ex)
                logger.debug("Exception", exc_info=True)
                m = Machine(self.hostname, 'root', self.password).util(LINUX)
                m.isAlive(self.timeout, 1)

    def collecting(self):
        cmd = ['tcpdump', '-lnpvi', 'any', 'dst', 'port', '68']
        cmd = list2cmdline(cmd)
        self.m = SSHSession(hostname=self.hostname, username='root',
                            password=self.password)
        logger.debug("Collecting starting... ")
        with self.m._getSession(self.timeout) as channel:
            # execute command
            channel.exec_command(cmd)

            channel.shutdown_write()

            # read stdout and stderr
            params = [[channel], [], [], self.timeout]
            while not channel.closed:
                select.select(*params)
                while channel.recv_stderr_ready() or channel.recv_ready():
                    if channel.recv_ready():
                        self.out += channel.recv(self.IOBUFF)
                        self.ready = True  # got some data
                    if channel.recv_stderr_ready():
                        logger.debug(channel.recv_stderr(self.IOBUFF))
                        self.ready = True  # printed info about capturing
                    self.parse()

            while channel.recv_ready():
                self.out += channel.recv(self.IOBUFF)
                self.parse()
            while channel.recv_stderr_ready():
                channel.recv_stderr(self.IOBUFF)
            channel.shutdown_read()
        logger.debug("Collection completed!!")

    def stop(self):
        self.exit = True
        if self.m is not None:
            self.m.close()
            self.m = None


class DHCPLeasesCatcher(object):
    """
    Provides access point into address_cache, and keeps all readers threads.
    """

    def __init__(self):
        super(DHCPLeasesCatcher, self).__init__()
        from art.rhevm_api.utils.threads import ThreadSafeDict
        self.cache = ThreadSafeDict()
        self.readers = []

    def add_reader(self, reader, timeout=10):
        if not isinstance(reader, Producer):
            raise TypeError("'%s' is not valid Producer class" % reader)
        self.readers.append(reader)
        while True:
            if reader.ready:
                break
            timeout -= 1
            if timeout < 0:
#                raise ReaderIsNotReady(reader)
                logger.warn("The output producer doesn't provide any output "
                            "yet: %s", reader)
            else:
                time.sleep(1)

    def get_ip(self, mac):
        with self.cache:
            return self.cache[mac]

    def stop(self):
        for reader in self.readers:
            reader.stop()


class MacToIpConverter(Component):
    """
    Plugin provides way to collect DHCP leases which are going through VDS.
    It allows to you collect MAC: IPs pairs, which could be used for
    """
    implements(IConfigurable, IApplicationListener, IPackaging,
               IConfigValidation)
    name = "Mac to IP converter"
    enabled = True
    depends_on = []

    def __init__(self):
        super(MacToIpConverter, self).__init__()
        self.catcher = None

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-mac-ip-conv', action='store_true',
                           dest='mac_ip_conv_enabled', help="enable plugin")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        self.catcher = DHCPLeasesCatcher()

        self.vds = conf[PARAMETERS].as_list(VDS)
        self.vds_passwd = conf[PARAMETERS].as_list(VDS_PASSWORD)
        mac_conf = conf.get(MAC_TO_IP_CONV)
        self.timeout = mac_conf.as_int(TIMEOUT)
        self.attempts = mac_conf.as_int(ATTEMPTS)
        self.wait_interval = mac_conf.as_float(WAIT_INT)
        self.debug = mac_conf.as_bool(DEBUG)

    def get_ip(self, mac, subnet_class_b, vlan):
        mac = unify_mac_format(mac)
        ip = self.catcher.get_ip(mac)
        subnet_class_b = subnet_class_b.replace('.', '[.]')
        if re.match('^%s' % subnet_class_b, ip):
            return ip
        raise KeyError(mac)

    def on_application_exit(self):
        if self.catcher is not None:
            self.catcher.stop()

    def on_application_start(self):
        for name, passwd in zip(self.vds, self.vds_passwd):
            ssh = SSHProducer(TCPDumpParser(self.catcher.cache, self.debug),
                              name, passwd, timeout=self.timeout)
            self.catcher.add_reader(ssh)

        # binding convertMacToIp function to cache
        def wrapper(mac=None, subnetClassB=None, vlan=None):
            for _ in range(my_self.attempts):
                try:
                    return my_self.get_ip(mac, subnetClassB, vlan)
                except KeyError:
                    time.sleep(my_self.wait_interval)
            else:
                raise CanNotTranslateMacToIP(mac)

        from utilities.utils import convertMacToIp
        convertMacToIp.func_code = wrapper.func_code
        convertMacToIp.func_globals['my_self'] = self
        convertMacToIp.func_globals['CanNotTranslateMacToIP'] =\
            CanNotTranslateMacToIP

    def on_plugins_loaded(self):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(MAC_TO_IP_CONV).as_bool(ENABLED)
        return params.mac_ip_conv_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'mac-to-ip'
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'MAC to IP address converter for ART'
        params['long_description'] = cls.__doc__.strip().replace('\n', ' ')
        params['requires'] = ['art-utilities']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'mac_converter_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(MAC_TO_IP_CONV, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[DEBUG] = 'boolean(default=%s)' % DEFAULT_DEBUG
        section_spec[TIMEOUT] = 'integer(default=%s)' % DEFAULT_TIMEOUT
        section_spec[ATTEMPTS] = 'integer(default=%s)' % DEFAULT_ATTEMPTS
        section_spec[WAIT_INT] = 'integer(default=%s)' % DEFAULT_WAIT
