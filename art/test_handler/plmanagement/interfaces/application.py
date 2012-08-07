from art.test_handler.plmanagement import Interface


class IApplicationListener(Interface):
    def on_application_start(self):
        """ Called after application starts. """
        pass

    def on_application_exit(self):
        """ Called before application exits. """
        pass

    def on_plugins_loaded(self):
        """ Called after all plugins loaded. """
        pass


class IConfigurable(Interface):
    @classmethod
    def add_options(cls, parser):
        """
        Allows to you add CLI options requires/provided by your plugin
        Parameters:
         * parser - argparse.ArgumentParser object

        EXAMPLE:
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-XXX', action='store_true', \
                dest='my_plugin_enabled', help="eniable plugin")
        """
        pass

    def configure(self, params, config):
        """
        Called when config file and CLI options are parsed
        Parameters:
         * params - argparse.Namespace contains parsed values
         * config - configobj.ConfigObj contains loaded config file
        """
        pass

