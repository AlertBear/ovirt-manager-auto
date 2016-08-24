"""
HE deployment via appliance tests
"""
import base_deploy


class TestApplianceDeploySanityNFS(base_deploy.BaseDeployOverNFS):
    """
    Basic deployment via appliance over NFS storage
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create answer file on all hosts
        """
        super(TestApplianceDeploySanityNFS, cls).setup_class()
        cls.create_answer_file_on_resources()

    def test_he_appliance_deploy(self):
        """
        Deploy hosted engine, check that all HE services and engine up
        """
        assert self.deploy_and_check_he_status_on_hosts()


class TestApplianceDeploySanityISCSI(base_deploy.BaseDeployOverISCSI):
    """
    Basic deployment via appliance over ISCSI storage
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create answer file on all hosts
        """
        super(TestApplianceDeploySanityISCSI, cls).setup_class()
        cls.create_answer_file_on_resources()

    def test_he_appliance_deploy(self):
        """
        Deploy hosted engine, check that all HE services and engine up
        """
        assert self.deploy_and_check_he_status_on_hosts()


class TestApplianceDeploySanityGluster(base_deploy.BaseDeployOverGluster):
    """
    Basic deployment via appliance over Gluster storage
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create answer file on all hosts
        """
        super(TestApplianceDeploySanityGluster, cls).setup_class()
        cls.create_answer_file_on_resources()

    def test_he_appliance_deploy(self):
        """
        Deploy hosted engine, check that all HE services and engine up
        """
        assert self.deploy_and_check_he_status_on_hosts()
