import pytest

import gnmi_pb2
from confd_gnmi_client import ConfDgNMIClient
from confd_gnmi_common import make_gnmi_path
from confd_gnmi_demo_adapter import GnmiDemoServerAdapter
from confd_gnmi_server import ConfDgNMIServicer, AdapterType
from utils.utils import log, nodeid_to_path


@pytest.mark.grpc
@pytest.mark.usefixtures("fix_method")
class TestGrpc(object):

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.leaf_paths_str = ["interface[name={}if_{}]/name",
                               "interface[name={}if_{}]/type"]
        self.list_paths_str = ["interface[name={}if_{}]", "interface"]

    @staticmethod
    def mk_gnmi_if_path(path_str, if_state_str="", if_id=None):
        if if_id != None:
            path_str = path_str.format(if_state_str, if_id)
        return make_gnmi_path(path_str)

    @pytest.fixture
    def fix_method(self, request):
        log.debug("==> fixture method setup request={}".format(request))
        nodeid_path = nodeid_to_path(request.node.nodeid)
        log.debug("request.fixturenames=%s", request.fixturenames)
        if 'adapter_type' in request.fixturenames:
            adapter_type = request.getfixturevalue('adapter_type')
        else:
            adapter_type = AdapterType.DEMO
        log.debug("adapter_type=%s", adapter_type)
        self.server = ConfDgNMIServicer.serve(adapter_type=adapter_type)
        self.client = ConfDgNMIClient()
        log.debug("<== fixture method setup")
        yield
        log.debug("==> fixture method teardown (nodeid %s)" % nodeid_path)
        self.server.stop(0)
        log.debug("<== fixture method teardown")

    @pytest.mark.parametrize("adapter_type",
                             [pytest.param(AdapterType.DEMO,
                                           marks=[pytest.mark.demo]),
                              pytest.param(AdapterType.API,
                                           marks=[pytest.mark.confd])])
    def test_capabilities(self, request, adapter_type):
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
            TestGrpc.assert_update(u, path_vals[i])

    @staticmethod
    def assert_in_updates(updates, path_vals):
        assert (len(updates) >= len(path_vals))
        for pv in path_vals:
            found = False
            for u in updates:
                if u.path == pv[0] and u.val == gnmi_pb2.TypedValue(
                        string_val=pv[1]):
                    found = True
                    break
            assert found

    def _test_get_subscribe_once(self, is_subscribe=False,
                                 datatype=gnmi_pb2.GetRequest.DataType.CONFIG):
        if_state_str = prefix_state_str= ""
        if datatype == gnmi_pb2.GetRequest.DataType.STATE:
            prefix_state_str="-state"
            if_state_str = "state_"
        prefix = make_gnmi_path("/interfaces{}".format(prefix_state_str))
        if_id = 8
        leaf_paths = [TestGrpc.mk_gnmi_if_path(self.leaf_paths_str[0], if_state_str, if_id),
                      TestGrpc.mk_gnmi_if_path(self.leaf_paths_str[1], if_state_str, if_id)]
        list_paths = [TestGrpc.mk_gnmi_if_path(self.list_paths_str[0], if_state_str, if_id),
                      TestGrpc.mk_gnmi_if_path(self.list_paths_str[1], if_state_str, if_id)]

        encoding = gnmi_pb2.Encoding.BYTES

        def verify_get_updates(paths, pv_list,
                               assert_fun=TestGrpc.assert_updates):
            log.debug("paths=%s pv_list=%s", paths, pv_list)
            notification = self.client.get(prefix, paths, datatype, encoding)
            log.debug("notification=%s", notification)
            for n in notification:
                log.debug("n=%s", n)
                assert (n.prefix == prefix)
                assert_fun(n.update, pv_list)

        subscription_mode = gnmi_pb2.SubscriptionList.ONCE

        def verify_sub_updates(paths, pv_list,
                               assert_fun=TestGrpc.assert_updates):
            log.debug("paths=%s pv_list=%s", paths, pv_list)
            subscription_list = ConfDgNMIClient.make_subscription_list(prefix,
                                                                       paths,
                                                                       subscription_mode)
            responses = self.client.subscribe(subscription_list)
            log.debug("responses=%s", responses)
            for response in responses:
                log.info("response=%s", response)
                assert (response.update.prefix == prefix)
                assert_fun(response.update.update, pv_list)

        verify_updates = verify_get_updates
        if is_subscribe:
            verify_updates = verify_sub_updates

        ifname = "{}if_{}".format(if_state_str, if_id)
        verify_updates([leaf_paths[0]],
                       [(leaf_paths[0], ifname)])
        verify_updates([leaf_paths[1]],
                       [(leaf_paths[1], "gigabitEthernet")])
        verify_updates(leaf_paths, [(leaf_paths[0], ifname),
                                    (leaf_paths[1],
                                     "gigabitEthernet")])
        verify_updates([list_paths[0]],
                       [(leaf_paths[0], ifname),
                        (leaf_paths[1],
                         "gigabitEthernet")])
        pv = []
        for i in range(1, GnmiDemoServerAdapter.num_of_ifs):
            pv.append((TestGrpc.mk_gnmi_if_path(self.leaf_paths_str[0], if_state_str, i),
                       "{}if_{}".format(if_state_str, i)))
            pv.append((TestGrpc.mk_gnmi_if_path(self.leaf_paths_str[1], if_state_str, i),
                       "gigabitEthernet"))
        verify_updates([list_paths[1]], pv,
                       assert_fun=TestGrpc.assert_in_updates)

    @pytest.mark.parametrize("adapter_type",
                             [pytest.param(AdapterType.DEMO,
                                           marks=[pytest.mark.demo]),
                              pytest.param(AdapterType.API,
                                           marks=[pytest.mark.confd])])
    @pytest.mark.parametrize("data_type", ["CONFIG", "STATE"])
    def test_get(self, request, adapter_type, data_type):
        log.info("testing get")
        datatype_map = {
            "ALL": gnmi_pb2.GetRequest.DataType.ALL,
            "CONFIG": gnmi_pb2.GetRequest.DataType.CONFIG,
            "STATE": gnmi_pb2.GetRequest.DataType.STATE,
            "OPERATIONAL": gnmi_pb2.GetRequest.DataType.OPERATIONAL,
        }
        self._test_get_subscribe_once(datatype=datatype_map[data_type])

    @pytest.mark.parametrize("adapter_type",
                             [pytest.param(AdapterType.DEMO,
                                           marks=[pytest.mark.demo]),
                              pytest.param(AdapterType.API,
                                           marks=[pytest.mark.confd])])
    def test_subscribe_once(self, request, adapter_type):
        log.info("testing subscribe_once")
        self._test_get_subscribe_once(is_subscribe=True)

    @pytest.mark.parametrize("adapter_type",
                             [pytest.param(AdapterType.DEMO,
                                           marks=[pytest.mark.demo]),
                              pytest.param(AdapterType.API,
                                           marks=[pytest.mark.confd])])
    def test_set(self, request, adapter_type):
        log.info("testing set")
        if_id = 8
        prefix = make_gnmi_path("/interfaces")
        paths = [TestGrpc.mk_gnmi_if_path(self.leaf_paths_str[1], "", if_id)]
        vals = [gnmi_pb2.TypedValue(string_val="fastEther")]
        response = self.client.set(prefix, list(zip(paths, vals)))
        assert (response.prefix == prefix)
        TestGrpc.assert_set_response(response.response[0],
                                     (paths[0], gnmi_pb2.UpdateResult.UPDATE))

        # fetch with get and see value has changed
        datatype = gnmi_pb2.GetRequest.DataType.CONFIG
        encoding = gnmi_pb2.Encoding.BYTES
        notification = self.client.get(prefix, paths, datatype, encoding)
        for n in notification:
            log.debug("n=%s", n)
            assert (n.prefix == prefix)
            TestGrpc.assert_updates(n.update, [(paths[0], "fastEther")])

        # put value back
        vals = [gnmi_pb2.TypedValue(string_val="gigabitEthernet")]
        response = self.client.set(prefix, list(zip(paths, vals)))
        TestGrpc.assert_set_response(response.response[0],
                                     (paths[0], gnmi_pb2.UpdateResult.UPDATE))
