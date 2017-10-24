import config
import pytest
from art.rhevm_api.tests_lib.low_level import templates as ll_templ


@pytest.fixture(scope="function")
def restore_template_name(request):
    template_obj = ll_templ.get_template_obj(config.BLANK_TEMPLATE)
    version = template_obj.get_version().version_number

    def fin():
        """
        Teardown:
            Change template name to default value "Blank".
        """
        assert ll_templ.updateTemplate(
            positive=True,
            template=config.NEW_NAME,
            name=config.BLANK_TEMPLATE,
            version_number=version
        ), "Failed to restore blank template default name."

    request.addfinalizer(fin)


@pytest.fixture(scope="function")
def restore_template_params(request):
    default_mem_value = None
    default_stateless_value = None
    template_boot_sequence = None

    template_obj = ll_templ.get_template_obj(config.BLANK_TEMPLATE)
    version = template_obj.get_version().version_number
    if request.getfixturevalue("memory"):
        default_mem_value = template_obj.get_memory()
    elif request.getfixturevalue("boot_device"):
        template_boot_sequence = ll_templ.get_template_boot_sequence(
            config.BLANK_TEMPLATE
        )
    elif request.getfixturevalue("stateless"):
        default_stateless_value = template_obj.get_stateless()

    def fin():
        """
        Teardown:
            Restore Blank template default values.
        """
        assert ll_templ.updateTemplate(
            positive=True,
            template=config.BLANK_TEMPLATE,
            memory=default_mem_value,
            stateless=default_stateless_value,
            boot=template_boot_sequence,
            version_number=version
        ), "Failed to restore blank template default boot sequence."

    request.addfinalizer(fin)
