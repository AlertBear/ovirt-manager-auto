
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import\
        ITestGroupHandler, ITestSuiteHandler, ITestCaseHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging

TCMS_OPTION = 'TCMS'
PARAMETERS = 'PARAMETERS'
TCMS_URL='https://tcms.engineering.redhat.com/xmlrpc/'
REALM = '@REDHAT.COM'
SENDER = 'noreply@redhat.com'
HEADERS = 'testName:sub_test,caseName:info,testType:str,params:text'
KT_EXT = '.keytab'
PLAN_TYPE = 23

logger = get_logger('tcms_agent')


# TODO: It also should consider TestSuites in parallel, but here is problem:
#       I am not able to know which test_case belongs to which test_suite.
#       Solutions:
#        * add pointer to its parent for each test_element
#        * os.fork whole test_runner for each test_suite


class TCMS(Component):
    """
    Plugin provides access to TCMS site.
    """
    implements(IConfigurable, ITestGroupHandler, ITestSuiteHandler, IPackaging, ITestCaseHandler)
    name = "TCMS"

    def __init__(self):
        super(TCMS, self).__init__()
        self.agent = None
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
        tcms_cfg = conf.get(TCMS_OPTION, {})
        user = params.tcms_user or tcms_cfg['user']
        c = {'tcms_url': TCMS_URL,\
                'placeholder_plan_type':  PLAN_TYPE,\
                'keytab_files_location': tcms_cfg['keytab_files_location'], \
                'redhat_email_extension': REALM, \
                'keytab_file_extension': KT_EXT,
                'configure_logger': False,
                'send_result_email': tcms_cfg['send_result_email'],
                'test_run_name_template': tcms_cfg['test_run_name_template'],
                'default_sender': SENDER,
                'header_names': HEADERS,}

        from art.test_handler.plmanagement.plugins import tcmsAgent
        self.agent = tcmsAgent.TcmsAgent(user, c)
        self.version = conf[PARAMETERS]['compatibility_version']
        self.category = tcms_cfg['category']


    def pre_test_suite(self, suite):
        if not getattr(suite, 'tcms_plan_id', None):
            return
        self.plan_id = suite.tcms_plan_id
        self.agent.init(test_type='Functionality',
                    test_name='REST_API',
                    build_name='unspecified',
                    product_name='RHEVM',
                    product_version=self.version,
                    header_names=HEADERS,
                    product_category=self.category,
                    test_plan_id=self.plan_id)

    def post_test_suite(self, suite):
        if self.agent:
            self.agent.testEnd()

    def pre_test_case(self, g):
        pass

    def test_group_skipped(self, g):
        pass

    def post_test_case(self, test):
        if not self.agent or not test.tcms_test_case:
            return

        self.agent.iterationInfo(sub_test_name=test.group,
                            test_case_name=test.test_name,
                            info_line = '%s,%s,%s,%s' %(test.group,
                                test.test_name, test.positive,
                                test.test_parameters),
                            iter_number=test.iteration,
                            iter_status=test.status,
                            bz_info=test.bz,
                            test_case_id=test.tcms_test_case)

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(TCMS_OPTION, {}).get('enabled', 'false').lower() == 'true'
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

