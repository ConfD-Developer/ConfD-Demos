from confd_gnmi_adapter import GnmiServerAdapter
from confd_gnmi_common import *

log = logging.getLogger('confd_gnmi_demo_adapter')


class GnmiDemoServerAdapter(GnmiServerAdapter):
    # simple demo database
    # map with XPath, value - both strings
    demo_db = {}
    demo_state_db = {}
    num_of_ifs = 10
    _instance: GnmiServerAdapter = None

    capability_list = [
        dict(name="tailf-common", organization="", version="2020-06-25"),
        dict(name="ietf-inet-types", organization="", version="2013-07-15"),
        dict(name="ietf-interfaces", organization="", version="2014-05-08"),
    ]

    def __init__(self):
        self._fill_demo_db()

    @classmethod
    def get_inst(cls):
        if cls._instance is None:
            cls._instance = GnmiDemoServerAdapter()
        return cls._instance

    def _fill_demo_db(self):
        log.debug("==>")
        for i in range(GnmiDemoServerAdapter.num_of_ifs):
            if_name = "if_{}".format(i + 1)
            state_if_name = "state_if_{}".format(i + 1)
            path = "/interfaces/interface[name={}]".format(if_name)
            state_path = "/interfaces-state/interface[name={}]".format(
                state_if_name)
            self.demo_db["{}/name".format(path)] = if_name
            self.demo_state_db["{}/name".format(state_path)] = state_if_name
            self.demo_db["{}/type".format(path)] = "gigabitEthernet"
            self.demo_state_db["{}/type".format(state_path)] = "gigabitEthernet"
        log.debug("<== self.demo_db=%s self.demo_state_db=%s", self.demo_db,
                  self.demo_state_db)

    class SubscriptionHandler(GnmiServerAdapter.SubscriptionHandler):

        def make_subscription_response(self) -> gnmi_pb2.SubscribeResponse:
            log.debug("==>")
            assert self.subscription_list != None
            # for now we only process GET type (fetch and return everything)
            assert self.subscription_stream_event_type == self.SubscriptionStreamEventType.GET

            update = []
            for s in self.subscription_list.subscription:
                path_with_prefix_str = make_xpath_path(s.path,
                                                       self.subscription_list.prefix)
                prefix_str = make_xpath_path(
                    gnmi_prefix=self.subscription_list.prefix)
                log.debug("path_with_prefix_str=%s perfix_str=%s",
                          path_with_prefix_str, prefix_str)
                for p, v in self.adapter.demo_db.items():
                    if p.startswith(path_with_prefix_str):
                        p = p[len(prefix_str):]
                        update.append(gnmi_pb2.Update(path=make_gnmi_path(p),
                                                      val=gnmi_pb2.TypedValue(
                                                          string_val=v)))
            delete = []
            notif = gnmi_pb2.Notification(timestamp=0,
                                          prefix=self.subscription_list.prefix,
                                          alias="/alias", update=update,
                                          delete=delete,
                                          atomic=False)

            response = gnmi_pb2.SubscribeResponse(update=notif)
            log.debug("<== response=%s", response)
            return response

    def get_subscription_handler(self) -> SubscriptionHandler:
        log.debug("==>")
        handler = self.SubscriptionHandler(self)
        log.debug("<== handler=%s", handler)
        return handler

    def get_instance(cls) -> GnmiServerAdapter:
        return GnmiDemoServerAdapter()

    def capabilities(self):
        cap = []
        for c in GnmiDemoServerAdapter.capability_list:
            cap.append(
                GnmiServerAdapter.CapabilityModel(name=c['name'],
                                                  organization=c[
                                                      'organization'],
                                                  version=c['version']))
        return cap

    def get_updates(self, path, prefix, data_type):
        log.debug("==> path=%s prefix=%s", path, prefix)
        path_with_prefix_str = make_xpath_path(gnmi_path=path,
                                               gnmi_prefix=prefix)
        prefix_str = make_xpath_path(gnmi_prefix=prefix)
        log.debug("path_with_prefix_str=%s perfix_str=%s",
                  path_with_prefix_str, prefix_str)
        update = []

        def process_db(db):
            for p, v in db.items():
                if p.startswith(path_with_prefix_str):
                    p = p[len(prefix_str):]
                    update.append(gnmi_pb2.Update(path=make_gnmi_path(p),
                                                  val=gnmi_pb2.TypedValue(
                                                      string_val=v)))

        if data_type == gnmi_pb2.GetRequest.DataType.CONFIG or \
                data_type == gnmi_pb2.GetRequest.DataType.ALL:
            process_db(self.demo_db)
        if data_type != gnmi_pb2.GetRequest.DataType.CONFIG:
            process_db(self.demo_state_db)
        log.debug("<== update=%s", update)
        return update

    def get(self, prefix, paths, data_type, use_models):
        log.debug("==> prefix=%s, paths=%s, data_type=%s, use_models=%s",
                  prefix, paths, data_type, use_models);
        notifications = []
        update = []
        for path in paths:
            update.extend(self.get_updates(path, prefix, data_type))
        notif = gnmi_pb2.Notification(timestamp=1, prefix=prefix,
                                      update=update,
                                      delete=[],
                                      atomic=True)
        notifications.append(notif)
        log.debug("<== notifications=%s", notifications)
        return notifications

    def set(self, prefix, path, val):
        log.info("==> prefix=%s, path=%s, val=%s",
                 prefix, path, val);
        path_str = make_xpath_path(path, prefix)
        op = gnmi_pb2.UpdateResult.INVALID
        if path_str in self.demo_db:
            if hasattr(val, "string_val"):
                str_val = val.string_val
            else:
                # TODO
                str_val = "{}".format(val)
            self.demo_db[path_str] = str_val
            op = gnmi_pb2.UpdateResult.UPDATE

        log.info("==> op=%s", op)
        return op
