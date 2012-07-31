from art.test_handler.plmanagement import Interface


class IConfigValidation(Interface):
    @classmethod
    def config_spec(self, conf_obj, val_funcs):
        """
        Called after plugins are loaded.
        This interface provides way to define validation rules for
        config options
        Parameters:
         * conf_obj - config object contains spec_options
         * val_funcs - dict contains user-defined validation functions
        """
