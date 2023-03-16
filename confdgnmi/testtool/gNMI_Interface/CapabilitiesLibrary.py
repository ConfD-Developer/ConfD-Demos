from __future__ import annotations
from dataclasses import dataclass
from typing import List
from robot.api.logger import warn
from confd_gnmi_common import encoding_int_to_str

from gNMIRobotLibrary import gNMIRobotLibrary


@dataclass
class CapabilitiesData:
    model_names: List[str]
    encodings: List[str]


def empty_capabilities_data():
    return CapabilitiesData([], [])


class CapabilitiesLibrary(gNMIRobotLibrary):
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    def __init__(self, enable_extra_logs = False) -> None:
        super().__init__(enable_extra_logs)
        self._capabilities_data = empty_capabilities_data()

    def cleanup_capabilities(self) -> None:
        """ Reset previously (if applicable) loaded ``CapabilityResponse`` data. """
        self._capabilities_data = empty_capabilities_data()

    def test_teardown(self):
        super().test_teardown()
        self.cleanup_capabilities()

    def get_capabilities_from_device(self) -> None:
        """ Dispatch ``CapabilityRequest`` to a target device and retrieve list of
            supported encodings and model names. """
        self.test_teardown()
        try:
            response = self._client.get_capabilities()
            self._capabilities_data = CapabilitiesData(
                model_names = [m.name for m in response.supported_models],
                encodings = [encoding_int_to_str(e, no_error=True) for e in response.supported_encodings]
            )
            self.last_response = response
        except Exception as ex:
            self.last_exception = ex

    def last_supported_encodings(self) -> List[str]:
        """ Return list of all the *encodings* advertised as supported by server. """
        return self._capabilities_data.encodings

    def last_supported_model_names(self) -> List[str]:
        """ Return list of all the *model names* advertised as supported by server. """
        return self._capabilities_data.model_names

    def last_unsupported_encodings(self):
        """ Return list of encodings that are NOT reported as supported by server.\n
            Created as a complement of all the possible encodings'
            to the `self.get_supported_encodings()` list. """
        ALL_ENCODINGS = ['JSON', 'BYTES', 'PROTO', 'ASCII', 'JSON_IETF']
        supported = self.last_supported_encodings()
        unsupported = [encoding for encoding in ALL_ENCODINGS if encoding not in supported]
        return unsupported

    def last_encodings_should_have_some_json(self):
        encodings = self._capabilities_data.encodings
        has_some_json = any(needed in encodings for needed in ['JSON', 'JSON_IETF'])
        if 'JSON' not in encodings:
            warn("Mandatory JSON (as per gNMI specification) not declared as supported")
        assert has_some_json, "Supported encodings do not include either JSON/JSON_IETF"
