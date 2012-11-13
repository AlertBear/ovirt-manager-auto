"""
----------------------------
Disabling Vital Tests Plugin
----------------------------

ART allows you to set any test case as vital. It means if it fails
no further test will be run. To map test case as vital in xml file
the following attribute should be added:
<vital>yes</vital>
Sometimes for debugging purposes you want to disable vital tests but
don't want to change your xml file.
This is exactly what this plugin provides for you.

CLI Options:
------------
    --vital-disable  Enable plugin

Configuration Options:
----------------------
    | **[VITAL_DISABLE]**
    | **enabled**   to enable the plugin (true/false)
"""

from art.test_handler.plmanagement import Component, implements, get_logger, PluginError
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
                                                    IConfigValidation


logger = get_logger('vital_disable')
SECTION_NAME = 'VITAL_DISABLE'
DEFAULT_STATE = False
ENABLED = 'enabled'


class NoVitalError(PluginError):
    pass


class VitalDisable(Component):
    """
    Plugin provides option to disable vital tests.
    """
    implements(IConfigurable, ITestCaseHandler, IPackaging, IConfigValidation)
    name = "Vital_Disable"

    def __init__(self):
        super(VitalDisable, self).__init__()

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--vital-disable', action='store_true', \
                dest='vital_disabled', help="enable plugin", default=False)

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(SECTION_NAME).as_bool(ENABLED)
        return params.vital_disabled or conf_en


    def configure(self, params, conf):
        if self.is_enabled(params, conf):
            logger.info("Will disable all vital tests.")


    def pre_test_case(self, t):
        try:
            t.test_vital = False
        except AttributeError:
            raise NoVitalError(t.test_name)


    def post_test_case(self, t):
        pass

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'vital-disable'
        params['version'] = '1.0'
        params['author'] = 'Elena Dolinin'
        params['author_email'] = 'edolinin@redhat.com'
        params['description'] = cls.__doc__.strip().replace('\n', ' ')
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.vital_disable_plugin']


    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(SECTION_NAME, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        spec[SECTION_NAME] = section_spec

