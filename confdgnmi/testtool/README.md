# gNMI Telemetry testing tool

This project is intended as a tool to help with automation testing of a telemetry capabilities of target device.
It uses a [Robot Framework](https://robotframework.org/) (a generic open source automation framework) to implement range of test suites and
test cases. These try to identify capabilities of a device to service typical telemetry related gNMI requests.

## requirements

We strongly depend on **Python3** for running the tests. All the `python` commands in following text assume that this binary resolves to a (fairly recent) python3 interpreter. Following is an example of supported (not necessarily lowest required) version:

```bash
$ python --version
Python 3.8.10
```

See Robot's [installation instructions](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#installation-instructions) for details on how to install the framework. To verify you have a `robot` installed, you can run `robot --version` shell command. As of writing this document, current version is:

```bash
$ robot --version
Robot Framework 6.0.2 (Python 3.8.10 on linux)
```

Actual test-runs require that supplementary gNMI client code (located in `../src`, primarily `confd_gnmi_client.py` module) can be run successfully. See the `../README.md` for requirements if you run into some issues.

## generating test specification

You can generate the "specification" of all the test suites/test cases from
the existing robot files without need of a live target device to test.
You can do this using Robot's supporting tool called [testdoc](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-documentation-tool-testdoc).

Assuming you have all the [requirements](#requirements) installed, just execute following shell command from within the current working directory (the one where this README.md file is located):

```bash
python -m robot.testdoc ./ TestDocumentation.html
```

This creates a single HTML file with specified name - that includes descriptions and details of all the test suites and test-cases from the project's `.robot` files.

It has a structure of a packed tree nodes that you can open to see specific test-suites and/or test-cases hierarchy, and read their names, descriptions, etc.

If needed, see "`python -m robot.testdoc --help`" for possible output configuration.

## running the tests

To run any tests, we you need a target device configuration file first.

When a test run is executed and finished, it creates few files by default (unless modified by `robot` command parameters).
- `report.html` - good as a starting point, summary of all the tests suites/cases and their results;<br/>
    it links into the following `log.html` file for details...
- `log.html` - detailed log for all the steps executed in test run

### PYTHONPATH and executing tests

Whether you run tests against "real" device, or the "ConfD adapter" (see further), you need properly set Python environment for tests to execute correctly.

<span style="background-color:red">TODO - think of some executor script to save user from having to declare PYTHONPATH?</span>

For our caste, this implies setting the **`PYTHONPATH`** variable for underlying python code to find all the required items spread across various directories of the project. Assuming you run the tests from current directory, you need to have following set for tests to run:

```bash
export PYTHONPATH=../src:./:./gNMI_Interface
```

### running against target device

<span style="background-color:red">TODO -
 maybe add a recommendation to verify target device connectivity from the shell before running tests to save some time/support effort?
</span>

To run the test cases against live target device, you need to write up your configuration file (e.g. "`MY.yaml`"). See `adapter.yaml` for an example of variables that need to be included in the file and their description. Create your own `.yaml` file that you can use in next step for executing the tests.

as a parameter in command below to run the test suites:

```bash
robot --variablefile MY.yaml ./
```

You may want to run only subset of tests. See `robot`'s `--help` output for details on customization the test-run.

We recommend primarily the `--include` and/or `--exclude` options to allow selecting specific test-cases depending on existing test "**tags**". See the `report.html`/`log.html` or actual `.robot` files  for list of existing tags.

"Successfully" executed (irrespective of actual test results) test run results in output into console like:

```text
==============================================================================
Testtool :: Telemetry testing suite for a brief verification of the device'...
==============================================================================
Testtool.gNMI Interface :: Test suite dedicated to verification of generic ...
==============================================================================
Testtool.gNMI Interface.Capabilities :: Generic device agnostic test suite ...
==============================================================================
Device sends CapabilityResponse (any) :: Device can respond with `... | PASS |
------------------------------------------------------------------------------
Mandatory JSON is advertised as supported encoding :: Get the list... | FAIL |
[ JSON_IETF | ASCII | PROTO ] does not contain value 'JSON'.
------------------------------------------------------------------------------
[ WARN ] Mandatory JSON (as per gNMI specification) not declared as supported
Supported encodings include JSON or JSON_IETF :: Test if the devic... | PASS |
------------------------------------------------------------------------------
Device should support some models :: Check that the ``supported_mo... | PASS |
------------------------------------------------------------------------------

...output continued...

Output:  .../output.xml
Log:     .../log.html
Report:  .../report.html
```

This results in creation of previously mentioned log files of interest - `report.html` and `log.html`.

### running without target device - ConfD based "adapter"

You can run tests without having any target device, e.g. to see an example test outputs/logs. You can do this by using the so-called "**ConfD gNMI adapter**" as a target device.

ConfD gNMI adapter serves as an proof-of-concept implementation of gNMI enabled device. It utilizes the ConfD to run and service the model-specific requests for some of OpenConfig standard models<span style="background-color:red">, and TODO...?</span> It includes a simple gNMI server written in Python to "proxy' the incoming gNMI requests into the ConfD database.

<span style="background-color:red">TODO - some seq. diagram could be useful here?</span

Previously mentioned `adapter.yaml` file already contains all the variables settings needed for this use-case.

<span style="background-color:red">TODO - add info on starting ConfD using Makefile (or add some helper script?) etc.</span>
