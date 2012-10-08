
# Usage: rhevm-log-collector [options] list
#        rhevm-log-collector [options] collect
#
# Options:
#   --version             show program's version number and exit
#   -h, --help            show this help message and exit
#   --conf-file=PATH      path to configuration file
#                         (default=/etc/rhevm/logcollector.conf)
#   --local-tmp=PATH      directory to copy reports to locally
#                         (default=/tmp/logcollector)
#   --ticket-number=TICKET
#                         ticket number to pass with the sosreport
#   --upload=ftp://dropbox.redhat.com/incoming
#                         Upload the report to Red Hat when instructed by a
#                         support representative.  The following URL should be
#                         used: ftp://dropbox.redhat.com/incoming.
#   --quiet               reduce console output (default=False)
#   --log-file=PATH       path to log file (default=/var/log/rhevm/rhevm-log-
#                         collector.log)
#   -v, --verbose
#
#   RHEV-M Configuration:
#     The options in the RHEV-M configuration group can be used to filter
#     log collection from one or more RHEV-H. If the --no-hypervisors option
#     is specified, data is not collected from any RHEV-H.
#
#     --no-hypervisors    skip collection from hypervisors (default=False)
#     -u user@rhevm.example.com, --user=user@rhevm.example.com
#                         username to use with the REST API.  This should be in
#                         UPN format.
#     -r rhevm.example.com, --rhevm=rhevm.example.com
##     -r rhevm.example.com, --engine=rhevm.example.com ## for ovirt
#                         hostname or IP address of the RHEV-M
#                         (default=localhost:8443)
#     -c CLUSTER, --cluster=CLUSTER
#                         pattern, or comma separated list of patterns to filter
#                         the host list by cluster name (default=None)
#     -d DATACENTER, --data-center=DATACENTER
#                         pattern, or comma separated list of patterns to filter
#                         the host list by data center name (default=None)
#     -H HOSTS_LIST, --hosts=HOSTS_LIST
#                         comma separated list of hostnames, hostname patterns,
#                         FQDNs, FQDN patterns, IP addresses, or IP address
#                         patterns from which the log collector should collect
#                         RHEV-H logs (default=None)
#
#   SOSReport Options:
#     The JBoss SOS plug-in will always be executed.  To activate data
#     collection from JBoss's JMX console enable-jmx, java-home, jboss-user,
#     and jboss-pass must also be specified.  If no jboss-pass is supplied
#     in the configuration file then it will be asked for prior to
#     collection time.
#
#     --jboss-home=/path/to/jbossas
#                         JBoss's installation dir (default=/var/lib/jbossas)
#     --java-home=/path/to/java
#                         Java's installation dir (default=/usr/lib/jvm/java)
#     --jboss-profile=PROFILE1, PROFILE2
#                         comma separated list of server profiles to limit
#                         collection (default='rhevm-slimmed')
#     --enable-jmx        Enable the collection of run-time metrics from the
#                         RHEV-M JBoss JMX interface
#     --jboss-user=admin  JBoss JMX username (default=admin)
#     --jboss-logsize=15  max size (MiB) to collect per log file (default=15)
#     --jboss-stdjar=on or off
#                         collect jar statistics for JBoss standard
#                         jars.(default=on)
#     --jboss-servjar=on or off
#                         collect jar statistics from any server configuration
#                         dirs (default=on)
#     --jboss-twiddle=on or off
#                         collect twiddle data (default=on)
#     --jboss-appxml=APP, APP2
#                         comma separated list of application's whose XML
#                         descriptors you want (default=all)
#
#   SSH Configuration:
#     The options in the SSH configuration group can be used to specify the
#     maximum number of concurrent SSH connections to RHEV-H(s) for log
#     collection, the SSH port, and a identity file to be used.
#
#     --ssh-port=PORT     the port to ssh and scp on
#     -k KEYFILE, --key-file=KEYFILE
#                         the identity file (private key) to be used for
#                         accessing the RHEV-Hs
#                         (default=/etc/pki/rhevm/keys/rhevm_id_rsa). If a
#                         identity file is not supplied the program will prompt
#                         for a password.  It is strongly recommended to use key
#                         based authentication with SSH because the program may
#                         make multiple SSH connections resulting in multiple
#                         requests for the SSH password.
#     --max-connections=MAX_CONNECTIONS
#                         max concurrent connections for fetching RHEV-H logs
#                         (default = 10)
#
#   PostgreSQL Database Configuration:
#     The log collector will connect to the RHEV-M PostgreSQL database and
#     dump the data for inclusion in the log report unless --no-postgresql
#     is specified.  The PostgreSQL user ID and database name can be
#     specified if they are different from the defaults.  If the PostgreSQL
#     database is not on the localhost set pg-dbhost, provide a pg-ssh-user,
#     and optionally supply pg-host-key and the log collector will gather
#     remote PostgreSQL logs.  The PostgreSQL SOS plug-in must be installed
#     on pg-dbhost for successful remote log collection.
#
#     --no-postgresql     This option causes the tool to skip the postgresql
#                         collection (default=false)
#     --pg-user=postgres  PostgreSQL database user name (default=postgres)
#     --pg-dbname=rhevm   PostgreSQL database name (default=rhevm)
#     --pg-dbhost=localhost
#                         PostgreSQL database hostname or IP address
#                         (default=localhost)
#     --pg-ssh-user=root  the SSH user that will be used to connect to the
#                         server upon which the remote PostgreSQL database
#                         lives. (default=root)
#     --pg-host-key=none  the identity file (private key) to be used for
#                         accessing the host upon which the PostgreSQL database
#                         lives (default=not needed if using localhost)
#
# Return values:
#     0: The program ran to completion with no errors.
#     1: The program encountered a critical failure and stopped.
#     2: The program encountered a problem gathering data but was able to continue.

import os
import re
from fnmatch import fnmatch
import glob
from contextlib import contextmanager

from rhevm_utils.base import Utility, logger, RHEVMUtilsTestCase
from rhevm_utils import errors
import utilities.utils as ut
from utilities import machine

NAME = 'log-collector'

OPT_HELP = set(('h', 'help'))
OPT_CLUSTER = set(('c', 'cluster'))
OPT_DATA_CENTER = set(('d', 'data-center'))
OPT_HOST = set(('H', 'hosts'))
OPT_NO_HYPERVISORS= 'no-hypervisors'
OPT_NO_POSGRES = 'no-postgresql'
OPT_DB_HOST = 'pg-dbhost'

ACTION_LIST = 'list'
ACTION_COLLECT = 'collect'


NAME_COLUMN = 'name'
HOST_NAME_COLUMN = 'host_name'
HOSTS_TABLE = 'vds'
VDS_GROUPS_TABLE = 'vds_groups'
VDS_GROUP_ID_COLUMN = 'vds_group_id'
ID_COLUMN = 'id'
STORAGE_POOL_TABLE = 'storage_pool'
STORAGE_POOL_ID_COLUMN = 'storage_pool_id'

RHEVM_REPORT_PATTERN = 'lc_reports_content/setup.xml'
DB_REPORT_PATTERN = 'lc_reports_content/db.xml'
HOST_REPORT_PATTERN = 'lc_reports_content/host.xml'

TIMEOUT = 5 * 60

# ( pattern, exeption, names of params, (sub errors, .. ) )
ERROR_PATTERNS = ()

class LogCollectorUtility(Utility):
    """
    Encapsulation of rhevm-log-collector utility
    """
    def __init__(self, *args, **kwargs):
        super(LogCollectorUtility, self).__init__(*args, **kwargs)
        self.kwargs = None
        self.action = None
        self.pathToRHEVMReportPattern = ut.getConfigFilePath(__file__, RHEVM_REPORT_PATTERN)
        self.pathToDBReportPattern = ut.getConfigFilePath(__file__, DB_REPORT_PATTERN)
        self.pathToHostReportPattern = ut.getConfigFilePath(__file__, HOST_REPORT_PATTERN)
        self.timeout = kwargs.get('timeout', TIMEOUT)
        self.optRHEVM = set(('r', self.setup.product))

    def autoTest(self):
        if OPT_HELP in self.kwargs:
            self.testReturnCode()
            return

        if self.action == ACTION_COLLECT and self.rc in (0, 2):
            self.testCollect()

        if self.action == ACTION_LIST and self.rc in (0, 2):
            self.testList()

        self.testReturnCode()

    def __call__(self, *args, **kwargs):
        self.action = None
        if len(args) >= 1:
            self.action = args[0]
        self.kwargs = self.clearParams(kwargs)

        if self.optRHEVM in self.kwargs:
            if self.kwargs[self.optRHEVM] not in ('localhost', '127.0.0.1'):
                logger.warning("test is not able to verify results on diffent machine yet")

        if self.action == ACTION_COLLECT:
            #FIXME: due to BZ #789040, #788993 don't collect data from hypervisors
            logger.warning("adding --no-hypervisors due to BZ #789040, #788993")
            self.kwargs[OPT_NO_HYPERVISORS] = None

        cmd = self.createCommand(NAME, self.kwargs)
        if self.action is not None:
            cmd.append(self.action)

        # set timout to (RHEVM + number of hosts) * timeout because it can take some time
        timeout = self.timeout * (1 + len(self.filterHosts()))
        self.execute(NAME, cmd, timeout=timeout)

        #self.autoTest()


    def filterHosts(self):
        """
        Returns set of hosts which matchs with passed kwargs
        """
        if OPT_NO_HYPERVISORS in self.kwargs:
            return set()

        opts = {
                'cluster': self.kwargs.get(OPT_CLUSTER, '*'),
                'datacenter': self.kwargs.get(OPT_DATA_CENTER, '*'),
                'host': self.kwargs.get(OPT_HOST, '*')
                }
        opts = dict((x,y.split(',')) for x, y in opts.items())

        sql = "SELECT d.%s, c.%s, v.%s FROM %s v join %s c on v.%s = c.%s "\
              "join %s d on d.%s = v.%s ;"

        info = self.setup.psql(sql, NAME_COLUMN, NAME_COLUMN, HOST_NAME_COLUMN, \
                HOSTS_TABLE, VDS_GROUPS_TABLE, VDS_GROUP_ID_COLUMN, \
                VDS_GROUP_ID_COLUMN, STORAGE_POOL_TABLE, ID_COLUMN, \
                STORAGE_POOL_ID_COLUMN)

        hosts = set()
        for line in info:
            if any([fnmatch(line[0], x) for x in opts['datacenter']])\
                and any([fnmatch(line[1], x) for x in opts['cluster']])\
                and any([fnmatch(line[2], x) for x in opts['host']]):
                hosts.add(line[2])
        return hosts

    @contextmanager
    def decompress(self, pathToTar, entryPatt):
        """
        Decompress archive and return path to target directory
        (use with 'with' statement)
        Parameters:
         * pathToTar - path to archive
         * entryPatt - pattern of expected directory
        """
        targetDir = ut.decompressDir(pathToTar)
        if not targetDir:
            raise errors.ReportsExtractionError(pathToTar)
        try:
            entry = os.listdir(targetDir)
            if len(entry) != 1:
                raise errors.LogCollectorUtilityError(\
                        "unexpected number of directories: %s" % entry)
            if not re.match(entryPatt, entry[0]):
                raise errors.LogCollectorUtilityError(\
                        "unexpected name of entry: '%s' doesn't match '%s'" % \
                        (entryPatt, entry[0]))
            entry = os.path.join(targetDir, entry[0])
            if not os.path.isdir(entry):
                raise errors.LogCollectorUtilityError(\
                        "expected directory, got file: %s" % entry)

            yield entry

        finally:
            machine.Machine().util(machine.LINUX).removeFile(targetDir)

    def testCollect(self):
        out = self.out + self.err
        # TODO: found out if it is bug or not (it should print these
        # information to stdout, not on err)
        match = re.search('Log files have been collected and placed in "\
                "(?P<file>.+[.]tar[.]xz)', out)
        if not match:
            raise errors.ReportsVerificationError(\
                    "failed to find out report in '%s'" % self.out)

        name = match.group('file')
        if not self.setup.copyFrom(name, self.setup.tmp):
            raise errors.ReportsExtractionError(\
                    "failed to fetch reports: %s:%s" % (self.setup.host, name))
        name = os.path.join(self.setup.tmp, os.path.basename(name))

        hosts = set()
        if OPT_NO_HYPERVISORS not in self.kwargs:
            hosts = self.filterHosts()

        try:
            self.verifyReportContent(name, hosts)
        finally:
            os.remove(name)

    def verifyReportContent(self, name, hosts):
        """
        Check content of collected logs
        Parameters:
         * name - path to archive
         * hosts - set of host names
        """
        hostname = ut.getHostName(self.setup.host).split('.')[0]
        with self.decompress(name, hostname+"-.*") as entry:

            checker = ut.DirectoryContentChecker(self.pathToRHEVMReportPattern)
            if not checker.checkContent(entry):
                raise errors.RHEVMReportsVerificationError(entry)

            entry = os.path.join(entry, self.getVar('PATH_TO_POSTGRES_REPORTS'))

            # check DB report
            path = glob.glob(os.path.join(entry, 'postgres*.xz'))
            if OPT_NO_POSGRES not in self.kwargs:
                if len(path) != 1:
                    raise errors.DBReportsVerificationError(\
                            "failed to find DB report in %s; there is %s" \
                            % (entry, path))
                hostname = self.setup.host
                if OPT_DB_HOST in self.kwargs:
                    hostname = self.kwargs[OPT_DB_HOST]
                    if hostname in ('localhost', '127.0.0.1'):
                        hostname = self.setup.host
                hostname = ut.getHostName(hostname).split('.')[0]
                with self.decompress(path[0], hostname+"-.*") as dbentry:
                    checker = ut.DirectoryContentChecker(self.pathToDBReportPattern)
                    if not checker.checkContent(dbentry):
                        raise errors.DBReportsVerificationError(dbentry)

            elif path:
                raise errors.DBReportsVerificationError(\
                        "there is unexpected DB report: %s" % path)

            # check report from hosts
            dirs = set( x for x in os.listdir(entry) if os.path.isdir(os.path.join(entry, x)) )
            if len(dirs) != len(hosts) or len(dirs - hosts) != 0:
                raise errors.HostReportsVerificationError(\
                        "unexpected reports from hosts: expected: %s; "\
                        "got: %s" % (hosts, dirs))

            for host in hosts:
                path = os.path.join(entry, host)
                hostname = ut.getHostName(host).split('.')[0]

                tar = glob.glob(os.path.join(path, host+"-*.xz"))
                if len(tar) != 1:
                    raise errors.HostReportsVerificationError(\
                            "failed to find host's report in %s, %s" % \
                            (path, tar))
                with self.decompress(tar[0], hostname+'-.*') as hostentry:
                    checker = ut.DirectoryContentChecker(self.pathToHostReportPattern)
                    if not checker.checkContent(hostentry):
                        raise errors.HostReportsVerificationError(hostentry)

    def testList(self):
        hosts = self.filterHosts()

        if not hosts:
            if not re.search('No hypervisors were found', self.out):
                raise errors.ListActionVerification(\
                        "no hypervisors expected, but got: %s" % self.out)
        else:
            res = [ [a.strip() for a in x.split('|')] \
                    for x in re.findall('.+[|].+[|].+', self.out)]

            for dc, cl, ip in res[1:]:
                if ip in hosts:
                    if dc and cl:
                        hosts.remove(ip)
                    else:
                        raise errors.ListActionVerification(\
                                "DC and Cluster are emtpy for host %s" % ip)
                else:
                    raise errors.ListActionVerification(\
                            "unexpected host in list: %s not in %s" % (ip, hosts))

            if hosts:
                raise errors.ListActionVerification(\
                        "expected hosts %s were not found in list: %s" % (hosts, self.out))

#### UNITTESTS #####


class LogCollectorTestCase(RHEVMUtilsTestCase):

    __test__ = False # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = LogCollectorUtility
    _multiprocess_can_split_ = True

