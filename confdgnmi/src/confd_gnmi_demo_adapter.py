from confd_gnmi_adapter import GnmiServerAdapter
from confd_gnmi_common import *

log = logging.getLogger('confd_gnmi_demo_adapter')


class GnmiDemoServerAdapter(GnmiServerAdapter):
    # simple demo database
    # map with XPath, value - both strings
    demo_db = {}
    _instance: GnmiServerAdapter = None

    def __init__(self):
        self._fill_demo_db()

    @classmethod
    def get_inst(cls):
        if cls._instance is None:
            cls._instance = GnmiDemoServerAdapter()
        return cls._instance

    def _fill_demo_db(self):
        log.debug("==>")
        if_num = 100
        for i in range(if_num):
            if_name = "cp_ont_{}".format(i + 1)
            path = "/interfaces/interface[name={}]".format(if_name)
            self.demo_db["{}/name".format(path)] = if_name
            self.demo_db["{}/type".format(path)] = "gigabitEthernet"
        log.debug("==> self.demo_db=%s", self.demo_db)

    class SubscriptionHandler(GnmiServerAdapter.SubscriptionHandler):

        # # TODO
        # key: int = 82
        #
        # def _make_name_elem(self, k) -> str:
        #     return "cp_ont_{}".format(k)

        # def _make_update(self, k):
        #     return gnmi_pb2.Update(path=make_gnmi_path(
        #         "interface[name={}]/name".format(self._make_name_elem(k))),
        #         val=gnmi_pb2.TypedValue(
        #             string_val=self._make_name_elem(k)))

        def make_subscription_response(self) -> gnmi_pb2.SubscribeResponse:
            log.debug("==>")
            assert self.subscription_list != None
            # for now we only process GET type (fetch and return everything)
            assert self.subscription_stream_event_type == self.SubscriptionStreamEventType.GET

            update = []
            for s in self.subscription_list.subscription:
                path_str = make_xpath_path(s.path,
                                           self.subscription_list.prefix)
                if path_str in self.adapter.demo_db:
                    update.append(
                        gnmi_pb2.Update(path=s.path,
                                        val=gnmi_pb2.TypedValue(
                                            string_val=self.adapter.demo_db[path_str]))
                    )
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
        cap = [
            GnmiServerAdapter.CapabilityModel(name="tailf-common",
                                              organization="tail-f",
                                              version="1.1"),
            GnmiServerAdapter.CapabilityModel(name="ietf-types",
                                              organization="ietf",
                                              version="1.2")
        ]
        return cap

    def get(self, prefix, paths, data_type, use_models):
        log.debug("==> prefix=%s, paths=%s, data_type=%s, use_models=%",
                  prefix, paths, data_type, use_models);
        notifications = []
        update = []
        for path in paths:
            path_str = make_xpath_path(path, prefix)
            if path_str in self.demo_db:
                up = gnmi_pb2.Update(path=path,
                                     val=gnmi_pb2.TypedValue(
                                         string_val=self.demo_db[path_str]))
                update.append(up)
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
