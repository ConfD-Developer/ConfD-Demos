from confd_gnmi_client import ConfDgNMIClient
import typing as t
from robot.api.logger import info


class GNMIClient:
    '''This is a user written keyword library.
    These libraries can be pretty handy for more complex tasks an typically
    more efficiant to implement compare to Resource files.

    However, they are less simple in syntax and less transparent in test protocols.

    The TestObject object (t) has the following public functions:

    '''
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    def __init__(self) -> None:
        self._client: t.Optional[ConfDgNMIClient] = None

    def connect(self, ip, username, passwd, insecure):
        self._client = ConfDgNMIClient(*ip.split(':'), insecure=insecure,
                                       username=username, password=passwd)
        info('started')

    def disconnect(self):
        self.close()

    def close(self):
        self._client.close()

    def get_capabilities(self):
        return self._client.get_capabilities()

    def model_names(self, capas):
        return [m.name for m in capas.supported_models]
