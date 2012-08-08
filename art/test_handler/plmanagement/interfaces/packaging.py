from art.test_handler.plmanagement import Interface

class IPackaging(Interface):
    """
    This interface provides easy way to get RPM for your plugin
    """
    @classmethod
    def fill_setup_params(cls, params):
        """
        Fill out all params which you want to pass to distutils.setup
        Paramaters:
         * params - dict of attributes

        EXAMPLE:
        params['name'] = cls.name.lower()
        params['version'] = '1.0'
        params['author'] = '<your_name>'
        params['author_email'] = '<your_email>'
        params['description'] = '<short_description>'
        params['long_description'] = '<long_description>'
        params['requires'] = ['list', 'of', 'yum', 'deps']
        params['pip_dep'] = ['list', 'of', 'pip', 'deps']
        params['py_modules'] = ['full.module.path.to.your.plugin', ...]
        """
