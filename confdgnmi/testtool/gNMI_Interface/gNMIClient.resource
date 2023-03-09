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
    Setup client     ${HOST}  ${PORT}  ${USERNAME}  ${PASSWORD}  ${INSECURE}

Close gNMI Client
    Close client

Teardown gNMI state
    Test teardown
