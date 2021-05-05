import logging
import random
import threading
import xml.etree.ElementTree as ET
from enum import Enum
from queue import Queue, Empty
from random import randint

import gnmi_pb2
from confd_gnmi_adapter import GnmiServerAdapter
from confd_gnmi_common import make_xpath_path, make_gnmi_path

log = logging.getLogger('confd_gnmi_demo_adapter')


class GnmiDemoServerAdapter(GnmiServerAdapter):
    # simple demo database
    # map with XPath, value - both strings
    demo_db = {}
    demo_state_db = {}
    # we use same lock for demo_db and demo_state_db
    db_lock = threading.Lock()
    num_of_ifs = 10
    _instance: GnmiServerAdapter = None
    # config map of config elements
    # "changes" - array of changes contains  (path, val)  tuples or "break"
    #             or "send" string
    # "changes_idx" - current index of processing of "changes" array
    config = {}

    capability_list = [
        dict(name="tailf-aaa", organization="", version="2018-09-12"),
        dict(name="ietf-inet-types", organization="", version="2013-07-15"),
        dict(name="ietf-interfaces", organization="", version="2014-05-08"),
    ]

    def __init__(self):
        self._fill_demo_db()

    @staticmethod
    def load_config_string(xml_cfg):
        """
        Load config from string
        """
        log.debug("==> cfg=%s", xml_cfg)
        root = ET.fromstring(xml_cfg)
        log.info("root=%s", root)
        assert root.tag == "demo"
        changes = root.findall("./subscription/STREAM/changes/element")
        log.debug("changes=%s", changes)
        if len(changes):
            if "changes" not in GnmiDemoServerAdapter.config:
                GnmiDemoServerAdapter.config["changes"] = []
                GnmiDemoServerAdapter.config["changes_idx"] = 0
            for el in changes:
                log.debug("len(el)=%s", len(el))
                if len(el):
                    if len(el) == 2:
                        (path, val) = (el[0], el[1])
                        log.debug("path.text=%s val.text=%s", path.text,
                                  val.text)
                        GnmiDemoServerAdapter.config["changes"].append(
                            (path.text, val.text))
                elif len(el) == 0:
                    log.debug("el.tag=%s", el.text)
                    GnmiDemoServerAdapter.config["changes"].append(el.text)
        log.debug("<== GnmiDemoServerAdapter.config=%s",
                  GnmiDemoServerAdapter.config)

    @classmethod
    def get_adapter(cls):
        if cls._instance is None:
            cls._instance = GnmiDemoServerAdapter()
        return cls._instance

    def _fill_demo_db(self):
        log.debug("==>")
        with self.db_lock:
            for i in range(GnmiDemoServerAdapter.num_of_ifs):
                if_name = "if_{}".format(i + 1)
                state_if_name = "state_if_{}".format(i + 1)
                path = "/interfaces/interface[name={}]".format(if_name)
                state_path = "/interfaces-state/interface[name={}]".format(
                    state_if_name)
                self.demo_db["{}/name".format(path)] = if_name
                self.demo_state_db["{}/name".format(state_path)] = state_if_name
                self.demo_db["{}/type".format(path)] = "gigabitEthernet"
                self.demo_state_db[
                    "{}/type".format(state_path)] = "gigabitEthernet"
        log.debug("<== self.demo_db=%s self.demo_state_db=%s", self.demo_db,
                  self.demo_state_db)

    class SubscriptionHandler(GnmiServerAdapter.SubscriptionHandler):

        class ChangeEvent(Enum):
            ADD = 0
            SEND = 1
            FINISH = 10

        def __init__(self, adapter, subscription_list):
            super().__init__(adapter, subscription_list)
            self.monitored_paths = []
            self.change_db = []
            self.change_db_lock = threading.Lock()
            self.change_thread = None
            self.change_event_queue = None

        def get_sample(self, path, prefix) -> []:
            log.debug("==>")
            update = []
            path_with_prefix_str = make_xpath_path(path, prefix)
            prefix_str = make_xpath_path(gnmi_prefix=prefix)
            log.debug("path_with_prefix_str=%s prefix_str=%s",
                      path_with_prefix_str, prefix_str)

            def get_updates(db):
                for p, v in db.items():
                    if p.startswith(path_with_prefix_str):
                        p = p[len(prefix_str):]
                        update.append(gnmi_pb2.Update(path=make_gnmi_path(p),
                                                      val=gnmi_pb2.TypedValue(
                                                          string_val=v)))

            with self.adapter.db_lock:
                get_updates(self.adapter.demo_db)
                # 'if' below is optimization
                if len(update) == 0:
                    get_updates(self.adapter.demo_state_db)

            log.debug("<== update=%s", update)
            return update

        def get_monitored_changes(self) -> []:
            with self.change_db_lock:
                log.debug("==> self.change_db=%s", self.change_db)
                assert len(self.change_db) > 0
                update = []
                for c in self.change_db:
                    prefix_str = make_xpath_path(
                        gnmi_prefix=self.subscription_list.prefix)
                    p = c[0]
                    if c[0].startswith(prefix_str):
                        p = c[0][len(prefix_str):]
                    update.append(gnmi_pb2.Update(path=make_gnmi_path(p),
                                                  val=gnmi_pb2.TypedValue(
                                                      string_val=c[1])))
                self.change_db = []
            log.debug("<== update=%s", update)
            return update

        def _get_random_changes(self):
            log.debug("==>")
            changes = []
            candidate_paths = set()
            for mp in self.monitored_paths:
                for p, v in self.adapter.demo_db.items():
                    if p.startswith(mp):
                        # we only simulate changes on type leaf
                        candidate_paths.add(
                            p.replace("/name", "/type"))
            log.debug("candidate_paths=%s", candidate_paths)
            for path in random.sample(candidate_paths,
                                      min(len(candidate_paths), 4)):
                new_val = "gigabitEthernet"
                if self.adapter.demo_db[path] == "gigabitEthernet":
                    new_val = "fastEther"
                log.debug("adding change path=%s, new_val=%s", path,
                          new_val)
                changes.append((path, new_val))
            if randint(0, 9) < 8:
                changes.append("send")
            else:
                changes.append("break")
            log.debug("<== changes=%s", changes)
            return changes

        @staticmethod
        def _get_config_changes():
            log.debug("==>")
            assert "changes_idx" in GnmiDemoServerAdapter.config
            assert "changes" in GnmiDemoServerAdapter.config
            changes = []
            idx = GnmiDemoServerAdapter.config["changes_idx"]
            if idx >= len(GnmiDemoServerAdapter.config["changes"]):
                idx = 0
            while idx < len(GnmiDemoServerAdapter.config["changes"]):
                c = GnmiDemoServerAdapter.config["changes"][idx]
                changes.append(c)
                idx += 1
                if isinstance(c, str):
                    break
            GnmiDemoServerAdapter.config["changes_idx"] = idx
            log.debug("<== changes=%s", changes)
            return changes

        def process_changes(self):
            log.debug("==>")
            add_count = 0
            # there may be more changes to same path, we cannot use map
            assert self.change_event_queue is not None
            assert len(self.change_db) == 0
            while True:
                try:
                    log.debug("getting event")
                    event = self.change_event_queue.get(timeout=1)
                    log.debug("event=%s", event)
                    if event == self.ChangeEvent.ADD:
                        # generate modifications and add them
                        with self.change_db_lock, self.adapter.db_lock:
                            if "changes" in GnmiDemoServerAdapter.config:
                                changes = self._get_config_changes()
                            else:
                                changes = self._get_random_changes()
                            send = False
                            for c in changes:
                                log.debug("processing change c=%s", c)
                                if isinstance(c, str):
                                    assert c == "send" or c == "break"
                                    if c == "send":
                                        send = True
                                    break
                                else:
                                    log.info("c=%s self.monitored_paths=%s",
                                             c, self.monitored_paths)
                                    if any(c[0].startswith(elem) for elem in
                                           self.monitored_paths):
                                        log.info("appending c=%s", c)
                                        self.change_db.append(c)
                                        if c[0] in self.adapter.demo_db:
                                            self.adapter.demo_db[c[0]] = c[1]
                                        elif c[0] in self.adapter.demo_state_db:
                                            self.adapter.demo_state_db[
                                                c[0]] = c[1]
                                        else:
                                            assert False
                        if send:
                            if len(self.change_db):
                                self.change_event_queue.put(
                                    self.ChangeEvent.SEND)
                    elif event == self.ChangeEvent.SEND:
                        # send all modified paths
                        self.put_event(self.SubscriptionEvent.SEND_CHANGES)
                    elif event == self.ChangeEvent.FINISH:
                        break
                    else:
                        log.warning("Unknown change processing event %s", event)
                except Empty:
                    # if we get timeout, let's add some modifications
                    log.debug("Empty timeout")
                    if add_count == 0:
                        add_count += 1
                        # sometimes skip add if is first from previous
                        if randint(0, 1) == 0:
                            continue
                    add_count = 0  # reset add count
                    self.change_event_queue.put(self.ChangeEvent.ADD)
            log.debug("<==")

        def add_path_for_monitoring(self, path, prefix):
            log.debug("==>")

            if self.change_event_queue is None:
                self.change_event_queue = Queue()
            path_with_prefix_str = make_xpath_path(path, prefix)
            self.monitored_paths.append(path_with_prefix_str)
            log.debug("<==")

        def start_monitoring(self):
            log.debug("==>")
            assert self.change_thread is None
            log.debug("** creating change_thread")
            self.change_thread = threading.Thread(
                target=self.process_changes)
            log.debug("** starting change_thread")
            self.change_thread.start()
            log.debug("** change_thread started")
            log.debug("<==")

        def stop_monitoring(self):
            log.debug("==>")
            # if there is an error during fetch of first subs. sample,
            # we do not start change thread
            if self.change_thread is None:
                log.warning("Cannot stop change thread! Not started?")
            else:
                log.debug("** stopping change_thread")
                self.change_event_queue.put(self.ChangeEvent.FINISH)
                self.change_thread.join()
                log.debug("** change_thread joined")
                assert self.change_event_queue.empty()
                self.change_thread = None
                self.change_event_queue = None
            self.monitored_paths = []
            log.debug("<==")

    def get_subscription_handler(self,
                                 subscription_list) -> SubscriptionHandler:
        log.debug("==>")
        handler = self.SubscriptionHandler(self, subscription_list)
        log.debug("<== handler=%s", handler)
        return handler

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
        log.debug("path_with_prefix_str=%s prefix_str=%s",
                  path_with_prefix_str, prefix_str)
        update = []

        def process_db(db):
            for p, v in db.items():
                if p.startswith(path_with_prefix_str):
                    p = p[len(prefix_str):]
                    update.append(gnmi_pb2.Update(path=make_gnmi_path(p),
                                                  val=gnmi_pb2.TypedValue(
                                                      string_val=v)))

        with self.db_lock:
            if data_type == gnmi_pb2.GetRequest.DataType.CONFIG or \
                    data_type == gnmi_pb2.GetRequest.DataType.ALL:
                process_db(self.demo_db)
            if data_type != gnmi_pb2.GetRequest.DataType.CONFIG:
                process_db(self.demo_state_db)
        log.debug("<== update=%s", update)
        return update

    def get(self, prefix, paths, data_type, use_models):
        log.debug("==> prefix=%s, paths=%s, data_type=%s, use_models=%s",
                  prefix, paths, data_type, use_models)
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
        log.info("==> prefix=%s, path=%s, val=%s", prefix, path, val)
        path_str = make_xpath_path(path, prefix)
        op = gnmi_pb2.UpdateResult.INVALID
        if path_str in self.demo_db:
            if hasattr(val, "string_val"):
                str_val = val.string_val
            else:
                # TODO
                str_val = "{}".format(val)
            with self.db_lock:
                self.demo_db[path_str] = str_val
            op = gnmi_pb2.UpdateResult.UPDATE

        log.info("==> op=%s", op)
        return op
