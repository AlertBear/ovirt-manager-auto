"""
--------------------
Hosts Cleanup Plugin
--------------------

This plugin removes Storage and Network leftovers from your VDS hosts
machines as defined in your configuration file.

CLI Options:
------------
    --with-cleanup   Enable the plugin and clean all
"""
import re
from itertools import cycle, izip
from utilities import machine
from art.test_handler.plmanagement import PluginError
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.resources_listener import \
    IResourcesListener
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation


logger = get_logger('host_cleanup')

DEFAULT_STATE = False
CLEANUP = 'HOSTS_CLEANUP'
RUN_SECTION = 'RUN'
SERVICES = ['rpcbind', 'nfslock', 'iptables']
PROCESSES = ['yum']
DC_DIR = '/rhev/data-center'


def cleanHostStorageSession(hostObj, **kwargs):
    '''
    Description: Runs few commands on a given host to clean storage related
                 session and dev maps.
    **Author**: talayan
    **Parameters**:
      **hostObj* - Object represnts the hostObj
    '''
#   check if there is an active session
    check_iscsi_active_session = ['iscsiadm', '-m', 'session']
    logger.info("Run %s to check if there are active iscsi sessions",
                " ".join(check_iscsi_active_session))
    res, out = hostObj.runCmd(check_iscsi_active_session)
    if not res:
        logger.info("Run %s Res: %s",
                    " ".join(check_iscsi_active_session), out)
        return

    logger.info("There are active session, perform clean and logout")

    commands = [['iscsiadm', '-m', 'session', '-u'],
                ['multipath', '-F'],
                ['dmsetup', 'remove_all']]

    for cmd in commands:
        logger.info("Run %s", " ".join(cmd))
        res, out = hostObj.runCmd(cmd)
        if not res:
            logger.info(str(out))


def killProcesses(hostObj, procName, **kwargs):
    '''
    Description: pkill procName

    **Author**: talayan
    **Parameters**:
      **hostObj* - Object represents the hostObj
      **procName* - process to kill
    '''
#   check if there is zombie qemu proccess
    pgrep_proc = ['pgrep', procName]
    logger.info("Run %s to check there are running processes..",
                " ".join(pgrep_proc))
    res, out = hostObj.runCmd(pgrep_proc)
    if not res:
        logger.info("Run %s Res: %s", " ".join(pgrep_proc), out)
        return

    logger.info("performing: pkill %s" % procName)

    pkill_proc = ['pkill', procName]

    logger.info("Run %s" % " ".join(pkill_proc))
    res, out = hostObj.runCmd(pkill_proc)
    if not res:
        logger.info(str(out))


def restartServices(hostObj):
    '''
    Description: stop and restart needed services

    **Author**: imeerovi
    **Parameters**:
      **hostObj* - Object represents the hostObj
    Returns: True if succeeded to stop/restart needed services
             and False in other case
    '''
    logger.info("Restarting services")
    for service in SERVICES:
        # iptables issue
        if service == 'iptables':
            if not hostObj.runCmd(['[', '-e', '/etc/sysconfig/iptables',
                                   ']'])[0]:
                logger.warning("Skipping restart of %s", service)
                logger.info("Flushing possible 'manually added' rules"
                            " with '%s -F'", service)
                hostObj.runCmd(['iptables', '-F'])
                continue

        if service == 'rpcbind' and not hostObj.checkRpm(service):
            logger.warning("{0} is not installed, Skipping restart of {0}".
                           format(service))
            continue

        logger.info("Restarting %s", service)
        if service == 'nfslock':
            res, osType = hostObj.getHostOsType()
            if res and osType:
                if re.search('7[.][1-9]', osType) is not None:
                    logger.info("Host os is 7.x; service name is nfs-lock")
                    service = 'nfs-lock'
            else:
                logger.info("Unknown osType ; skip restarting %s", service)
                continue

        logger.info("Restarting %s", service)
        if not hostObj.restartService(service):
            logger.error("Failed to restart %s", service)
            return False
    return True


def checkIfProcessIsRunning(hostObj):
    '''
    Description: checking if specific processes are running and print to log
    **Author**: imeerovi
    **Parameters**:
      **hostObj* - Object represents the hostObj
    Returns: None
    '''
    logger.info("checking for running processes")
    _, process_status = hostObj.runCmd(['ps', 'xt'])
    process_status_list = process_status.split('\r\n')
    logger.debug("Dumping 'ps xt' command output:\n%s",
                 '\n'.join(process_status_list))

    for process in PROCESSES:
        process_status = filter(lambda x: process in x, process_status_list)
        if len(process_status):
            logger.info("Process '%s' status:\n%s", process,
                        '\n'.join(process_status))
        else:
            logger.info("Process '%s' is not running", process)


def cleanupDatacenters(hostObj):
    '''
    Description: cleanup old datacenters data
    **Author**: imeerovi
    **Parameters**:
        **hostObj* - Object represents the hostObj
    Returns: True if succeeded to remove old data, else in other case
    '''
    logger.info("Cleaning {0}/* if {0} exists".format(DC_DIR))
    if hostObj.runCmd("[ '-d' '{0}' ]".format(DC_DIR), cmd_list=False)[0]:
        out = hostObj.runCmd("ls -ls {0}/".format(DC_DIR), cmd_list=False)[1]
        if 'total 0' in out:
            logger.info("No cleanup was done since {0}/ {1}".format(DC_DIR,
                        "is empty"))
            return True

        logger.info('ls -ls {0}/ output:\n{1}'.format(DC_DIR, out))
        logger.info("Cleaning {0}/".format(DC_DIR))
        cmd = 'rm -rf {0}/*'.format(DC_DIR)
        rc, out = hostObj.runCmd(cmd, cmd_list=False)
        if not rc:
            logger.error("Failed to run %s with error: %s", cmd, out)
            return False

        logger.info("{0}/ was successfully cleaned".format(DC_DIR))
        return True

    logger.info("No cleanup was done since {0} doesn't exists".format(DC_DIR))
    return True


def unmountRhevmMounts(hostObj):
    '''
    Description: unmount rhev mounts
    **Author**: imeerovi
    **Parameters**:
        **hostObj* - Object represents the hostObj
    Returns: True if succeeded to unmount all mounts, else in other case
    '''
    rc = True
    _, out = hostObj.runCmd(['mount'])
    for mountPoint in [
        x.split()[0] for x in out.splitlines() if '/rhev/' in x
    ]:
        if mountPoint == "none":
            logger.debug(
                "Not trying to unmount %s, this is a valid mount point for "
                "RHEV-H >= 7", mountPoint
            )
            continue

        logger.info("Unmounting %s", mountPoint)
        cmdRc, out = hostObj.runCmd(['umount', '-l', mountPoint])
        if not cmdRc:
            logger.error("Failed to unmount %s with error: %s", mountPoint,
                         out)
            rc = False
    return rc


def cleanCorruptedISCSIDBFiles(hostObj):
    '''
    Description: WA for bug #915747, it cleans iscsi db files with size 0
    **Author**: imeerovi
    **Parameters**:
        **hostObj* - Object represents the hostObj
    Returns: True if succeeded to remove corrupted files, else in other case
    '''
    rc = True
    logger.info("Checking for corrupted ISCSI files (WA for bug #915747)")
    _, out = hostObj.runCmd(['ls', '-ls',  '/var/lib/iscsi/nodes/'])
    for line in [x.split() for x in out.splitlines() if 'iqn' in x]:
        file_size = line[5]
        file_name = line[-1]
        if file_size == '0':
            logger.info("Erasing empty file %s", file_name)
            cmdRc, out = hostObj.runCmd(['echo', 'y', '|', 'rm', '-rf',
                                         '/var/lib/iscsi/nodes/%s' %
                                         file_name])
            if not cmdRc:
                logger.error("Failed to remove %s with error: %s", file_name,
                             out)
                rc = False
    return rc


def hostCleanup(address, password, username='root'):
    '''
    Description: function that cleanup hosts

    **Author**: imeerovi
    **Parameters**:
      **address* - host address
      **password* - password
      **username* - username [root]
    Returns: True if succeeded to cleanup host and False in other case
    '''
    hostObj = machine.Machine(address, username, password).util('linux')

    cleanHostStorageSession(hostObj)
    killProcesses(hostObj, 'qemu')
    checkIfProcessIsRunning(hostObj)
    return unmountRhevmMounts(hostObj) and restartServices(hostObj) \
        and cleanCorruptedISCSIDBFiles(hostObj) and cleanupDatacenters(hostObj)


class CleanUpHosts(Component):
    """
    Plugin provides cleanup procedure for hosts.
    """
    implements(IResourcesListener, IConfigurable, IConfigValidation,
               IPackaging)
    name = "CleanUp hosts"
    priority = 1001

    def __init__(self):
        super(CleanUpHosts, self).__init__()
        self.cleanup = None
        self.conf = None

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group = group.add_mutually_exclusive_group()
        group.add_argument('--with-cleanup', action="store_true",
                           dest='cleanup_enabled',
                           help="enable cleanup functionality", default=False)

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        logger.info("Configuring hosts cleanup plugin.")
        self._conf = conf['PARAMETERS']
        self._hosts = self._conf.as_list('vds')
        self._passwords = self._conf.as_list('vds_password')

    def on_storages_prep_request(self):
        pass

    def on_storages_cleanup_request(self):
        pass

    def on_hosts_cleanup_req(self):
        logger.info('Starting hosts cleanup process...')
        for host, password in izip(self._hosts, cycle(self._passwords)):
            logger.info('Running on %s', host)
            if not hostCleanup(host, password):
                errMsg = 'Cleaning process was Failed on %s' % host
                raise PluginError(errMsg)
        logger.info('Finish Cleanup process')

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[CLEANUP].as_bool('enabled')
        return params.cleanup_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'hosts-cleanup'
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Hosts cleanup for ART'
        params['long_description'] = 'Plugin for ART which is responsible '\
            'for clear VDS machines.'
        params['requires'] = []
        params['py_modules'] = \
            ['art.test_handler.plmanagement.plugins.hosts_cleanup_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(CLEANUP, {})
        section_spec['enabled'] = 'boolean(default=%s)' % DEFAULT_STATE
