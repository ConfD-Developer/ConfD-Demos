README.md

Automating NETCONF NED Building and testing with drned-xmnr
===========================================================

ned-test.py is a little helper program that tries to simplify
verification of NETCONF and YANG interfaces published by network
devices.

ned-test.py is intended to be used with NSO and drned-xmnr and
automates common tasks encountered when using those tools to test
NETCONF and YANG.

ned-test currently supports four tasks:
1. Setup NSO to work with a particular network devices

2. Build a NETCONF NED for a device.  The YANG-models for the NED are
   either fetched from the device using the NETCONF <get-schema> RPC
   or, directly from YANG-models provided by the user in a local
   directory.

3. Import test cases or configuration states.  The test cases can be
   in any format supported by drned-xmnr: NSO CLI or XML format or
   native device CLI format although in the latter case a simple
   driver is needed to help drned-xmnr translate the CLI commands to
   NETCONF.

4. Run the tests and report the result. When applying test
   configuration two methods are supported, apply configurations one
   at a time or apply all possible configuration combinations.

To get help with available commands and syntax, just do `$ ned-test.py
--help` or `$ ned-test.py <command> --help` for detailed information.

    $ ned-test.py --help
    usage: ned-test [-h] {init,build-ned,import-tests,test-ned,cleanup,debug} ...

    positional arguments:
      {init,build-ned,import-tests,test-ned,cleanup,debug}
                            sub-command help
        init                Configure device and authentication information.
        build-ned           Build a NETCONF NED based on YANG models found on
                            device_name or local YANG-models.
        import-tests        Import test vectors and optionally translate test
                            configurations.
        test-ned            Test the NETCONF/YANG interface of "device_name" by
                            applying all installed test configurations.
        cleanup             Remove test device and artifacts produced during
                            testing.
        debug               Test commands

    optional arguments:
      -h, --help            show this help message and exit

Example Commands
----------------

We always start by telling NSO about the device we want to test

`$ ned-test.py init --cli-port 63352 --ip-address 172.26.228.156 --netconf-port 63352 --username admin --password admin nc0`

The init sub-command creates a device and an authgroup called nc0
and fills in everything NSO and drned-xmnr needs to talk to the
device.  Note that --netconf-port can be skipped if have sane default
(830).

`$ ned-test.py build-ned --exclude "*openconfig*" --install --ned-name fancy-ned --vendor acme --version 7.5 --yang-source device nc0`

The build-ned builds a NETCONF NED for a device.  The build-ned
sub-command assumes that init has been performed.  build-ned allows
users to specify ned-name, vendor and version information as well as
where to get the YANG-models (a directory or the special place
'device') and a comma-separated list of YANG-modules (or wildcards) to
exclude from the list.

`$ ned-test.py import-tests --filter '*l2vpn*' nc0`

The import-tests sub-command does exactly that, import a set of tests
in one of the formats supported by drned-xmnr.  In this example
--convert indicate that we intend to convert the imported test from
native CLI to NETCONF and --filter indicate that we only want to import
the the subset that match the wildcard. Note that --cli-port is only
required if we plan to translate device CLI configurations to NETCONF,
if not we will only interact with the device using the NETCONF
protocol.

`$ ned-test.py test-ned nc0`

When that is done we perform the test using the test-ned sub-command.
The test will apply all imported tests in order and report the result
at the end.


Dependencies
------------

* ncs and _ncs
* argparse
* pexpect
* os
* shutil
* subprocess
* sys
* time

Disclaimer
----------

ned-test.py should be considered beta quality at this point.  New
features will be added, commands will change and the implementation
will be improved.

TODO
----

* Replace ncs_cli invocations with maapi/maagic API calls
* Use a dedicated build device when building NEDs, that way we won't
  risk hitting the "ned-id must be netconf" error after installing a
  newly built NED.
* Implement verbose mode for increased logging
* Make location of local YANG modules configurable or maybe better, an
  argument to build-ned


References
----------

* [NSO](https://developer.cisco.com/site/nso/)
* [drned-xmnr](https://github.com/NSO-developer/drned-xmnr)
* [NYAT User Guide](https://info.tail-f.com/netconf_yang_automation_testing)
