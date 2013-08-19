from art.test_handler.plmanagement import Interface


class IConfigurator(Interface):
    """
    This interface allows plugins to change  runtime configuration
    of the application
    """
    def configure_app(self, config):
        """
        Called to change runtime configuration.

        Parameters:
        config - the runtime configuration
        """
        pass
