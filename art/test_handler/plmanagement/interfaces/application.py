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
        pass

    def configure(self, params, config):
        pass

