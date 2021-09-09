#!/usr/bin/env python
# -*- mode: python; python-indent: 4 -*-
#

import argparse
from os import getcwd
from os.path import dirname
import pexpect
import shutil
import subprocess
import sys
from time import sleep


import ncs
from _ncs import cs_node_cd, decrypt


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
        self.cli_port = args.cli_port
        self.dir = args.dir
        self.device_name = args.device_name
        self.ip_address = args.ip_address
        self.ned_id = args.ned_id
        self.netconf_port = args.netconf_port
        self.password = args.password
        self.username = args.username

    def build_ned_package(self):
        cmd = "make -C /tmp/%s/src clean all" % self.ned_id
        subprocess.run(cmd, shell=True, check=True, text=True)

    def create_ned_package(self, ned_name, netsim, vendor, version):
        self.ned_id = '%s-nc-%s' % (ned_name, version)
        shutil.rmtree(self.ned_id, ignore_errors=True)
        cmd = ("ncs-make-package --netconf-ned /tmp/yangs %s --dest /tmp/%s "
               "--no-java%s --no-python --no-test --verbose --vendor %s "
               "--package-version %s" % (ned_name, self.ned_id, netsim, vendor, version))
        subprocess.run(cmd, shell=True, check=True, text=True)

    def get_yang_modules(self, ned_name, vendor, version,
                         exclude_patterns, yang_source='device'):
        if yang_source == 'device':
            download_yang_modules(self.device_name, ned_name,
                                  self.username, vendor, version)
            src_dir = 'state/netconf-ned-builder/cache/%s-nc-%s' % (ned_name, version)
        elif yang_source == 'local':
            src_dir = '/yangs'
        else:
            raise Exception('Unknown YANG source:', yang_source)

        dst_dir = '/tmp/yangs'
        shutil.rmtree('/tmp/yangs', ignore_errors=True)
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(*exclude_patterns.split(' ')))


    def install_ned(self):
        package_dir = "%s/packages/%s" % (self.dir, self.ned_id)
        shutil.rmtree(package_dir, ignore_errors=True)
        shutil.copytree("/tmp/%s" % self.ned_id,
                        package_dir, dirs_exist_ok=True)
        cli_str = r'''
        packages reload force
        '''
        cmd = "ncs_cli -C -u admin"
        subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True)

    def setup_cli_device(self):
        template = '%s/bin/device.template' % self.dir
        driver = '%s/states/%s.py' % (self.dir, self.device_name)
        shutil.copyfile(template, driver)
        maapi_set_elem_str('/devices/device{%s}/drned-xmnr/cli-port' % self.device_name,
                           self.cli_port)
        maapi_set_elem_str('/devices/device{%s}/drned-xmnr/driver' % self.device_name,
                           driver)

    def setup_drned_xmnr(self):
        cli_str = r'''
        devices device %s drned-xmnr setup setup-xmnr overwrite true
        ''' % self.device_name
        cmd = "ncs_cli -C -u admin"
        subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True)
        cli_str = r'''
        devices device %s drned-xmnr state record-state state-name start overwrite true
        ''' % self.device_name
        subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True)

    def setup_netconf_device(self):
        authgroup = create_authgroup(self.device_name, self.username, self.password)
        create_device(self.device_name, self.ip_address, self.netconf_port, self.ned_id, authgroup)
        fetch_host_keys(self.device_name)
        sync_from(self.device_name)

    def test_ned(self, strategy):
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

        cmd = "ncs_cli -C -u admin"
        subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True)

    def translate(self, filter):
        cli_str = r'''
        devices device %s drned-xmnr state import-convert-cli-files file-path-pattern states/%s overwrite true
        ''' % (self.device_name, filter)
        cmd = "ncs_cli -C -u admin"
        subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True)


def create_authgroup(group, user, password):
    cli_str = r'''
    config
     devices authgroups group %s
     default-map remote-name %s
     default-map remote-password %s
     !
    commit
    !
    ''' % (group, user, password)
    cmd = "ncs_cli -C -u admin"
    subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True)
    return group


def create_device(device_name, device_ip, device_port, ned_id, authgroup):
    cli_str = r'''
    config
     devices device %s
     address %s
     port %s
     authgroup %s
     device-type netconf ned-id %s
     trace pretty
     read-timeout 300
     write-timeout 300
     commit-queue enabled-by-default false
     state admin-state unlocked
     !
    commit
    !
    ''' % (device_name, device_ip, device_port, authgroup, ned_id)
    cmd = "ncs_cli -C -u admin"
    subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True)


def download_yang_modules(device_name, ned_name, username, vendor, version):
    # Start the nso interactive session
    p = pexpect.spawn('ncs_cli -C -u admin')
    p.logfile_read = sys.stdout.buffer
    p.expect_exact('admin@ncs#')
    p.sendline('devices device %s ssh fetch-host-keys' % device_name)
    p.expect('result.*admin@ncs#')
    p.sendline('devtools true')
    p.expect_exact('admin@ncs#')
    p.sendline('config')
    p.expect_exact("admin@ncs(config)#")

    # Remove possible leftovers from earlier sessions
    p.sendline('no netconf-ned-builder project %s %s' % (ned_name, version))
    p.expect_exact('admin@ncs(config)#')
    p.sendline('commit')

    # Setup NETCONF NED builder
    p.sendline('netconf-ned-builder project %s %s device %s local-user %s vendor %s' % (ned_name, version, device_name, username, vendor))
    p.expect_exact('admin@ncs(config-project-%s/%s)#' % (ned_name, version))
    p.sendline('commit')
    p.expect_exact('admin@ncs(config-project-%s/%s)#' % (ned_name, version))
    p.sendline('exit')
    p.expect_exact('admin@ncs(config)#')
    p.sendline('exit')
    p.expect_exact('admin@ncs#')

    # Fetch YANG module list and select what YANG modules to include in the NED...
    p.sendline('netconf-ned-builder project %s %s fetch-module-list' % (ned_name, version))
    p.expect_exact(['admin@ncs#', 'admin@ncs#'], timeout=120)
    p.sendline('netconf-ned-builder project %s %s module * * select' % (ned_name, version))
    p.expect_exact('admin@ncs#', timeout=120)

    # Wait for netconf-ned-builder to download all YANG models
    while True:
        p.sendline('show netconf-ned-builder project %s %s module * status | notab | nomore | exclude deselected | exclude module | exclude downloaded | count' % (ned_name, version))
        p.expect(r'Count: (\d+) lines')
        if p.match.group(1).decode('utf-8') == '0':
            break
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
    cli_str = r'''
    devices device %s ssh fetch-host-keys
    ''' % device_name
    cmd = "ncs_cli -C -u admin"
    subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True)


def sync_from(device_name):
    cli_str = r'''
    devices device %s sync-from
    ''' % device_name
    cmd = "ncs_cli -C -u admin"
    subprocess.run(cmd, input=cli_str, shell=True, check=True, text=True)


def maapi_exists(xpath):
    with ncs.maapi.single_read_trans('admin', 'read-ctx') as t:
        return t.exists(xpath)


def maapi_set_ned_id(dev, ned_id):
    with ncs.maapi.single_write_trans('admin', 'write-ctx') as t:
        t.set_elem2(ned_id, '/devices/device{%s}/device-type/netconf/ned-id' % dev)
        t.apply()


def maapi_set_elem_str(xpath, str):
    with ncs.maapi.single_write_trans('admin', 'write-ctx') as t:
        t.set_elem2(str, xpath)
        t.apply()


def maapi_maagic(device_name):
    with ncs.maapi.single_read_trans('admin', 'write-ctx') as t:
        root = ncs.maagic.get_root(t)
        device_node = root.devices.device[device_name]
        return device_node


def get_device(device_name):
    args = Dummy()
    args.device_name = device_name

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

    print("done", flush=True)


def is_nso_running():
    "Check if NSO is running."

    cmd = r"ncs --status 2> /dev/null | grep -E '^status: started$' > /dev/null"
    o = subprocess.run(cmd, shell=True, text=True)
    return o.returncode


def create_test_device(args):
    td = TestDevice(args)
    td.setup_netconf_device()
    if args.cli_port is not None:
        td.setup_cli_device()


def build_ned(args):
    xpath = '/devices/device{%s}' % args.device_name
    if not maapi_exists(xpath):
        msg = 'Must create the device %s before we can build the NED.' % xpath
        raise TestNedError(msg)

    td = get_device(args.device_name)
    if td.ned_id != 'netconf':
        msg = 'ned-id must be "netconf"'
        raise TestNedError(msg)

    td.get_yang_modules(args.ned_name, args.vendor, args.version, args.exclude, args.yang_source)
    td.create_ned_package(args.ned_name, args.netsim, args.vendor, args.version)
    td.build_ned_package()
    td.install_ned()
    if args.install == True:
        maapi_set_ned_id(td.device_name, td.ned_id)


def import_tests(args):
    td = get_device(args.device_name)
    td.setup_drned_xmnr()

    td.translate(args.filter)


def test_ned(args):
    td = get_device(args.device_name)
    td.test_ned(args.strategy)


def cleanup(args):
    with ncs.maapi.single_write_trans('admin', 'write-ctx') as t:
        t.delete('/devices/device{%s}' % args.device_name)
        t.apply()


# Just use this for testing
def debug(args):
    # print(maapi_exists('devices/device{asr9k}'))
    # print(get_device(args.device_name))
    # dev = maapi_maagic(args.device_name)
    with ncs.maapi.single_read_trans('admin', 'write-ctx') as t:
        root = ncs.maagic.get_root(t)
        device_node = root.devices.device[args.device_name]
        authgroup = root.devices.authgroups.group[device_node.authgroup]
        pw = authgroup.default_map.remote_password
        t.maapi.install_crypto_keys()
        print(authgroup.default_map.remote_name, decrypt(pw))


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
    build_ned_parser.add_argument('-e', '--exclude',
                                  help='Excluded YANG-models. <space> separated list of YANG modules (glob-style patterns) to exclude from the NED (default: %(default)s).',
                                  default='""')
    build_ned_parser.add_argument('-i', '--install',
                                  help='Install the ned NED for the specified device.',
                                  action='store_true')
    build_ned_parser.add_argument('-n', '--netsim',
                                  help='Include netsim support in the NED (default: %(default)s).',
                                  action='store_const', const=' ', default=' --no-netsim')
    build_ned_parser.add_argument('-N', '--ned-name',
                                  help='NED name, (e.g. the name of the class of devices managed through this NED). The ned-id will be of the form <ned-name>-nc-<version>.',
                                  required=True)
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
                                  help='Device name. A device previously created with ned-test init ...',
                                  nargs='?', metavar='device_name', default='nedbuilder')

    build_ned_parser.set_defaults(func=build_ned)

    # Import test cases.  Import test-cases from saved configuration
    # files.  Importing test-cases in NSO XML and CLI format is
    # supported.
    import_tests_parser = subparsers.add_parser('import-tests',
                                                help='Import test vectors and optionally translate test configurations.')
    import_tests_parser.add_argument('-f', '--filter',
                                     help='Filter available tests (default: %(default)s).', default='')
    import_tests_parser.add_argument('device_name',
                                     help='Device name.  A device previously created with ned-test init ...')

    import_tests_parser.set_defaults(func=import_tests)

    # Run stored tests.
    test_ned_parser = subparsers.add_parser('test-ned',
                                            help='Test the NETCONF/YANG interface of "device_name" by applying all installed test configurations.')
    test_ned_parser.add_argument('-s', '--strategy',
                                 help='Strategy for applying test configurations, explore or walk (default: %(default)s).', default='walk')
    test_ned_parser.add_argument('device_name',
                                 help='Device name.  A device previously created with ned-test init ...')

    test_ned_parser.set_defaults(func=test_ned)

    # Cleanup after testing
    cleanup_parser = subparsers.add_parser('cleanup',
                                           help='Remove test device and artifects produced during testing.')
    cleanup_parser.add_argument('device_name',
                                help='Device name.  A device previously created with ned-test init ...')

    cleanup_parser.set_defaults(func=cleanup)

    # Simple way to test functions
    debug_parser = subparsers.add_parser('debug', help='Test commands')
    debug_parser.add_argument('device_name', help='Device name')

    debug_parser.set_defaults(func=debug)

    args = parser.parse_args(arguments)

    # Wait for NSO to start...
    wait_for_nso()

    # Run the action
    args.func(args)


if __name__ == '__main__':
    ned_test(sys.argv[1:])
