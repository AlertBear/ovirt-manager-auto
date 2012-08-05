import re
import sys
import types
import logging
import traceback
import os.path

import utilities.utils as utils
import utilities.errors as errors
from utilities.enum import Enum
from utilities.cache import Cache
from utilities.event import ReturnableEvent
from utilities.emailTool import EmailTool

# NOTE: do not remove the imports below since
# they are needed by __constructWrapperObject method.
from tcmsEntryWrapper import TestPlanWrapper
from tcmsEntryWrapper import TestCaseWrapper
from tcmsEntryWrapper import UserInfoWrapper
from tcmsEntryWrapper import ProductCategoryWrapper
from tcmsEntryWrapper import ProductVersionWrapper
from tcmsEntryWrapper import BuildWrapper
from customNitrate import eTcmsEntity
from customNitrate import CustomNitrateKerbXmlrpc, UnsupportedEntityTypeError

# Valid statuses of TestCaseRun
eCaseRunStatus = Enum(  PASS=2,
                        FAIL=3)

# Need to finalize a TestRun at the end of the test
eTestRunStatus = Enum(FINISHED=1)

# Translation map for TCMS entity types
TCMS_ENTITY_MAP = { eTcmsEntity.TestCase: 'cases',
                      eTcmsEntity.ProductVersion: 'versions',
                      eTcmsEntity.ProductCategory: 'categories',
                      eTcmsEntity.Build: 'builds'}

# Pattern for iteration status recognition
SUCCESS = re.compile("^[Pp]ass|1|^[Tt]rue|^[Ss]ucc")

# BZ info string
BZ_INFO = "'case_run_id': '{0}', \
            'bug_id': '{1}', \
            'bug_system_id': '1', \
            'summary': 'Bug info', \
            'description': 'Bug info'"

# List of atomic tests. TCMS TestCase creation is allowed for tests of these types
ATOMIC_TEST_TYPES = ("functionality", "benchmark")


class TcmsObjectCreationError(errors.GeneralException):
    message = "failed to create TcmsAgent object"


class CaseStepsCache(Cache):
    """
        This class represents cache for iterations (steps) of a single test case.
        We need such functionality for supporting a single TCMS TestCase
        which has multiple steps in its ATOM implementation.
    """
    def __init__(self):
        """
            C'tor.
            Author: mbenenso
            Parameters: none
            Return: none
        """
        super(CaseStepsCache, self).__init__()
        self.createCaseRunEvent = ReturnableEvent()
        self.stepsResults = []
        self.caseId = []

    def _add(self, key, value):
        """
            Cache details of a single case step and store step result.
            Author: mbenenso
            Parameters:
             * key - step number
             * value - step details dictionary
            Return: none
        """
        super(CaseStepsCache, self).add(key, value)
        self.stepsResults.append(value.get('status', False))

    def _clear(self):
        """
            Clear the cache and the list of steps results.
            Author: mbenenso
            Parameters: none
            Return: none
        """
        super(CaseStepsCache, self).clear()
        self.stepsResults[:] = []

    def _isCaseChanged(self, ids):
        """
            Check if TestCase ID has been changed.
            Author: mbenenso
            Parameters:
            * ids - a list with TestCase ID(s)
            Return: True on change, False otherwise
        """
        return bool(filter(lambda id: id not in self.caseId, ids))

    def add(self, **kwargs):
        """
            Deal with a single case step details: store in cache and create
            new TCMS TestCaseRun on caseId change.
            Author: mbenenso
            Parameters:
            * status - the status of a step
            * name - the name of a step
            * index - the step number (iteration number)
            * caseId - a list with TestCase ID(s)
            * notes - case step notes
            Return: list with TestCaseRun ID(s) on TestCase change, an empty list otherwise
        """
        caseRunId = []
        if self._isCaseChanged(kwargs['caseId']):
            # New TestCase(s) received, handle the prevoius one first
            if not self.isEmpty:
                # Raise an event (Create TestCaseRun for previous TestCase and its steps)
                caseRunId = self.onCaseChange()
            self.caseId = list(kwargs['caseId'])

        # Store a case step in the cache
        self._add(kwargs['index'], kwargs)

        return caseRunId

    def onCaseChange(self):
        """
            Handle TestCase change event. Prepare notes string from the TestCase
            steps details and create a new TestCaseRun(s) by calling an appropriate
            subscriber's method.
            Author: mbenenso
            Parameters: none
            Return: a list of TestCaseRun ID(s) on success, an empty list otherwise
        """
        runs = []
        if not self.isEmpty:
            notes = ''
            notesTemplate = r"{0}) Step: {1}\nStatus: {2}\nStep params: {3}\nATOM iter number: {4}\n--------\n"
            # Determine TestCase result using steps results
            caseResult = eCaseRunStatus.PASS if all(self.stepsResults) else eCaseRunStatus.FAIL

            # Create notes string from the cache
            for ind, value in enumerate(sorted(self.getAll.iteritems()), 1):
                notes += notesTemplate.format(ind,
                                            value[1].get('name'),
                                            "Pass" if value[1].get('status') else "Fail",
                                            value[1].get('notes'),
                                            value[0]
                                            )

            # Create new TestCaseRun for every stored TestCase
            for id in self.caseId:
                runs.append(self.createCaseRunEvent(id, str(caseResult), notes))

            # Clear the steps cache
            self._clear()

        return runs


class TcmsAgent(object):
    """
        This class is used to translate and store the data (like tests execution details
        and results) from ATOM testing system of RHEV QE automation team
        into TCMS data base. It uses Nitrate xmlrpc service and API.
    """
    def __init__(self, userName, conf=None):
        """
            C'tor.
            Author: mbenenso
            Parameters:
            * userName - the name of the user
            * conf - dict with configuration
            Return: none
            Throws: TcmsObjectCreationError
        """
        self._nitrateApi = self.user = self.testRunId = None
        self.productVersionId = self.productCategoryId = self.testPlanTypeId = ''
        self.testName = self.productId = self.buildId = ''
        self.headerNames = []
        self.atomicTest = True
        self.aggregation = False
        self.__cache = Cache()
        self._runs = {}

        # Read configuration file
        self.confFile = re.sub('.py[c]*$', '.cfg', __file__)
        agentParams = conf or self._getParams(self.confFile)
        if not agentParams:
            raise TcmsObjectCreationError("agent's configuration file is empty %s" % self.confFile)

        # Configure logger
        if utils.parseStringToBoolean(agentParams['configure_logger']):
            self._configureLogger(agentParams['log_file_location'])
        # TODO: revert after formatter change
        self.logger = logging.getLogger("tcmsAgent-{0}".format(userName))

        self.placeholderTypeId = agentParams.get('placeholder_plan_type')
        self.testRunName = agentParams.get('test_run_name_template')

        # Store TCMS url as a member for deserialization needs
        self.tcmsUrl = agentParams.get('tcms_url', '')
        # Store url of ATOM's report page to link a TestRun later
        self.atomTestLink = agentParams.get('atom_test_link')

        # Send (or not) an email regarding TestRun result at the end of the test
        self.sendMail = utils.parseStringToBoolean(agentParams['send_result_email'])
        self.sender = agentParams['default_sender']

        try:
            # Initialize Nitrate API object
            username = userName + agentParams['redhat_email_extension']
            pathToKeyTab = os.path.join(agentParams['keytab_files_location'],
                                        userName + agentParams['keytab_file_extension'])
            self._nitrateApi = CustomNitrateKerbXmlrpc(self.tcmsUrl, username, pathToKeyTab)
        except Exception as err:
            self.logger.error(traceback.format_exc())
            raise TcmsObjectCreationError("%s" % str(err))

    def _getParams(self, confFilePath):
        """
            Read configuration file.
            Author: mbenenso
            Parameters:
            * confFilePath - path to configuration file
            Return: parameters dictionary on success, an empty dict otherwise
            Throws: TcmsObjectCreationError:
        """
        try:
            return utils.readConfFile(confFilePath)
        except Exception as err:
            raise TcmsObjectCreationError(str(err))

    def __getstate__(self):
        """
            Prepare the class object for serialization process.
            Author: mbenenso
            Parameters: none
            Return: a dictionary with the namespace content of the object
        """
        # Remove unserializable members of the instance
        del self.__dict__['logger']
        del self.__dict__['_nitrateApi']
        return self.__dict__

    def __setstate__(self, state):
        """
            Restore the class object after deserialization process.
            Author: mbenenso
            Parameters:
            * state - a dictionary with the namespace content of the object
            Return: dictionary with the namespace content of the object
        """
        if "logger" not in state:
            self.logger = logging.getLogger("tcmsAgent")
        # Do not perform additional login to TCMS
        if "_nitrateApi" not in state:
            self._nitrateApi = CustomNitrateKerbXmlrpc(state['tcmsUrl'])
        self.__dict__.update(state)

    @property
    def connected(self):
        return self._nitrateApi is not None and self._nitrateApi.isConnected()

    @property
    def initialized(self):
        return self.testRunId is not None

    @property
    def cache(self):
        return self.__cache

    def _runCommand(self, verb, *args):
        return self._nitrateApi.runCommand(verb, *args)

    def _configureLogger(self, logFileLocation='/tmp/tcmsAgent.log'):
        """
            Configure the logger for the instance of the class.
            Author: mbenenso
            Parameters:
            * logFileLocation - location of a log file
            Return: none
        """
        assert not "TODO: this should be changed", "TODO: this should be changed"
        logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s | %(name)s | %(levelname)s - %(message)s',
                        datefmt='%d-%m-%Y %H:%M:%S',
                        filename=logFileLocation,
                        filemode='a+')

    def logout(self):
        """
            Delete TCMS session information and the cache.
            Author: mbenenso
            Parameters: none
            Return: none
        """
        if self.connected:
            self._nitrateApi.do_command("Auth.logout")
            del self._nitrateApi
            self._nitrateApi = None

        if self.initialized:
            del self.__cache
            self.__cache = self.testRunId = None

    def _fromCache(self, category, key, property=''):
        """
            Return cached TCMS entity (or specified property) by its name/id.
            Author: mbenenso
            Parameters:
            * category - cache category
            * key - entity name/id
            * property - entity's property to return (optional)
            Return: wrapped TCMS cached entity (or its property) if it found in cache,
                    an empty string otherwise
        """
        if self.cache.hasKey(category):
            if self.cache.get(category).hasKey(key):
                if not property:
                    # Return cached TCMS entity
                    return self.cache.get(category).get(key)

                try:
                    # Return a specific property of cached entity
                    return getattr(self.cache.get(category).get(key), property)
                except AttributeError:
                    msg = "cached entity has no such attribute: '{0}', key: '{1}'"
                    self.logger.error(msg.format(property, key))
            else:
                msg = "cache category {0} has no such key: '{1}'"
                self.logger.warning(msg.format(eTcmsEntity.toString(category), key))
        else:
            msg = "cache category {0} doesn't exist"
            self.logger.warning(msg.format(eTcmsEntity.toString(category)))

        return ''

    def iterationInfo(self, **kwargs):
        """
            Handle ATOM's single iteration.
            Author: mbenenso
            Parameters:
            * info_line - iteration details
            * iter_number - iteration number
            * iter_status - iteration status
            * test_case_name - the name of a case (optional)
            * sub_test_name - the name of a sub-test (optional)
            * test_case_id - an ID of a TestCase in the TCMS database (optional)
            * bz_info - an ID of a bug (which is attached to the TestCase) in the Bugzilla system (optional)
            Return: none
        """
        ERR_MSG = "failed to handle iteration info - {0}"
        if self.initialized:
            if utils.validDict(kwargs, 'sub_test_name', 'test_case_name', 'bz_info', 'test_case_id'):
                self.logger.debug("iteration info details: %s" % kwargs)
                try:
                    self.__handleTestIteration(kwargs)
                except:
                    self.logger.error(ERR_MSG.format("%s" % traceback.format_exc()))
            else:
                self.logger.error(ERR_MSG.format("wrong test iteration parameters dictionary"))
        else:
            self.logger.error(ERR_MSG.format("the agent has no cache data"))

    def _setBZInfo(self, caseRunId, bzInfo):
        """
            Attach Bugzilla bug ID to a TestCaseRun.
            Author: mbenenso
            Parameters:
            * caseRunId - an ID of a TestCaseRun
            * bzInfo - an ID of a bug in the Bugzilla database
            Return: none
        """
        if not self._runCommand("TestCaseRun.attach_bug",
                                self._toDictionary(BZ_INFO.format(caseRunId, bzInfo))):
            msg = "failed to attach BZ info with ID {0} to TestCaseRun with ID {1}"
            self.logger.error(msg.format(bzInfo, caseRunId))

    def testEnd(self):
        """
            Finalize the test run. Write the last test case info for non atomic tests.
            Updates the status of a TestRun(s) to finished and perform logout.
            Author: mbenenso
            Parameters: none
            Return: none
        """
        if self.initialized:
            if not self.atomicTest:
                # Write the last TestCase
                self.caseStepsCache.onCaseChange()
            # Finalize TestRun(s)
            for run in self._runs.values():
                self._update(eTcmsEntity.TestRun, run[0],
                            self._toDictionary(self._toStringWithOptions("status", str(eTestRunStatus.FINISHED))))

            if self.sendMail:
                # Send results email to the tester
                self._sendEmail(self.testRunResult)
        self.logout()

    @property
    def testRunResult(self):
        """
            Determine test run result based on the results of test case runs.
            Author: mbenenso
            Parameters: none
            Return: PASS string if all test case runs passed, FAIL string otherwise
        """
        passedCaseRuns = []
        if self.testRunResultsList:
            passedCaseRuns = filter(lambda result: eCaseRunStatus.parse(result) == eCaseRunStatus.PASS, self.testRunResultsList)
            if len(passedCaseRuns) == len(self.testRunResultsList):
                return "PASS"
        return "FAIL"

    def _sendEmail(self, result):
        """
            Send results email to the tester.
            Author: mbenenso
            Parameters:
            * result - test result
            Return: none
        """
        try:
            emailTool = EmailTool()
            emailTool.compose(("TestRun #{0} from TestPlan #{1} has finished " +
                            "with [{2}] result.\n\n" +
                            "TestPlan summary: {3}\n" +
                            "TestRun summary: {4}\n\n" +
                            "Link to the TestRun: {5}\n\n" +
                            "Tester: {6}\n\n" +
                            "Product: {7}\n" +
                            "Version: {8}\n" +
                            "Build: {9}").format(self.testRunId,
                                            self.planId,
                                            result,
                                            self.testName,
                                            self.testRunName.format(self.testName),
                                            self.tcmsUrl.replace("xmlrpc", "run") + self.testRunId,
                                            self.user.name,
                                            self.product_name,
                                            self.product_version,
                                            self.build_name),
                            ("[TCMS] Run {0} from plan {1} has " +
                            "finished [{2}]").format(self.testRunId,
                                                self.planId,
                                                result))
            emailTool.setRecipients(self.sender, self.user.name)
            emailTool.send()
        except Exception as err:
            self.logger.error("failed to send email to %s: %s" % (self.user.name, str(err)))

    def _toDictionary(self, query):
        """
            Convert string to dictionary wrapper.
            Author: mbenenso
            Parameters:
            * query - string to convert
            Return: a dictionary
        """
        return self._nitrateApi._options_dict(query)

    def _toStringWithOptions(self, option, value):
        """
            Convert two strings into a pair wrapper.
            Author: mbenenso
            Parameters:
            * option - option string to convert
            * value - value string to convert
            Return: "'option': 'value'" on success, an empty string otherwise
        """
        return self._nitrateApi._string_option(option, value).rstrip(", ")

    def __createTcmsEntry(self, entityType, args):
        """
            Create new TCMS entry.
            Author: mbenenso
            Parameters:
            * entityType - the type of the entity to create
            * args - entity arguments
            Return: True and created TCMS entity on success, False and None otherwise
        """
        try:
            entityName = self._getEntityName(entityType)
        except UnsupportedEntityTypeError:
            return False, None

        retObject = self._runCommand("{0}.create".format(entityName), args)
        if not retObject:
            self.logger.error("failed to create new TCMS entry of type '%s'" % entityName)
            return False, None

        # Store newly created TestCase in the agent's cache
        if entityType == eTcmsEntity.TestCase:
            # Wrap newly created TestCase with the appropriate wrapper class
            obj = self.__constructWrapperObject("{0}Wrapper".format(entityName), retObject[0])
            # Store the wrapped object into the agent's cache
            if not self.cache.hasKey(entityType):
                self.cache.add(entityType, Cache())
            self.cache.get(entityType).add(obj.id, obj)

        return True, retObject[0]

    def createTestCase(self, caseSummary):
        """
            Create new TCMS TestCase entry.
            Author: mbenenso
            Parameters:
            * caseSummary - test case summary
            Return: a string representation of the ID of newly crated TestCase on success,
                        an empty string otherwise
        """
        if utils.valid(caseSummary):
            query = self._toDictionary("'product': " + self.productId + ", " + \
                                "'plan': " + self.planId + ", " + \
                                "'category': " + self.productCategoryId + ", " + \
                                "'summary': " + self._nitrateApi._string_no_option(caseSummary) + ", " + \
                                "'default_tester': " + self._nitrateApi._string_no_option(self.user.name) + ", " + \
                                "'case_status': 2, " + \
                                "'priority': 1, " + \
                                "'is_automated': 1")
            rc, retObj = self.__createTcmsEntry(eTcmsEntity.TestCase, query)
            if rc:
                return str(retObj['case_id'])
        return ''

    def createTestRun(self):
        """
            Create new TCMS TestRun entry.
            Author: mbenenso
            Parameters: none
            Return: a string representation of the ID of newly crated TestRun on success, None otherwise
        """
        query = self._toDictionary("'product': " + self.productId + ", " + \
                            "'plan': " + self.planId + ", " + \
                            "'product_version': " + self.productVersionId + ", " + \
                            "'default_product_version': " + self.productVersionId + ", " + \
                            "'default_tester': " + self.user.id + ", " + \
                            "'summary': " + self._nitrateApi._string_no_option(self.testRunName.format(self.testName)) + ", " + \
                            "'manager': " + self.user.id + ", " + \
                            "'build': " + self.buildId)
        rc, retObj = self.__createTcmsEntry(eTcmsEntity.TestRun, query)
        if rc:
            return str(retObj['run_id'])
        return None

    def createTestCaseRun(self, caseId, status, notes=''):
        """
            Create new TCMS TestCaseRun entry.
            Author: mbenenso
            Parameters:
            * caseId - an ID of a TestCase
            * status - TestCase status
            * notes - TestCaseRun notes (optional)
            Return: a list with string representation of the ID of newly crated
                    TestCaseRun on success, an empty list otherwise
        """
        if utils.valid(status, caseId):
            query = self._toDictionary("'run': " + self.testRunId + ", " + \
                                "'case': " + caseId + ", " + \
                                "'notes': " + self._nitrateApi._string_no_option(notes) + ", " + \
                                "'assignee': " + self.user.id + ", " + \
                                "'case_run_status': " + status + ", " + \
                                "'build': " + self.buildId)
            rc, retObj = self.__createTcmsEntry(eTcmsEntity.TestCaseRun, query)
            if rc:
                self.testRunResultsList.append(status)
                return [str(retObj['case_run_id'])]
        return []

    def init(self, preview=False, **kwargs):
        """
            Initialize the agent and its cache. Create new TestRun for the test.
            Author: mbenenso
            Parameters:
            * preview - "read-only" mode for testing purposes (False by default)
            * test_type - the type of the test
            * test_name - the name of the test
            * build_name - the number of the build
            * product_name - the name of the tested product
            * product_version - the version of the tested product
            * product_category - the tested module of the product
            * header_names - the names of the headers for ATOM reports
            * test_plan_id - an ID of the TCMS TestPlan for the test
            * test_report_id - an ID of the test in the ATOM db (optional)
            Return: True if agent's initialization succeeded, False otherwise
        """
        if not self.connected:
            self.logger.error("no connection established to TCMS database")
        elif self.initialized:
            self.logger.warning("agent has been initialized already")
            return True
        else:
            self.logger.debug("test parameters received from ATOM agent %s" % kwargs)
            if not utils.validDict(kwargs, 'test_report_id'):
                self.logger.error("wrong initial parameters for test")
            else:
                try:
                    # Get current user details from TCMS
                    self.user = UserInfoWrapper(self._runCommand('User.get_me')[0])
                    self.logger.info("initializing the agent for user: %s" % self.user.name)
                    if self.__initAgent(kwargs):
                        if preview or self.aggregation:
                            # Preview mode (for testing purposes, allows to use the
                            # agent as "read-only") and aggregation mode both must
                            # wait for first iteration in order to fetch the "real" TestPlan ID.
                            # So in both cases we exit with True without creating TestRun.
                            self.testRunId = 'dummy'
                            return True
                        # Continue initialization process
                        if self._initTestRun():
                            return True
                except:
                    self.logger.error("%s" % traceback.format_exc())
        self.logger.error("agent's initialization has failed, unable to continue...")
        self.logout()

        return False

    def _initTestRun(self):
        """
            Initialize TestRun.
            Author: mbenenso
            Parameters: none
            Return: True if succeeded, False otherwise
        """
        # Try to fetch TestPlan ID from the cache
        if self.planId in self._runs.keys():
            self.testRunId = self._runs.get(self.planId)[0]
            return True

        # Create new TestRun for the test
        self.testRunId = self.createTestRun()
        self.logger.info("new TestRun created: '{0}'".format(str(self.testRunId)))
        if self.testRunId is not None:
            # Store created TestRun ID to re-use later in the test.
            # The list will hold results of all TestCaseRuns to determine
            # the whole TestRun status at the end of test.
            self._runs[self.planId] = (self.testRunId, [])

            if self.test_report_id:
                # Attach to the created TestRun a link to the test report in ATOM
                linkToReport = self.atomTestLink + str(self.test_report_id)
                self._update(eTcmsEntity.TestRun, self.testRunId,
                            self._toDictionary(self._toStringWithOptions("notes", linkToReport)))

            return True

        self.logger.error("failed to create new TestRun, TestPlan '{0}'".format(self.planId))
        return False

    @property
    def testRunResultsList(self):
        return self._runs.get(self.planId)[1]

    def _update(self, entity, id, query):
        """
            Update TCMS entry.
            Author: mbenenso
            Parameters:
            * entity - TCMS entity type
            * id - an ID of the entity
            * query - a query to update with
            Return: True if an update of TCMS entity succeeded, False otherwise
        """
        cmd = "{0}.update"
        try:
            entityName = self._getEntityName(entity)
        except UnsupportedEntityTypeError:
            pass
        else:
            if self._runCommand(cmd.format(entityName), id, query):
                return True
            self.logger.error("failed to update %s with ID %s" % (entityName, id))
        return False

    def __initAgent(self, testDetails):
        """
            Initialize the agent. Store all needed attributes, build the cache and
            store all vital variables as the instance members.
            Author: mbenenso
            Parameters: see init() method
            Return: True on successful initialization of agent parameters, False otherwise
        """
        # Set instance attributes
        for key, value in testDetails.iteritems():
            if key.lower() == 'header_names':
                # Prepare ATOM header names list
                self.headerNames = self._buildHeaderNamesList(value)
            else:
                setattr(self, key, str(value).lower())

        # Interrupt the initialization process if TestPlan ID is missing
        try:
            getattr(self, 'test_plan_id')
            self.planId = self.test_plan_id.strip(" ").strip(",")
        except AttributeError:
            self.logger.error("test plan ID is missing, unable to continue")
            return False

        # Get TestPlan details
        if not self._getPlan():
            return False

        self.atomicTest = self.test_type.lower() in ATOMIC_TEST_TYPES
        if not self.atomicTest:
            # Create a kind of cache for storing case steps of non-atomic test
            self.caseStepsCache = CaseStepsCache()
            # Add handler to self.caseStepsCache publisher
            self.caseStepsCache.createCaseRunEvent += self.createTestCaseRun

        # Indicates aggregation of few tests written by Manual team
        self.aggregation = str(self._fromCache(eTcmsEntity.TestPlan, self.planId, 'type_id')) == str(self.placeholderTypeId)
        self.logger.debug("aggregation mode {0}".format({True: 'enabled', False: 'disabled'}[self.aggregation]))
        # Fetch TCMS id of the tested product
        self.productId = self._fromCache(eTcmsEntity.TestPlan, self.planId, 'product_id')
        if not self.productId:
            self.logger.error("failed to fetch TCMS Product ID for the test")
            return False

        # Build cache based on tested product and current TestPlan
        for entityType in TCMS_ENTITY_MAP.keys():
            if self.aggregation and entityType == eTcmsEntity.TestCase:
                continue
            if not self.__buildCache(entityType):
                self.logger.error("failed to build cache")
                return False

        if not self.aggregation:
            self.testName = self._fromCache(eTcmsEntity.TestPlan, self.planId, 'name').title()
            self.testPlanTypeId = self._getTestPlanTypeIdByName(self.test_type)

        # Store some vital parameters as instance members
        if not self._saveMandatoryParams():
            self.logger.error("failed to initialize one of agent's mandatory members")
            return False

        return True

    def _getPlan(self):
        """
            Get TestPlan details.
            Author: mbenenso
            Parameters: none
            Return: True on success, False otherwise
        """
        # First lookup in the cache
        if not self._fromCache(eTcmsEntity.TestPlan, self.planId):
            # Search in TCMS db
            plan = self._nitrateApi.getById(eTcmsEntity.TestPlan, self.planId)
            if not plan:
                self.logger.error("invalid TCMS TestPlan ID %s" % self.planId)
                return False

            try:
                # If fetched from TCMS, store it in the cache
                self._populateCache(plan, eTcmsEntity.TestPlan, byId=True)
            except Exception as err:
                self.logger.error("failed to cache TesPlan with ID '%s': %s" % (self.planId, str(err)))
                return False

        return True

    def _saveMandatoryParams(self):
        """
            Save some vital parameters for the test.
            Author: mbenenso
            Parameters: none
            Return: True on success, False otherwise
        """
        self.buildId = self._fromCache(eTcmsEntity.Build, self.build_name, 'id')
        if not self.buildId:
            # Add a new Build entry to TCMS database
            self.buildId = self.__createNewBuildEntry(self.productId, self.build_name)

        self.productVersionId = self._fromCache(eTcmsEntity.ProductVersion, self.product_version, 'id')
        self.productCategoryId = self._fromCache(eTcmsEntity.ProductCategory, self.product_category, 'id')

        return all([self.buildId, self.productVersionId, self.productCategoryId])

    def __createNewBuildEntry(self, productId, buildName):
        """
            Create new TCMS build entry.
            Author: mbenenso
            Parameters:
            * productId - an ID of the tested product
            * buildName - the product's build name
            Return: a string representation of the ID of newly crated
                    TCMS Build on success, an empty string otherwise
        """
        if utils.valid(productId, buildName):
            self.logger.info("create new build entry for the build %s" % buildName)
            query = self._toDictionary("'product': " + productId + ", " + \
                                    "'name': " + self._nitrateApi._string_no_option(buildName) + ", " + \
                                    "'description': 'None', " + \
                                    "'is_active': 1")
            rc, retObj = self.__createTcmsEntry(eTcmsEntity.Build, query)
            if rc:
                return str(retObj['build_id'])
        return ''

    def __buildCache(self, entityType):
        """
            Fetch and cache entityType related information from TCMS database.
            Author: mbenenso
            Parameters:
            * entityType - TCMS entity type
            Return: True if the cache successfully initialized, False otherwise
        """
        cmd = "Product.get_" + TCMS_ENTITY_MAP.get(entityType)
        try:
            if entityType == eTcmsEntity.TestCase:
                # Get TestCases attached to the existing TestPlan
                tcmsEntries = self._runCommand("TestPlan.get_test_cases", self.planId)
                # Extend the TestCases cache. Store every TestCase entry twice:
                # by its ID and by its name, it will allow more effective search
                self._populateCache(tcmsEntries, entityType, byId=True)
            else:
                # Get all existing TCMS entries of entity type for tested product
                tcmsEntries = self._runCommand(cmd, self.productId)
            # Populate cache category for entity type with received TCMS data
            self._populateCache(tcmsEntries, entityType)
        except:
            msg = "populate cache for entity type {0} has been failed: {1}"
            self.logger.error(msg.format(eTcmsEntity.toString(entityType), traceback.format_exc()))
            return False

        return True

    def _populateCache(self, data, entityType, byId=False):
        """
            Fill cache objects of the agent.
            Author: mbenenso
            Parameters:
            * data - TCMS entries to cache
            * entityType - the type of the entry
            * byId - use entry's ID as the key instead of a name
            Return: none
            Throws: WrongParameterError, TcmsObjectCreationError
        """
        if not utils.valid(entityType):
            raise errors.WrongParameterError(entityType)
        entityTypeName = self._getEntityName(entityType)

        # Create new cache category for entityType in the agent's main cache
        if not self.cache.hasKey(entityType):
            self.cache.add(entityType, Cache())
        cache = self.cache.get(entityType)

        attr = {True: 'id', False: 'name'}[byId]
        for entry in data:
            # Wrap TCMS entry with simple object
            entryObj = self.__constructWrapperObject("{0}Wrapper".format(entityTypeName), entry)
            try:
                # Store wrapped object in appropriate cache
                if not cache.hasKey(getattr(entryObj, attr)):
                    cache.add(str(getattr(entryObj, attr)), entryObj)
            except AttributeError as err:
                raise TcmsObjectCreationError(str(err))

    def _getEntityName(self, entityType):
        """
            Try to fetch TCMS entity name from its enum value.
            Author: mbenenso
            Parameters:
            * entityType - entity type enum
            Return: entity type name if legal type, raise exception otherwise
            Throws: UnsupportedEntityTypeError
        """
        try:
            return eTcmsEntity.toString(entityType)
        except ValueError:
            raise UnsupportedEntityTypeError(entityType)

    def __constructWrapperObject(self, entityTypeName, args={}):
        """
            Create TCMS entry wrapper object.
            Author: mbenenso
            Parameters:
            * entityTypeName - the class name of the entity to create
            * args - a dictionary with arguments (optional)
            Return: wrapper object
        """
        cls = getattr(sys.modules[__name__], entityTypeName)
        if isinstance(cls, types.TypeType):
            return cls(dict=args)
        return types.InstanceType(cls, {"dict": args})

    def _isTestCaseAttachedToPlan(self, testCaseId, testPlanId):
        """
            Validate if TestCase is indeed attached to TestPlan.
            Author: mbenenso
            Parameters:
            * testCaseId - an ID of TCMS TestCase
            * testPlanId - an ID of TCMS TestPlan
            Return: True if the given TestCase is attached to the given TestPlan, False otherwise
        """
        plans = self.getTestPlanByTestCaseId(testCaseId)
        return bool(filter(lambda plan: str(plan.get('plan_id')) == testPlanId, plans))

    def _prepareCaseName(self, testCaseName, subTestName, iter):
        """
            Prepare TestCase name based on the ATOM test type.
            Author: mbenenso
            Parameters:
            * testCaseName - ATOM test case name
            * subTestName - ATOM sub test name
            * iter - ATOM test iteration number
            Return: ATOM test name in TCMS format
        """
        caseName = testCaseName
        if testCaseName and subTestName:
            # Test with subtest and test case name (Functionality etc.)
            caseName = subTestName + "::" + testCaseName
        elif not testCaseName and not subTestName:
            # Test without subtest and test case name (Benchmarks)
            caseName = self.testName + "_" + str(iter)

        return caseName

    def _handleTestCase(self, caseName, params):
        """
            Process ATOM test case.
            Author: mbenenso
            Parameters:
            * caseName - ATOM test case name
            * params - ATOM test case parameters
            Return: a list with TestCase IDs on success, an empty list otherwise
        """
        caseIds = []
        if not params['test_case_id']:
            caseIds = self.__handleUnMappedCase(caseName)
        else:
            params['test_case_id'] = params['test_case_id'].strip(" ").strip(",").split(",")
            if self.aggregation:
                id = self.getTestPlanByTestCaseId(params['test_case_id'][0])[0]['plan_id']
                if id and str(id) != self.planId:
                    msg = "switching TestPlan, old: '{0}', new: '{1}'"
                    self.logger.debug(msg.format(self.planId, str(id)))
                    if not self.onPlanChange(str(id)):
                        msg = "failed to change TestPlan for TestCase(s) {0}, skipping TestCaseRun creation"
                        self.logger.error(msg.format(params['test_case_id']))
                        return caseIds

            caseIds = self.__handleMappedCase(params)

        return caseIds

    def __handleTestIteration(self, params):
        """
            Write ATOM iteration info into TCMS database.
            It creates TestCase (if needed) and TestCaseRun.
            Author: mbenenso
            Parameters: see iterationInfo method
            Return: none
        """
        testCaseId = []
        caseRunId = []
        notes = self._createCaseRunNotes(params['info_line'])

        # Prepare TestCase name
        caseName = self._prepareCaseName(params['test_case_name'],
                                        params['sub_test_name'],
                                        params['iter_number'])

        # Get/create TestCase
        testCaseId = self._handleTestCase(caseName, params)
        if not testCaseId:
            msg = "failed to fetch TestCase ID (unmapped test case probably), skipping TestCaseRun creation"
            self.logger.warning(msg)
            return

        # Create TestCaseRun
        if self.atomicTest:
            caseRunId = self.createTestCaseRun(testCaseId[0],
                                                str(self.__getCaseRunStatus(params['iter_status'])),
                                                notes)
        else:
            # Store step info of the current case in the steps cache
            caseRunId = self.caseStepsCache.add(status=self._translateIterationStatus(params['iter_status']),
                                                name=caseName.title(),
                                                index=params['iter_number'],
                                                caseId=testCaseId,
                                                notes=notes)

        if caseRunId and params['bz_info']:
            # Attach bug info to the created TestCaseRun
            self._setBZInfo(caseRunId, str(params['bz_info']))

    def onPlanChange(self, id):
        """
            Handle TestPlan change situation.
            Author: mbenenso
            Parameters:
            * id - TestPlan ID
            Return: True on successfull TestPlan change, False otherwise
        """
        # Start initialization process for newly received TestPlan
        self.planId = id
        if self._getPlan():
            if self.__buildCache(eTcmsEntity.TestCase):
                self.testName = self._fromCache(eTcmsEntity.TestPlan, self.planId, 'name').title()
                self.testPlanTypeId = self._getTestPlanTypeIdByName(self.test_type)
                return self._initTestRun()
        return False

    def __handleMappedCase(self, params):
        """
            Handle ATOM test case (iteration) which is mapped to TCMS TestCase(s).
            Author: mbenenso
            Parameters:
            * params - see iterationInfo() method for detailed list of parameters
            Return: a list with TestCase ID(s) on success, an empty list otherwise
        """
        cases = []
        for id in params['test_case_id']:
            if self.atomicTest:
                # Check if TestCase is indeed attached to the current TestPlan
                if self._isTestCaseAttachedToPlan(id, self.planId):
                    cases.append(self._fromCache(eTcmsEntity.TestCase, id, 'id'))
                else:
                    msg = "TestCase with ID {0} is not attached to TestPlan with ID {1}"
                    self.logger.error(msg.format(id, self.planId))
            else:
                if not self._fromCache(eTcmsEntity.TestCase, id):
                    # We are going to re-use an existing TestCases written by
                    # manual team to avoid TestCase duplication in TCMS,
                    # the following line will link an existing TestCase to the current TestPlan
                    msg = "linking an existing TestCase with ID {0} to the TestPlan with ID {1}"
                    self.logger.info(msg.format(id, self.planId))
                    self._runCommand("TestCase.link_plan", id, self.planId)
                    # Update "Automated" property of the TestCase to both: "Manual" and "Auto"
                    self._update(eTcmsEntity.TestCase, id,
                                self._toDictionary(self._toStringWithOptions("is_automated", "2")))

                cases.append(id)

        return cases

    def __handleUnMappedCase(self, caseName):
        """
            Handle ATOM test case (iteration) which is not mapped to TCMS TestCase.
            Author: mbenenso
            Parameters:
            * caseName - the name of a test case
            Return: a list with TestCase ID on success, an empty list otherwise
        """
        if not self.atomicTest:
            msg = "TestCase creation is not allowed for '{0}' tests (non-atomic type)"
            self.logger.error(msg.format(self.test_type.title()))
            return []

        # Get TestCase ID by its name if it already stored in the
        # agent's cache, means already exists in TCMS database
        id = self._fromCache(eTcmsEntity.TestCase, caseName.lower(), 'id')
        if not id:
            # Create new TestCase (allowed since current test is an atomic test)
            id = self.createTestCase(caseName.title())

        return [id]

    def _translateIterationStatus(self, status):
        """
            Convert the status of ATOM iteration into boolean value.
            Author: mbenenso
            Parameters:
            * status - a string representation of iteration status
            Return: True if iteration pass, False otherwise
        """
        return bool(SUCCESS.match((str(status)).lower()))

    def __getCaseRunStatus(self, status):
        """
            Return CaseRunStatus in TCMS acceptable format.
            Author: mbenenso
            Parameters:
            * status - a boolean status
            Return: eCaseRunStatus.PASS if CaseRun passed, eCaseRunStatus.FAIL otherwise
        """
        if self._translateIterationStatus(status):
            return eCaseRunStatus.PASS
        return eCaseRunStatus.FAIL

    def __sub(self, i_str):
        """
            Remove quotes and replace commas with space.
            Author: mbenenso
            Parameters:
            * i_str - input string
            Return: edited string
        """
        text = re.sub('\'', '', i_str)
        text = re.sub(',', ' ', text)
        return text

    def _buildHeaderNamesList(self, headersString):
        """
            Prepare a list of test's header names.
            Author: mbenenso
            Parameters:
            * headersString - a string with header names
            Return: header names list on success, an empty list otherwise
        """
        headerNames = []
        if utils.valid(headersString):
            headerNames = [headerName.split(":")[0] for headerName in headersString.split(",")]
        else:
            self.logger.warning("headers string is empty")
        return headerNames

    def _createCaseRunNotes(self, infoArr):
        """
            Create notes string for TestCaseRun.
            Author: mbenenso
            Parameters:
            * infoArr - an array of case parameters
            Return: notes string on success, an empty string otherwise
        """
        resultString = ''
        template = "{0}={1}, "
        if infoArr:
            for index, headerName in enumerate(self.headerNames):
                if headerName.lower() == "params":
                    resultString = resultString.rstrip(", ")
                    resultString += r"\n{0}: {1}".format("Action params", \
                                                        self.__sub(infoArr[index]))
                else:
                    resultString += template.format(headerName, infoArr[index])
            resultString = resultString.strip(", ")
        else:
            msg = "unable to create notes - infoArr received from ATOM is empty"
            self.logger.warning(msg)

        return resultString

    def _getTestPlanTypeIdByName(self, planType):
        """
            Retrieve an ID of TestPlan type by its name.
            Author: mbenenso
            Parameters:
            * planType - a TestPlan type string
            Return: TCMS TestPlan type ID on success, an empty string otherwise
        """
        planType = self._runCommand('TestPlan.check_plan_type',
                                    self._nitrateApi._string_no_option(str(planType).title()))
        if planType:
            return str(planType[0]['id'])
        return ''

    # Public interfaces for integration with ATOM (django)
    def getTestPlanByTestCaseId(self, id):
        """
            Retrieve a list of TestPlan(s) that TestCase with id is linked to.
            Author: mbenenso
            Parameters:
             * id - the ID of a TestCase
            Return: a list of TestPlan(s) on success, an empty list otherwise
        """
        if utils.valid(id):
            return self._runCommand("TestCase.get_plans", id)
        self.logger.error("TestCase id is empty")
        return []

    def getTestCase(self, id):
        """
            Retrieve a list with TestCase object by its id.
            Author: mbenenso
            Parameters:
             * id - the ID of a TestCase
            Return: a list with TestCase object on success, an empty list otherwise
        """
        return self._nitrateApi.getById(eTcmsEntity.TestCase, id)


def main():
    """
        Main for example.
        Author: mbenenso
        Parameters: none
        Return: none
    """
    agent = TcmsAgent("mbenenso")

    agent.init(test_type='Functionality',
                test_name='REST_API',
                build_name='ic114',
                product_name='RHEVM',
                product_version='4.6',
                product_category='API',
                header_names='testName:sub_test,caseName:info,testType:str,params:text',
                test_plan_id='3173',
                test_report_id='1997')

    agent.iterationInfo(sub_test_name='Datacenters',
                        test_case_name='Create NFS Data Center',
                        info_line='Datacenters,Create NFS Data Center,positive,name=RestDataCenter1 storage_type=NFS version=2.2',
                        iter_number='1',
                        iter_status='Pass',
                        bz_info=None,
                        test_case_id='70577')

    agent.testEnd()


if __name__ == "__main__":
    main()
