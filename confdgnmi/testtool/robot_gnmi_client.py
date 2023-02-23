from confd_gnmi_client import ConfDgNMIClient
import typing as t


class GNMIClient:
    'Common functionality for Robot tests'
    def __init__(self) -> None:
        self._client: t.Optional[ConfDgNMIClient] = None

    def setup_client(self, ip, username, passwd, insecure):
        self._client = ConfDgNMIClient(*ip.split(':'), insecure=insecure,
                                       username=username, password=passwd)

    def close_client(self):
        self._client.close()
