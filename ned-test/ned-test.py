#!/usr/bin/env python3
# -*- mode: python; python-indent: 4 -*-
#

import argparse
from os import getcwd
from os.path import isdir, exists
import pexpect
import shutil
import subprocess
import sys
from time import sleep


import ncs
from _ncs import cs_node_cd, decrypt, fatal


class TestNedError(Exception):
    def __init__(self, info):
        if type(info) is dict:
            self.info = info
        else:
            self.info = {'failure': info}

    def get_info(self):
        return self.info


class Dummy:
    pass


class TestDevice(object):
    def __init__(self, args):
        """Constructor for internal representation for a test device."""

        # self.cli_port = args.cli_port
        self.dir = args.dir
        self.device_name = args.device_name
        self.ip_address = args.ip_address
        self.ned_id = args.ned_id
        self.netconf_port = args.netconf_port
        self.password = args.password
        self.username = args.username

    def build_ned_package(self, ned_id):
        """Build a NED """

        cmd = "make -C /tmp/%s/src clean all" % ned_id
        subprocess.run(cmd, shell=True, check=True, text=True)

    def create_ned_package(self, ned_name, netsim, vendor, version):
        """Create a NED package - i.e. ncs-make-package.  The package lives
        under /tmp in order to not contaminate the packages directory with
        broken NEDs in case something goes wrong during compilation."""

        ned_id = '%s-nc-%s' % (ned_name, version)
        shutil.rmtree(ned_id, ignore_errors=True)
        cmd = ("ncs-make-package --netconf-ned /tmp/yangs %s --dest /tmp/%s "
               "--no-java%s --no-python --no-test --verbose --vendor %s "
               "--package-version %s" % (ned_name, ned_id, netsim, vendor, version))
        subprocess.run(cmd, shell=True, check=True, text=True)
        return ned_id

    def get_yang_modules(self, debug, ned_name, vendor, version,
                         exclude_patterns, yang_source='device'):
        """Fetch all YANG-modules and copy them to the /tmp/yangs directory.
        Handle the different cases when getting modules from a device or a
        local directory."""

        if yang_source == 'device':
            download_yang_modules(debug, self.device_name, ned_name,
                                  self.username, vendor, version)
            src_dir = 'state/netconf-ned-builder/cache/%s-nc-%s' % (ned_name, version)
        elif isdir(yang_source):
            src_dir = yang_source
        else:
            raise Exception('Unknown YANG source:', yang_source)

        dst_dir = '/tmp/yangs'
        shutil.rmtree('/tmp/yangs', ignore_errors=True)
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(*exclude_patterns.split(' ')))

    def install_ned(self, ned_id):
        """Install a NED, i.e.copy it to the packages directory."""

        package_dir = "%s/packages/%s" % (self.dir, ned_id)
        src_dir = "/tmp/%s" % ned_id
        shutil.rmtree(package_dir, ignore_errors=True)
        shutil.copytree(src_dir, package_dir, dirs_exist_ok=True)
        with ncs.maapi.Maapi() as m:
            with ncs.maapi.Session(m, 'admin', 'python'):
                root = ncs.maagic.get_root(m)
                input = root.packages.reload.get_input()
                input.force.create()
                output = root.packages.reload.request(input)
                return output.reload_result[ned_id].result

    def setup_cli_device(self, cli_port):
        """Set up CLI device for translation of CLI test cases to NETCONF."""

        template = '%s/bin/device.template' % self.dir
        driver = '%s/states/%s.py' % (self.dir, self.device_name)
        shutil.copyfile(template, driver)
        maapi_set_elem_str('/devices/device{%s}/drned-xmnr/cli-port'
                           % self.device_name,
                           cli_port)
        maapi_set_elem_str('/devices/device{%s}/drned-xmnr/driver'
                           % self.device_name, driver)

    def setup_drned_xmnr(self):
        """Run the drned-xmnr setup action and record the current configuration
        as the base state."""

        if not exists('/nyat/xmnr/%s/test/drned-skeleton' % self.device_name):
            print('Setup drned-xmnr...', end='', flush=True)
            res = maapi_run_action('/ncs:devices/device{%s}/drned-xmnr:drned-xmnr/setup/setup-xmnr' % self.device_name,
                                   'devices device %s drned-xmnr setup setup-xmnr overwrite true' % self.device_name)
            if 'success' in res:
                print('ok', flush=True)

    def record_test(self, state_name):
        """Record a new test case."""

        print('Sync configuration...', end='', flush=True)
        res = maapi_run_action('/ncs:devices/device{%s}/sync-from' % self.device_name,
                               'devices device %s sync-from' % self.device_name)
        if 'result true' in res:
            print('ok', flush=True)
        print('Record start state...', end='', flush=True)
        res = maapi_run_action('/ncs:devices/device{%s}/drned-xmnr:drned-xmnr/state/record-state' % self.device_name,
                               'devices device %s drned-xmnr state record-state state-name %s overwrite true' % (self.device_name, state_name))
        if 'success' in res:
            print('ok', flush=True)

    def import_tests(self, directory, pattern):
        """Import pre-recorded configuration states, currently only NETCONF
        tests are supported.  Later, import = automatic translation of CLI
        test will be added."""

        print('import tests from %s...' % directory, end='', flush=True)
        res = maapi_run_action('/ncs:devices/device{%s}/drned-xmnr:drned-xmnr/state/import-state-files' % self.device_name,
                               'devices device %s drned-xmnr state import-state-files format nso-xml file-path-pattern %s/%s overwrite true' % (self.device_name, directory, pattern))
        if 'success' in res:
            print('ok', flush=True)
        else:
            print('fail', flush=True)

    def setup_netconf_device(self):
        """Create a NETCONF device with matching authgroup.  In order to ensure
        that we're not overwriting authentication information we create a
        matching authgroup for each device."""

        create_authgroup(self.device_name, self.username, self.password)
        create_device(self.device_name, self.ip_address,
                      self.netconf_port, self.ned_id)
        fetch_host_keys(self.device_name)
        sync_from(self.device_name)

    def test_ned(self, strategy):
        """Run all recorded tests.  Both walk-states and explore-transitions
        actions are supported."""

        if strategy == 'walk':
            cli_str = r'''
            devices device %s drned-xmnr transitions walk-states rollback true
            ''' % (self.device_name)
        elif strategy == 'explore':
            cli_str = r'''
            devices device %s drned-xmnr transitions explore-transitions
            ''' % (self.device_name)
        else:
            raise Exception('Unknown test strategy', strategy)

        # We spawn a subprocess, rather than invoking the action using
        # maapi, in order to provive continuous console feedback since
        # the commands typically takes a long time to run.
        cmd = 'ncs_cli -C -u admin'
        subprocess.run(cmd, input=cli_str, shell=True,
                       check=True, text=True).check_returncode()

    # # We spawn a subprocess, rather than invoking the action using
    # # maapi, in order to provive continuous console feedback since the
    # # commands typically takes a long time to run.
    # def translate(self, filter):
    #     cli_str = r'''
    #     devices device %s drned-xmnr state import-convert-cli-files file-path-pattern states/%s overwrite true
    #     ''' % (self.device_name, filter)
    #     cmd = 'ncs_cli -C -u admin'
    #     subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True).check_returncode()


def create_authgroup(authgroup, username, password):
    """Create an authgroup to go with a device."""

    with ncs.maapi.single_write_trans('admin', 'write-ctx') as t:
        if not maapi_exists('/devices/authgroups/group{%s}' % authgroup):
            t.create('/devices/authgroups/group{%s}' % authgroup)
            t.create('/devices/authgroups/group{%s}/default-map' % authgroup)
            t.set_elem2(username,
                        '/devices/authgroups/group{%s}/default-map/remote-name' % authgroup)
            t.set_elem2(password,
                        '/devices/authgroups/group{%s}/default-map/remote-password' % authgroup)
            t.apply()


def create_device(device_name, device_ip, device_port, ned_id):
    """Create a NETCONF device."""

    with ncs.maapi.single_write_trans('admin', 'write-ctx') as t:
        t.create('/devices/device{%s}' % device_name)
        t.set_elem2(device_ip,
                    '/devices/device{%s}/address' % device_name)
        t.set_elem2(device_port,
                    '/devices/device{%s}/port' % device_name)
        t.set_elem2(ned_id,
                    '/devices/device{%s}/device-type/netconf/ned-id' % device_name)
        t.set_elem2(device_name,
                    '/devices/device{%s}/authgroup' % device_name)
        t.set_elem2('raw',
                    '/devices/device{%s}/trace' % device_name)
        t.set_elem2('300',
                    '/devices/device{%s}/read-timeout' % device_name)
        t.set_elem2('300',
                    '/devices/device{%s}/write-timeout' % device_name)
        t.set_elem2('false',
                    '/devices/device{%s}/commit-queue/enabled-by-default' % device_name)
        t.set_elem2('unlocked',
                    '/devices/device{%s}/state/admin-state' % device_name)
        t.apply()


def download_yang_modules(debug, device_name, ned_name, username, vendor, version):
    """Download YANG-modules from <device_name> using the nedbuilder tool."""

    # Start the nso interactive session
    p = pexpect.spawn('ncs_cli -C -u admin')
    if debug == True:
        p.logfile_read = sys.stdout.buffer
    p.expect_exact('admin@ncs#')
    print('Fetch hostkeys...', end='', flush=True)
    p.sendline('devices device %s ssh fetch-host-keys' % device_name)
    index = p.expect(['result failed', 'result (updated|unchanged).*admin@ncs#'])
    if index == 0:
        print('error, cannot fetch host keys!', flush=True)
        sys.exit(1)
    print('ok', flush=True)

    p.sendline('devtools true')
    p.expect_exact('admin@ncs#')
    p.sendline('config')
    p.expect_exact("admin@ncs(config)#")

    # Remove possible leftovers from earlier sessions
    p.sendline('no netconf-ned-builder project %s %s' % (ned_name, version))
    p.expect_exact('admin@ncs(config)#')
    p.sendline('commit')

    # Setup NETCONF NED builder
    print('Create NED Builder project...', end='', flush=True)
    p.sendline('netconf-ned-builder project %s %s device %s local-user %s vendor %s' % (ned_name, version, device_name, username, vendor))
    p.expect_exact('admin@ncs(config-project-%s/%s)#' % (ned_name, version))
    p.sendline('commit')
    p.expect_exact('admin@ncs(config-project-%s/%s)#' % (ned_name, version))
    p.sendline('exit')
    p.expect_exact('admin@ncs(config)#')
    p.sendline('exit')
    p.expect_exact('admin@ncs#')
    print('ok', flush=True)

    # Fetch YANG module list and select what YANG modules to include
    # in the NED.
    print('Fetch list of YANG moduels from %s...' % device_name, end='', flush=True)
    p.sendline('netconf-ned-builder project %s %s fetch-module-list' % (ned_name, version))
    p.expect_exact('admin@ncs#', timeout=120)
    p.sendline('show netconf-ned-builder project %s %s module | nomore' % (ned_name, version))
    index = p.expect_exact(['% No entries found.\r\nadmin@ncs#', 'admin@ncs#'], timeout=120)
    if index == 0:
        print('error', flush=True)
        print('Try ned-test.py build-ned -d ... to see what went wrong.', flush=True)
        sys.exit(1)
    print('ok', flush=True)

    p.sendline('netconf-ned-builder project %s %s module * * select' % (ned_name, version))
    p.expect_exact('admin@ncs#', timeout=120)

    # Wait for netconf-ned-builder to download all YANG models
    print('Downloading YANG modules from %s...' % device_name, flush=True)
    while True:
        p.sendline('show netconf-ned-builder project %s %s module * status | notab | nomore | exclude deselected | exclude module | exclude downloaded | count' % (ned_name, version))
        p.expect(r'Count: (\d+) lines')
        if p.match.group(1).decode('utf-8') == '0':
            break
        print('%s modules left...' % p.match.group(1).decode('utf-8'), flush=True)
        sleep(10)
    p.sendline('exit')
    p.expect(pexpect.EOF, timeout=None)
    # Don't use netconf-ned-builder to build the NED because
    #  1. We get greater control of build parameters when we create the
    #     build environment ourselves
    #  2. We must support building a NED based on user provided YANG-models
    #     anyways
    #  3. It's esier to see what goes wrong if the build fail


def fetch_host_keys(device_name):
    """Fetch host keys from <device_name>."""

    print('Fetch host keys...', end='', flush=True)
    res = maapi_run_action('/ncs:devices/device{%s}/ssh/fetch-host-keys' % device_name,
                           'devices device %s ssh fetch-host-keys' % device_name)
    if 'result failed' in res:
        fatal(res)
    print('ok', flush=True)


def sync_from(device_name):
    """Sync configuration from <device name>."""

    print('Sync configuration from %s...' % device_name, end='',flush=True)
    res = maapi_run_action('/ncs:devices/device{%s}/sync-from' % device_name,
                           'devices device %s sync-from' % device_name)
    if 'result false' in res:
        fatal(res)
    print('ok', flush=True)


def maapi_exists(xpath):
    """Return True if the node referred by <xpath> exists."""

    with ncs.maapi.single_read_trans('admin', 'read-ctx') as t:
        return t.exists(xpath)


def maapi_set_ned_id(device_name, ned_id):
    """Update ned-id for <device_name>."""

    with ncs.maapi.single_write_trans('admin', 'write-ctx') as t:
        t.set_elem2(ned_id, '/devices/device{%s}/device-type/netconf/ned-id' % device_name)
        t.apply()


def maapi_set_elem_str(xpath, str):
    """Set node reference by <xpath> to <str>."""

    with ncs.maapi.single_write_trans('admin', 'write-ctx') as t:
        t.set_elem2(str, xpath)
        t.apply()


def maapi_maagic(device_name):
    with ncs.maapi.single_read_trans('admin', 'write-ctx') as t:
        root = ncs.maagic.get_root(t)
        device_node = root.devices.device[device_name]
        return device_node


def maapi_run_action(action, args):
    """Run an action."""

    with ncs.maapi.single_read_trans('admin', 'read-ctx') as t:
        return t.request_action_str_th(args, action)


def get_device(device_name):
    """Read configuration for <device_name> and create a TestDevice."""

    args = Dummy()
    args.device_name = device_name
    args.cli_port = None
    args.dir = getcwd()

    with ncs.maapi.single_read_trans('admin', 'read-ctx') as t:
        authgroup = t.get_elem('/devices/device{%s}/authgroup' % device_name)

        if t.exists('/devices/device{%s}/drned-xmnr/cli-port' % device_name) and \
           t.exists('/devices/device{%s}/drned-xmnr/driver' % device_name):
            args.cli_port = t.get_elem('/devices/device{%s}/drned-xmnr/cli-port' % device_name)
            path_value = t.get_elem('/devices/device{%s}/drned-xmnr/driver' % device_name)
            args.dir = path_value.as_pyval().replace('/states/%s.py' % device_name, '')

        args.ip_address = t.get_elem('/devices/device{%s}/address' % device_name)
        args.ned_id = t.get_elem('/devices/device{%s}/device-type/netconf/ned-id' % device_name)
        args.netconf_port = t.get_elem('/devices/device{%s}/port' % device_name)
        encrypted_pw = t.get_elem('/devices/authgroups/group{%s}/default-map/remote-password' % authgroup)
        t.maapi.install_crypto_keys()
        cs_node = cs_node_cd(None, '/devices/authgroups/group{%s}/default-map/remote-password' % authgroup)
        args.password = decrypt(encrypted_pw.val2str(cs_node))
        args.username = t.get_elem('/devices/authgroups/group{%s}/default-map/remote-name' % authgroup)

    td = TestDevice(args)
    return td


def wait_for_nso():
    "Wait for NSO to start. In this context, start means up and running and have loaded all packages."

    print("Wait for NSO to start...", end='', flush=True)
    while is_nso_running():
        print(".", end='', flush=True)
        sleep(5)

    print("ok", flush=True)


def is_nso_running():
    "Check if NSO is running."

    cmd = r"ncs --status 2> /dev/null | grep -E '^status: started$' > /dev/null"
    o = subprocess.run(cmd, shell=True, text=True)
    return o.returncode


def create_test_device(args):
    "Create a new devices in NSO."

    td = TestDevice(args)
    td.setup_netconf_device()
    if args.cli_port is not None:
        td.setup_cli_device(args.cli_port)


def build_ned(args):
    "Build a NETCONF NED.  The device use for building the NED must use the plain (non device specific) NETCONF NED."

    device_path = '/devices/device{%s}' % args.device_name
    if not maapi_exists(device_path):
        msg = 'Must create the device %s before we can build the NED.' % device_path
        raise TestNedError(msg)

    td = get_device(args.device_name)
    if td.ned_id != 'netconf':
        msg = 'ned-id must be "netconf"'
        raise TestNedError(msg)

    td.get_yang_modules(args.debug, args.ned_name, args.vendor,
                        args.version, args.exclude, args.yang_source)
    ned_id = td.create_ned_package(args.ned_name, args.netsim,
                                   args.vendor, args.version)
    td.build_ned_package(ned_id)
    td.install_ned(ned_id)
    if args.install is True:
        maapi_set_ned_id(td.device_name, ned_id)


def record_test(args):
    "Record current configuration drned-xmnr state."

    td = get_device(args.device_name)
    td.setup_drned_xmnr()
    state_name = '/devices/device{%s}/drned-xmnr/state/states{%s}' % (args.device_name, args.state_name)
    if not maapi_exists(state_name):
        td.record_test(args.state_name)
    else:
        msg = '%s already exist' % args.state_name
        raise TestNedError(msg)


def import_tests(args):
    "Import pre-existing configuration states into drned-xmnr."

    td = get_device(args.device_name)
    td.setup_drned_xmnr()
    if exists(args.directory):
        td.import_tests(args.directory, args.pattern)
    else:
        msg = '%s must exist' % args.directory
        raise TestNedError(msg)

    # td.translate(args.filter)


def install_ned(args):
    "Install a NETCONF NED for the specified device, both the NED and the devive must exist."

    td = get_device(args.device_name)
    maapi_set_ned_id(td.device_name, args.ned_id)


def test_ned(args):
    "Run configured tests against the specified device."

    td = get_device(args.device_name)
    td.test_ned(args.strategy)


def cleanup(args):
    "Remove device and authgroup."

    with ncs.maapi.single_write_trans('admin', 'write-ctx') as t:
        t.delete('/devices/device{%s}' % args.device_name)
        t.delete('/devices/authgroups/group{%s}' % args.device_name)
        t.apply()


# Just use this for testing
def debug(args):
    "Easy way to quickly test constructs."

    # print(maapi_exists('devices/device{asr9k}'))
    # print(get_device(args.device_name))
    # dev = maapi_maagic(args.device_name)
    # with ncs.maapi.single_read_trans('admin', 'write-ctx') as t:
    #     root = ncs.maagic.get_root(t)
    #     device_node = root.devices.device[args.device_name]
    #     authgroup = root.devices.authgroups.group[device_node.authgroup]
    #     pw = authgroup.default_map.remote_password
    #     t.maapi.install_crypto_keys()
    #     print(authgroup.default_map.remote_name, decrypt(pw))
    # with ncs.maapi.single_read_trans('admin', 'read-ctx') as t:
    #     t.request_action_th(params, '/ncs:packages/reload')
    with ncs.maapi.Maapi() as m:
        with ncs.maapi.Session(m, 'admin', 'python'):
            root = ncs.maagic.get_root(m)
            input = root.packages.reload.get_input()
            input.force.create()
            output = root.packages.reload.request(input)
            print(output.reload_result['drned-xmnr'].result)


def ned_test(arguments):
    "Run NED test with specified arguments."

    parser = argparse.ArgumentParser(prog='ned-test')

    # Create a test device.  This is the the regular NSO device
    # representation + CLI port (needed if we want to be able to
    # translate CLI tests to NETCONF)
    subparsers = parser.add_subparsers(help='sub-command help')
    init_parser = subparsers.add_parser('init',
                                        help='Configure device and authentication information.')
    init_parser.add_argument('-c', '--cli-port',
                             help='CLI port.  SSH port for the CLI on the device.  '
                                  'Optional, only needed if we want to translate legacy CLI tests to NETCONF tests.')
    init_parser.add_argument('-d', '--dir',
                             help='Absolute path to the NSO run directory (default: %(default)s).',
                             default=getcwd())
    init_parser.add_argument('-i', '--ip-address',
                             help='The IP address of the test device.', required=True)
    init_parser.add_argument('-N', '--ned-id',
                             help='NETCONF NED id.  The name of the NETCONF NED to use, the NED must exist.  Default: %(default)s a basic NED without device YANG models.',
                             default='netconf')
    init_parser.add_argument('-n', '--netconf-port',
                             help='NETCONF port, only NETCONF over ssh is supported (default: %(default)s).',
                             default='830')
    init_parser.add_argument('-p', '--password',
                             help='Password for admin access to the device (default: %(default)s).',
                             default='admin')
    init_parser.add_argument('-u', '--username',
                             help='Admin username for the device (default: %(default)s).',
                             default='admin')
    init_parser.add_argument('device_name',
                             help='Device name. Local name for the device, can be anything.',
                             metavar='device_name')
    init_parser.set_defaults(func=create_test_device)

    # Build a NETCONF NED.  Build a NED for the specified device (must
    # have been created with ned-test init ...).  Optionally, install
    # the NED.
    build_ned_parser = subparsers.add_parser('build-ned',
                                             help='Build a NETCONF NED based on YANG models found on device_name or local YANG-models.')
    build_ned_parser.add_argument('-d', '--debug',
                                  help='Debug mode.',
                                  action='store_true')
    build_ned_parser.add_argument('-e', '--exclude',
                                  help='Excluded YANG-models. <space> separated list of YANG modules (glob-style patterns) to exclude from the NED (default: %(default)s).',
                                  default='""')
    build_ned_parser.add_argument('-i', '--install',
                                  help='Install the ned NED for the specified device.',
                                  action='store_true')
    build_ned_parser.add_argument('-m', '--netsim',
                                  help='Include netsim support in the NED (default: %(default)s).',
                                  action='store_const', const=' ', default=' --no-netsim')
    build_ned_parser.add_argument('-N', '--ned-name',
                                  help='NED name, (e.g. the name of the class of devices managed through this NED). The ned-id will be of the form <ned-name>-nc-<version>.',
                                  required=True)
    build_ned_parser.add_argument('-n', '--netconf-port',
                                  help='NETCONF port, only NETCONF over ssh is supported (default: %(default)s).',
                                  default='830')
    build_ned_parser.add_argument('-v', '--vendor',
                                  help='NED vendor (e.g. company name).',
                                  required=True)
    build_ned_parser.add_argument('-V', '--version',
                                  help='NED version.  Should be what ever make sense for the NED (e.g. match the OS version for the target device).',
                                  required=True)
    build_ned_parser.add_argument('-y', '--yang-source',
                                  help='YANG source. Indicate where YANG modules can be found, supported options are the absolute path of a local directory or "device", meaning retrive the modules from <device_name>.',
                                  default='device')
    build_ned_parser.add_argument('device_name',
                                  help='Device name. A device previously created with ned-test init',
                                  nargs='?', metavar='device_name', default='nedbuilder')
    build_ned_parser.set_defaults(func=build_ned)

    # Record a state
    record_test_parser = subparsers.add_parser('record-test',
                                               help='Save a test configuration.')
    record_test_parser.add_argument('device_name',
                                     help='Device name.  A device previously created with ned-test init.')
    record_test_parser.add_argument('-s', '--state-name',
                                    help='Name of state configuration to record.',
                                    required=True)
    record_test_parser.set_defaults(func=record_test)

    # Import test cases.  Import test-cases from saved configuration
    # files.  Importing test-cases in NSO XML and CLI format is
    # supported.
    import_tests_parser = subparsers.add_parser('import-tests',
                                                help='Import test vectors and optionally translate test configurations.')
    import_tests_parser.add_argument('-d', '--directory',
                                     help='Tests to import can be found in this directory.')
    import_tests_parser.add_argument('-p', '--pattern',
                                     help='Filter available tests (default: %(default)s).', default='*.xml')
    import_tests_parser.add_argument('device_name',
                                     help='Device name.  A device previously created with ned-test init.')
    import_tests_parser.set_defaults(func=import_tests)

    # Add a previously built NED to the specified device.  Both NED
    # and device must exist.
    install_ned_parser = subparsers.add_parser('install-ned',
                                               help='Install a previously built NED.')
    install_ned_parser.add_argument('-N', '--ned-id',
                                    help='NETCONF NED id.  The name of the NETCONF NED to use, the NED must exist.  Default: %(default)s a basic NED without device YANG models.',
                                    required=True)
    install_ned_parser.add_argument('device_name',
                                    help='Device name.  A device previously created with ned-test init.')
    install_ned_parser.set_defaults(func=install_ned)

    # Run stored tests.
    test_ned_parser = subparsers.add_parser('test-ned',
                                            help='Test the NETCONF/YANG interface of "device_name" by applying all installed test configurations.')
    test_ned_parser.add_argument('-s', '--strategy',
                                 help='Strategy for applying test configurations, explore or walk (default: %(default)s).', default='walk')
    test_ned_parser.add_argument('device_name',
                                 help='Device name.  A device previously created with ned-test init.')
    test_ned_parser.set_defaults(func=test_ned)

    # Cleanup after testing. (Remove device and authgroup)
    cleanup_parser = subparsers.add_parser('cleanup',
                                           help='Remove test device and artifacts produced during testing.')
    cleanup_parser.add_argument('device_name',
                                help='Device name.  A device previously created with ned-test init ...')
    cleanup_parser.set_defaults(func=cleanup)

    # Simple way to test functions
    debug_parser = subparsers.add_parser('debug', help='Test commands')
    debug_parser.add_argument('device_name', help='Device name')
    debug_parser.set_defaults(func=debug)

    # Print brief help text if no arguments was given
    if len(arguments) == 0:
        parser.error("Missing required command")

    args = parser.parse_args(arguments)

    # Wait for NSO to start...
    wait_for_nso()

    # Run the action
    args.func(args)


if __name__ == '__main__':
    ned_test(sys.argv[1:])
