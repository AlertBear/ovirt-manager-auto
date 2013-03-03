"""
--------------------
Provisioning tools Plugin
--------------------

This plugin sets parameters for provisioning tools

CLI Options:
------------
    --with-provisioning-tools  Enable the plugin
"""
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from art.test_handler.settings import opts

logger = get_logger('provisioning_tools')

DEFAULT_STATE = False
PROVISIONING_TOOLS = 'PROVISIONING_TOOLS'
RUN_SECTION = 'RUN'


class ProvisioningTools(Component):
    """
    Plugin provides provisioning tools for vms creation.
    """
    implements(IConfigurable, IConfigValidation, IPackaging)
    name = "Provisioning tools"

    def __init__(self):
        super(ProvisioningTools, self).__init__()
        self.cleanup = None
        self.conf = None

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group = group.add_mutually_exclusive_group()
        group.add_argument('--with-provisioning-tools', action="store_true",
                           dest='provisioning_enabled',
                           help="enable provisioning tools functionality",
                           default=False)

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        logger.info("Configuring provisioning tools plugin.")
        self._conf = conf[PROVISIONING_TOOLS]
        provisioning_tool = self._conf['provisioning_tool']
        opts['provisioning_tool'] = provisioning_tool
        provisioning_tool = provisioning_tool.upper()
        opts['provisioning_tool_api'] = self._conf[provisioning_tool]['api']
        opts['provisioning_tool_user'] = self._conf[provisioning_tool]['user']
        opts['provisioning_tool_password'] = \
            self._conf[provisioning_tool]['password']
        opts['provisioning_tool_common_parameters'] = \
            dict(filter(lambda x: x[0] not in ['api', 'user', 'password'],
                        self._conf[provisioning_tool].iteritems()))
        # passing only specific provisioning tool
        opts['provisioning_profiles'] = \
            dict([(x, conf['PROVISIONING_PROFILES'][x][
                provisioning_tool.upper()]) for x in
                conf['PROVISIONING_PROFILES']])

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[PROVISIONING_TOOLS].as_bool('enabled')
        return params.provisioning_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Ilia Meerovich'
        params['author_email'] = 'iliam@redhat.com'
        params['description'] = 'Hosts cleanup for ART'
        params['long_description'] = 'Plugin for ART which is responsible '\
            'for configuring provisioning tools'
        params['requires'] = []
        params['py_modules'] = \
            ['art.test_handler.plmanagement.plugins.provisioning_tools_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(PROVISIONING_TOOLS, {})
        section_spec['enabled'] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec['provisioning_tool'] = \
            'option("cobbler", "foreman", default="cobbler")'
        cobbler_spec = section_spec.setdefault('COBBLER', {})
        cobbler_spec['api'] = "string(default=None)"
        cobbler_spec['user'] = "string(default=None)"
        cobbler_spec['password'] = "string(default=None)"
        foreman_spec = section_spec.setdefault('FOREMAN', {})
        foreman_spec['api'] = "string(default=None)"
        foreman_spec['user'] = "string(default=None)"
        foreman_spec['password'] = "string(default=None)"
