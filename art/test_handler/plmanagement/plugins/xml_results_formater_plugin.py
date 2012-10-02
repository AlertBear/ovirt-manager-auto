from lxml.etree import Element, ElementTree
from lxml.builder import E
import threading
import datetime
from dateutil import tz

import os
from art.test_handler.plmanagement import Component, implements
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.report_formatter import IResultsFormatter
from art.test_handler.plmanagement.interfaces.packaging import IPackaging


# TODO: same problem as tcms_plugin


class XMLFormatter(Component):
    """
    Generates XML report; default: %(const)s
    """
    implements(IResultsFormatter, IConfigurable, IPackaging)
    name = 'XML'
    enabled = True
    default_file_name = "results.xml"
    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self):
        super(XMLFormatter, self).__init__()
        self.path = None
        self.root = None
        self.tree = None

    @classmethod
    def add_options(cls, parser):
        out = os.path.abspath("results/%s" % cls.default_file_name)
        parser.add_argument('--rf-xml', '--res', action="store", dest='rf_xml', \
                help=cls.__doc__, const=out, default=out, nargs='?')

    def configure(self, params, config):
        if not self.is_enabled(params, config):
            return
        self.path = params.rf_xml
        self.suite_type = config['RUN']['engine']
        self.root = Element(self.suite_type)
        self.tree = ElementTree(self.root)
        self.root.attrib['testfile'] = config['RUN']['tests_file']
        from art.test_handler.settings import opts
        self.root.attrib['logfile'] = opts['log']

    # FIXME: I hate this hardcoded names, get rid of them
    def add_test_result(self, kwargs, test_case):
        if not kwargs._report:
            return
        module = Element(kwargs['module_name']) \
                    if kwargs['module_name'] \
                    else Element('test')
        if 'group_desc' in kwargs:
            module.set('description', kwargs['group_desc'])

        # Convet times to machine-local timezone and write it.
        local_tz = tz.tzlocal()
        s_time = kwargs['start_time'].astimezone(local_tz)
        e_time = kwargs['end_time'].astimezone(local_tz)
        module.append(E.start_time(s_time.strftime(self.TIME_FORMAT)))
        module.append(E.end_time(e_time.strftime(self.TIME_FORMAT)))

        # Write the remaining fields.
        written = set(['start_time', 'end_time', 'module_name', 'group_desc'])
        for key in set(kwargs.keys()) - written:
            element = Element(key)
            element.text = unicode(kwargs[key])
            module.append(element)

        self.root.append(module)
        self.generate_report()

    def generate_report(self):
        if self.tree is not None:
            folder = os.path.dirname(self.path)
            if not os.path.exists(folder):
                os.makedirs(folder)
            self.tree.write(self.path, encoding="utf-8",
                            pretty_print=True, xml_declaration=True)

    @classmethod
    def is_enabled(cls, params, conf):
        #return params.rf_xml is not None
        return True # on requirement: this should be default format
        # NOTE: in this case it means, XML report will be generated everytime

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'xml-reports'
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'XML results formatter for ART'
        params['long_description'] = 'Plugin for ART which allows to you '\
                'generete results in XML format.'
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.xml_results_formater_plugin']

