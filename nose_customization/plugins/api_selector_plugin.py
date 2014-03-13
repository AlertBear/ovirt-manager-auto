import logging
import os
from nose.util import transplant_class
from nose.plugins import Plugin as NosePlugin
from nose.loader import defaultTestLoader

log = logging.getLogger('nose.plugins.apiselector')


class APISelectorPlugin(NosePlugin):
    name = 'apiselector'

    def options(self, parser, env=os.environ):
        log.info('Setting APISelector options')
        super(APISelectorPlugin, self).options(parser, env=env)

    def configure(self, options, conf):
        log.info('Configuring APISelector')
        if options.enable_plugin_apiselector:
            self.enabled = True

    def makeTest(self, obj, parent):
        if parent and obj.__module__ != parent.__name__:
            obj = transplant_class(obj, parent.__name__)
        objs = []

        for api in iter(getattr(obj, 'apis', ['rest'])):
            log.info('creating  %s for api %s', obj.__name__, api)
            new_name = "%s%s" % (obj.__name__, api.upper())
            new_dict = dict(obj.__dict__)
            new_dict.update({'api': api})
            new_obj = type(new_name, obj.__bases__, new_dict)
            log.info('%s for api %s created', new_obj.__name__, api)

            objs.append(defaultTestLoader().loadTestsFromTestCase(new_obj))

        return defaultTestLoader().suiteClass(objs)
