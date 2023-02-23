from __future__ import annotations

from robot_gnmi_client import GNMIClient
from confd_gnmi_common import make_gnmi_path, get_encoding
from confd_gnmi_client import ConfDgNMIClient


class SubscribeLibrary(GNMIClient):
    "ROBOT test suite library for servicing the gNMI SubscribeRequest tests."
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    def test_subscribe(self, mode, path):
        slist = ConfDgNMIClient.make_subscription_list(make_gnmi_path(''),
                                                       [make_gnmi_path(path)],
                                                       mode,
                                                       get_encoding('JSON_IETF'))
        responses = self._client.subscribe(slist)
        return next(responses)
