*** Settings ***
Documentation    This is a common set of gNMI keywords used by all our Robot gNMI libraries.
...
...              The keywords marked here as "undefined" are implemented in respective
...              ``.resource`` files by including a Library that inherits
...              from ``gNMIRobotLibrary`` (directly or transitively).
...
...              The variables marked here as "undefined" are included into project
...              by specifying the ``.yaml`` file on the test run
...              (see ``adapter.yaml`` for an example).


*** Keywords ***
Setup gNMI Client
    [Documentation]    Setup the connection to target device/gNMI server.
    ...                To be used as test suite setup method.
    Setup client     ${HOST}  ${PORT}  ${USERNAME}  ${PASSWORD}  ${INSECURE}

Close gNMI Client
    [Documentation]    Close the existing connection to target device/gNMI server.
    ...                To be used as test suite teardown method.
    Close client

Teardown gNMI state
    [Documentation]    Clean the state data of custom gNMI library.
    ...                To be used as test-case teardown method (or template iteration teardown).
    Test teardown
