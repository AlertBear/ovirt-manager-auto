import logging
from contextlib import contextmanager
from abc import ABCMeta, abstractmethod

from utilities.utils import generateShortGuid
from utilities.cobblerApi import Cobbler
from utilities.foremanApi import ForemanActions
from art.test_handler.settings import opts

logger = logging.getLogger(__name__)


class ProvisioningAPI(object):
    """
    Description: Abstract class that defines ProvisioningAPI interfaces
                 All Classes that encapsulate provisioning APIs should inherit
                 from it.
    Author: imeerovi
    """

    __metaclass__ = ABCMeta

    @staticmethod
    @abstractmethod
    def provisioning_api_access(*args, **kwargs):
        """
        Description: This method will provide api access
        Author: imeerovi
        """

    @staticmethod
    @abstractmethod
    def add_system(*args, **kwargs):
        """
        Description: This method will add system
        Author: imeerovi
        """

    @staticmethod
    @abstractmethod
    def remove_system(*args, **kwargs):
        """
        Description: This method will remove system
        Author: imeerovi
        """

    @staticmethod
    @abstractmethod
    def set_host_name(*args, **kwargs):
        """
        Description: This method will set host names system
        Author: imeerovi
        """


class ForemanProvisioning(ProvisioningAPI):
    """
    Description: class that implements ProvisioningAPI interfaces for Foreman
    Author: imeerovi
    """

    @staticmethod
    def provisioning_api_access(api_access_point, api_user, api_passwd):
        """
        Description: This method connects to Foreman host provision API
        Author: imeerovi
        Parameters:
            * api_access_point - Foreman API URI
            * api_user - username
            * api_passwd - password
        Returns: Foreman API handle
        """
        return ForemanActions(uri=api_access_point, user=api_user,
                              passwd=api_passwd)

    @staticmethod
    def add_system(api, mac, common_parameters, provisioning_profile):
        """
        Description: This method adds system to Foreman
        Author: imeerovi
        Parameters:
            * api - Foreman host provision API handle
            * mac - provisioned vm mac
            * common_parameters - Foreman profile common parameters
            * provisioning_profile - Foreman profile for specific OS image
        Returns: status of Foreman host provision create_host method
        """
        name = 'ART-test-vm-%s' % generateShortGuid()
        return api.create_host(
            name, mac, hostgroup=provisioning_profile['hostgroup'],
            common_parameters=common_parameters)

    @staticmethod
    def remove_system(api, mac):
        """
        Description: This method removes system
        Author: imeerovi
        Parameters:
            * mac - mac of vm to remove
        Returns: status of Foreman host provision remove_host method
        """
        return api.remove_host(mac)

    @staticmethod
    def set_host_name(*args, **kwargs):
        """
        Description: This method will set host names system, for now it is stub
                     that returns True
        Author: imeerovi
        """
        return True


class CobblerProvisioning(ProvisioningAPI):
    """
    Description: class that implements ProvisioningAPI interfaces for Cobbler
    Author: imeerovi
    """

    @staticmethod
    def provisioning_api_access(api_access_point, api_user, api_passwd):
        """
        Description: This method connects to Cobbler API
        Author: imeerovi
        Parameters:
            * api_access_point - Cobbler IP/hostname
            * api_user - username
            * api_passwd - password
        Returns: Cobbler API handle
        """
        return Cobbler(host=api_access_point, user=api_user, passwd=api_passwd)

    @staticmethod
    def add_system(api, mac, common_parameters, provisioning_profile):
        """
        Description: This method adds system to Cobbler
        Author: imeerovi
        Parameters:
            * api - Cobbler API handle
            * mac - provisioned vm mac
            * common_parameters - not usable for Cobbler
            * provisioning_profile - Cobbler data for specific OS image
        Returns: status of Cobbler API addNewSystem method
        """
        return api.addNewSystem(mac, provisioning_profile['profile'])

    @staticmethod
    def remove_system(api, mac):
        """
        Description: This method removes system
        Author: imeerovi
        Parameters:
            * mac - mac of vm to remove
        Returns: status of Cobbler API removeSystem method
        """
        return api.removeSystem(mac)

    @staticmethod
    def set_host_name(api, name, hostname):
        """
        Description: This method sets linux system hostname
        Author: imeerovi
        Parameters:
            * name - system name
            * hostname - New system hostname
        Returns: status of Cobbler API setSystemHostName method
        """
        return api.setSystemHostName(name=name, hostname=hostname)


class ProvisionProvidersType(type):
    """
    Description: metaclass for ProvisionProvider. It sets provisioning tool
                parameters and creates ProvisionProvider class
    Author: imeerovi
    Parameters:
        * cls - metaclass to use for class creation
        * name - name of the class
        * bases - tuple of the parent class (for inheritance, can be empty)
        * dct - dictionary containing attributes names and values
    """

    _provisioning_providers = {'cobbler': CobblerProvisioning,
                               'foreman': ForemanProvisioning}

    def __new__(cls, name, bases, dct):
        # creating needed class
        new_cls = super(ProvisionProvidersType, cls).__new__(cls, name, bases,
                                                             dct)
        if 'provisioning_tool' in opts:
            # providing needed api provisioning parameters
            new_cls.provisioning_tool = \
                ProvisionProvidersType._provisioning_providers[
                    opts['provisioning_tool']]
            new_cls.common_parameters = \
                opts['provisioning_tool_common_parameters']
            new_cls.provisioning_profiles = opts['provisioning_profiles']

            # providing needed api access parameters
            new_cls.provisioning_tool_api = opts['provisioning_tool_api']
            new_cls.provisioning_tool_user = opts['provisioning_tool_user']
            new_cls.provisioning_tool_password = opts[
                'provisioning_tool_password']
        else:
            logger.info("Provisioning_tools_plugin disabled, %s is not "
                        "functional", __name__)

        return new_cls


class ProvisionProvider(object):
    """
    Description: User API for provisioning tools
    Author: imeerovi
    """
    provisioning_tool = None
    provisioning_tool_api = None
    provisioning_tool_user = None
    provisioning_tool_password = None
    common_parameters = None
    provisioning_profiles = None

    __metaclass__ = ProvisionProvidersType

    class Context(object):
        """
        This wrapper cache systems which were managed via this interface.
        And it provides method which unamage these systems.

        The usage is:

        with ProvisionProvider.Context() as c:
            c.add_system(xx, yy)
            c.add_system(zz, aa)
            # watch the installation process
        # you are done
        """
        def __init__(self):
            super(ProvisionProvider.Context, self).__init__()
            self.systems = {}

        def __enter__(self):
            return self

        def __exit__(self, type_, value, tb):
            self.clear()

        @staticmethod
        def unify_mac(mac):
            return ''.join(x for x in mac.lower() if x not in [':', '-'])

        def add_system(self, mac, os_name):
            umac = self.unify_mac(mac)
            if umac in self.systems:
                logger.info("The mac %s is already managed -> removing", mac)
                try:
                    self.remove_system(mac)
                except Exception as ex:
                    logger.error(
                        "The mac %s couldn't be unmanaged: %s", mac, ex
                    )
            result = ProvisionProvider.add_system(mac, os_name)
            self.systems[umac] = mac
            return result

        def remove_system(self, mac):
            umac = self.unify_mac(mac)
            self.systems.pop(umac, None)
            return ProvisionProvider.remove_system(mac)

        def clear(self):
            """
            Removes all systems which were intrumented in this context
            """
            while self.systems:
                umac, mac = self.systems.popitem()
                try:
                    self.remove_system(mac)
                except Exception as ex:
                    logger.error("Can not remove system %s: %s", umac, ex)

        def set_host_name(self, *args, **kwargs):
            return ProvisionProvider.set_host_name(*args, **kwargs)

    @classmethod
    @contextmanager
    def api_connection(cls, func_name, *args, **kwargs):
        """
        Description: context management for provisioning api handler
        Author: imeerovi
        Parameters:
            * cls - ProvisionProvider class
            * func_name - name of method that is using this context manager
            * *args, **kwargs - func_name parameters
        Returns: None
        """
        try:
            # The __enter__ processing
            logger.info("Connecting to %s API.",
                        cls.provisioning_tool.__name__)
            api_handler = getattr(
                cls.provisioning_tool,
                'provisioning_api_access')(cls.provisioning_tool_api,
                                           cls.provisioning_tool_user,
                                           cls.provisioning_tool_password)
            logger.info("Running %s with args: %s kwargs: %s", func_name, args,
                        kwargs)
            yield api_handler
            logger.info("Finished to run %s with args: %s kwargs: %s",
                        func_name, args, kwargs)
            # The __exit__ processing -- if everything's ok
            logger.info("Disconnecting from %s API.",
                        cls.provisioning_tool.__name__)
            del api_handler
        except Exception:
            # The __exit__ processing -- if there as an exception
            raise

    @classmethod
    def add_system(cls, mac, os_name):
        """
        Description: This method adds system, it uses provisioning api
                     according to parameters that were set by
                     ProvisionProvidersType
        Author: imeerovi
        Parameters:
            * cls - ProvisionProvider class
            * mac - provisioned vm mac
            * os_name - OS/image to install/provide
        Returns: return value of add_system method of provisioning api
                 that it used
        """

        with cls.api_connection(
            cls.add_system.__func__.__name__,
            mac,
            os_name
        ) as api:
            return getattr(
                cls.provisioning_tool,
                'add_system'
            )(
                api,
                mac,
                cls.common_parameters,
                cls.provisioning_profiles[os_name]
            )

    @classmethod
    def remove_system(cls, mac):
        """
        Description: This method removes system, it uses provisioning api
                     according to parameters that were set by
                     ProvisionProvidersType
        Author: imeerovi
        Parameters:
            * cls - ProvisionProvider class
            * mac - mac of vm to remove
        Returns: return value of remove_system method of provisioning api
                 that it used
        """
        with cls.api_connection(
            cls.remove_system.__func__.__name__,
            mac
        ) as api:
            return getattr(
                cls.provisioning_tool,
                'remove_system'
            )(api, mac)

    @classmethod
    def set_host_name(cls, *args, **kwargs):
        """
        Description: This method set host name system, it uses provisioning
                      api
                     according to parameters that were set by
                     ProvisionProvidersType
        Author: imeerovi
        Parameters:
            * cls - ProvisionProvider class
            * args, kwargs - parameters for specific provisioning tool
        Returns: return value of set_host_name method of provisioning api
                 that it used
        """
        with cls.api_connection(cls.set_host_name.__func__.__name__, args,
                                kwargs) as api:
            return getattr(cls.provisioning_tool,
                           'set_host_name')(api, args, kwargs)
