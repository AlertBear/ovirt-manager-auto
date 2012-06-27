
import os
from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.application import IConfigurable
from test_handler.plmanagement.interfaces.report_formatter import IResultsFormatter

class XMLFormatter(Component):
    """
    Generates XML report; default: %(const)s
    """
    implements(IResultsFormatter, IConfigurable)
    name = 'XML'
    enabled = True
    default_file_name = "xml_output.xml"

    def __init__(self):
        super(XMLFormatter, self).__init__()
        self.path = None

    @classmethod
    def add_options(cls, parser):
        out = os.path.expanduser("~/results/%s" % cls.default_file_name)
        parser.add_argument('--rf-xml', action="store", dest='rf_xml', \
                help=cls.__doc__, const=out, default=None, nargs='?')

    def configure(self, params, config):
        self.path = params.rf_xml

    def generate_report(self, reports):
        # TODO: implement it
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        return params.rf_xml is not None

