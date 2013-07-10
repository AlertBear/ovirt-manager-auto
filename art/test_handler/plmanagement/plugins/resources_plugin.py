from art.test_handler.plmanagement import Component, ExtensionPoint, implements
from art.test_handler.plmanagement.interfaces.application import IApplicationListener
from art.test_handler.plmanagement.interfaces.resources_listener import IResourcesListener


class Resources(Component):
    implements(IApplicationListener)
    resources_listeners = ExtensionPoint(IResourcesListener)
    name = "Resources plugin"

    def on_plugins_loaded(self):
        pass

    def on_application_start(self):
        #for rl in self.resources_listeners:
        #    rl.on_hosts_cleanup_req()
        self.resources_listeners.on_hosts_cleanup_req()
        #for rl in self.resources_listeners:
        #    rl.on_storages_prep_request()
        self.resources_listeners.on_storages_prep_request()

    def on_application_exit(self):
        #for rl in self.resources_listeners:
        #    rl.on_storages_cleanup_request()
        self.resources_listeners.on_storages_cleanup_request()

    @classmethod
    def is_enabled(cls, params, config):
        return True
