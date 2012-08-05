
from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.application import IConfigurable
from test_handler.plmanagement.interfaces.tests_listener import ITestGroupHandler, ITestSuiteHandler

TCMS_OPTION = 'TCMS'


class TCMS(Component):
    """
    Plugin provides access to TCMS site.
    """
    implements(IConfigurable, ITestGroupHandler, ITestSuiteHandler)
    name = "TCMS"

    _kt_ext = '.keytab'
    _placeholder_plan_type = 23

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
        group.add_argument('--tcms-url', action='store', dest='tcms_url', \
                help="TCMS site")
        group.add_argument('--tcms-realm', action='store', dest='tcms_realm', \
                help="kerberos realm")

    def configure(self, params, conf):
        if not params.tcms_enabled:
            # added option to enable tcms from config_file
            return
        user = params.tcms_user or conf[TCMS_OPTION]['user']
        kt_path = conf[TCMS_OPTION]['keytab_files_location']
        realm = params.tcms_realm or conf[TCMS_OPTION]['realm']
        kt_ext = conf[TCMS_OPTION]['kt_ext'] or self._kt_ext
        pl_plan_type = conf[TCMS_OPTION]['placeholder_plan_type']\
                or self._placeholder_plan_type
        c = {'tcms_url': params.tcms_url or conf['tcms_url'],\
                'placeholder_plan_type': pl_plan_type,\
                'keytab_files_location': kt_path, \
                'redhat_email_extension': realm, \
                'keytab_file_extension': kt_ext}
        for v in ('atom_test_link', 'log_file_location', 'default_sender', \
                'configure_logger', 'send_result_email', \
                'test_run_name_template'):
            c[v] = conf[v]
        from test_handler.plmanagement.plugins import tcmsAgent
        self.agent = tcmsAgent.TcmsAgent(user, c)


    def pre_test_suite(self, suite):
        if not hasattr(suite, 'tcms'):
            return
        self.plan_id = suite.tcms
        self.agent.init(test_type='?',
                    test_name='?',
                    build_name='?',
                    product_name='?',
                    product_version='?',
                    product_category='?',
                    header_names='testName:%s,caseName:%s,testType:%s,params:%s'\
                            % ('?', '?', '?', '?'),
                    test_plan_id=self.plan_id,
                    test_report_id=None) # ?

    def post_test_suite(self, suite):
        self.agent.testEnd()

    def pre_test_group(self, g):
        pass

    def test_group_skipped(self, g):
        pass

    def post_test_group(self, test):
        if not hasattr(test, 'tcms'):
            return
        self.agent.iterationInfo(sub_test_name=test.test_name,
                            test_case_name=test.action.func_name,
                            info_line='Datacenters,Create NFS Data Center,positive,name=RestDataCenter1 storage_type=NFS version=2.2', # ?
                            iter_number=test.iteration,
                            iter_status=test.status,
                            bz_info=None,
                            test_case_id=test.tcms)

    @classmethod
    def is_enabled(cls, params, conf):
        return params.tcms_enabled

