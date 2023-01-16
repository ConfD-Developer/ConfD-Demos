import json
import logging
import random
import re
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
    NS_INTERFACES = "ietf-interfaces:"
    NS_IANA = "iana-if-type:"

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
        dict(name="http://tail-f.com/ns/aaa/1.1:tailf-aaa",
             organization="", version="2018-09-12"),
        dict(name="urn:ietf:params:xml:ns:yang:ietf-inet-types:ietf-inet-types",
             organization="", version="2013-07-15"),
        dict(name="urn:ietf:params:xml:ns:yang:ietf-interfaces:ietf-interfaces",
             organization="", version="2014-05-08"),
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
                            (GnmiDemoServerAdapter._nsless_xpath(path.text),
                             val.text.replace(GnmiDemoServerAdapter.NS_IANA, "")))
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
            # make interfaces alphabetically sorted
            ifs = sorted(str(i+1) for i in range(GnmiDemoServerAdapter.num_of_ifs))
            for if_id in ifs:
                if_name = f"if_{if_id}"
                state_if_name = "state_if_{}".format(if_id)
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

    @staticmethod
    def _nsless_xpath(xpath: str):
        return xpath.replace(GnmiDemoServerAdapter.NS_INTERFACES, "")

    @staticmethod
    def _get_key_from_xpath(xpath):
        key = re.search('\\[name=(.+)\\]', xpath)
        if key is not None:
            key = key.group(1)
        return key

    @staticmethod
    def _get_elem_from_xpath(xpath):
        elem = re.search(']/(.+)', xpath)
        if elem is not None:
            elem = elem.group(1)
        return elem

    @staticmethod
    def _demo_db_to_key_elem_map(db):
        log.debug("==>")
        map_db = {}
        for p, v in db.items():
            key = GnmiDemoServerAdapter._get_key_from_xpath(p)
            elem = GnmiDemoServerAdapter._get_elem_from_xpath(p)
            elem_map = {}
            if key in map_db:
                elem_map = map_db[key]
            if elem == "type":
                v = "{}{}".format(GnmiDemoServerAdapter.NS_IANA, v)
            elem_map[elem] = v
            map_db[key] = elem_map
        log.debug("<== map_db={}".format(map_db))
        return map_db

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
            log.debug("==> path=%s prefix=%s", path, prefix)

            with self.adapter.db_lock:
                updates = self.adapter.get_db_updates_for_path(path, prefix,
                                                               self.adapter.demo_db)
                # 'if' below is optimization
                if len(updates) == 0:
                    updates = self.adapter.get_db_updates_for_path(path, prefix,
                                                                   self.adapter.demo_state_db)

            log.debug("<== updates=%s", updates)
            return updates

        def get_monitored_changes(self) -> []:
            with self.change_db_lock:
                log.debug("==> self.change_db=%s", self.change_db)
                assert len(self.change_db) > 0
                update = []
                for c in self.change_db:
                    prefix_str = self.adapter._nsless_xpath(make_xpath_path(
                        gnmi_prefix=self.subscription_list.prefix))
                    p = self.adapter._nsless_xpath(c[0])
                    if p.startswith(prefix_str):
                        p = p[len(prefix_str):]
                    v = "{}{}".format(GnmiDemoServerAdapter.NS_IANA, c[1])
                    json_val = gnmi_pb2.TypedValue(
                        json_ietf_val=json.dumps(v).encode())
                    update.append(gnmi_pb2.Update(path=make_gnmi_path(p),
                                                  val=json_val))
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
                                    (path, val) = c
                                    if path[0] != '/':
                                        path = '/' + path
                                    if any(path.startswith(elem) for elem in
                                           self.monitored_paths):
                                        log.info("appending (path, val)=%s", (path, val))
                                        self.change_db.append((path, val))
                                        if path in self.adapter.demo_db:
                                            self.adapter.demo_db[path] = val
                                        elif path in self.adapter.demo_state_db:
                                            self.adapter.demo_state_db[
                                                path] = val
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
            self.monitored_paths.append(GnmiDemoServerAdapter._nsless_xpath(path_with_prefix_str))
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

    def get_db_updates_for_path(self, path, prefix, db):
        log.debug("==> path={} prefix={}".format(path, prefix))

        path_with_prefix = make_xpath_path(gnmi_path=path,
                                           gnmi_prefix=prefix)
        prefix_str = make_xpath_path(gnmi_prefix=prefix)
        log.debug("path_with_prefix=%s prefix_str=%s",
                  path_with_prefix, prefix)

        updates = []
        path_val_list = []
        map_db = self._demo_db_to_key_elem_map(db)
        ifaces = self._nsless_xpath(path_with_prefix)
        if ifaces == "/interfaces" or ifaces == "/interfaces-state":
            if list(db.keys())[0].startswith(ifaces):
                path_val_list = [
                    (path_with_prefix, {"interface": list(map_db.values())})]
        else:
            paths = []
            for p, v in db.items():
                if self._nsless_xpath(p).startswith(
                        self._nsless_xpath(path_with_prefix)):
                    paths.append(p)
            keys_done = set()
            for p in paths:
                key = self._get_key_from_xpath(p)
                if key in keys_done:
                    continue
                keys_done.add(key)
                elem_val = map_db[key]
                path_elem = self._get_elem_from_xpath(path_with_prefix)
                path = p
                if path_elem:
                    elem_val = elem_val[path_elem]
                else:
                    path = p.replace("/type", "").replace("/name", "")
                path_val_list.append((path, elem_val))

        if len(path_val_list):
            for pv in path_val_list:
                path_without_prefix = pv[0][
                                      len(self._nsless_xpath(prefix_str)):]
                val = gnmi_pb2.TypedValue(
                    json_ietf_val=json.dumps(pv[1]).encode())
                updates.append(
                    gnmi_pb2.Update(path=make_gnmi_path(path_without_prefix),
                                    val=val))
        log.debug("<== updates=%s", updates)
        return updates

    def get_updates(self, path, prefix, data_type):
        log.debug("==> path=%s prefix=%s", path, prefix)

        with self.db_lock:
            if data_type == gnmi_pb2.GetRequest.DataType.CONFIG or \
                    data_type == gnmi_pb2.GetRequest.DataType.ALL:
                updates = self.get_db_updates_for_path(path, prefix, self.demo_db)
            if data_type != gnmi_pb2.GetRequest.DataType.CONFIG:
                updates = self.get_db_updates_for_path(path, prefix,
                                                       self.demo_state_db)

        log.debug("<== updates=%s", updates)
        return updates

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

    def set_update(self, prefix, path, val):
        log.info("==> prefix=%s, path=%s, val=%s", prefix, path, val)
        path_str = make_xpath_path(path, prefix)
        op = gnmi_pb2.UpdateResult.INVALID
        if self._nsless_xpath(path_str) in self.demo_db:
            if val.string_val:
                str_val = val.string_val
            elif val.json_ietf_val:
                str_val = json.loads(val.json_ietf_val)
            elif val.json_val:
                str_val = json.loads(val.json_val)
            else:
                # TODO
                str_val = "{}".format(val)
            str_val = str_val.replace(self.NS_IANA, "")
            with self.db_lock:
                self.demo_db[path_str] = str_val
            op = gnmi_pb2.UpdateResult.UPDATE

        log.info("==> op=%s", op)
        return op

    def set(self, prefix, updates):
        log.info("==> prefix=%s, updates=%s", prefix, updates)
        ops = [(up.path, self.set_update(prefix, up.path, up.val))
               for up in updates]

        log.info("==> ops=%s", ops)
        return ops

    def delete(self, prefix, paths):
        log.info("==> prefix=%s, paths=%s", prefix, paths)
        ops = []
        # TODO
        log.info("==> ops=%s", ops)
        return ops
