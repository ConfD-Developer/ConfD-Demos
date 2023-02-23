import typing as t
from confd_gnmi_client import ConfDgNMIClient


class GNMIClient:
    'Common functionality for Robot tests'
    def __init__(self) -> None:
        self._client: t.Optional[ConfDgNMIClient] = None

    def setup_client(self, ip, username, passwd, insecure):
        """ Initialize new gNMI client instance for dispatching the requests to server. """
        self._client = ConfDgNMIClient(*ip.split(':'), insecure=insecure,
                                       username=username, password=passwd)

    def close_client(self):
        """ Close previously initialized gNMI client instance. """
        self._client.close()
