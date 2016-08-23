import pytest
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    templates as ll_templates
)
from rhevmtests.storage import config, helpers as storage_helpers


@pytest.fixture(scope='class')
def initializer_class(request, storage):
    """
    Prepare the environment for test
    """
    self = request.node.cls

    self.storage_domains = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, self.storage
    )
    self.storage_domain = self.storage_domains[0]
    self.clone_vm_args = config.clone_vm_args.copy()
    self.clone_vm_args['clone'] = True
    self.clone_vm_args['template'] = None
    self.vm_names = [
        storage_helpers.create_unique_object_name(
            self.__class__.__name__ + '1' + '%s' %
            self.storage, config.OBJECT_TYPE_VM
        ),
        storage_helpers.create_unique_object_name(
            self.__class__.__name__ + '2' + '%s' %
            self.storage, config.OBJECT_TYPE_VM
        )
    ]
    self.templates_names = [
        storage_helpers.create_unique_object_name(
            self.__class__.__name__ + '1', config.OBJECT_TYPE_TEMPLATE
        ),
        storage_helpers.create_unique_object_name(
            self.__class__.__name__ + '2', config.OBJECT_TYPE_TEMPLATE
        )
    ]
    self.disks_to_remove = [
        storage_helpers.create_unique_object_name(
            self.__class__.__name__ + '1', config.OBJECT_TYPE_DISK
        ),
        storage_helpers.create_unique_object_name(
            self.__class__.__name__ + '2', config.OBJECT_TYPE_DISK
        )
    ]


@pytest.fixture(scope='class')
def extract_template_disks(request, storage):
    """
    Extracts template disks
    """
    self = request.node.cls

    self.disk = ll_templates.getTemplateDisks(self.template_name)[0]
