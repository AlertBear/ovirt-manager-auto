"""
    rhevm cleanup module
"""

from rhevm_utils.base import RHEVMUtilsTestCase, istest, config
from utilities.rhevm_tools.cleanup import CleanUpUtility
from utilities.rhevm_tools import errors

NAME = 'cleanup'

_multiprocess_can_split_ = True


class CleanUpTestCase(RHEVMUtilsTestCase):
    """
        rhevm cleanup test cases
    """

    __test__ = True
    utility = NAME
    utility_class = CleanUpUtility
    _multiprocess_can_split_ = True

    @istest
    def cleanUp(self):
        """ clean_Up """
        self.ut()
        self.ut.autoTest()

    @istest
    def cleanUpDontRemoveCA(self):
        """ clean_Up_Dont_Remove_CA """
        self.ut(c=None)
        self.ut.autoTest()

    @istest
    def cleanUpDontRemoveDB(self):
        """ clean_Up_Dont_Remove_DB """
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
        """ clean_Up_Dont_Remove_Any_Thing """
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
        """ TCMS_4657_112243_Stop_Rhevm_Notifierd_Service """
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
    def TCMS_4657_112241_PostgresqlServiceIsDown(self):
        """ TCMS_4657_112241_Postgresql_Service_Is_Down """
        # 1. Stop posgresql service by running the command: service postgresql stop
        self.ut.setup.stopService('postgresql')
        # Expect: Service is down
        self.assertFalse(self.ut.setup.isServiceRunning('posgresql'))
        # 2. Run rhevm-cleanup utility
        self.ut()
        # Expect: Rhevm-cleanup utility process fail.
        self.assertRaises(errors.ReturnCodeError, self.ut.testReturnCode)

    @istest
    def TCMS_4657_112240_MissingDataBase(self):
        """ TCMS_4657_112240_Missing_Data_Base """
        # 1. Drop db by running the command; dropdb rhevm -U postgres
        self.ut.stopJboss()
        rc = self.ut.setup.dropDb()
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
        """ TCMS_4657_111386_Run_Clean_Up_Utility_While_Connection_To_The_DB_Is_Open """
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
        self.ut.setup.install(conf=config)
        # Expect: Installation process finished successfully.


    @istest
    def TCMS_4657_111384_RunningRhevmSetupWhenRHEVMIsAlreadyInstalled(self):
        """ TCMS_4657_111384_Running_Rhevm_Setup_When_RHEVM_Is_Already_Installed """
        # 1. Run rhevm-cleanup utility
        self.ut()
        self.ut.autoTest()
        # TODO: check logs
        self.ut.setup.install(conf=config)


