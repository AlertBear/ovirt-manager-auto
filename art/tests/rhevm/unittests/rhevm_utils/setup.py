
# Usage: rhevm-setup [options]
#
# Options:
#   -h, --help            show this help message and exit
#   --gen-answer-file=GEN_ANSWER_FILE
#                         Generate a template of an answer file, using this
#                         option excludes all other option
#   --answer-file=ANSWER_FILE
#                         Runs the configuration in none-interactive mode,
#                         extracting all information from the
#                         configuration file. using this option excludes all
#                         other option
#
#   General configuration parameters:
#     --http-port=HTTP_PORT
#                         Configures HTTP service port
#     --https-port=HTTPS_PORT
#                         Configures HTTPS service port
#     --host-fqdn=HOST_FQDN
#                         The Host's fully qualified domain name
#     --auth-pass=AUTH_PASS
#                         Password for local admin user
#     --db-pass=DB_PASS   Password for the locally created database
#     --org-name=ORG_NAME
#                         Organization Name for the Certificate
#     --default-dc-type=['NFS', 'FC', 'ISCSI']
#                         Default Data Center Storage Type
#
#   ISO Domain paramters:
#     --nfs-mp=NFS_MP     NFS mount point
#     --iso-domain-name=ISO_DOMAIN_NAME
#                         ISO Domain name
#     --config-nfs=['yes', 'no']
#                         Whether to configure NFS share on this server to be
#                         used as an ISO domain
#
#   Firewall related paramters:
#     --override-iptables=['yes', 'no']
#                         Should the installer configure the local firewall,
#                         overriding the current configuration


#__test__ = False
import time

from contextlib import closing
from configobj import ConfigObj
import time

from rhevm_utils.base import Utility, Setup, RHEVMUtilsTestCase, logger, \
        config, istest
from rhevm_utils import errors

NAME = 'setup'

INSTALL_TIMEOUT = 1800

OPT_HELP = set(('h', 'help'))
OPT_GEN_ANSW = 'gen-answer-file'
OPT_ANSW = 'answer-file'

# ( pattern, exeption, names of params, (sub errors, .. ) )
ERROR_PATTERNS = (
        ( 'Failed handling answer file: Error reading '\
            'parameter (?P<name>[^ ]+) from answer file', \
            errors.WrongOptionsInAnswerFile, ('name',), (\
                ( 'The IP (?P<ip>[0-9]+.[0-9]+.[0-9]+.[0-9]+) '\
                'does not hold a PTR record for the FQDN: (?P<host>[^ ]+)', \
                errors.MissingPTRRecord, ('ip', 'host'), ()),
                ( 'mount point is not a valid path', \
                errors.MountPointIsNotValidPath, (), ()
                ),
                ( "can't accept an empty answer for param", \
                errors.EmptyParamInAnswerFile, (), ()
                )
            )
        ),
    )

# TODO:
# Add check for errors and add appropiate exceptions:
#    - rhevm-setup run on machine before
#    - ... maybe more ...

def getInstallParams(rpmVer, conf, answers=config.get('ANSWERS', {})):
    """
    Select set of appropriate config options according to setup version
    Parameters:
     * rpmVer - version of RPM
     * conf - your default options
     * answers - dict of sets of answers
    Return: dict of answers
    """
    if rpmVer not in answers:
        logger.warn("there is no section for version, use __default__: %s" % rpmVer)
        rpmVer = '__default__'
        #raise errors.RHEVMUtilsError("there is no section for version: %s" % rpmVer)
    params = {}
    #for name, val in answers[rpmVer].items():
    #    if val.startswith('<-'):
    #        val = val[2:]
    #        if val in conf:
    #            val = conf[val]
    #        elif val in answers:
    #            val = answers[val]
    #        else:
    #            raise errors.RHEVMUtilsError("cannot find value for %s" % name)
    #    params[name] = val
    for val in answers[rpmVer]:
        params[val] = answers[val]
    return params

class SetupUtility(Utility):
    """
    Encapsulation of rhevm-setup utility
    """
    def __init__(self, *args, **kwargs):
        super(SetupUtility, self).__init__(*args, **kwargs)
        self.kwargs = None
        self.args = None
        self.installTimeout = INSTALL_TIMEOUT

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = self.clearParams(kwargs)
        self.adjustParams()

        cmd = self.createCommand(NAME, self.kwargs)

        self.execute(NAME, cmd, self.installTimeout)

        #self.autoTest()

    def adjustParams(self):
        if OPT_ANSW in self.kwargs:
            self.kwargs[OPT_ANSW] = self.checkPassedFile(self.kwargs[OPT_ANSW])

    def fillAnswerFile(self, **kwargs):
        """
        Fill answer file with specific config options
        Parameters:
         * kwargs - dict of config options
        """
        if not kwargs:
            return
        with self.setup.ssh as ssh:
            fh = ssh.getFileHandler()
            with closing(fh.open(self.kwargs[OPT_GEN_ANSW])) as ans:
                conf = ConfigObj(infile=ans)
            for name, val in kwargs.items():
                if val is None:
                    del conf['general'][name]
                else:
                    conf['general'][name] = val
            with closing(fh.open(self.kwargs[OPT_GEN_ANSW], 'w')) as ans:
                conf.write(ans)


    # ====== TESTS ========

    def autoTest(self):
        if OPT_HELP in self.kwargs:
            self.testReturnCode()
            return
        if OPT_GEN_ANSW in self.kwargs:
            self.testGenerateAnswerFile()
        if OPT_ANSW in self.kwargs:
            self.testInstallation()
        self.testReturnCode()
        # TODO: cover another casses

    def testGenerateAnswerFile(self):
        self.testReturnCode()
        path = self.kwargs[OPT_GEN_ANSW]
        if not self.setup.isFileExists(path):
            raise errors.MissingAnswerFile(path)
        # TODO: maybe it could verify generated options in answer file

    def testInstallation(self):
        if self.rc == 0:
            self.testDBExists()
            self.testJbossRunning()
            self.testHttp()
        else:
            # find out type of error
            # FIXME: There should be self.err !!!
            self.recognizeError(ERROR_PATTERNS, self.out)

    def testDBExists(self):
        try:
            self.setup.psql("-- Test DB exests")
            # TODO: Maybe we will need check tables
        except errors.ExecuteDBQueryError:
            raise errors.MissingDatabase(self.setup.dbname)

    def testJbossRunning(self, interval=6, attempts=10):
        for i in range(attempts):
            if self.setup.isServiceRunning(self.getVar('JBOSS_SERVICE')):
                break
            elif i < attempts - 1:
                time.sleep(interval)
        else:
            raise errors.JbossIsNotRunning(self.getVar('JBOSS_SERVICE'))

    def testHttp(self, https_port=None, http_port=None):
        if (http_port is None or https_port is None) and OPT_ANSW in self.kwargs:
            with self.setup.ssh as ssh:
                fh = ssh.getFileHandler()
                with closing(fh.open(self.kwargs[OPT_ANSW])) as ans:
                    conf = ConfigObj(infile=ans)
                    if http_port is None:
                        http_port = int(conf['general']['HTTP_PORT'])
                    if https_port is None:
                        https_port = int(conf['general']['HTTPS_PORT'])
        if http_port is None or https_port is None:
            msg = "cannot determine ports http(%s) https(%s)" % (http_port, https_port)
            raise errors.HTTPConnectionError(msg)

        def checkConnectivity(host, port, timeout=300, interval=5):
            t = time.time()
            while True:
                if self.setup._isTcpPortOpen(host, port):
                    return
                if time.time() - t > timeout:
                    raise errors.HTTPConnectionError("port %s is not open" % port)
                time.sleep(interval)

        # FIXME: maybe we will need better way
        checkConnectivity(self.setup.host, http_port)
        checkConnectivity(self.setup.host, https_port)



#### UNITTESTS #####

_multiprocess_can_split_ = True

class SetupTestCase(RHEVMUtilsTestCase):

    __test__ = True
    utility = NAME
    utility_class = SetupUtility
    clear_snap = 'clear_machine'
    _multiprocess_can_split_ = True

    @classmethod
    def setUpClass(cls):
        cls.c = config[cls.utility]
        cls.manager.prepareSetup(cls.utility)

    @classmethod
    def tearDownClass(cls):
        super(SetupTestCase, cls).tearDownClass()

    def setUp(self):
        self.manager.saveSetup(self.utility, self.clear_snap)
        self.ut = self.utility_class(self.manager.dispatchSetup(self.utility))
        self.ut.installTimeout = int(config.get('install_timeout', INSTALL_TIMEOUT))

    def tearDown(self):
        self.manager.restoreSetup(self.utility, self.clear_snap)

    @istest
    def generatingAnswerFile(self):
        self.ut(gen_answer_file=self.c['answer_file'])
        self.ut.testGenerateAnswerFile()

    @istest
    def installSetup(self):
        self.generatingAnswerFile()
        params = getInstallParams(self.ut.setup.rpmVer, self.c)
        self.ut.fillAnswerFile(**params)
        self.ut(answer_file='host:'+self.c['answer_file'])
        self.ut.testInstallation()

    @istest
    def TCMS_4657_111385_RunCleanUpUtilityBeforeRhevmSetup(self):
        # 1. Run rhevm-cleanup utility
        from rhevm_utils import cleanup
        cl = cleanup.CleanUpUtility(self.ut.setup)
        cl()
        # Expect: rhevm-cleanup utility is running.
        # 2. Ensure that: db no longer exists for user rhevm, both files under: /etc/pki/rhevm deleted, rhevm-slimmed profile successfully removed (/var/lib/jbossas/server/rhevm-slimmed), and jbossas service is down
        # Expect: Getting out print of: "Cleanup process succeeded".
        # 3. Ensure that you are getting the right message printed on screen.
        # TODO: check message printed on screen
        # Expect: DB , files , rhevm-slimmed profile successfully removed, and jbossas service is down.
        jboss = self.ut.getVar('JBOSS_SERVICE')
        self.assertFalse(self.ut.setup.isServiceRunning(jboss))
        cl.autoTest()
        # 4. Go to cleanup.log file under: /var/log/rhevm/cleanup.log , and check: spelling check, logs are clearly.
        # Expect: Logs written correctly, and clearly to the user.
        # TODO: check message in log
        # 5. Run rhevm-setup and ensure rhevm installation process finished successfully.
        # Expect: Installation process finished successfully.
        self.installSetup()

