"""
----------------------
Polarion mapper plugin
----------------------

Plugin adds polarion-id to report which is used by jenkins redhat-ci-plugin
to report results to Polarion site.

CLI Options
------------
    --with-polarion Enable the plugin

Configuration Options:
    | **[POLARION]**
    | **enabled** - to enable plugin (true/false)

"""

from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import (
    IConfigurable,
)
from art.test_handler.plmanagement.interfaces.config_validator import (
    IConfigValidation
)
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.report_formatter import (
    IResultExtension,
)
from art.test_handler import tools


logger = get_logger('polarion')
SECTION = "POLARION_MAPPER"
ENABLED = "enabled"
POLARION_ID = "polarion_id"


def polarion_decorator(polarion_id):
    """
    Polarion decorator
    """
    def wrapper(func):
        setattr(func, POLARION_ID, polarion_id)
        return func
    return wrapper


class Polarion(Component):
    """
    Polarion plugin, this plugin generates property file which is used
    to map test-case name to polarion ID.
    """
    implements(
        IConfigurable,
        IConfigValidation,
        IPackaging,
        IResultExtension,
    )
    name = "Polarion Mapper"

    def __init__(self):
        super(Polarion, self).__init__()
        self.__register_functions()

    def __register_functions(self):
        setattr(tools, "polarion", polarion_decorator)

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument(
            '--with-polarion-mapper', action='store_true',
            dest='polarion_enabled', help="enable plugin",
        )

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

    def pre_test_result_reported(self, res, tc):
        polarion_id = tc.attrs.get(POLARION_ID)

        if polarion_id:
            res['polarion-id'] = polarion_id

    def pre_group_result_reported(self, result, test_group):
        pass

    def pre_suite_result_reported(self, result, test_suite):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(SECTION).as_bool(ENABLED)
        return params.polarion_enabled or conf_en

    def config_spec(self, spec, val_funcs):
        section = spec.setdefault(SECTION, {})
        section[ENABLED] = "boolean(default=False)"

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(" ", "-")
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Polarion mapper plugin'
        params['long_description'] = 'Adds polarion-id into report'
        params['py_modules'] = [
            'art.test_handler.plmanagement.plugins.polarion_mapper_plugin',
        ]
