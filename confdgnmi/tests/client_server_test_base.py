import subprocess
import threading
import xml.etree.cElementTree as ET
from time import sleep

import gnmi_pb2
import pytest

from confd_gnmi_client import ConfDgNMIClient
from confd_gnmi_common import make_gnmi_path, get_data_type, \
    make_formatted_path
from confd_gnmi_demo_adapter import GnmiDemoServerAdapter
from confd_gnmi_server import AdapterType, ConfDgNMIServicer
from utils.utils import log, nodeid_to_path


@pytest.mark.grpc
@pytest.mark.usefixtures("fix_method")
class GrpcBase(object):

    @pytest.fixture
    def fix_method(self, request):
        log.debug("==> fixture method setup request={}".format(request))
        # set_logging_level(logging.DEBUG)
        nodeid_path = nodeid_to_path(request.node.nodeid)
        log.debug("request.fixturenames=%s", request.fixturenames)
        self.set_adapter_type()
        self.server = ConfDgNMIServicer.serve(adapter_type=self.adapter_type)
        self.client = ConfDgNMIClient()
        log.debug("<== fixture method setup")
        yield
        log.debug("==> fixture method teardown (nodeid %s)" % nodeid_path)
        self.client.close()
        self.server.stop(0)
        self.server.wait_for_termination()
        log.debug("<== fixture method teardown")

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.leaf_paths_str = ["interface[name={}if_{}]/name",
                               "interface[name={}if_{}]/type"]
        self.list_paths_str = ["interface[name={}if_{}]", "interface"]

    @staticmethod
    def mk_gnmi_if_path(path_str, if_state_str="", if_id=None):
        if if_id is not None:
            path_str = path_str.format(if_state_str, if_id)
        return make_gnmi_path(path_str)

    def test_capabilities(self, request):
        log.info("testing capabilities")
        supported_models = self.client.get_capabilities()

        def capability_supported(cap):
            supported = False
            for s in supported_models:
                if s.name == cap['name'] and s.organization == cap[
                    'organization'] and s.version == cap['version']:
                    log.debug("capability cap=%s found in s=%s", cap, s)
                    supported = True
                    break
            return supported

        # check if selected capabilities are supported
        for cap in GnmiDemoServerAdapter.capability_list:
            assert (capability_supported(cap))

    @staticmethod
    def assert_update(update, path_val):
        assert (update.path == path_val[0])
        assert (update.val == gnmi_pb2.TypedValue(string_val=path_val[1]))

    @staticmethod
    def assert_set_response(response, path_op):
        assert (response.path == path_op[0])
        assert (response.op == path_op[1])

    @staticmethod
    def assert_updates(updates, path_vals):
        assert (len(updates) == len(path_vals))
        for i, u in enumerate(updates):
            GrpcBase.assert_update(u, path_vals[i])

    @staticmethod
    def assert_in_updates(updates, path_vals):
        log.debug("==> updates=%s path_vals=%s", updates, path_vals)
        assert (len(updates) >= len(path_vals))
        for pv in path_vals:
            found = False
            for u in updates:
                if u.path == pv[0] and u.val == gnmi_pb2.TypedValue(
                        string_val=pv[1]):
                    found = True
                    break
            assert found
        log.debug("<==")

    def verify_get_response_updates(self, prefix, paths, path_value,
                                    datatype, encoding, assert_fun=None):
        if assert_fun is None:
            assert_fun = GrpcBase.assert_updates
        log.debug("prefix=%s paths=%s pv_list=%s datatype=%s encoding=%s",
                  prefix, paths, path_value, datatype, encoding)
        notification = self.client.get(prefix, paths, datatype, encoding)
        log.debug("notification=%s", notification)
        for n in notification:
            log.debug("n=%s", n)
            assert (n.prefix == prefix)
            assert_fun(n.update, path_value)

    def verify_sub_sub_response_updates(self, prefix, paths, path_value,
                                        assert_fun=None,
                                        subscription_mode=gnmi_pb2.SubscriptionList.ONCE,
                                        poll_interval=0,
                                        poll_count=0, read_count=-1):
        if assert_fun is None:
            assert_fun = GrpcBase.assert_updates
        log.debug("paths=%s path_value=%s", paths, path_value)
        response_count = 0
        thread_exception = False
        pv_idx = 0
        for pv in path_value:
            if not isinstance(pv, list):
                pv_idx = -1
                break
        log.debug("pv_idx=%s", pv_idx)

        def read_subscribe_responses(responses, read_count=-1):
            nonlocal response_count, pv_idx, thread_exception
            try:
                for response in responses:
                    response_count += 1
                    log.debug("response=%s response_count=%i", response,
                              response_count)
                    assert (response.update.prefix == prefix)
                    pv_to_check = path_value
                    if pv_idx != -1:
                        assert pv_idx < len(path_value)
                        pv_to_check = path_value[pv_idx]
                        pv_idx += 1
                    if len(pv_to_check) > 0:  # skip empty arrays
                        assert_fun(response.update.update, pv_to_check)
                    log.info("response_count=%i", response_count)
                    if read_count > 0:
                        read_count -= 1
                        if read_count == 0:
                            log.info("read count reached")
                            break
                assert read_count == -1 or read_count == 0
            except Exception as e:
                log.exception(e)
                thread_exception = True

        read_thread = read_subscribe_responses
        subscription_list = \
            ConfDgNMIClient.make_subscription_list(prefix,
                                                   paths,
                                                   subscription_mode)

        responses = self.client.subscribe(subscription_list,
                                          read_thread=read_thread,
                                          poll_interval=poll_interval,
                                          poll_count=poll_count,
                                          read_count=read_count)

        assert thread_exception is False
        log.debug("responses=%s", responses)
        if poll_count:
            assert (poll_count + 1 == response_count)

    def _test_get_subscribe(self, is_subscribe=False,
                            datatype=gnmi_pb2.GetRequest.DataType.CONFIG,
                            subscription_mode=gnmi_pb2.SubscriptionList.ONCE,
                            poll_interval=0,
                            poll_count=0, read_count=-1):

        kwargs = {"assert_fun": GrpcBase.assert_updates}
        if_state_str = prefix_state_str = ""
        if datatype == gnmi_pb2.GetRequest.DataType.STATE:
            prefix_state_str = "-state"
            if_state_str = "state_"
        prefix = make_gnmi_path("/interfaces{}".format(prefix_state_str))
        kwargs["prefix"] = prefix
        if_id = 8
        leaf_paths = [
            GrpcBase.mk_gnmi_if_path(self.leaf_paths_str[0], if_state_str,
                                     if_id),
            GrpcBase.mk_gnmi_if_path(self.leaf_paths_str[1], if_state_str,
                                     if_id)]
        list_paths = [
            GrpcBase.mk_gnmi_if_path(self.list_paths_str[0], if_state_str,
                                     if_id),
            GrpcBase.mk_gnmi_if_path(self.list_paths_str[1], if_state_str,
                                     if_id)]
        ifname = "{}if_{}".format(if_state_str, if_id)

        if is_subscribe:
            verify_response_updates = self.verify_sub_sub_response_updates
            kwargs["subscription_mode"] = subscription_mode
            kwargs["poll_interval"] = poll_interval
            kwargs["poll_count"] = poll_count
            kwargs["read_count"] = read_count
        else:
            encoding = gnmi_pb2.Encoding.BYTES
            verify_response_updates = self.verify_get_response_updates
            kwargs["datatype"] = datatype
            kwargs["encoding"] = encoding

        kwargs["paths"] = [leaf_paths[0]]
        kwargs["path_value"] = [(leaf_paths[0], ifname)]
        verify_response_updates(**kwargs)
        kwargs["paths"] = [leaf_paths[1]]
        kwargs["path_value"] = [(leaf_paths[1], "gigabitEthernet")]
        verify_response_updates(**kwargs)
        kwargs["paths"] = leaf_paths
        kwargs["path_value"] = [(leaf_paths[0], ifname),
                                (leaf_paths[1], "gigabitEthernet")]
        verify_response_updates(**kwargs)
        kwargs["paths"] = [list_paths[0]]
        kwargs["path_value"] = [(leaf_paths[0], ifname), (leaf_paths[1],
                                                          "gigabitEthernet")]
        verify_response_updates(**kwargs)
        pv = []
        for i in range(1, GnmiDemoServerAdapter.num_of_ifs):
            pv.append((GrpcBase.mk_gnmi_if_path(self.leaf_paths_str[0],
                                                if_state_str, i),
                       "{}if_{}".format(if_state_str, i)))
            pv.append((GrpcBase.mk_gnmi_if_path(self.leaf_paths_str[1],
                                                if_state_str, i),
                       "gigabitEthernet"))
        kwargs["paths"] = [list_paths[1]]
        kwargs["path_value"] = pv
        kwargs["assert_fun"] = GrpcBase.assert_in_updates
        verify_response_updates(**kwargs)
        pass

    @pytest.mark.parametrize("data_type", ["CONFIG", "STATE"])
    def test_get(self, request, data_type):
        log.info("testing get")
        self._test_get_subscribe(datatype=get_data_type(data_type))

    @pytest.mark.parametrize("data_type", ["CONFIG", "STATE"])
    def test_subscribe_once(self, request, data_type):
        log.info("testing subscribe_once")
        self._test_get_subscribe(is_subscribe=True,
                                 datatype=get_data_type(data_type))

    @pytest.mark.long
    @pytest.mark.parametrize("data_type", ["CONFIG", "STATE"])
    @pytest.mark.parametrize("poll_args",
                             [(0.2, 2), (0.5, 2), (1, 2), (0.2, 10)])
    def test_subscribe_poll(self, request, data_type, poll_args):
        log.info("testing subscribe_poll")
        self._test_get_subscribe(is_subscribe=True,
                                 datatype=get_data_type(data_type),
                                 subscription_mode=gnmi_pb2.SubscriptionList.POLL,
                                 poll_interval=poll_args[0],
                                 poll_count=poll_args[1])

    def _send_change_list_to_confd_thread(self, prefix_str, changes_list):
        log.info("==>")
        log.debug("prefix_str=%s change_list=%s", prefix_str, changes_list)
        oper_cmd = ""
        config_cmd = ""
        sleep(1)

        def send_to_confd(config_cmd, oper_cmd):
            def confd_cmd_subprocess(confd_cmd):
                log.info("confd_cmd=%s", confd_cmd)
                subprocess.run(confd_cmd, shell=True, check=True)

            log.info("config_cmd=%s oper_cmd=%s", config_cmd, oper_cmd)
            if config_cmd != "":
                confd_cmd = "confd_cmd -c \"{}\"".format(
                    config_cmd)
                confd_cmd_subprocess(confd_cmd)
            if oper_cmd != "":
                confd_cmd = "confd_cmd -o -fr -c \"set {}\"".format(
                    oper_cmd)
                confd_cmd_subprocess(confd_cmd)

        for c in changes_list:
            log.debug("processing c=%s", c)
            if isinstance(c, str) and c == "send":
                send_to_confd(config_cmd, oper_cmd)
                oper_cmd = config_cmd = ""
                sleep(1)
            else:
                path_prefix = make_gnmi_path(prefix_str)
                path = make_gnmi_path(c[0])
                cmd = "{} {}".format(
                    make_formatted_path(path, gnmi_prefix=path_prefix),
                    c[1])
                if "state" in prefix_str:
                    oper_cmd += "{} ".format(cmd)
                else:
                    config_cmd += "mset {};".format(cmd)
        log.info("<==")

    @staticmethod
    def _changes_list_to_pv(changes_list):
        '''
        Return path_value_list created from changes_list.
        :param changes_list:
        :return:
        '''
        path_value = []
        pv_idx = 0
        for c in changes_list:
            if isinstance(c, str):
                if c == "send":
                    pv_idx += 1
            else:
                if len(path_value) < pv_idx + 1:
                    path_value.append([])
                path_value[pv_idx].append((make_gnmi_path(c[0]), c[1]))
        log.debug("path_value=%s", path_value)
        return path_value

    @staticmethod
    def _changes_list_to_xml(changes_list, prefix_str):
        demo = ET.Element("demo")
        sub = ET.SubElement(demo, "subscription")
        stream = ET.SubElement(sub, "STREAM")
        changes = ET.SubElement(stream, "changes")
        for c in changes_list:
            el = ET.SubElement(changes, "element")
            if isinstance(c, str):
                el.text = c
            else:
                ET.SubElement(el, "path").text = "{}/{}".format(prefix_str,
                                                                c[0])
                ET.SubElement(el, "val").text = c[1]
        xml_str = ET.tostring(demo, encoding='unicode')
        log.debug("xml_str=%s", xml_str)
        return xml_str

    @pytest.mark.long
    @pytest.mark.parametrize("data_type", ["CONFIG", "STATE"])
    def test_subscribe_stream(self, request, data_type):
        log.info("testing subscribe_stream")
        if_state_str = prefix_state_str = ""
        if data_type == "STATE":
            prefix_state_str = "-state"
            if_state_str = "state_"

        changes_list = [
            ("interface[name={}if_5]/type".format(if_state_str),
             "fastEther"),
            ("interface[name={}if_6]/type".format(if_state_str),
             "fastEther"),
            "send",
            ("interface[name={}if_5]/type".format(if_state_str),
             "gigabitEthernet"),
            ("interface[name={}if_6]/type".format(if_state_str),
             "gigabitEthernet"),
            "send",
        ]
        if data_type == "STATE" and self.adapter_type == AdapterType.API:
            # TODO state `confd_cmd` is not transactional, so we need to check
            # every item - add 'send' after each item (or fix checking method?)
            new_change_list = []
            for c in [x for x in changes_list if x != "send"]:
                new_change_list.append(c)
                new_change_list.append("send")
            changes_list = new_change_list
        log.info("change_list=%s", changes_list)

        path_value = [[]]  # empty element means no check
        path_value.extend(self._changes_list_to_pv(changes_list))

        prefix_str = "/interfaces{}".format(prefix_state_str)
        prefix = make_gnmi_path(prefix_str)
        paths = [GrpcBase.mk_gnmi_if_path(self.list_paths_str[1], if_state_str,
                                          "N/A")]

        kwargs = {"assert_fun": GrpcBase.assert_in_updates}
        kwargs["prefix"] = prefix
        kwargs["paths"] = paths
        kwargs["path_value"] = path_value
        kwargs["subscription_mode"] = gnmi_pb2.SubscriptionList.STREAM
        kwargs["read_count"] = len(path_value)
        kwargs["assert_fun"] = GrpcBase.assert_in_updates

        if self.adapter_type == AdapterType.DEMO:
            GnmiDemoServerAdapter.load_config_string(
                self._changes_list_to_xml(changes_list, prefix_str))
        if self.adapter_type == AdapterType.API:
            sleep(1)
            thr = threading.Thread(
                target=self._send_change_list_to_confd_thread,
                args=(prefix_str, changes_list,))
            thr.start()

        self.verify_sub_sub_response_updates(**kwargs)

        if self.adapter_type == AdapterType.API:
            thr.join()
            # TODO reset ConfD DB to original values

    def test_set(self, request):
        log.info("testing set")
        if_id = 8
        prefix = make_gnmi_path("/interfaces")
        paths = [GrpcBase.mk_gnmi_if_path(self.leaf_paths_str[1], "", if_id)]
        vals = [gnmi_pb2.TypedValue(string_val="fastEther")]
        response = self.client.set(prefix, list(zip(paths, vals)))
        assert (response.prefix == prefix)
        GrpcBase.assert_set_response(response.response[0],
                                     (paths[0], gnmi_pb2.UpdateResult.UPDATE))

        # fetch with get and see value has changed
        datatype = gnmi_pb2.GetRequest.DataType.CONFIG
        encoding = gnmi_pb2.Encoding.BYTES
        notification = self.client.get(prefix, paths, datatype, encoding)
        for n in notification:
            log.debug("n=%s", n)
            assert (n.prefix == prefix)
            GrpcBase.assert_updates(n.update, [(paths[0], "fastEther")])

        # put value back
        vals = [gnmi_pb2.TypedValue(string_val="gigabitEthernet")]
        response = self.client.set(prefix, list(zip(paths, vals)))
        GrpcBase.assert_set_response(response.response[0],
                                     (paths[0], gnmi_pb2.UpdateResult.UPDATE))
