__author__ = 'khakimi'

import threading
import collections
import logging.config
import logging.handlers
import os
import re
import sys
import yaml
from ConfigParser import ConfigParser
if sys.version_info < (2, 7):
    # There is no NullHandler < py2.7
    class NullHandler(logging.Handler):
        def emit(self, *args, **kwargs):
            pass
else:
    from logging import NullHandler  # flake8: noqa


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGGER_UTILS_CONF = 'logger_utils.conf'
DEFAULT_CONF_FILE = os.path.join(BASE_DIR, LOGGER_UTILS_CONF)
DEFAULT_LOG_FILE = '/var/tmp/test.log'
TEMP_CONFIG_FILE = '/tmp/transformed_log_config.conf'


def fileConfig(fname, defaults=None, disable_existing_loggers=True):
    """
    We would like to use logging.config.dictConfig, but it is new in 2.7
    and we still needs to support 2.6. This function transforms yaml to ini.

    :param fname: ini / yaml logger config
    :type fname: str
    """
    if fname.endswith('.yaml') or fname.endswith('.yml'):
        # Load yaml config for dictConfig
        y2i = Yaml2IniConfig(defaults=defaults)
        with open(fname) as fh:
            y2i.read(fh)
        # Write ini config for fileConfig
        with open(TEMP_CONFIG_FILE, 'w') as fh:
            y2i.write(fh)
        fname = TEMP_CONFIG_FILE

    # Configure logger
    logging.config.fileConfig(fname, defaults, disable_existing_loggers)


class Yaml2IniConfig(object):
    """
    Translate YAML logger config to INI logger config.
    """
    elements = (
        ('formatter', 'formatters'),
        ('logger', 'loggers'),
        ('handler', 'handlers'),
    )
    reserved_keys = {
        'formatter': set(['format', 'datefmt']),
        'logger': set(),
        'handler': set(['formatter', 'level']),
    }

    def __init__(self, defaults=None):
        super(Yaml2IniConfig, self).__init__()
        self._ini = ConfigParser(defaults=defaults)
        self._yml = None

    def _translate_section(self, element, collection):
        elements = []
        for fn, fv in self._yml.get(collection, {}).iteritems():
            if fv is None:
                continue
            elements.append(fn)
            in_ = "%s_%s" % (element, fn)
            self._ini.add_section(in_)
            if '()' in fv or 'class' in fv:  # Custom
                self._ini.set(
                    in_, 'class', fv.pop('()', fv.pop('class', None))
                )
                # Put reserved keys first
                for reserved in self.reserved_keys[element]:
                    if reserved in fv:
                        self._ini.set(in_, reserved, fv.pop(reserved))
                # Compose arguments for constructor from remaining
                args = [
                    arg[1] for arg in sorted(
                        fv.items(), cmp=lambda x, y: cmp(x[0], y[0])
                    )
                ]
                self._ini.set(in_, 'args', self._create_args(args))
            else:
                for key, value in fv.iteritems():
                    if isinstance(value, (list, tuple)):
                        value = ','.join(value)
                    self._ini.set(in_, key, value)
        # Update list of elements
        if not self._ini.has_section(collection):
            self._ini.add_section(collection)
            self._ini.set(collection, 'keys', ','.join(elements))
        else:
            keys = self._ini.get(collection, 'keys')
            new_keys = ','.join(elements)
            if keys and new_keys:
                keys = keys + ',' + new_keys
            else:
                keys = keys + new_keys
            self._ini.set(collection, 'keys', keys)

    def _create_args(self, args):
        value = "("
        for a in args:
            if isinstance(a, basestring):
                if a.startswith('ext://'):
                    value = "%s%s," % (value, a[6:])
                else:
                    value = "%s'%s', " % (value, a)
            else:
                value = "%s%s," % (value, a)
        return value + ")"

    def _translate(self):
        for e, c in self.elements:
            self._translate_section(e, c)

    def read(self, fd):
        self._yml = yaml.load(fd)
        self._translate()

    def write(self, fd):
        self._ini.write(fd)


class ColoredFormatter(logging.Formatter):
    """
    class to colorize the log level name
    """

    # define the foreground colors
    BLACK, RED, GREEN, YELLOW, BLUE = range(30, 35)

    COLORS = {
        'WARNING': YELLOW,
        'INFO': GREEN,
        'DEBUG': BLUE,
        'CRITICAL': RED,
        'ERROR': RED,
    }

    def __init__(self, fmt, datefmt):
        logging.Formatter.__init__(self, fmt=fmt, datefmt=datefmt)
        self._fmt_original = fmt
        self._regex = re.compile(r'(%[(]levelname[)]s)')

    def format(self, record):
        """
        colorize the level name
        :param record: log record to update the levelname
        :type record: LogRecord object
        :return : the formatted message
        :rtype : str
        """
        color = self.COLORS.get(record.levelname)
        if color:
            # This is the sequences need to get colored level name
            replacement = "\\033[{0}m%(levelname)s\\033[0m".format(color)
            self._fmt = self._regex.sub(replacement, self._fmt_original)
        msg = logging.Formatter.format(self, record)
        self._fmt = self._fmt_original
        return msg


class DuplicatesFilter(logging.Filter):
    """
    This is a filter which removes duplications of the same log
    In the case where we query an object a lot of times,
    while waiting for object status to change
    we see a lot of logs, which look the same, but actually make it more
    difficult to read the logs
    also this results in a large log, which cannot be processed by junit plugin
    """

    SKIPPING_MSG = 'Skipping duplicate log-messages...'

    def __init__(self, *args, **kwargs):
        logging.Filter.__init__(self, *args, **kwargs)
        self._lock = threading.Lock()
        self.last_records = collections.deque()
        self.num_records_to_keep = 4

    def filter(self, record):
        with self._lock:
            # if the current message is 'skipping' we dont want it
            if record.msg == self.SKIPPING_MSG:
                return False
            for rec in self.last_records:
                if (
                    record.levelname == rec['level']
                    and record.msg == rec['msg']
                    and record.args == rec['args']
                ):
                    # we already printed the skipping message
                    if rec['duplicate']:
                        return False
                    # update the current record so it will print 'skipping...'
                    # this update triggers the filter again
                    record.msg = self.SKIPPING_MSG
                    record.levelname = 'DEBUG'
                    record.args = None
                    rec['duplicate'] = True
                    return True
            # we want to keep only the last num_records_to_keep records
            if len(self.last_records) == self.num_records_to_keep:
                self.last_records.popleft()
            self.last_records.append(
                {'msg': record.msg, 'level': record.levelname,
                 'args': record.args, 'duplicate': False}
            )
            return True


def initialize_logger(conf_file=DEFAULT_CONF_FILE, log_file=DEFAULT_LOG_FILE):
    """
    Initialize logger so that it spits output to file and stdout.
    Colorize only the messages going to stdout to not cause mess in the files.
    :param conf_file: full path conf file
    :type conf_file: str
    :param log_file: full path to log file
    :type log_file: str
    """
    fileConfig(
        conf_file, disable_existing_loggers=False,
        defaults={'logfile': log_file},
    )


class DuplicateFileHandler(logging.handlers.RotatingFileHandler):
    """
    Handler for file logging request with duplicates filter
    """

    def __init__(self, *args, **kwargs):
        logging.handlers.RotatingFileHandler.__init__(self, *args, **kwargs)
        self.addFilter(DuplicatesFilter())


class DuplicateConsoleHandler(logging.StreamHandler):
    """
    Handler for file console request with duplicates filter
    """

    def __init__(self, *args, **kwargs):
        logging.StreamHandler.__init__(self, *args, **kwargs)
        self.addFilter(DuplicatesFilter())
