
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import \
        IConfigurable, IApplicationListener
from art.test_handler.plmanagement.interfaces.tests_listener import\
        ITestGroupHandler, ITestSuiteHandler, ITestCaseHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
                                                    IConfigValidation

TCMS_OPTION = 'TCMS'
PARAMETERS = 'PARAMETERS'
TCMS_URL='https://tcms.engineering.redhat.com/xmlrpc/'
REALM = '@REDHAT.COM'
SENDER = 'noreply@redhat.com'
HEADERS = 'testName:sub_test,caseName:info,testType:str,params:text'
KT_EXT = '.keytab'
PLAN_TYPE = 23
DEFAULT_STATE = False
ENABLED = 'enabled'
USER = 'user'
KEYTAB_LOCATION = 'keytab_files_location'
CATEGORY = 'category'
SEND_MAIL = 'send_result_email'
RUN_NAME_TEMPL = 'test_run_name_template'

TCMS_DEC = 'tcms'
TCMS_TEST_CASE = 'tcms_test_case'
TCMS_PLAN_ID = 'tcms_plan_id'

logger = get_logger('tcms_agent')


# TODO: It also should consider TestSuites in parallel, but here is problem:
#       I am not able to know which test_case belongs to which test_suite.
#       Solutions:
#        * add pointer to its parent for each test_element
#        * os.fork whole test_runner for each test_suite


def tcms_decorator(plan_id, case_id):
    """
    TCMS decorator
    """
    def decorator(func):
        setattr(func, TCMS_PLAN_ID, plan_id)
        setattr(func, TCMS_TEST_CASE, case_id)
        return func
    return decorator


class TCMS(Component):
    """
    Plugin provides access to TCMS site.
    """
    implements(IConfigurable, ITestGroupHandler, IApplicationListener, \
                    IPackaging, ITestCaseHandler, IConfigValidation)
    name = "TCMS"

    def __init__(self):
        super(TCMS, self).__init__()
        self.plan_id = None

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-tcms', action='store_true', \
                dest='tcms_enabled', help="enable plugin")
        group.add_argument('--tcms-user', action="store", dest='tcms_user', \
                help="username for TCMS")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        tcms_cfg = conf.get(TCMS_OPTION)

        self.user = params.tcms_user or tcms_cfg[USER]
        self.info = {'tcms_url': TCMS_URL,\
                'placeholder_plan_type':  PLAN_TYPE,\
                'keytab_files_location': tcms_cfg[KEYTAB_LOCATION], \
                'redhat_email_extension': REALM, \
                'keytab_file_extension': KT_EXT,
                'configure_logger': False,
                'send_result_email': tcms_cfg[SEND_MAIL],
                'test_run_name_template': tcms_cfg[RUN_NAME_TEMPL],
                'default_sender': SENDER,
                'header_names': HEADERS,}

        self.version = conf[PARAMETERS]['compatibility_version']
        self.category = tcms_cfg[CATEGORY]
        self.results = {}
        self.tcms_plans = []
        self.__register_functions()

    def __register_functions(self):
        from art.test_handler import tools
        setattr(tools, TCMS_DEC, tcms_decorator)

    def pre_test_group(self, group):
        tcms_plan = getattr(group, TCMS_PLAN_ID, None)
        if tcms_plan:
            self.tcms_plans.append(tcms_plan)

    def post_test_group(self, group):
        self.post_test_case(group)
        tcms_plan = getattr(group, TCMS_PLAN_ID, None)
        if tcms_plan and tcms_plan == self.tcms_plans[-1]:
            self.tcms_plans.pop()

    def pre_test_case(self, g):
        pass

    def test_group_skipped(self, g):
        pass

    def post_test_case(self, test):
        tcms_case = getattr(test, TCMS_TEST_CASE, None)
        if not tcms_case:
            return

        plan = getattr(test, TCMS_PLAN_ID, None)
        if not plan and self.tcms_plans:
            plan = self.tcms_plans[-1]

        assert plan, "Missing tcms_plan for test_case %s" % tcms_case
                        # NOTE: it shouldn't happen

        res = self.results.get(plan, {})
        res[tcms_case] = test
        self.results[plan] = res

    def on_application_exit(self):
        if self.results:
            self.__upload_results()

    def __upload_results(self):
        from art.test_handler.plmanagement.plugins import tcmsAgent
        self.agent = tcmsAgent.TcmsAgent(self.user, self.info)

        for plan, cases in self.results.items():
            self.__upload_plan(plan, cases)

        self.agent.testEnd()

    def __upload_plan(self, plan, cases):
        self.agent.init(test_type='Functionality',
                    test_name='REST_API',
                    build_name='unspecified',
                    product_name='RHEVM',
                    product_version=self.version,
                    header_names=HEADERS,
                    product_category=self.category,
                    test_plan_id=str(plan))

        for case, test in cases.items():
            self.__fill_test_case(case, test)

    def __fill_test_case(self, case, test):
        if test.status == test.TEST_STATUS_SKIPPED:
            return # TODO: don't know how to report skipped tests

        self.agent.iterationInfo(sub_test_name=test.test_name,
                            test_case_name=test.test_name,
                            info_line = str(test),
                            iter_number=test.serial,
                            iter_status=test.status,
                            bz_info=getattr(test, 'bz', None),
                            test_case_id=str(case))


    def on_application_start(self):
        pass

    def on_plugins_loaded(self):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(TCMS_OPTION).as_bool(ENABLED)
        return params.tcms_enabled or conf_en


    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower()
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'TCMS plugin for ART'
        params['long_description'] = 'Provides connection to TCMS DB and '\
                'reports there tests results.'
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.tcms_plugin', \
                'art.test_handler.plmanagement.plugins.tcmsAgent', \
                'art.test_handler.plmanagement.plugins.tcmsEntryWrapper']


    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(TCMS_OPTION, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[USER] = "string(default=None)"
        section_spec[KEYTAB_LOCATION] = "string(default=None)"
        section_spec[CATEGORY] = "string(default=None)"
        section_spec[SEND_MAIL] = 'boolean(default=true)'
        section_spec[RUN_NAME_TEMPL] =\
            "string(default='Auto TestRun for {0} TestPlan')"
        spec[TCMS_OPTION] = section_spec

