from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from threading import Event

from confd_gnmi_common import *

log = logging.getLogger('confd_gnmi_adapter')


class GnmiServerAdapter(ABC):
    @dataclass
    class CapabilityModel:
        name: str
        organization: str
        version: str
        schema: str = ""

    @abstractmethod
    def capabilities(self):
        """
        Invoke capabilities oon adapter and return list of Capabilities
        :return: list of  CapabilityModel elements (schema is empty string for now TODO)
        """
        pass

    @abstractmethod
    def get(self, prefix, paths, data_type, use_models):
        """
        Invoke get operation on adapter and return list of notifications
        :param prefix:  gnmi_pb2.Path with prefix for all paths
        :param paths: list of gnmi_pb2.Path elements to get data subtrees
        :param data_type: gnmi_pb2.DataType (ALL, CONFIG, STATE, OPERATIONAL)
        :param use_models: list of gnmi_pb2.ModelData  elements to use
        :return: list of gnmi_pb2.Notification were
                  prefix - is prefix
                  alias - not set (TODO)
                  updated - list of gnmi_pb2.Update elements (one for each path)
                  delete - empty list
                  timestamp - current time in nanoseconds since Epoch
                  atomic - not set (TODO)
        Note: iteration of all paths is in adapter, so adapter can make optimization,
            if possible
        """
        pass

    @abstractmethod
    def set(self, prefix, path, val):
        """
        Set value for given path
        TODO this is simple version for initial implmentation
        To reflect fully gNMI Set,
        we should pass all delete, replace and update lists
        :param prefix: gNMI path prefix
        :param path: gNMI path
        :param val: gNMI type value
        :return: gNMI UpdateResult operation
        """
        pass


    class SubscriptionHandler(ABC):

        def __init__(self, adapter):
            self.adapter = adapter

        subscription_list = None

        class SubscriptionStreamEventType(Enum):
            GET = 0
            FINISH = 1

        subscription_stream_event_type: SubscriptionStreamEventType = None
        thread_event: Event = None

        @abstractmethod
        def make_subscription_response(self) -> gnmi_pb2.SubscribeResponse:
            """
            Create subscription response according to self.subscription_stream_event_type
            :return: gNMI subscription response
            """
            pass

        def add_subscription_list(self, subscription_list):
            """
            Add  (initial) subscription list to the handler
            This method can be called  only once (TODO  - cosntructor might be better)
            :param subscription_list: TODO
            :return:
            """
            log.debug("==> subscription_list=%s", subscription_list)
            log.info("++++++ adding subscription subscription_list=%s",
                     subscription_list)
            # TODO exception
            assert (self.subscription_list == None)
            self.subscription_list = subscription_list
            log.debug("<== self.subscription_list=%s", self.subscription_list)

        def _set_event(self, event):
            log.info("==> event=%s", event)
            assert self.subscription_list != None
            assert self.thread_event != None
            self.subscription_stream_event_type = event
            self.thread_event.clear()
            self.thread_event.set()
            log.info("<== self.subscription_stream_event_type=%s",
                     self.subscription_stream_event_type)

        def stop(self):
            """
            Stop processing of subscriptions (read generator function should end)
            """
            log.info("==>")
            # TODO exception
            self._set_event(self.SubscriptionStreamEventType.FINISH)
            log.info("<==")

        def read(self, streaming=False):
            """
            Read (get) subscription response(s) (in stream) for added subscription requests
            This should be generator function
            Response contains `notification` or `sync_response`
            :param streaming: indicates this is streaming read request (POLL, STREAM),
                            if yes, keep processing and wait for SubscriptionStreamEventType.FINISH
            :return: TODO
            """
            log.info("==>")
            # TODO exceptions
            self.subscription_stream_event_type = self.SubscriptionStreamEventType.GET
            assert self.subscription_list != None
            if streaming:
                self.thread_event = Event()
            while True:
                if self.subscription_stream_event_type == self.SubscriptionStreamEventType.GET:
                    log.debug("processing response")
                    response = self.make_subscription_response()
                    yield response
                    if not streaming:
                        break
                elif self.subscription_stream_event_type == self.SubscriptionStreamEventType.FINISH:
                    log.debug("finishing subscription read")
                    break
                elif self.subscription_stream_event_type == None:
                    log.warning(
                        "**** self.subscription_stream_event_type is None ! ****")
                    # TODO error
                    break
                else:
                    log.warning(
                        "**** self.subscription_stream_event_type not processed ! ****")
                    # TODO error
                    break
                log.debug("Waiting self.subscription_stream_event_type=%s ...",
                         self.subscription_stream_event_type)
                self.thread_event.wait()
                #TODO can there be a race condition? E.g. someone calling `stop`?
                self.thread_event.clear()
                log.debug("Woke up self.subscription_stream_event_type=%s",
                         self.subscription_stream_event_type)

            log.info("<==")

        def poll(self):
            """
            poll current state according to the subscription_list and add it to stream
            """
            log.info("==>")
            # TODO exception
            self._set_event(self.SubscriptionStreamEventType.GET)
            log.info("<==")

    @abstractmethod
    def get_subscription_handler(self) -> SubscriptionHandler:
        pass

    @classmethod
    @abstractmethod
    def get_inst(cls):
        """
        Get adapter instance
        :return: adapter instance
        """
        pass
