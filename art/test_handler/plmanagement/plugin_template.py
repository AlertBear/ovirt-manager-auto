"""
This is ART plug-in template. Copy this to into plugins/ directory.
IMPORTANT: rename it to <name_of_your_plugin>_plugin.py
"""

# this things are base of whole plugin
from art.test_handler.plmanagement import Component, implements, get_logger
# also you need import tnterfaces which you want to implement
from art.test_handler.plmanagement.interfaces import IConfigurable

# create logger, it creates logger which bellongs under 'plmanagement' logger,
# so in this case: plmanagement.<name_of_your_plugin>
logger = get_logger('<name_of_your_plugin>')


# please select some suitable name for plugin class inherited from Component
class <PluginClass>(Component):
    """
    <description of your plugin>
    """
    # here you have to specify which interfaces you want to implement
    implements(IConfigurable, another_interfaces, ...)
    name = '<name_of_your_plugin>'

    # here we are implementing add_options from IConfigurable interface
    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--enable-my-pl', action='store_true', \
                dest='enable_my_pl', help="enable plugin")

    # another method from IConfigurable interface
    def configure(self, params, conf):
        if self.is_enabled(params, conf):
            return
        # init plugin

    # here implement all methods from interfaces which you wanted use.

    # this method tells ART if plugin is ready work. if this returns False
    # no interface_method will be executed (except add_options and configure)
    @classmethod
    def is_enabled(cls, params, conf):
        return params.enable_my_pl

