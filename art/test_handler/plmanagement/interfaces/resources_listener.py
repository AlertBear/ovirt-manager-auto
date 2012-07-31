from art.test_handler.plmanagement import Interface

class IResourcesListener(Interface):
    def on_hosts_cleanup_req(self):
        """ Called to prepare hosts. """
        pass

    def on_storages_prep_request(self):
        """ Called to prepare storages. """
        pass

    def on_storages_cleanup_request(self):
        """ Called to prepare storages. """
        pass
