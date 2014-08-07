import os.path
import re
import logging
import urllib
import time
import config

LOGGER = logging.getLogger(__name__)

CPU = 'cpu'
MEMORY = 'mem'
IO = 'io'
NETWORK = 'net'

MEM_PHYS = 'RSS'
MEM_SHRD = 'ps'
NET_IN = 'IN'
NET_OUT = 'OUT'

ENGINE = 'jboss'
ENGINE_REPORTS = 'dwh'
DB = 'postgres'
TOTAL = 'total'
SYSTEM = 'system'

TEMPLATE_DIR = 'templates'
TEMPLATE_NAME = 'engine_resources.html'


class ResourceMonitor(object):
    """
        Based class for compute and saving of host(-s)
        resources measurements.
        Nagios used as a source of data currently.
    """

    def formatted_time(self, time_sec):
        """
            Format time from seconds to readable hour:min string
            Parameters:
                * time_sec - time in seconds since the epoch
            Return:
                string in the format hour:min
        """
        return time.strftime('%H:%M', time.localtime(time_sec))

    def _get_data_from_url(self, url, patt, result):
        """
            Get data specified by pattern from url
            Parameters:
                * url - URL to data in text format
                * patt - pattern to search
                * dictionary to save data
        """
        try:
            fh = urllib.urlopen(url)
            lines = fh.readlines()
            fh.close()
            member = None
            for line in lines:
                res = patt.search(line)
                if res:
                    m = line.split(',')
                    member = m[0]
                    valid_data = [float(v) for v in m[4:]
                                  if v != 'None' and v != 'None\n']
                    if len(valid_data) >= (len(m[4:]) / 2):
                        LOGGER.warning(
                            "Too much of non-valid data from url %s", url)
                    avg = sum([v for v in valid_data]) / len(valid_data) \
                        if valid_data else None
                    result[member] = dict(start=m[1], end=m[2],
                                          step=m[3].split('|')[0],
                                          data=m[4:], avg=avg)
            if not member:
                raise Exception("Failed to parse url data, wrong content type")
        except IOError:
            LOGGER.error("Failed to open url %s", url)
        except Exception as ex:
            LOGGER.error("Failed to get data from url %s, error: %s",
                         url, ex)

    def _prepare_avg_data(self, url_data):
        """
            Format average data
            Parameters:
                * url_data - dictionary containing data
                * patt - pattern to search
            Return:
                list of average values
        """
        header = url_data.keys()
        try:
            return [header,
                    [round(url_data[header[k]]['avg'], 2)
                     for k in range(len(header))]]
        except Exception as ex:
            LOGGER.error("Failed to prepare average data for template: %s", ex)
            return []

    def _prepare_data_for_template(self, url_data):
        """
            Format data for html tamplate
            Parameters:
                * url_data - dictionary containing data
            Return:
                dictionary of processed data
        """
        template_data = []
        try:
            header = url_data.keys()
            key = header[0]
            start_time = int(url_data[key]['start'])
            time_step = int(url_data[key]['step'])
            for i in range(len(url_data[key]['data'])):
                step_data = []
                for k in range(len(header)):
                    step_data.append(url_data[header[k]]['data'][i])
                if 'None' in step_data:
                    continue
                if 'None\n' in step_data:
                    break
                step_data_adj = [round(float(step_data[j]), 2)
                                 for j in range(len(step_data))]
                step_data_adj.insert(0, self.formatted_time(
                                     start_time + time_step * i))
                template_data.append(step_data_adj)
            header.insert(0, 'Time')
            template_data.insert(0, header)
        except Exception as ex:
            LOGGER.error("Failed to prepare data for template: %s", ex)

        avg_data = self._prepare_avg_data(url_data)
        all_data = {'all': template_data, 'avg': avg_data}
        return all_data

    def get_data_from_url(self):
        """
        Get resource data from url
        """
        self._get_data_from_url(self.URL, self.patt, self.data)
        return self._prepare_data_for_template(self.data)


class CPUMonitor(ResourceMonitor):
    """
    Class responsible for collecting of CPU measurements.
    """

    URL = config.CPU_URL

    def __init__(self):
        super(CPUMonitor, self).__init__()
        self.data = {
            ENGINE: {},
            ENGINE_REPORTS: {},
            DB: {},
            TOTAL: {},
        }
        self.patt = re.compile(
            '{0}|{1}|{2}|{3}'.format(
                ENGINE,
                ENGINE_REPORTS,
                DB,
                TOTAL
            ),
            re.I
        )


class MemoryMonitor(ResourceMonitor):
    """
    Class responsible for collecting of memory -
    physical and shared - measurements.
    """

    URL = config.MEMORY_URL

    def __init__(self):
        super(MemoryMonitor, self).__init__()
        self.data = {
            '%s %s' % (ENGINE, MEM_PHYS): {},
            '%s %s' % (ENGINE, MEM_SHRD): {},
            '%s %s' % (ENGINE_REPORTS, MEM_PHYS): {},
            '%s %s' % (ENGINE_REPORTS, MEM_SHRD): {},
            '%s %s' % (DB, MEM_PHYS): {},
            '%s %s' % (DB, MEM_SHRD): {},
            '%s %s' % (TOTAL, MEM_PHYS): {},
            '%s %s' % (TOTAL, MEM_SHRD): {},
        }
        self.patt = re.compile(
            '{0} {1}|{2} {3}|{4} {5}|{6} {7}|{8} {9}|{10} '
            '{11}|{12} {13}|{14} {15}'.format(
                ENGINE,
                MEM_PHYS,
                ENGINE,
                MEM_SHRD,
                ENGINE_REPORTS,
                MEM_PHYS,
                ENGINE_REPORTS,
                MEM_SHRD,
                DB,
                MEM_PHYS,
                DB,
                MEM_SHRD,
                TOTAL,
                MEM_PHYS,
                TOTAL,
                MEM_SHRD
            ),
            re.I
        )


class NetworkMonitor(ResourceMonitor):
    """
    Class responsible for collecting of network measurements.
    """

    URL = config.NETWORK_URL

    def __init__(self):
        super(NetworkMonitor, self).__init__()
        self.data = {
            '%s %s' % (ENGINE, NET_IN): {},
            '%s %s' % (ENGINE, NET_OUT): {},
            '%s %s' % (ENGINE_REPORTS, NET_IN): {},
            '%s %s' % (ENGINE_REPORTS, NET_OUT): {},
            '%s %s' % (DB, NET_IN): {},
            '%s %s' % (DB, NET_OUT): {},
            '%s %s' % (TOTAL, NET_IN): {},
            '%s %s' % (TOTAL, NET_OUT): {},
        }
        self.patt = re.compile(
            '{0} {1}|{2} {3}|{4} {5}|{6} {7}|{8} {9}|{10} '
            '{11}|{12} {13}|{14} {15}'.format(
                ENGINE,
                NET_IN,
                ENGINE,
                NET_OUT,
                ENGINE_REPORTS,
                NET_IN,
                ENGINE_REPORTS,
                NET_OUT,
                DB,
                NET_IN,
                DB,
                NET_OUT,
                TOTAL,
                NET_IN,
                TOTAL,
                NET_OUT),
            re.I
        )


class IOMonitor(ResourceMonitor):
    """
    Class responsible for collecting of disk I/O measurements.
    """

    URL = config.IO_URL

    def __init__(self):
        super(IOMonitor, self).__init__()
        self.data = {
            ENGINE: {},
            ENGINE_REPORTS: {},
            DB: {},
            TOTAL: {},
        }
        self.patt = re.compile(
            '{0}|{1}|{2}|{3}'.format(
                ENGINE,
                ENGINE_REPORTS,
                DB,
                TOTAL),
            re.I
        )


class ResourcesTemplate(object):
    """
    Create resource monitoring report in html format
    using template engine jinja2
    """

    def __init__(self):
        self.template_path = os.path.join(os.path.dirname(__file__),
                                          TEMPLATE_DIR)
        self.out_file = config.MEASURE_RES_FILE
        self.data = {}

    def _create_out_file(self):
        """
        Format out file name
        """
        tstamp = time.strftime('%Y%m%d_%H%M%S')
        return '{0}_{1}.html'.format(self.out_file, tstamp)

    def collect_data(self):
        """
        collect all the data resources
        """
        try:
            self.data.update(dict(CPU=CPUMonitor().get_data_from_url()))
            self.data.update(dict(MEMORY=MemoryMonitor().get_data_from_url()))
            self.data.update(
                dict(
                    NETWORK=NetworkMonitor().get_data_from_url()
                )
            )
            self.data.update(dict(IO=IOMonitor().get_data_from_url()))
        except Exception as ex:
            LOGGER.error("Failed to collect data from URLs: %s", ex)

    def create_report(self, title):
        """
        Create html report
        Parameters:
            * title - report title
        """
        self.collect_data()
        try:
            from jinja2 import Environment, FileSystemLoader
            env = Environment(loader=FileSystemLoader(self.template_path))
            template = env.get_template(TEMPLATE_NAME)
            template_as_str = template.render(title=title, data=self.data)

            ofile = self._create_out_file()
            LOGGER.info("Resources report saved in file: %s" % ofile)
            with open(ofile, 'w') as of:
                of.write(template_as_str)
        except Exception as ex:
            LOGGER.error("Failed to create html report: %s", ex)
