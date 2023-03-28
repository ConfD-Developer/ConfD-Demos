from enum import Enum
import logging
from typing import Tuple, Dict, List, Iterable
import re

import gnmi_pb2

VERSION = "0.3.0-dev"
HOST = "localhost"
PORT = 50061


def config_logging(
        format='%(asctime)s %(levelname)s:%(filename)s:%(lineno)s:%(funcName)s '
               '%(message)s [%(threadName)s]',
        level=logging.WARNING,
        force=False):
    logging.basicConfig(format=format, level=level, force=force)


config_logging()
log = logging.getLogger('confd_gnmi_common')


def common_optparse_options(parser):
    parser.add_argument("--logging", action="store", dest="logging",
                        choices=["error", "warning", "info", "debug"],
                        help="Logging level",
                        default="warning")
    parser.add_argument("--insecure", action="store_true", dest="insecure",
                        help="Use insecure connection",
                        default=False)
    parser.add_argument("--port", action="store", dest="port",
                        type=int,
                        help="port number (default: {})".format(PORT),
                        default=PORT)
    parser.add_argument("--host", action="store", dest="host",
                        help="host (name, ip, default: {})".format(HOST),
                        default=HOST)


def common_optparse_process(opt, log):
    level = None
    if opt.logging == "error":
        level = logging.ERROR
    elif opt.logging == "warning":
        level = logging.WARNING
    elif opt.logging == "info":
        level = logging.INFO
    elif opt.logging == "debug":
        level = logging.DEBUG
    else:
        log.warning("Unknown logging level %s", opt.logging)
    set_logging_level(level)


def set_logging_level(level):
    if level is not None:
        # Thanks https://stackoverflow.com/a/53250066
        [logging.getLogger(name).setLevel(level) for name in
         logging.root.manager.loggerDict]
    config_logging(level=level, force=True)


# TODO tests
def make_name_keys(elem_string) -> Tuple[str, Dict[str, str]]:
    """
    Split element string to element name and keys.
    e.g. elem[key1=7][key2=aaa] => (elem, {key1:7, key2:aaa})
    :param elem_string:
    :return: tuple with element name and key map
    """
    log.debug("==> elem_string=%s", elem_string)
    keys = {}
    name = elem_string
    if '[' in elem_string:
        ks = elem_string.split("[")
        name = ks[0]
        for k in ks[1:]:
            if k != '':
                key = k.replace("]", '').split('=')
                keys[key[0]] = key[1]
    log.debug("<== name=%s keys=%s", name, keys)
    return name, keys


def parse_instance_path(xpath_string) -> Iterable[Tuple[str, List[Tuple[str, str]]]]:
    """Parse instance path to an iterable of (tag, keys) tuples.

    Instance paths are a limited form of XPath expressions - only
    predicates in the form of a key assignment are accepted.
    """

    tag_rx = re.compile(r'/?(?P<tag>[^/\[\]]+)(?P<preds>(?:\[[^\]]*\])*)')
    predicate_rx = re.compile(r'\[([^=]+)=([^\]]*)\]')

    for match in tag_rx.finditer(xpath_string):
        mdict = match.groupdict()
        keys = [pred.groups() for pred in predicate_rx.finditer(mdict['preds'])]
        yield (mdict['tag'], keys)


# Crate gNMI Path object from string representation of path
# see: https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md#222-paths
# TODO tests
def make_gnmi_path(xpath_string: str, origin: str = None, target: str = None) -> gnmi_pb2.Path:
    """ Create gNMI path from input string. """
    log.debug("==> xpath_string=%s origin=%s target=%s", xpath_string, origin, target)
    path_elms = [gnmi_pb2.PathElem(name=tag, key=dict(keys))
                 for tag, keys in parse_instance_path(xpath_string)]
    path = gnmi_pb2.Path(elem=path_elms, target=target, origin=origin)
    log.debug("<== path=%s", path)
    return path


def _make_string_path(gnmi_path=None, gnmi_prefix=None, quote_val=False,
                      xpath=False) -> str:
    """
    Create string path from gnmi_path and gnmi_prefix
    :param gnmi_path:
    :param gnmi_prefix:
    :param quote_val:
    :param xpath:
    :return:
    """
    log.debug("==> gnmi_path=%s gnmi_prefix=%s quote_val=%s xpath=%s",
              gnmi_path, gnmi_prefix, quote_val, xpath)

    def make_path(gnmi_path):
        path = ""
        for e in gnmi_path.elem:
            path += "/" + e.name
            for k, v in e.key.items():
                val = v if not quote_val else "\"{}\"".format(v)
                path += "[{}={}]".format(k, val) if xpath else "{{{}}}".format(
                    val)
        if path == "":
            path = "/"
        return path

    path_str = ""
    if gnmi_prefix is not None and len(gnmi_prefix.elem) > 0:
        path_str = make_path(gnmi_prefix)
    if gnmi_path is not None:
        path_str = path_str + make_path(gnmi_path)
    log.debug("<== path_str=%s", path_str)
    return path_str


# TODO tests
def make_xpath_path(gnmi_path=None, gnmi_prefix=None, quote_val=False) -> str:
    """
    Create string path from gnmi_path and gnmi_prefix
    :param gnmi_path:
    :param gnmi_prefix:
    :param quote_val:
    :return:
    """
    log.debug("==> gnmi_path=%s gnmi_prefix=%s quote_val=%s",
              gnmi_path, gnmi_prefix, quote_val)

    path_str = _make_string_path(gnmi_path=gnmi_path, gnmi_prefix=gnmi_prefix,
                                 quote_val=quote_val, xpath=True)

    log.debug("<== path_str=%s", path_str)
    return path_str


def make_formatted_path(gnmi_path, gnmi_prefix=None, quote_val=False) -> str:
    """
    Create string path from gnmi_path and gnmi_prefix
    :param gnmi_path:
    :param gnmi_prefix:
    :param quote_val:
    :return:
    """
    log.debug("==> gnmi_path=%s gnmi_prefix=%s quote_val=%s",
              gnmi_path, gnmi_prefix, quote_val)

    path_str = _make_string_path(gnmi_path=gnmi_path, gnmi_prefix=gnmi_prefix,
                                 quote_val=quote_val, xpath=False)

    log.debug("<== path_str=%s", path_str)
    return path_str


def add_path_prefix(path, prefix):
    return gnmi_pb2.Path(elem=list(prefix.elem) + list(path.elem),
                         origin=path.origin,
                         target=path.target)


def remove_path_prefix(path, prefix):
    assert path.elem[:len(prefix.elem)] == prefix.elem[:]
    return gnmi_pb2.Path(elem=path.elem[len(prefix.elem):],
                         origin=path.origin,
                         target=path.target)


def _convert_enum_format(constructor, value, exception_str, do_return_unknown, unknown_value):
    """ Private. Convert between string/int enumeration values using the input `constructor`.
        If unknown/unsupported value is encountered, either raise exception or return value
        depending on input parameters. """
    try:
        if isinstance(value, str):
            # If the input is "UNKNOWN(x)" string - that ve most probably
            # created previously, convert it back to raw integer "x".
            num_str = value.lstrip('UNKNOWN(').rstrip(')')
            if len(num_str) > 0:
                return str(num_str)
        return constructor(value)
    except ValueError as ex:
        if do_return_unknown:
            return unknown_value
        raise ValueError(exception_str) from ex

def datatype_str_to_int(data_type: str, no_error=False) -> int:
    """ Convert text representation of DataType to standardized integer. """
    return _convert_enum_format(gnmi_pb2.GetRequest.DataType.Value, data_type,
                                f'Unknown DataType! ({data_type})', no_error, -1)

def encoding_str_to_int(encoding: str, no_error=False) -> int:
    """ Convert text representation of Encoding to standardized integer. """
    return _convert_enum_format(gnmi_pb2.Encoding.Value, encoding,
                                f'Unknown Encoding! ({encoding})', no_error, -1)

def encoding_int_to_str(encoding: int, no_error=False) -> str:
    """ Convert integer representation of Encoding to standardized string. """
    return _convert_enum_format(gnmi_pb2.Encoding.Name, encoding,
                                f'Unknown Encoding value! ({encoding})',
                                no_error, f'UNKNOWN({encoding})')

def subscription_mode_str_to_int(mode: str, no_error=False) -> int:
    """ Convert text representation of SubscriptionList to standardized integer. """
    return _convert_enum_format(gnmi_pb2.SubscriptionList.Mode.Value, mode,
                                f'Unknown subscription mode! ({mode})',
                                no_error, f'UNKNOWN({mode})')
