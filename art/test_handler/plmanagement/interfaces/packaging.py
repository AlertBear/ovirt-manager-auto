from art.test_handler.plmanagement import Interface

class IPackaging(Interface):
    @classmethod
    def fill_setup_params(cls, params):
        """
        Fill out all params which you want to pass to distutils.setup
        """
