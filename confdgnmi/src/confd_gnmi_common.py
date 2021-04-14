import logging

import gnmi_pb2

VERSION = "0.2.0"
HOST = "localhost"
PORT = 50061
logging.basicConfig(
    format='%(asctime)s:%(relativeCreated)s %(levelname)s:%(filename)s:%(lineno)s:%(funcName)s %(message)s [%(threadName)s]',
    level=logging.WARNING)
log = logging.getLogger('confd_gnmi_common')


def common_optparse_options(parser):
    parser.add_option("--logging", action="store", dest="logging",
                      help="Logging level [error, warning, info, debug]",
                      default="warning")


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


# TODO tests
def make_name_keys(elem_string) -> (str, str):
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


# Crate gNMI Path object from string representation of path
# see: https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md#222-paths
# TODO tests
def make_gnmi_path(xpath_string, origin=None, target=None) -> gnmi_pb2.Path:
    """
    Create gnmi path from string path
    :param xpath_string:
    :param origin:
    :param target:
    :return:
    """
    log.debug("==> path_string=%s origin=%s target=%s",
              xpath_string, origin, target)
    elems = []
    elem_strings = xpath_string.split('/')
    log.debug("elem_strings=%s", elem_strings)
    for e in elem_strings:
        if e != '':
            (name, keys) = make_name_keys(e)
            elem = gnmi_pb2.PathElem(name=name, key=keys)
            elems.append(elem)
    path = gnmi_pb2.Path(elem=elems, target=target, origin=origin)
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


def get_data_type(datatype_str):
    datatype_map = {
        "ALL": gnmi_pb2.GetRequest.DataType.ALL,
        "CONFIG": gnmi_pb2.GetRequest.DataType.CONFIG,
        "STATE": gnmi_pb2.GetRequest.DataType.STATE,
        "OPERATIONAL": gnmi_pb2.GetRequest.DataType.OPERATIONAL,
    }
    return datatype_map[datatype_str]


def get_sub_mode(mode_str):
    mode_map = {
        "ONCE": gnmi_pb2.SubscriptionList.ONCE,
        "POLL": gnmi_pb2.SubscriptionList.POLL,
        "STREAM": gnmi_pb2.SubscriptionList.STREAM,
    }
    return mode_map[mode_str]
