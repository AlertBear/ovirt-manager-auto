
"""
File contains base classes for this module.
"""

__test__ = False

import re
import os
import time
import logging
from contextlib import contextmanager
import unittest
# Folowing 'try-except' blocks are here because this modules are needed only
# for nose testframework, but you can use this module also for another purposes.
try:
    from ovirtsdk.api import API
    from ovirtsdk.xml import params as sdk_params
except ImportError:
    API = None
    sdk_params = None
try:
    from testconfig import config
    if not config:
        raise ImportError()
except ImportError:
    #from unittest_conf import config
    config = {}
try:
    from nose.tools import istest
except ImportError:
    def istest(f):
        return f

from utilities.machine import LinuxMachine, LINUX
import utilities.utils as ut
from rhevm_utils import errors
from art.test_handler.settings import opts

logger = logging.getLogger('rhevm-utils')

BIN = {
        'psql'          :   '/usr/bin/psql',
        'grep'          :   '/bin/grep',
        'cut'           :   '/bin/cut'
        }

_BIN = {
        'config'        : '/usr/bin/%s-config',
        'setup'         : '/usr/bin/%s-setup',
        'upgrade'       : '/usr/bin/%s-upgrade',
        'manage-domains': '/usr/bin/%s-manage-domains',
        'cleanup'       : '/usr/bin/%s-cleanup',
        'iso-uploader'  : '/usr/bin/%s-iso-uploader',
        'log-collector' : '/usr/bin/%s-log-collector'
        }

PRODUCT_OVIRT = 'engine'
PRODUCT_RHEVM = 'rhevm'

PRODUCT_RPM = {PRODUCT_OVIRT: 'ovirt-engine',
                PRODUCT_RHEVM: 'rhevm'}

DB_USER = 'postgres'
TIMEOUT = 10
HOST_PATH_TO_TMP = "/tmp"
WAIT_TIMEOUT = 600

CONFIG_ELEMENTS = 'elements_conf'
CONFIG_SECTION = 'RHEVM Utilities'

DB_NAME = 'DB_NAME'

# TODO:
# create patterns for errors recognition
# also think about moving of message patterns to consts, because it can be
# changed in next versions

class Setup(LinuxMachine):

    VARS = opts[CONFIG_ELEMENTS][CONFIG_SECTION]

    def __init__(self, host, user, passwd, dbuser=DB_USER, product=None):
        # TODO: remote DB
        LinuxMachine.__init__(self, host, user, passwd, local=False)

        if product is None:
            if self.checkRpm(PRODUCT_RPM[PRODUCT_RHEVM]):
                self.product = PRODUCT_RHEVM
            elif self.checkRpm(PRODUCT_RPM[PRODUCT_OVIRT]):
                self.product = PRODUCT_OVIRT
            else:
                raise errors.ProductIsNotInstaled(PRODUCT_RPM)
            self.rpmVer = self._fetchRPMVersion(PRODUCT_RPM[self.product])
        else:
            self.product = product
            self.rpmVer = '__default__'

        self.dbname = self.getVar(DB_NAME)
        self.dbuser = dbuser
        self.setDBConnection()
        self._bin = dict((x, y % self.product) for x, y in _BIN.items())
        self.connectionTimeout = TIMEOUT
        self.execTimeout = TIMEOUT
        self.tmp = HOST_PATH_TO_TMP

    def setDBConnection(self, host=None, root_passwd=None):
        """
        Set connection to DB
        Parameters:
         * host - address, None means local DB
         * root_passwd - password for root account
        """
        if host is None:
            self.db = self
        else:
            if root_passwd is None:
                root_passwd = self.passwd
            self.db = LinuxMachine(host, 'root', root_passwd, local=False)

    def _fetchRPMVersion(self, rpmname):
        rc, out = self.runCmd(['rpm', '-qa', rpmname])
        out = out.strip()
        if not rc or not out:
            raise errors.ProductIsNotInstaled(rpmname)
        m = re.match('.*-(?P<ver>[^-]+-[^-]+)[.][^.]+', out)
        if not m:
            raise errors.RHEVMUtilsError("failed to fetch rpm version: %s" % out)
        return m.group('ver')

    def getVar(self, name):
        """
        Fetch variable from config file
        Parameters:
         * name - name of variable
        """
        pr = 'RHEVM'
        if self.product == PRODUCT_OVIRT:
            pr = 'OVIRT'
        name = "%s_%s" % (pr, name)
        return self.VARS[name]

    def psql(self, sql, *args, **kwargs):
        """
        Executes sql command on setup
        Parameters:
         * sql - query
         * args - positional args in query; '%s'
         * kwargs - keyword args in query: '%(key)s'
        """
        sep = '__RECORD_SEPARATOR__'
        timeout = kwargs.get('timeout', TIMEOUT)
        if args:
            sql = sql % tuple(args)
        cmd = [BIN['psql'], '-d', self.dbname, '-U', self.dbuser, '-R', sep, '-t', '-A', '-c', sql]
        with self.db.ssh as ssh:
            rc, out, err = ssh.runCmd(cmd, timeout=self.connectionTimeout, conn_timeout=timeout)
        if rc:
            raise errors.ExecuteDBQueryError(self.db.host, sql, rc, out, err)
        return [ a.strip().split('|') for a in out.strip().split(sep) if a.strip() ]

    @contextmanager
    def runCmdOnBg(self, cmd, killSig='-2', **kwargs):
        """
        Runs command on background in specific context (need to use 'with' statement)
        Parameters:
         * cmd - command
         * killSig - signal used to kill process after finish
         * kwargs - opional args for runCmd command
        """
        if 'bg' not in kwargs:
            kwargs['bg'] = True
        rc, pid = self.runCmd(cmd, **kwargs)
        logger.info("execute command: %s, %s, %s, %s", cmd, rc, pid, kwargs)
        if not rc and not self.isProcessExists(pid):
            raise errors.RHEVMUtilsError(\
                    "failed to run command on bg: %s, %s", cmd, kwargs)
        try:
            yield pid
        finally:
            self.killProcess([pid], killSig)

    def install(self, conf=None):
        """
        Install RHEVM on setup
        Parameters:
         conf - dictionary with installation data
        """
        if not conf:
            conf = ut.getConfigFilePath(__file__, 'unittest_conf.py')
            logger.warn("fetch installation data from %s" % conf)
            import unittest_conf
            conf = unittest_conf.config
        # lazy import due cyclic deps
        from rhevm_utils import setup
        util = setup.SetupUtility(self)
        util.installTimeout = \
                int(conf.get('install_timeout', setup.INSTALL_TIMEOUT))
        ans = os.path.join(self.tmp, 'answers')
        util(gen_answer_file=ans)
        params = setup.getInstallParams(self.rpmVer, conf['testing_env'], conf['ANSWERS'])
        util.fillAnswerFile(**params)
        logger.info("%s: install setup with %s", self.host, params)
        # TODO: adjust DB connection according to DB params in answer file, automatically.
        util(answer_file='host:'+ans)
        util.testInstallation()


class Utility(object):
    """
    Description: Base class for rhevm utilities
    """

    def __init__(self, setup):
        """
        C'tor
        Parameters:
         * setup - instance of Setup class
        """
        super(Utility, self).__init__()
        self.setup = setup
        self.rc = None
        self.out = None
        self.err = None

    @property
    def version(self):
        m = re.match('^([0-9]+)[.]([0-9]+).+', self.setup.rpmVer)
        if m:
            #self.version = (int(m.group(1)), int(m.group(2)))
            return (int(m.group(1)), int(m.group(2)))
        raise errors.RHEVMUtilsError("failed to fetch version: %s" % self.setup.rpmVer)

    def __call__(self, *args, **kwargs):
        raise NotImplementedError("you have to implement this")

    def clearParams(self, kwargs):
        return Options((x.replace('_', '-'), y) for x, y in kwargs.items())

    def createCommand(self, name, kwargs, long_prefix='--', long_glue='='):
        cmd = [self.setup._bin[name]]
        cmd.extend(ut.createCommandLineOptionFromDict(kwargs, long_prefix, long_glue=long_glue))
        return cmd

    def _fetchLogs(self):
        """
        Tries to locate logs according outputs and fetch them to local machine
        NOTE: experimental
        """
        reg = re.compile(r'(?P<log>(/[^/ ]*)+[.]log)', re.I)
        for o in self.out, self.err:
            m = reg.search(o)
            if m:
                path = m.group('log')
                target = os.path.join('/tmp', os.path.basename(path))
                if self.setup.copyFrom(path, target):
                    logger.info("fetched log %s to %s", path, target)
                else:
                    logger.warn("found log %s, but failed to get it to %s", path, target)

    def execute(self, name, cmd, timeout=None):
        self.rc = None
        self.out = None
        self.err = None
        if timeout is None:
            timeout = self.setup.execTimeout
        with self.setup.ssh as ssh:
            self.rc, self.out, self.err = ssh.runCmd(cmd, timeout=timeout, \
                    conn_timeout=self.setup.connectionTimeout)
        logger.info("executed command: %s ; rc: %s, out: %s; err: %s", cmd, \
                self.rc, self.out, self.err)
        self._fetchLogs()

    def checkPassedFile(self, filepath):
        if not re.match('^host:', filepath):
            if not self.setup.copyTo(filepath, self.setup.tmp):
                msg = "failed to copy file %s to %s:%s " % (filepath, \
                        self.setup.host, self.setup.tmp)
                raise errors.FileTransferError(msg)
        else:
            filepath = filepath[5:]
        # Maybe we will want to check what it does in case the file doens't exists
        #if not self.setup.isFileExists(filepath):
        #    msg = "%s:%s doesn't exists" % (self.setup.host, filepath)
        #    raise CheckFileError(msg)
        return filepath

    def getVar(self, name):
        """
        Fetch variable from config file
        Parameters:
         * name - name of variable
        """
        return self.setup.getVar(name)

    def recognizeError(self, patterns, out, addpars=None, sub=False):
        """
        Tries to recognize expected error messages and raise appropriate exeption
        Parameters:
         * patterns - data-structure with patterns and exceptions
                    ( pattern, exeption, names of params, (sub errors, .. ) )
                    it should containt every module
         * out - output, which will used for searching
         * addpars - list of args for exception
         * sub - suberror flag
        """
        for pattr, exc, params, subs in patterns:
            m = re.search(pattr, out)
            if m:
                params = [m.group(name) for name in params ]
                self.recognizeError(subs, out, params, True)
                if addpars is not None:
                    params.extend(addpars)
                raise exc(*params)
        if not sub:
            raise errors.UnrecognizedError(out)

    def isDBExists(self):
        """
        Checks whether DB exists
        """
        try:
            self.setup.psql('-- Check whether DB exists')
        except errors.ExecuteDBQueryError as ex:
            logger.debug("DB doesn't exists: %s", ex)
            return False
        return True

    def isJbossRunning(self):
        return self.setup.isServiceRunning(self.getVar('JBOSS_SERVICE'))

    def startJboss(self):
        return self.setup.startService(self.getVar('JBOSS_SERVICE'))

    def stopJboss(self):
        return self.setup.stopService(self.getVar('JBOSS_SERVICE'))

    def restartJboss(self):
        self.stopJboss()
        self.startJboss()

    # ====== TESTS ========

    def autoTest(self):
        """
        Description: Calls tests according to passed options.
        """
        raise NotImplementedError("you have to implement this")

    def testReturnCode(self, rc=0):
        if self.rc != rc:
            raise errors.ReturnCodeError(rc, self.rc, self.out, self.err)


class Options(dict):
    """
    Description: Adjusted dict to be able to map more specific keys to
                 one value. Used for command's options (-h and --help has
                 same meaning)
    """
    def __getitem__(self, name):
        if isinstance(name, set):
            res = set(self.keys()) & name
            if not res:
                raise KeyError(name)
            name = res.pop()
        return super(Options, self).__getitem__(name)

    def get(self, k, d):
        try:
            return self.__getitem__(k)
        except KeyError:
            return d

    def __contains__(self, name):
        try:
            self.__getitem__(name)
        except KeyError:
            return False
        return True

class SDK(object):
    API = None
    params = sdk_params
    manager = None

    @classmethod
    def __new__(cls, sub):
        if cls.API is None:
            if config:
                conf = config['SDK']
                SDK.init(conf['address'], conf['user'], conf['password'])
            else:
                logger.warn("You can have problem with SDK connection, which is used for testing purposes")
        return cls.API

    @classmethod
    def init(cls, address, user, passwd):
        if API is not None:
            cls.API = API(address, user, passwd)
        else:
            logger.warn("SDK package is missing some functionality couldn't work")


class SetupManager(object):
    """
    Class which is able to work with setup and perform cleanning action
    NOTE: I guess this will be generalized and moved somewhere else, because
          it is usable for another tasks as well.
    """

    BASE_SNAPSHOT = 'working_snapshot'

    def __init__(self):
        """
        C'tor
        """
        self.sdk = SDK()
        self.maps = {}
        self.setups = {}

    def _waitForEvent(self, event, machine, timeout=None, interval=2):
        if timeout is None:
            timeout = config.get('wait_timeout', WAIT_TIMEOUT)
        start = time.time()
        while True:
            if event():
                break
            if time.time() - start > timeout:
                name = machine.get_name()
                raise errors.WaitForStatusTimeout(timeout, name)
            time.sleep(interval)

    def waitForMachineStatus(self, machine, status, timeout=None, interval=2):
        """
        Wait until machine get specific status
        Parameters:
         * machine - VM object
         * status - name of status or list of acceptable states
         * timeout - timeout in seconds
         * interval - sleep interval between each check in seconds
        """
        def event(machine=machine, status=status):
            machine = self.sdk.vms.get(id=machine.id)
            st = machine.status.get_state()
            return st == status
        self._waitForEvent(event, machine, timeout, interval)

    def waitForAgentIsUp(self, machine, timeout=None, interval=2):
        """
        Wait until agent respond
        Parameters:
         * machine - VM object
         * timeout - timeout in seconds
         * interval - sleep interval between each check in seconds
        """
        def event(machine=machine):
            machine = self.sdk.vms.get(id=machine.id)
            guest_info = machine.get_guest_info()
            return guest_info is not None
        self._waitForEvent(event, machine, timeout, interval)

    def ensureMachineIsDown(self, machine):
        """
        Stop machine and wait for down status
        Parameters:
         * machine - VM object
        """
        machine = self.refreshMachine(machine)
        st = machine.status.get_state()
        if st != 'down':
            machine.stop()
            self.waitForMachineStatus(machine, 'down')

    def popMachine(self, name):
        """
        Return machine for test
        """
        # now it only takes vm_name from config, but it will use pool feature
        # as soon as we will create it.
        vm_name = config[name]['vm_name']
        machine = self.sdk.vms.get(name=vm_name)
        if not machine:
            raise errors.SetupsManagerError("can't find testing machine: %s" % vm_name)
        if machine.status.get_state() != 'down':
            raise errors.SetupsManagerError("machine is not down: %s" % vm_name)
        self.maps[name] = machine
        return machine

    def releaseMachine(self, name):
        try:
            m = self.maps.pop(name)
            self.waitForMachineStatus(m, 'down')
        except KeyError:
            logger.error("machine wasn't alloceted for test: %s", name)

    def refreshMachine(self, machine):
        """
        Reload machine's data
        Parameters:
         * machine - VM object
        Return: fresh VM object
        """
        name = machine.get_name()
        machine = self.sdk.vms.get(id=machine.id)
        if not machine:
            raise errors.SetupsManagerError("can't find testing machine: %s" % name)
        return machine

    def createSnapshot(self, machine, name):
        """
        Creates snapshot of machine
        Parameters:
         * machine - VM machine
         * name - name of snapshot
        """
        self.ensureMachineIsDown(machine)
        machine = self.refreshMachine(machine)
        machine.snapshots.add(SDK.params.Snapshot(name=name, description=name))
        self.waitForMachineStatus(machine, 'down')

    def restoreSnapshot(self, machine, name):
        """
        Restores to snapshot
        Parameters:
         * machine - VM object
         * name - name of snapshot
        """
        self.ensureMachineIsDown(machine)
        machine = self.refreshMachine(machine)
        #snap = machine.snapshots.get(name=name)
        snap = machine.snapshots.get(description=name)
        if snap is not None:
            snap.restore()
            self.waitForMachineStatus(machine, 'down')

    def getIp(self, machine):
        """
        Retrieve ip address for machine (needs agent)
        Parameters:
         * machine - VM object
        Return: ip
        """
        machine = self.refreshMachine(machine)
        g = machine.get_guest_info()
        ips = g.get_ips()
        for ip in ips.get_ip():
            ip = ip.get_address()
            if ip:
                return ip
        raise errors.NoIpFoundError(machine.get_name())

    def prepareSetup(self, name):
        machine = self.popMachine(name)
        sn_list = [ x.description for x in machine.snapshots.list()]
        #if self.BASE_SNAPSHOT in sn_list:
        #    if self.BASE_SNAPSHOT == sn_list[-1]:
        #        return
        #    else:
        #        self.restoreSnapshot(machine, self.BASE_SNAPSHOT)
        self.createSnapshot(machine, self.BASE_SNAPSHOT)

    def startSetup(self, name):
        machine = self.maps[name]
        machine.start()
        self.waitForMachineStatus(machine, 'up')

    def stopSetup(self, name):
        machine = self.maps[name]
        machine.stop()
        self.waitForMachineStatus(machine, 'down')

    def saveSetup(self, name, point):
        self.createSnapshot(self.maps[name], point)

    def restoreSetup(self, name, point):
        self.restoreSnapshot(self.maps[name], point)

    def dispatchSetup(self, name):
        machine = self.refreshMachine(self.maps[name])
        if machine.status.get_state() != 'up':
            machine.start()
            self.waitForMachineStatus(machine, 'up')
        self.waitForAgentIsUp(machine)
        ip = self.getIp(machine)
        conf = config['testing_env']
        return Setup(ip, 'root', conf['password'])

    def releaseSetup(self, name):
        try:
            machine = self.refreshMachine(self.maps[name])
            if machine.status.get_state() == 'up':
                machine.stop()
                self.waitForMachineStatus(machine, 'down')
            self.restoreSnapshot(machine, self.BASE_SNAPSHOT)
        finally:
            self.releaseMachine(name)

    def installSetup(self, name):
        m = self.dispatchSetup(name)
        # TODO: install


_multiprocess_can_split_ = True

class RHEVMUtilsTestCase(unittest.TestCase):
    """
    Base class for test plan. It contains general setUp and tearDown class
    which are suiteable for most of RHEVM utilities
    """
    __test__ = False
    utility = None
    utility_class = None
    manager = SetupManager()
    snapshot_setup_installed = "installed_setup"
    _multiprocess_can_split_ = True

    @classmethod
    def setUpClass(cls):
        """
        Prepares setup machine, install RHEVM on it, and create snapshot
        """
        cls.c = config[cls.utility]
        cls.manager.prepareSetup(cls.utility)
        machine = cls.manager.dispatchSetup(cls.utility)
        machine.install(config)
        #cls.manager.saveSetup(cls.utility, cls.snapshot_setup_installed)

    @classmethod
    def tearDownClass(cls):
        """
        Remove all snapshosts, and relase machine
        """
        cls.manager.releaseSetup(cls.utility)

    def setUp(self):
        """
        Fetch instance of utility for test-case
        """
        self.manager.saveSetup(self.utility, self.snapshot_setup_installed)
        self.ut = self.utility_class(self.manager.dispatchSetup(self.utility))

    def tearDown(self):
        """
        Discart changes which was made by test-case
        """
        self.manager.restoreSetup(self.utility, self.snapshot_setup_installed)

