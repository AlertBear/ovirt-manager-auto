#! /usr/bin/python
# -*- coding: utf-8 -*-

import logging
from art.rhevm_api.utils.test_utils import get_api


logger = logging.getLogger('cpumodel')

VERSION = get_api('cluster_level', 'clusterlevels')
MIN_MODEL = {
    'Intel': "model_Conroe",
    'AMD': "model_Opteron_G1",
    'IBM POWER': 'model_POWER7_v2.0',
}


class CpuModelError(Exception):
    pass


class UnknownCpuModel(CpuModelError):
    pass


class HostVendorMismatch(CpuModelError):
    """
    This exception happens when you try mix two different vendors.
    For example: Intel and AMD
    """


class CpuModelDenominator(object):
    """
    Helps you to find the highest common denominator of cpu model
    for list of hosts.

    c = CpuModelDenominator()

    try:
        cpu_info = c.get_common_cpu_model(config.VDS_HOSTS)
    except CpuModelError:  # Fallback
        cpu_info = c.get_minimal_cpu_model(config.VDS_HOSTS)

    cpu_info = c.get_common_cpu_model(config.VDS_HOSTS, version="3.0")

    ...
    """
    def __init__(self):
        super(CpuModelDenominator, self).__init__()
        self.cpus = dict(
            (
                v.get_id(), {
                    "cpus": [
                        {
                            'cpu': c.get_name(),
                            'level': c.get_level(),
                            'model': self._id_to_model(c.get_name()),
                            'vendor': self._id_to_vendor(c.get_name()),
                        } for c in v.get_cpu_types().get_cpu_type()
                    ],
                    'current': v.get_id(),
                }
            ) for v in VERSION.get(abs_link=False)
        )

    def _id_to_model(self, cpu_id):
        model = 'model_'
        if 'Intel' in cpu_id:
            model += cpu_id.split(' ')[1]
        elif 'AMD' in cpu_id:
            model += cpu_id[4:].replace(' ', '_')
        elif 'IBM POWER' in cpu_id:
            split_name = cpu_id.split()
            if len(split_name) == 4:
                model += "%s%s_%s" % tuple(split_name[1:])
            elif len(split_name) == 3:
                model += "%s%s" % tuple(split_name[1:])
            else:
                logger.warning("Unknown model name: %s", cpu_id)
                model = None
        else:
            logger.warning('Unknown vendor of %s', cpu_id)
            model = None
        return model

    def _id_to_vendor(self, cpu_id):
        vendor = None
        if 'Intel' in cpu_id:
            vendor = 'Intel'
        elif 'AMD' in cpu_id:
            vendor = 'AMD'
        elif 'POWER' in cpu_id:
            vendor = 'IBM POWER'
        return vendor

    def get_cpu_list(self, version=None):
        """
        :param version: rhevm version (compatibility)
        :type version: string
        :return: list of cpu info
        :rtype: list(dict(cpu=str, level=int, model=str, vendor=str))
        """
        if version is None:
            # Find current version
            try:
                return [
                    c['cpus'] for c in self.cpus.itervalues()
                    if c['current']
                ][0]
            except IndexError:
                return CpuModelError(
                    "There is no cpu list for current version"
                )
        try:
            return self.cpus[str(version)]['cpus']
        except KeyError:
            raise CpuModelError("Version %s is not supported" % version)

    def fetch_host_caps(self, host):
        """
        Retrieves host's cpu capabilities, provided by vdsm and /proc/cpuinfo.

        Args:
            host (Host): instance of resources.Host

        Returns
            dict: host's cpu capabilities dict(models=list(str), vendor=str)
        """
        e = host.executor()
        cmd_cpuinfo = (
            'grep', 'vendor_id', '/proc/cpuinfo', '|',
            'sort', '|',
            'uniq', '|',
            'cut', '-d:', '-f2',
        )
        with e.session() as ss:
            # Find vendor
            rc, out, err = ss.run_cmd(cmd_cpuinfo)
            vendor = out.strip()
            if rc or not vendor:
                raise CpuModelError("Can not resolve host's cpuinfo: %s" % err)

            # List cpu models
            vds_caps = host.vds_client(cmd="Host.getCapabilities")
            vds_caps = dict() if not vds_caps else vds_caps
            cpu_flags = vds_caps.get("cpuFlags", "").split(",")
            models = [i for i in cpu_flags if "model_"in i]
            if not models:
                logger.warning("Can not resolve host's models: %s", err)
                models = [
                    MIN_MODEL.get(self._id_to_vendor(vendor))
                ]
                logger.warning(
                    "Setting minimal cpu model for %s: %s", vendor, models[0])
        return {
            'models': models,
            'vendor': vendor,
        }

    def get_cpu_info(self, value, key='model', version=None):
        """
        Gets cpu info by one of the cpu info dictionary keys - default is model

        Args:
            value (obj): Value to filter cpu info by
            key (str): Which key from cpu info dictionary to filter by (can be
                'model', 'cpu', 'level', vendor')
            version (str): Compatibility version to get cpu list from

        Returns:
            dict: cpu info = dict(cpu=str, level=int, model=str, vendor=str)
        """
        try:
            return [
                cpu for cpu in self.get_cpu_list(version)
                if cpu[key] == value
            ][0]
        except IndexError:
            raise UnknownCpuModel("%s for %s version" % (value, version))

    def _list_cpu_info(self, models, version):
        info_list = []
        for model in models:
            try:
                info_list.append(self.get_cpu_info(model, version=version))
            except UnknownCpuModel as ex:
                logger.warning("Unsupported model: %s", ex)
        return info_list

    def get_common_cpu_model(self, hosts, version=None):
        """
        Finds the maximal compatible cpu model which has all passed hosts
        in common, considering compatibility version as well.
        :param hosts: list of hosts
        :type hosts: list(resources.Host)
        :param version: compatibility version
        :type version: str
        :return: cpu info for specific model which is common for all of them.
        :rtype: dict(cpu=str, level=int, model=str, vendor=str)
        """
        selected_cpu = None
        for host in hosts:
            host_info = self.fetch_host_caps(host)
            best_cpu = max(
                self._list_cpu_info(host_info['models'], version),
                key=lambda info: info['level']
            )
            if selected_cpu is None:
                selected_cpu = best_cpu
            else:
                if best_cpu['vendor'] != selected_cpu['vendor']:
                    raise HostVendorMismatch(
                        "%s != %s" % (
                            best_cpu['vendor'], selected_cpu['vendor'],
                        )
                    )
                if best_cpu['level'] < selected_cpu['level']:
                    selected_cpu = best_cpu
        return selected_cpu

    def get_minimal_cpu_model(self, hosts, version=None):
        """
        Select minimal cpu_model for vendor, this function just make sure that
        both host have same vendor.
        :param hosts: list of hosts
        :type hosts: list(resources.Host)
        :param version: compatibility version
        :type version: str
        :return: cpu info for specific model which is minimal for vendor.
        :rtype: dict(cpu=str, level=int, model=str, vendor=str)
        """
        vendor = None
        for host in hosts:
            host_info = self.fetch_host_caps(host)
            if vendor is None:
                vendor = self._id_to_vendor(host_info['vendor'])
            else:
                host_vendor = self._id_to_vendor(host_info['vendor'])
                if vendor != host_vendor:
                    raise HostVendorMismatch(
                        "%s != %s" % (vendor, host_vendor,)
                    )
        return self.get_cpu_info(MIN_MODEL.get(vendor), version=version)

    def get_maximal_cpu_model(self, hosts, version=None):
        """
        Get the cpu model name of the host with the highest cpu model from
        a list of hosts.

        Args:
            hosts (list): list of hosts resources objects
            version (str): compatibility version

        Returns:
            dict(cpu=str, level=int, model=str, vendor=str):
            cpu info for the host with highest cpu model.
        """
        max_cpu_of_all_hosts = None
        for host in hosts:
            host_info = self.fetch_host_caps(host)
            # Determine the highest cpu model supported by 'host'
            max_host_cpu = max(
                self._list_cpu_info(host_info.get('models'), version),
                key=lambda info: info.get('level')
            )
            # Initialize 'max_cpu_of_all_hosts' in 1st iteration
            if max_cpu_of_all_hosts is None:
                max_cpu_of_all_hosts = max_host_cpu
            else:
                # check if we are comparing between cpu models of same vendor
                if (
                    max_host_cpu.get('vendor') !=
                    max_cpu_of_all_hosts.get('vendor')
                ):
                    raise HostVendorMismatch(
                        "%s != %s" % (
                            max_host_cpu.get('vendor'),
                            max_cpu_of_all_hosts.get('vendor'),
                        )
                    )
                # Updates 'max_cpu_of_all_hosts' if higher model found
                if (
                    max_host_cpu.get('level') >
                    max_cpu_of_all_hosts.get('level')
                ):
                    max_cpu_of_all_hosts = max_host_cpu
        logger.info(
            "The maximal cpu model found: %s", max_cpu_of_all_hosts.get('cpu')
        )
        return max_cpu_of_all_hosts

    def get_relative_cpu_model(self, cpu_name, higher=True, version=None):
        """
        Get a cpu model of the same vendor as given cpu_name but with higher
        or lower cpu model level (according to higher flag).

        Args:
            cpu_name (str): cpu model name of some host or cluster.
            higher (bool): Looks for a higher level model if True, otherwise
                looks for a lower version model
            version (str): compatibility version

        Returns:
            dict: {cpu=str, level=int, model=str, vendor=str} if found,
                otherwise empty dict
        """
        cpu_info = self.get_cpu_info(cpu_name, key='cpu', version=version)
        for cpu in self.get_cpu_list(version):
            operation = (
                cpu.get('level') > cpu_info.get('level') if higher else
                cpu.get('level') < cpu_info.get('level')
            )
            if cpu.get('vendor') == cpu_info.get('vendor') and operation:
                logger.info("The cpu model found is %s", cpu.get('cpu'))
                return cpu
        logger.warning("No cpu model found")
        return {}
