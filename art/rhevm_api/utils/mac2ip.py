"""
Module captures DHCP leases on host, which means you are able to get
IP address of VMs according to MAC address which are running on that host.
"""

import re
import select
import time
import logging
from threading import Thread
from random import random


logger = logging.getLogger("art.utils.mac2ip")


class MacToIpConverterError(Exception):
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

    P_REPLY = re.compile('BOOTP/DHCP, Reply')
    P_YOUR_IP = re.compile('Your-IP (?P<ip>([0-9]+[.]){3}[0-9]+)')
    P_SERVER_IP = re.compile('Server-IP')
    P_GW_IP = re.compile('Gateway-IP')
    P_MAC = re.compile(
        'Client-Ethernet-Address (?P<mac>([0-9a-f]+[-:]){5}[0-9a-f]+)', re.I,
    )
    P_MSG = re.compile(
        'DHCP-Message Option [0-9]+, length [0-9]+: (?P<msg>[a-z]+)', re.I,
    )

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
            expect = " OR ".join(
                ["'%s'" % x.pattern for x in self.EXPECT[self.st]]
            )
            logger.debug("EXPECT %s GOT %s", expect, line)

        if self.st == self.S_UNKNOWN:
            if self.P_REPLY.search(line):
                # saw reply -> waiting for IP
                self.st = self.S_REPLY
                return
        elif self.st == self.S_REPLY:
            # saw IP -> waiting for server IP
            m = self.P_YOUR_IP.search(line)
            if m:
                self.ip = m.group('ip')
                self.st = self.S_CL_IP
                return
        elif self.st == self.S_CL_IP:
            # saw server IP -> waiting for GW
            if self.P_SERVER_IP.search(line):
                self.st = self.S_SER_IP
                return
        elif self.st == self.S_SER_IP:
            if self.P_GW_IP.search(line):
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
            m = self.P_MSG.search(line)
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
        m = self.P_MAC.search(line)
        if m:
            self.mac = unify_mac_format(m.group('mac'))
            self.st = self.S_MSG
            return True
        return False

    def __store_mac(self):
        old_ip = self.c.get(self.mac, None)
        self.c[self.mac] = self.ip
        if old_ip != self.ip:
            logger.info("Caught %s for %s", self.ip, self.mac)


class Producer(Thread):
    """
    Reads lines from specific stream and pass them into parser
    """

    def __init__(self, parser):
        super(Producer, self).__init__()
        self.p = parser
        self.ready = False

    def run(self):
        raise NotImplementedError()

    def stop(self):
        pass


class StreamProducer(Producer):
    def __init__(self, parser, stream):
        super(StreamProducer, self).__init__(parser)
        self.s = stream

    def run(self):
        with self.s:
            for line in self.s.readline():
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

    def __init__(self, parser, host, timeout=10):
        super(SSHProducer, self).__init__(parser)
        self.daemon = True
        self.setName("tcpdump-%s" % host)
        self.host = host
        self.m = None
        self.out = ''
        self.timeout = timeout
        self.exit = False

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

    def collecting(self):
        cmd = ['tcpdump', '-lnpvi', 'any', 'dst', 'port', '68']
        self.m = self.host.executor().session(timeout=self.timeout)
        logger.debug("Collecting starting... ")
        with self.m as session:
            command = session.command(cmd)

            with command.execute() as (in_, out, err):
                params = [[out.channel], [], [], self.timeout]
                while not self.exit:
                    ready_fds = select.select(*params)[0]
                    if not ready_fds:
                        continue
                    channel = ready_fds[0]
                    if channel.recv_ready():
                        self.out += channel.recv(self.IOBUFF)
                        self.ready = True  # got some data
                    if channel.recv_stderr_ready():
                        logger.debug(channel.recv_stderr(self.IOBUFF))
                        self.ready = True  # printed info about capturing
                    self.parse()
            logger.debug("Collecting completed!!")

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
        self.cache = dict()
        self.readers = []

    def add_reader(self, reader, timeout=20):
        if not isinstance(reader, Producer):
            raise TypeError("'%s' is not valid Producer class" % reader)
        self.readers.append(reader)
        reader.start()
        step = timeout / 5.0
        treshold = 0
        while True:
            if reader.ready:
                break
            if treshold > timeout:
                logger.warn(
                    "The output producer doesn't provide any output yet: %s",
                    reader,
                )
                raise ReaderIsNotReady(reader)
            else:
                sleepstep = random() * step
                time.sleep(sleepstep)
                treshold += sleepstep

    def get_ip(self, mac):
        return self.cache.get(unify_mac_format(mac))

    def stop(self):
        for reader in self.readers:
            reader.stop()
