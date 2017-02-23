import re
import time
import logging
from art.rhevm_api.utils.threads import ThreadSafeDict
# need to solve this cyclic deps
from art.rhevm_api.utils.test_utils import get_api
from art.rhevm_api.utils.test_utils import convertMacToIp
from art.core_api.apis_exceptions import APIException, EntityNotFound


logger = logging.getLogger('test_utils')

VM_API = get_api('vm', 'vms')
HOST_API = get_api('host', 'hosts')
NIC_API = get_api('nic', 'nics')


class IpLookUpError(APIException):
    """
    Can not found ip for:
    """


class LookUpIpByEntityName(object):
    """
    Base class for all name2ip resolutions
    """
    cache = ThreadSafeDict()
    entity = None

    def __init__(self, target_var, source_var, cache_exp=60*10):
        """
        target_var - ipVar
        source_var - nameVar
        """
        super(LookUpIpByEntityName, self).__init__()
        self.tv = target_var
        self.sv = source_var
        self.exp = cache_exp
        self.func = None

    @classmethod
    def reset_cache(cls, entity='.+', entity_name='.+'):
        reg = re.compile('^%s-%s$' % (entity, entity_name))
        with cls.cache:
            elms = [x for x in cls.cache.keys() if reg.match(x)]
            for elm in elms:
                del cls.cache[elm]

    def __call__(self, *args, **kwargs):
        if self.func is None:
            self.func = args[0]
            self.adjust_doc()
            return self  # decorator self-calling
        return self.wrapper(*args, **kwargs)

    def adjust_doc(self):
        try:
            sub = re.compile('^((.*)%s\s*([=-]).*)$' % self.tv, re.M)
            doc = sub.sub(
                r'\1\n\2%s \3 name of entity (can supply %s)' % (
                    self.sv, self.tv
                ),
                self.func.func_doc, 1,
            )
            self.func.func_doc = doc
            # self.wrapper.im_func.func_doc = doc
            # self.wrapper.im_func.func_name = self.func.func_name
        except Exception as ex:
            logger.warn(
                "failed to add '%s' into doc-string of '%s': %s",
                self.sv, self.func.func_name, ex,
            )

    def wrapper(self, *args, **kwargs):
        if kwargs.get(self.tv, None):
            return self.func(*args, **kwargs)
        if not kwargs.get(self.sv, None):
            raise ValueError("parameter %s is not passed" % self.sv)

        src_val = kwargs[self.sv]
        if isinstance(src_val, (list, tuple)):
            res = []
            for val in src_val:
                res.append(self.look_up(val))
            kwargs[self.tv] = res
        else:
            kwargs[self.tv] = self.look_up(src_val)

        del kwargs[self.sv]
        return self.func(*args, **kwargs)

    def look_up(self, source_value):
        cache_rec_name = "%s-%s" % (self.entity, source_value)
        with self.cache:
            cache_rec = self.cache.get(cache_rec_name, {'ip': None, 'exp': 0})
            time_stmp = time.time()
            if cache_rec['exp'] < time_stmp:  # record expired
                ip = self.get_ip(source_value)
                if ip is None:
                    raise IpLookUpError(cache_rec_name)
                cache_rec['ip'] = ip

                cache_rec['exp'] = time_stmp + self.exp
                self.cache[cache_rec_name] = cache_rec

            return cache_rec['ip']

    def get_ip(self, src_val):
        raise NotImplementedError()


def resetName2IpCache(entity='.+', entityName='.+'):
    """
    Description: Removes all/specific record (entityName -> ip-address)
    from cache.
    Parameters:
     * entity - type of entity (e.g.: vms), you can use regexpr
     * entityName - name of entity, you can use regexpr
     * expTime - sets expiration time for cached records (seconds)
    """
    LookUpIpByEntityName.reset_cache(entity, entityName)
    return True


class LookUpVMIpByName(LookUpIpByEntityName):
    """
    Implements name2ip for VM element
    """
    entity = 'vms'

    def __init__(
        self, target_var='vm_ip', source_var='vm_name', cache_exp=60*10, nic=0
    ):
        super(LookUpVMIpByName, self).__init__(
            target_var, source_var, cache_exp,
        )
        self.nic = nic

    def get_ip(self, src_val, check_mac=True):
        ip = self._get_ip_from_vm(src_val)
        ip = ip[0] if ip else None
        if ip is None and check_mac:
            ip = self._get_ip_from_mac(src_val)
        return ip

    def _get_ip_from_vm(self, vm_name, ip_version='v4'):
        ip_list = list()
        import art.rhevm_api.tests_lib.low_level.vms as ll_vms
        nics = ll_vms.get_vm_nics_obj(vm_name)
        if not nics:
            logger.error('The nics object of vm_name: %s is empty', vm_name)
            return ip_list
        for nic in nics:
            reported_devices = nic.get_reported_devices()
            if not reported_devices:
                continue
            reported_devices = reported_devices.get_reported_device()
            for reported_device in reported_devices:
                ips = reported_device.get_ips()
                if not ips:
                    continue
                ips = ips.get_ip()
                for ip in ips:
                    if ip.get_version() == ip_version:
                        ip_list.append(ip.get_address())
        logger.info(
            'The vm %s ip addresses %s are: %s', vm_name, ip_version, ip_list
        )
        return ip_list

    def _get_ip_from_mac(self, vm_name):
        import art.rhevm_api.tests_lib.low_level.vms as ll_vms
        nics = ll_vms.get_vm_nics_obj(vm_name)
        if not nics:
            return None
        nic = nics[self.nic]
        mac = nic.mac.address
        return convertMacToIp(mac)


class LookUpHostIpByName(LookUpIpByEntityName):
    """
    Implements name2ip for Host element
    """
    entity = 'hosts'

    def get_ip(self, host_name):
        host = HOST_API.find(host_name)
        return host.get_address()


class name2ip(LookUpIpByEntityName):
    """
    Encapsulates name2ip resolutions for VM and Host elements.
    It expects source_value as "entity_collection:entity_name"
    """
    ENTITY = {
        LookUpVMIpByName.entity: LookUpVMIpByName,
        LookUpHostIpByName.entity: LookUpHostIpByName,
    }

    def look_up(self, source_value):
        m = re.match("^(?P<entity>[^:]+):(?P<name>.+)$", source_value)
        if m:  # use only specific resolver
            self.entity = m.group('entity')
            if self.entity not in self.ENTITY:
                raise ValueError("unknown entity: '%s'" % self.entity)
            look = self.ENTITY[self.entity](self.tv, self.sv, self.exp)
            return look.look_up(m.group('name'))
        # try all resolvers
        for cls in self.ENTITY.values():
            look = cls(self.tv, self.sv, self.exp)
            try:
                return look.look_up(source_value)
            except (IpLookUpError, EntityNotFound) as ex:
                logger.warn(str(ex))
                continue
        else:
            raise IpLookUpError(source_value)

    def get_ip(self, src_val):
        assert False, "should't be used in this class"


# # EXAMPLE OF USAGE
#
# @LookUpVMIpByName('vm_ip', 'name_vm')
# def pingVm(vm_ip, attempts):
#     pass # lets do ping
#
# if __name__ == '__main__':
#     pingVm(vm_name='my_vm')
