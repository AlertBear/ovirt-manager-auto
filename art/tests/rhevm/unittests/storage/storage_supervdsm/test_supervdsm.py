"""
Test supervdsm
Make sure to run this test with "remove_packages"  plugin to test the
installation of supervdsm when adding the host to the Data Center
"""
import logging
import config
import time
from art.unittest_lib import StorageTest as TestCase
from nose.tools import istest

from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import storagedomains as \
    ll_storagedomains

from art.rhevm_api.utils import test_utils
from art.test_handler.tools import tcms

from utilities.machine import LINUX, Machine

logger = logging.getLogger(__name__)

SUPERVDSM_LOG = "/var/log/vdsm/supervdsm.log"
VDSM_LOG = "/var/log/vdsm/vdsm.log"
SVDSM_LOCK = "/var/run/vdsm/svdsm.sock"
SUPERVDSMD = "supervdsmd"
VDSMD = "vdsmd"

HW_INFO_COMMAND = ["vdsClient", "-s", "0", "getVdsHardwareInfo"]
SLEEP_SERVICE = 10

# Error messages
ERROR_EXEC_SERVICE_ACTION = "Failed to execute %s on service %s"
ERROR_SERVICE_NOT_UP = "Service %s is not running"
ERROR_SERVICE_UP = "Service %s is running"
ERROR_HW_OUTPUT = "Cannot get HW Info, output:\n%s"
FILE_DOES_NOT_EXIST = "File %s does not exist"


def getSupervdsmPid(machine):
    return machine.getPidByName("supervdsmServer")[1][0]["ProcessId"]


def getVdsmPid(machine):
    return machine.getPidByName("vdsm")[1][0]["ProcessId"]


def isVdsmRunning(machine):
    """
    Make sure is running checking the process and the System Init status
    """
    try:
        getVdsmPid(machine)
        return machine.isServiceRunning(VDSMD)
    except IndexError:
        return False


def isSupervdsmRunning(machine):
    """
    Make sure is running checking the process and the System Init status
    """
    try:
        getSupervdsmPid(machine)
        return machine.isServiceRunning(SUPERVDSMD)
    except IndexError:
        return False


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE, basename=config.BASENAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    ll_storagedomains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)


class SuperVDSMTestBase(TestCase):
    """
    Base test for SuperVDSM
    """

    def setUp(self, startvdsm=True):
        # If there's a problem with vdsm the host switches between
        # non_operational - non_responsive status
        if not hosts.isHostUp(True, config.FIRST_HOST):
            logger.error("Host %s was down unexpectedly."
                         "Starting it up" % config.FIRST_HOST)
            self.assertTrue(hosts.activateHost(True, config.FIRST_HOST),
                            "Host %s was not activated" % config.FIRST_HOST)
        self.machine = Machine(
            config.FIRST_HOST, "root",
            config.FIRST_HOST_PASSWORD).util(LINUX)
        self.machine.enableServiceSupport()


class TestCase289230(SuperVDSMTestBase):
    """
    supervdsm test case, sanity
    https://tcms.engineering.redhat.com/case/289230/?from_plan=10030
    """
    __test__ = True
    tcms_plan_id = '10030'
    tcms_test_case = '289230'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def supervdsm_sanity(self):
        """
        Test basic funtionality is running after host is installed
        """
        logger.info("Make sure services are running after host is added "
                    "to rhevm in the setup Class")
        self.assertTrue(isVdsmRunning(self.machine), "VDSM is not running")
        self.assertTrue(isSupervdsmRunning(self.machine),
                        "VDSM is not running")

        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        self.assertTrue(success, ERROR_HW_OUTPUT % output)

        logger.info("Make sure log files exists")
        self.assertTrue(
            self.machine.isFileExists(SUPERVDSM_LOG),
            FILE_DOES_NOT_EXIST % SUPERVDSM_LOG)
        self.assertTrue(
            self.machine.isFileExists(VDSM_LOG),
            FILE_DOES_NOT_EXIST % VDSM_LOG)


class TestCase289539(SuperVDSMTestBase):
    """
    supervdsm test case, command options
    https://tcms.engineering.redhat.com/case/289539/?from_plan=10030
    """
    __test__ = True
    tcms_plan_id = '10030'
    tcms_test_case = '289539'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def command_options_test(self):
        """
        Test command options
        """
        def vdsm_is_running(function):
            try:
                pid = getVdsmPid(self.machine)
                value = function()
                if pid != getVdsmPid(self.machine):
                    self.fail("VDSM changed during supervdsm restart")
            except IndexError, ex:
                self.fail("Couldn't find vdsm PID")

            return value

        def runSystemInitSupervdsmd(cmd):
            command = ["/etc/init.d/supervdsmd", cmd]
            try:
                pid = getSupervdsmPid(self.machine)
                success, output = self.machine.runCmd(command)
                if not success or pid == getSupervdsmPid(self.machine):
                    logger.error("Executed %s, output: %s" % (command, output))
                    return False
                return True
            except IndexError:
                self.fail("Couldn't find supervdsm PID")

        logger.info("Stopping supervdsm")
        self.assertTrue(
            vdsm_is_running(
                lambda: self.machine.stopService(SUPERVDSMD)
            ), ERROR_EXEC_SERVICE_ACTION % ("stop", "supervdsm")
        )
        logger.info("Starting supervdsm")
        self.assertTrue(
            vdsm_is_running(
                lambda: self.machine.startService(SUPERVDSMD)
            ), ERROR_EXEC_SERVICE_ACTION % ("start", "supervdsm")
        )
        restart_commands = ['restart', 'condrestart', 'force-reload',
                            'try-restart']
        for command in restart_commands:
            logger.info("Restarting supervdsm")
            self.assertTrue(
                vdsm_is_running(
                    lambda: runSystemInitSupervdsmd(command)
                ), ERROR_EXEC_SERVICE_ACTION % (command, "supervdsm")
            )


class TestCase289547(SuperVDSMTestBase):
    """
    supervdsm test case, communication between supervdsm and vdsm
    https://tcms.engineering.redhat.com/case/289547/?from_plan=10030
    """
    __test__ = True
    tcms_plan_id = '10030'
    tcms_test_case = '289547'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_communication(self):
        """
        Test that both services work when one is stopped
        """
        logger.info("Stopping vdsmd")
        self.assertTrue(self.machine.stopService(VDSMD),
                        "vdsm didn't stop")
        time.sleep(SLEEP_SERVICE)
        self.assertTrue(isSupervdsmRunning(self.machine),
                        ERROR_SERVICE_NOT_UP % "supervdsm")
        logger.info("Starting vdsmd")
        self.assertTrue(self.machine.startService(VDSMD),
                        "vdsm didn't start")
        # After restart vdsm wait for host to be up
        self.assertTrue(hosts.waitForHostsStates(
            True, config.FIRST_HOST, states='up', timeout=60),
            "Host never activated after vdsm restarted.")
        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        self.assertTrue(success, ERROR_HW_OUTPUT % output)

        logger.info("Stopping supervdsmd")
        self.assertTrue(self.machine.stopService(SUPERVDSMD),
                        "Supervdsm didn't stop")
        time.sleep(SLEEP_SERVICE)
        self.assertTrue(isVdsmRunning(self.machine),
                        ERROR_SERVICE_NOT_UP % "vdsm")
        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        self.assertFalse(success,
                         "Get HW Info is suppose to fail:\n%s" % output)
        logger.info("Starting supervdsmd")
        self.assertTrue(self.machine.startService(SUPERVDSMD),
                        "Supervdsm didn't start")
        time.sleep(SLEEP_SERVICE)
        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        self.assertTrue(success, ERROR_HW_OUTPUT % output)


class TestCase289565(SuperVDSMTestBase):
    """
    supervdsm test case, supervdsm stress test
    https://tcms.engineering.redhat.com/case/289565/?from_plan=10030
    """
    __test__ = True
    tcms_plan_id = '10030'
    tcms_test_case = '289565'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def supervdsm_stress_test(self):
        """
        supervdsm stress tests
        """
        N = 1000
        # is much faster run it with one ssh session
        cmd = "for i in `seq 0 %(iter)d`; do vdsClient -s 0 " \
            "getVdsHardwareInfo >& /dev/null; if [ $? -ne 0 ];" \
            "then exit -1; fi; done;" % {'iter': N}

        logger.info("Executing vdsClient get HW Info for %d times" % N)
        # ~ 0.3 sec per execution
        success, output = self.machine.runCmd(cmd.split(' '), timeout=N*0.3)
        self.assertTrue(
            success,
            "Couldn't execute %(iter)d times the command. %(output)s:" % {
                "iter": N,
                "output": output,
            }
        )


class TestCase293152(SuperVDSMTestBase):
    """
    deleting supervdsm log and changing log file permissions
    https://tcms.engineering.redhat.com/case/293152/?from_plan=10030
    """
    __test__ = True
    tcms_plan_id = '10030'
    tcms_test_case = '293152'

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def change_supervdsm_log(self):
        """
        change permissions and delete supervdsm log
        """
        logger.info("Removing supervdsm log file to test recovery")
        self.assertTrue(self.machine.removeFile(SUPERVDSM_LOG),
                        "Error removing %s file" % SUPERVDSM_LOG)
        self.assertTrue(isSupervdsmRunning(self.machine),
                        ERROR_SERVICE_NOT_UP % "supervdsm")
        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        self.assertTrue(
            success, "Supervdsm didn't recover from removing log file")
        self.assertTrue(self.machine.isFileExists(SUPERVDSM_LOG),
                        "%s should be created" % SUPERVDSM_LOG)

        logger.info("Changing supervdsm log file permissions to test recovery")
        success, output = self.machine.runCmd(["chmod", "0000", SUPERVDSM_LOG])
        self.assertTrue(
            success, "Error changing %s permissions %s" % (
                SUPERVDSM_LOG, output
            )
        )
        self.assertTrue(isSupervdsmRunning(self.machine),
                        ERROR_SERVICE_NOT_UP % "supervdsm")
        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        self.assertTrue(
            success, "Supervdsm didn't recover from changing "
            "log file's permissions")

    def tearDown(self):
        """
        Make sure to restore supervdsm log file
        """
        self.machine.stopService(SUPERVDSMD)
        self.machine.runCmd(["touch", SUPERVDSM_LOG])
        self.machine.runCmd(["chmod", "0644", SUPERVDSM_LOG])
        self.machine.runCmd(["chown", "vdsm:kvm", SUPERVDSM_LOG])
        self.machine.startService(SUPERVDSMD)
