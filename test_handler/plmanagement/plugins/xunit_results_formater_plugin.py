
import os
from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.application import IConfigurable
from test_handler.plmanagement.interfaces.report_formatter import IResultsFormatter

class XUnit(Component):
    """
    Generates x-unit report; deafult: %(const)s
    """
    implements(IResultsFormatter, IConfigurable)
    name = 'X unit'
    enabled = True
    default_file_name = "xunit_output.xml"

    def __init__(self):
        super(XUnit, self).__init__()
        self.path = None

    @classmethod
    def add_options(cls, parser):
        out = os.path.expanduser("~/results/%s" % cls.default_file_name)
        parser.add_argument('--rf-x-unit', action="store", dest='rf_x_unit', \
                help=cls.__doc__, const=out, default=None, nargs='?')

    def configure(self, params, config):
        self.path = params.rf_x_unit

    def generate_report(self, reports):
        # TODO: implement it
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        return params.rf_x_unit is not None

