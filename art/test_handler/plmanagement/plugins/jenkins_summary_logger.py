#!/usr/bin/env python
import os
import logging
from art.test_handler.plmanagement import get_logger, PluginError

logger = logging.getLogger('jenkins_summary_logger')
fw_logger = get_logger('jenkins_summary_logger')

def to_filename(s):
    """
    Just a simple check... safe enough thoug
    """
    return "".join(x for x in s if x.isalnum())


class Cell():
    "A simple table cell"
    def __init__(self, value, data=None, title=None, bgcolor="#ffffff",
                 fontcolor="#000000", fontattribute="normal", href=None,
                 align="none", width=None):
        self._add_attribs(value=value, data=data, title=title or value,
                           bgcolor=bgcolor, fontcolor=fontcolor,
                           fontattribute=fontattribute, href=href,
                           align=align, width=width)

    def _add_attribs(self, **kwargs):
        for name, val in kwargs.iteritems():
            setattr(self, name, val)

    def get_attr_str(self, attr):
        return hasattr(self, attr) \
                and ' %s="%s"' % (attr, getattr(self, attr)) \
                or ''

    def __str__(self):
        return '<td' \
               + ''.join(self.get_attr_str(attr)
                         for attr in ('value', 'title', 'bgcolor', 'fontcolor',
                                      'fontattribute', 'href', 'align',
                                      'width')) \
               + (self.data and '>%s</td>' % self.data or '/>')

    def __eq__(self, other):
        """
        The value is what is printed with the href in the table, so it's used
        as the identifier of the cell, rather than title or data
        """
        return self.value == other.value


class Table(dict):
    """
    NOTE: This implementation of an htlm table does not allow repeated rows
    nor columns
    """
    def __init__(self, sorttable=True):
        super(dict, self).__init__()
        self.sorttable = sorttable
        self.cols = []

    def add_col(self, cname, **attribs):
        if Cell(cname) in self.cols:
            return
        if 'fontattribute' not in attribs:
            attribs['fontattribute'] = 'bold'
        self.cols.append(Cell(cname, **attribs))
        for rname, row in self.iteritems():
            self[rname].append(Cell(''))

    def add_row(self, rname, **attribs):
        if rname in self.keys():
            return
        if 'fontattribute' not in attribs:
            attribs['fontattribute'] = 'bold'
        self[rname] = [Cell(rname, **attribs)] + [Cell('')] * len(self.cols)

    def add_cell(self, rname, cname, data, **attribs):
        """
        Adds a cell to the table, attribs is a dict with the attribs for the
        given cell (see the cell definition to see the valid attribs)
        """
        if rname not in self:
            self.add_row(rname)
        if Cell(cname) not in self.cols:
            self.add_col(cname)
        self[rname][self.cols.index(Cell(cname)) + 1] = Cell(data, **attribs)

    def generate_xml(self):
        return '<table%s>\n\t<tr>\n\t\t<td></td>\n\t\t' \
                    % (self.sorttable and ' sortable="yes" ' or '') \
               + '\n\t\t'.join('%s' % cell for cell in self.cols) \
               + '\n\t</tr>' \
               + '\n'.join('\n\t<tr>\n\t\t'
                            + '\n\t\t'.join('%s' % data for data in row)
                            + '\n\t</tr>' for row in self.itervalues()
                            ) \
               + '\n</table>'


def getLogger(logger_name, *args, **kwargs):
    """
    Customize our logger to add the new methods and attributes
    It's a replacement to the logging.getLogger method
    """
    return LoggerWrapper(logger_name, *args, **kwargs)


def element(fn):
    """
    Decorator that handles the addition of new elements to the xml output
    """
    if fn.__name__.startswith('logger_'):
        fn.__name__ = fn.__name__[7:]
    def fun(self, open=True, *args, **kwargs):
        if open:
            if hasattr(self, fn.__name__ + '_close'):
                self.opened.append(getattr(self, fn.__name__ + '_close'))
            else:
                self.opened.append(lambda: self.write('</%s>' % fn.__name__))
            fn(self, *args, **kwargs)
        else:
            self.close_one()
    return fun


"""
Actually all the methods that start with 'logger_' are added to the logger
instance

The ones with the descriptor @element, will add some function that
will be called when closing the element. (</element_name> by default).
This default function is overriden with the function logger_element_name_close

TODO: implement tabs and accordion
TODO: Autoclose entities when oppening one that can not be inside the opened
      one
"""
class LoggerWrapper():
    def __init__(self, section_name='noname', logdir="."):
        """
        It must have one section per file, no more and no less. Each time you
        create a new section, a new file is created.
        """
        ## This variable stores the 'closing' methods of all the opened elements
        self.opened = []
        self.logdir = logdir
        self.section(name=section_name, close=False)
        self.tables = []

    def close_one(self):
        """
        Closes the last opened element
        """
        if not self.opened:
            raise PluginError("Nothing to close")
        self.opened.pop()()

    def close(self, num):
        """
        Closes the last opened element
        """
        for n in xrange(num):
            self.close_one()

    def write(self, data):
        if hasattr(self, 'fd'):
            self.fd.write(data)
            self.fd.flush()

    ## Section element
    @element
    def section(self, name='noname', fontcolor='#000000', close=True):
        if close:
            self.close_one()
        if hasattr(self, 'fd'):
            fw_logger.info("Generated summary XML report at %s" % self.fd.name)
            self.fd.close()
        fname = os.path.join(self.logdir, to_filename(name) + '_summary_report.xml')
        self.fd = open(fname, 'w')
        fw_logger.info("Generating summary XML report at %s" % self.fd.name)
        self.write('<section name="%s" fontcolor="%s">' % (name, fontcolor))

    ## Table element
    @element
    def table(self):
        self.tables.append(Table())

    def table_close(self):
        if self.tables:
            tbl = self.tables.pop()
            self.write(tbl.generate_xml())

    def table_add_column(self, cname, **attribs):
        if not self.tables:
            self.table()
        self.tables[-1].add_col(cname, **attribs)

    def table_add_row(self, rname, **attribs):
        if not self.tables:
            self.table()
        self.tables[-1].add_row(rname, **attribs)

    def table_add_cell(self, row, column, data, **attribs):
        if not self.tables:
            self.table()
        self.tables[-1].add_cell(row, column, data, **attribs)

    ## Field element
    @element
    def field(self, name='noname', value='', href='', type='',
                           titlecolor='', detailcolor='#000000', cdata=None):
        self.write('<field name="%(name)s" value="%(value)s" href="%(href)s" '
                   'type="%(type)s" titlecolor="%(titlecolor)s" '
                   'detailcolor="%(detailcolor)s">' % locals())
        if cdata:
            self.write('<![CDATA[\n%s\n]]>' % (cdata,))
        self.close_one()

    def close_all(self):
        "Close all the remaining opened elements"
        while self.opened:
            self.opened.pop()()


"""
Usage example
"""
if __name__ == '__main__':
    ## get the logger, this creates a file named test.xml with a section named
    ## test on it
    log = getLogger('test')
    ## add a section, this will create a new file also
    log.section(name='Logstash logs')
    ## add some fields with data
    log.field(name='field1', cdata="lerele")
    log.field(name='field2')
    ## add a new section, that will create a new file and will finish (add the
    ## closing tags) of the one before
    log.section(name='section2')
    log.table()
    log.table_add_column('col1')
    log.table_add_column('col2')
    log.table_add_row('row1')
    log.table_add_row('row2')
    ## add some data
    log.table_add_cell('row1', 'col1', 'data1', href='http://www.redhat.com')
    log.table_add_cell('row1', 'col2', 'data2')
    log.table_add_cell('row2', 'col1', 'data3')
    log.table_add_cell('row2', 'col2', 'data4')
    ## you can add more columns, the data for the new cells will be '' by default
    log.table_add_column('col2')
    ## painfully the last one still must be closed explicitly
    log.close_all()
