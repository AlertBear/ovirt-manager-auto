__author__ = 'khakimi'

import threading
import collections
import logging.config
import logging.handlers
import os
import re
import yaml
from jinja2 import Environment, FileSystemLoader


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGGER_UTILS_CONF = 'logger_utils.conf'
DEFAULT_CONF_FILE = os.path.join(BASE_DIR, LOGGER_UTILS_CONF)
DEFAULT_LOG_FILE = '/var/tmp/test.log'
TEMP_CONFIG_FILE = '/tmp/transformed_log_config.conf'


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
    env = Environment(loader=FileSystemLoader('/'))
    template = env.get_template(conf_file)
    rendered_data = template.render(logfile=log_file)
    config = yaml.load(rendered_data)
    logging.config.dictConfig(config)


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
