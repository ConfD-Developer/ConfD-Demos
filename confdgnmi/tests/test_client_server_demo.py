import pytest

from client_server_test_base import GrpcBase
from confd_gnmi_server import AdapterType

_confd_DEBUG = 1


@pytest.mark.grpc
@pytest.mark.demo
@pytest.mark.usefixtures("fix_method")
class TestGrpcDemo(GrpcBase):

    def set_adapter_type(self):
        self.adapter_type = AdapterType.DEMO
