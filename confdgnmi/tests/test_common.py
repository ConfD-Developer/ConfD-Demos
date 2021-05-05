import pytest

from confd_gnmi_api_adapter_defaults import ApiAdapterDefaults
from confd_gnmi_client import parse_args as client_parse_args
from confd_gnmi_common import make_name_keys, make_gnmi_path, make_xpath_path, \
    make_formatted_path
from confd_gnmi_server import parse_args as server_parse_args


@pytest.mark.unit
@pytest.mark.parametrize("input, output", [
    ("name[key1=val1]", ("name", {"key1": "val1"})),
    ("name[key1=val1][key2=val2]",
     ("name", {"key1": "val1", "key2": "val2"})),
    ("name[key1=val1][key2=val2][key3=val3]",
     ("name", {"key1": "val1", "key2": "val2", "key3": "val3"})),
])
def test_make_name_keys(input, output):
    (name, keys) = make_name_keys(input)
    assert name == output[0]
    assert keys == output[1]


@pytest.mark.unit
@pytest.mark.parametrize("path",
                         ["/name1", "/", "/name1/name2", "/name1[key1=val1]"])
def test_make_path(path):
    def xpath_to_formatted(xpath):
        formatted = ""
        for elem in path.split('/'):
            formatted += "/"
            if elem != "":
                elem_string = elem
                if "[" in elem:
                    namekeys = make_name_keys(elem)
                    elem_string = namekeys[0]
                    for k, v in namekeys[1].items():
                        elem_string += "{{{}}}".format(v)
                formatted += elem_string
        formatted = formatted.replace("//", "/")
        return formatted

    gnmi_path = make_gnmi_path(path)
    xpath_path = make_xpath_path(gnmi_path)
    assert path == xpath_path
    formatted_path = make_formatted_path(gnmi_path)
    assert xpath_to_formatted(path) == formatted_path


def check_in_args(args, check_dict):
    args_dict = vars(args)
    # print("args_dict={}", args_dict)
    for k, v in check_dict.items():
        assert k in args_dict and str(args_dict[k]) == str(v)


def check_args(check_array, parse_args):
    for c in check_array:
        for a in c["args"]:
            for v in c["vals"]:
                check_in_args(parse_args([a, v]), {c["dest"]: v})
            if "invalid" in c:
                # TODO testing for invalid args
                pass
                # for v in c["invalid"]:
                #    with pytest.raises(SystemExit):
                #        check_in_args(server_parse_args([a, v]), {c["dest"]: v})


@pytest.mark.unit
def test_client_argparse():
    check_in_args(client_parse_args([]),
                  {'operation': 'capabilities', 'logging': 'warning',
                   'prefix': '',
                   'paths': [], 'datatype': 'CONFIG', 'vals': [],
                   'submode': 'ONCE', 'pollcount': 5, 'pollinterval': 0.5,
                   'readcount': 4})

    check_in_args(client_parse_args(["-t", "CONFIG"]), {"datatype": "CONFIG"})
    check = [{"dest": "operation", "args": ["-o", "--oper"],
              "vals": ["capabilities", "set", "get", "subscribe"], },
             {"dest": "prefix", "args": ["--prefix"],
              "vals": ["", "/interfaces", "/interfaces-state"]},
             # todo test for array values
             # {"dest": "paths", "args": ["-p", "--path"],
             #  "vals": [ "/interfaces", "interfaces-state"]},
             {"dest": "datatype", "args": ["-t", "--data-type"],
              "vals": ["ALL", "CONFIG", "STATE", "OPERATIONAL"]},
             # todo test for array values
             # {"dest": "vals", "args": ["-v", "--vals"],
             #  "vals": [ "gigabitEthernet", "fastEther"]},
             {"dest": "submode", "args": ["-s", "--sub-mode"],
              "vals": ["ONCE", "POLL", "STREAM"]},
             {"dest": "pollcount", "args": ["--poll-count"],
              "vals": ["1", "10", "100"]},
             {"dest": "pollinterval", "args": ["--poll-interval"],
              "vals": ["0.1", "0.5", "1.0"]},
             {"dest": "readcount", "args": ["--read-count"],
              "vals": ["1", "10", "100"]},
             {"dest": "logging", "args": ["--logging"],
              "vals": ["error", "warning", "info", "debug"]},
             ]
    check_args(check, client_parse_args)
    # TODO more args tests


@pytest.mark.unit
def test_server_argparse():
    check_in_args(server_parse_args([]),
                  {"type": "demo", "logging": "warning", "confd_debug": "debug",
                   "confd_addr": ApiAdapterDefaults.CONFD_ADDR,
                   "confd_port": ApiAdapterDefaults.CONFD_PORT,
                   "monitor_external_changes": ApiAdapterDefaults.MONITOR_EXTERNAL_CHANGES,
                   "external_port": ApiAdapterDefaults.EXTERNAL_PORT,
                   "cfg": None})

    check = [{"dest": "type", "args": ["-t", "--type"],
              "vals": ["demo", "api"], "invalid": ["netconf"]},
             {"dest": "confd_debug", "args": ["-d", "--confd-debug"],
              "vals": ["trace", "debug", "silent", "proto"]},
             {"dest": "confd_addr", "args": ["--confd-addr"],
              "vals": [str(ApiAdapterDefaults.CONFD_ADDR), "10.0.0.1"]},
             {"dest": "confd_port", "args": ["--confd-port"],
              "vals": [str(ApiAdapterDefaults.CONFD_PORT), "3210"]},
             {"dest": "monitor_external_changes",
              "args": ["--monitor-external-changes"],
              "vals": []},
             {"dest": "external_port", "args": ["--external-port"],
              "vals": [str(ApiAdapterDefaults.EXTERNAL_PORT), "1234"]},
             {"dest": "logging", "args": ["--logging"],
              "vals": ["error", "warning", "info", "debug"]}, ]
    check_args(check, server_parse_args)
    # TODO more args tests
