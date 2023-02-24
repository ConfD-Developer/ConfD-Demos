from __future__ import annotations

from robot_gnmi_client import GNMIClient
from confd_gnmi_common import make_gnmi_path
from confd_gnmi_client import ConfDgNMIClient

from gnmi_proto_helpers import encoding_str_to_int


class SubscribeLibrary(GNMIClient):
    "ROBOT test suite library for servicing the gNMI SubscribeRequest tests."
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    def test_subscribe(self, mode, path):
        slist = ConfDgNMIClient.make_subscription_list(make_gnmi_path(''),
                                                       [make_gnmi_path(path)],
                                                       mode,
                                                       encoding_str_to_int('JSON_IETF'))
        responses = self._client.subscribe(slist)
        return next(responses)
