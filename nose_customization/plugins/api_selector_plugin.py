import logging
import os
import inspect
from nose.util import transplant_class
from nose.plugins import Plugin as NosePlugin
from art.test_handler.settings import opts

log = logging.getLogger('nose.plugins.apiselector')


class APISelectorPlugin(NosePlugin):
    name = 'apiselector'

    def options(self, parser, env=os.environ):
        log.info('Setting APISelector options')
        super(APISelectorPlugin, self).options(parser, env=env)

    def configure(self, options, conf):
        super(APISelectorPlugin, self).configure(options, conf)
        log.info('Configuring APISelector')
        if options.enable_plugin_apiselector:
            self.enabled = True
        self.allowed_engines = set(opts.get('engines', ['rest']))

    def prepareTestLoader(self, loader):
        # we need to use configured loader in order to have plugins working
        self.loader = loader

    def makeTest(self, obj, parent):
        # Skipping non-classes objects
        if not inspect.isclass(obj):
            return []
        if parent and obj.__module__ != parent.__name__:
            obj = transplant_class(obj, parent.__name__)

        objs = []
        required_apis = set(getattr(obj, 'apis', ['rest']))
        for api in iter(self.allowed_engines & required_apis):
            log.info('creating  %s for api %s', obj.__name__, api)
            new_name = "%s%s" % (obj.__name__, api.upper())
            new_dict = dict(obj.__dict__)
            new_dict.update({'api': api})
            bases = [obj] + list(obj.__bases__)
            new_obj = type(new_name, tuple(bases), new_dict)
            log.info('%s for api %s created', new_obj.__name__, api)

            objs.append(self.loader.loadTestsFromTestCase(new_obj))

        return self.loader.suiteClass(objs)
