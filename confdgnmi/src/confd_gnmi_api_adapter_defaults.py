# dataclass
class ApiAdapterDefaults:
    CONFD_ADDR = "127.0.0.1"
    # keep the same as _confd.CONFD_PORT
    # (cannot be directly used, so we do not have dependency on _confd module)
    CONFD_PORT = 4565
    MONITOR_EXTERNAL_CHANGES = False
    EXTERNAL_PORT = 5055
