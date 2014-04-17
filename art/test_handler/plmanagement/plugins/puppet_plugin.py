"""
--------------------------------
Puppet Plugin
--------------------------------

Plugin disables puppet daemon on VDC and VDSs machines before test is
executed and also enables puppet daemon when test is done.

CLI Options:
------------
    --with-puppet  Enable the plugin

Configuration Options:
----------------------
    | **[PUPPET]**
    | **enabled**   to enable the plugin (true/false)
"""

from art.test_handler.plmanagement import Component, implements, get_logger,\
     PluginError
from art.test_handler.plmanagement.interfaces.application import\
     IConfigurable, IApplicationListener
from art.test_handler.plmanagement.interfaces.config_validator import\
              IConfigValidation
from art.test_handler.plmanagement.interfaces.packaging import IPackaging


from utilities.machine import Machine, LINUX

logger = get_logger('puppet')


ENABLED = 'enabled'
PUPPET_SEC = 'PUPPET'
VDC_PARAMS = 'REST_CONNECTION'
PARAMETERS = 'PARAMETERS'
VDS = 'vds'
VDC = 'host'
VDC_PASSWD = 'vdc_root_password'
VDS_PASSWORD = 'vds_password'

PUPPET_DAEMON = 'puppet'
OPT_ENABLE = '--enable'
OPT_DISABLE = '--disable'

class PuppetPlugin(Component):
    """
    Plugin disables puppet daemon on VDC and VDSs machines before test is
    executed. And also enables puppet daemon when test is done.
    """
    implements(IConfigurable, IApplicationListener, IConfigValidation, \
            IPackaging)

    name = "Puppet"
    priority = -2000 # to ensure it runs first

    def __init__(self):
        super(PuppetPlugin, self).__init__()
        self.machines = []

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-puppet', action='store_true', \
                dest='puppet_enabled', help="enable plugin")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        vdc_passwd = conf[PARAMETERS][VDC_PASSWD]
        vdc = conf[VDC_PARAMS][VDC]
        vds = conf[PARAMETERS].as_list(VDS)
        vds_passwd = conf[PARAMETERS].as_list(VDS_PASSWORD)
        user = 'root'

        self.machines = [Machine(vdc, user, vdc_passwd).util(LINUX)]

        for name, passwd in  zip(vds, vds_passwd):
            self.machines.append(Machine(name, user, passwd).util(LINUX))

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[PUPPET_SEC].as_bool(ENABLED)
        return params.puppet_enabled or conf_en

    def on_plugins_loaded(self):pass

    def on_application_start(self):
        self.__exec_toogle_puppet(OPT_DISABLE)

    def on_application_exit(self):
        self.__exec_toogle_puppet(OPT_ENABLE)

    def __exec_toogle_puppet(self, opt):
        toogle_cmd = [PUPPET_DAEMON, 'agent', opt, '--detailed-exitcodes']
        test_cmd = [PUPPET_DAEMON, 'agent', '--test', '--detailed-exitcodes']
        error_log_msg = "%s: failed execute %s with %s err: %s; out: %s"

        if opt == OPT_ENABLE:
            cmds = (toogle_cmd, test_cmd)
            action_msg = 'enabled'
        elif opt == OPT_DISABLE:
            cmds = (test_cmd, toogle_cmd)
            action_msg = 'disabled'
        else:
            assert False, "opt argument must be %s or %s, but got %s" % \
                    (OPT_ENABLE, OPT_DISABLE, opt)

        for m in self.machines:
            fail = False
            with m.ssh as conn:
                for cmd in cmds:
                    rc, out, err = conn.runCmd(cmd)
                    if rc not in (0, 2):
                        fail = True
                        logger.error(error_log_msg, m.host, cmd, rc, err, out)
            if not fail:
                logger.info("%s: puppet daemon was %s", m.host, action_msg)
#            else:
#                here could be raised exception

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower()
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Puppet plugin for ART'
        params['long_description'] = cls.__doc__
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.puppet_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(PUPPET_SEC, {})
        section_spec[ENABLED] = "boolean(default=False)"
        spec[PUPPET_SEC] = section_spec
        parms_spec = spec.get(PARAMETERS, {})
        parms_spec[VDC_PASSWD] = "string(default=None)"
        spec[PARAMETERS] = parms_spec
