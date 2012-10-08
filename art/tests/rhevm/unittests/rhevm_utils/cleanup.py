
# Usage: rhevm-cleanup [options]
#
# Options:
#   -h, --help            show this help message and exit
#   -u, --unattended      unattended cleanup
#   -d, --dont-drop-db    Don't drop database
#   -c, --dont-remove-ca  Don't remove CA
#   -s, --dont-remove-profile
#                         Don't remove rhevm-slimmed JBoss profile
#   -l, --dont-unlink-ear # FOR RHEVM >=3.1

__test__ = False

import os
import re
from rhevm_utils.base import Utility, logger, RHEVMUtilsTestCase, istest
from rhevm_utils import errors

NAME = 'cleanup'

OPT_HELP = set(('h', 'help'))
OPT_UNATENDED = set(('u', 'unattended'))
OPT_DONT_DROP_DB = set(('d', 'dont-drop-db'))
OPT_DONT_REMOVE_CA = set(('c', 'dont-remove-ca'))
OPT_DONT_REMOVE_PROFILE = set(('s', 'dont-remove-profile', \
                                'l', 'dont-unlink-ear'))

TIMEOUT = 10 * 60

# ( pattern, exeption, names of params, (sub errors, .. ) )
ERROR_PATTERNS = ()

class CleanUpUtility(Utility):
    """
    Encapsulation of rhevm-cleanup utility
    """
    def __init__(self, *args, **kwargs):
        super(CleanUpUtility, self).__init__(*args, **kwargs)
        self.cleanTimeout = kwargs.get('timeout', TIMEOUT)
        self.kwargs = None

    def __call__(self, *args, **kwargs):
        self.kwargs = self.clearParams(kwargs)

        if OPT_HELP not in self.kwargs and OPT_UNATENDED not in self.kwargs:
            logger.warn("adding --unattended option to avoid prompt")
            self.kwargs['unattended'] = None

        cmd = self.createCommand(NAME, self.kwargs)

        self.execute(NAME, cmd, timeout=self.cleanTimeout)

        #self.autoTest()

    # ====== TESTS ========

    def autoTest(self):
        if OPT_HELP in self.kwargs:
            self.testReturnCode()
            return
        self.testReturnCode()
        self.testCleanup()

    def testCleanup(self):
        db_exists = self.isDBExists()
        if OPT_DONT_DROP_DB not in self.kwargs and db_exists:
            raise errors.DBExistsError(self.setup.dbname)
        if OPT_DONT_DROP_DB in self.kwargs and not db_exists:
            raise errors.DBDoesntExistError(self.setup.dbname)

        with self.setup.ssh as ssh:

            fh = ssh.getFileHandler(timeout=self.setup.connectionTimeout)

            for name in ('.truststore', '.keystore'):
                path = os.path.join(self.getVar('CA_PATH'), name)
                caExists = fh.exists(path) and not fh.isDir(path)
                if OPT_DONT_REMOVE_CA in self.kwargs and not caExists:
                    raise errors.CADoesntExistError(self.setup.host, path)
                if OPT_DONT_REMOVE_CA not in self.kwargs and caExists:
                    raise errors.CAExistsError(self.setup.host, path)

            # NOTE: parameter -s disappear
            #profPath = self.getVar('JBOSS_PROFILE_PATH')
            #profExists = fh.exists(profPath) and fh.isDir(profPath)
            #if OPT_DONT_REMOVE_PROFILE in self.kwargs and not profExists:
            #    raise errors.ProfileDoesntExistError(self.setup.host, profPath)
            #if OPT_DONT_REMOVE_PROFILE not in self.kwargs and profExists:
            #    raise errors.ProfileExistsError(self.setup.host, profPath)

            if OPT_DONT_REMOVE_CA not in self.kwargs:
                pass #TODO: need to verify backup
            if OPT_DONT_DROP_DB not in self.kwargs:
                pass #todo: need to verify backup
            #if OPT_DONT_REMOVE_PROFILE not in self.kwargs:
            #    pass #todo: need to verify backup

            if self.isJbossRunning():
                raise errors.JbossIsStillRunning()

#### UNITTESTS #####


_multiprocess_can_split_ = True

class CleanUpTestCase(RHEVMUtilsTestCase):

    __test__ = True
    utility = NAME
    utility_class = CleanUpUtility
    _multiprocess_can_split_ = True

    @istest
    def cleanUp(self):
        self.ut()
        self.ut.autoTest()

    @istest
    def cleanUpDontRemoveCA(self):
        self.ut(c=None)
        self.ut.autoTest()

    @istest
    def cleanUpDontRemoveDB(self):
        self.ut(d=None)
        import time
        self.ut.autoTest()

#    @istest
#    def cleanUpDontRemoveProfile(self):
#        #v = self.ut.version
#        #if v[0] > 3 or (v[0] == 3 and v[1] >= 1):
#        #    self.ut(l=None)
#        #else:
#        #    self.ut(s=None)
#        self.ut(s=None)
#        self.ut.autoTest()

    @istest
    def cleanUpDontRemoveAnyThing(self):
        #v = self.ut.version
        #if v[0] > 3 or (v[0] == 3 and v[1] >= 1):
        #    self.ut(d=None, c=None, l=None)
        #else:
        #    self.ut(d=None, c=None, s=None)
        self.ut(d=None, c=None)#, s=None)
        self.ut.autoTest()

    # TCMS testcases function names notation:
    # testTCMS_<plan_id>_<testcase_id>_<short_name>

    @istest
    def TCMS_4657_112243_StopRhevmNotifierdService(self):
        # 1. Stop notifierd service by running: service notifierd stop
        service = self.ut.getVar('NOTIFIERD_SERVICE')
        self.ut.setup.stopService(service)
        # Expect: Service is down
        self.assertFalse(self.ut.setup.isServiceRunning(service))
        # 2. Run rhevm-cleanup utility
        self.ut()
        # Expect: 2. Rhevm-cleanup utility process successfull.
        self.ut.testCleanup()

    @istest
    def TCMS_4657_112242_RunCleanUpUtilityWhenFileIsOpen(self):
        script = "import os\n"\
                 "import time\n"\
                 "try:\n"\
                 "    fd = os.open('%s', os.O_RDONLY)\n"\
                 "    time.sleep(3600)\n"\
                 "    os.close(fd)\n"\
                 "except KeyboardInterrupt:\n"\
                 "    os.close(fd)\n"
        def openFileAndCheckItFailed(filename, data):
            data = data % filename
            # 1. Open <filename> file using python
            with self.ut.setup.runCmdOnBg(['python'], data=data) as pid:
                # 2. Run rhevm-cleanup utility
                self.ut()
                # Expect: 2. Rhevm-cleanup utility process failed.
                # TODO: I think we can be more specific here, what failed and, verify damages
                self.assertRaises(errors.ReturnCodeError, self.ut.testReturnCode)
                self.assertTrue(self.ut.setup.isProcessExists(pid))

        # run testcase for jbossas related files
        openFileAndCheckItFailed(self.ut.getVar('JBOSS_PROFILE_PATH'), script)
        # run testcase for certs related files
        openFileAndCheckItFailed(self.ut.getVar('CA_PATH'), script)

    @istest
    def TCMS_4657_112241_PostgresqlServiceIsDown(self):
        # 1. Stop posgresql service by running the command: service postgresql stop
        self.ut.setup.stopService('postgresql')
        # Expect: Service is down
        self.assertFalse(self.ut.setup.isServiceRunning('posgresql'))
        # 2. Run rhevm-cleanup utility
        self.ut()
        # Expect: 2. Rhevm-cleanup utility process successfull.
        self.ut.testCleanup()

    @istest
    def TCMS_4657_112240_MissingDataBase(self):
        # 1. Drop db by running the command; dropdb rhevm -U postgres
        self.ut.stopJboss()
        rc, out = self.ut.setup.runCmd(['dropdb', self.ut.setup.dbname, \
                '-U', self.ut.setup.dbuser])
        logger.info("remove DB: %s, %s", rc, out)
        self.assertTrue(rc)
        # Expect: No longer db exist for rhevm user
        self.assertFalse(self.ut.isDBExists())
        self.ut.startJboss()
        # 2. Run rhevm-cleanup utility
        self.ut()
        # Expect: 2. Rhevm-cleanup utility process successfull.
        self.ut.testCleanup()

    @istest
    def TCMS_4657_111386_RunCleanUpUtilityWhileConnectionToTheDBIsOpen(self):
        # 1. Open connection to the rhevm DB using PGAdmin3
        script = "import subprocess as s\n"\
                "import time\n"\
                "p = s.Popen(['psql', '%s', '%s'], stdin=s.PIPE)\n"\
                "try:\n"\
                "    time.sleep(3600)\n"\
                "except KeyboardInterrupt:\n"\
                "    p.terminate()\n" % (self.ut.setup.dbname, self.ut.setup.dbuser)
        with self.ut.setup.runCmdOnBg(['python'], data=script) as pid:
            # Expect: Connection to the DB is open.
            # 2. Run rhevm-cleanup utility
            self.ut()
            # Expect: rhevm-cleanup utility is running.
        # 3. Ensure that: db no longer exists for user rhevm, both files under: /etc/pki/rhevm deleted, rhevm-slimmed profile successfully removed (/var/lib/jbossas/server/rhevm-slimmed), and jbossas service is down
        self.ut.autoTest()
        # 4. Ensure that you are getting the right message printed on screen.
        # TODO: check message on screen
        # Expect: Getting out print of: "Cleanup process succeeded".
        # 5. Go to cleanup.log file under: /var/log/rhevm/cleanup.log , and check: spelling check, logs are clearly.
        # TODO: check messagess in log
        # Expect: Logs written correctly, and clearly to the user.
        # 6. Run rhevm-setup and ensure rhevm installation process finished successfully.
        self.ut.setup.install()
        # Expect: Installation process finished successfully.


    @istest
    def TCMS_4657_111384_RunningRhevmSetupWhenRHEVMIsAlreadyInstalled(self):
        # 1. Run rhevm-cleanup utility
        self.ut()
        self.ut.autoTest()
        # TODO: check logs
        self.ut.setup.install()


