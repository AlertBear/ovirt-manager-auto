import logging
import os
from nose.util import transplant_class
from nose.plugins import Plugin as NosePlugin
from art.test_handler.settings import opts
from art.test_handler.plmanagement import get_logger

log = logging.getLogger('nose.plugins.apiselector')
art_log = get_logger("apiselector")


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
        self.original_engine = opts['engine']

    def prepareTestLoader(self, loader):
        # we need to use configured loader in order to have plugins working
        self.loader = loader

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

            objs.append(self.loader.loadTestsFromTestCase(new_obj))

        return self.loader.suiteClass(objs)

    def _set_api(self, test):
        api = getattr(test, 'api', None)
        if not api:
            return
        opts['engine'] = api
        art_log.info("The API backend switched to %s", api)

    def startTest(self, test):
        self._set_api(test)

    def stopTest(self, test):
        opts['engine'] = self.original_engine
        art_log.info("The API backend switched to %s", self.original_engine)
