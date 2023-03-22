from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from typing import List

import gnmi_pb2

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
        Invoke capabilities on adapter and return list of Capabilities
        :return: list of  CapabilityModel elements (schema is empty string for now TODO)
        """
        pass

    @abstractmethod
    def encodings(self) -> list[int]:
        """
        Return list of encodings supported by server.
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
                  updated - list of gnmi_pb2.Update elements (one for each path)
                  delete - empty list
                  timestamp - current time in nanoseconds since Epoch
                  atomic - not set (TODO)
        Note: iteration of all paths is in adapter, so adapter can make optimization,
            if possible
        """
        pass

    @abstractmethod
    def set(self, prefix, updates):
        """
        Apply given updates.
        :param prefix: gNMI path prefix
        :param updates: gNMI updates (with path and val) to be set
        :return: gNMI UpdateResult operation
        """
        pass

    @abstractmethod
    def delete(self, prefix, paths):
        """
        Delete value(s) for given path
        TODO this is simple version for initial implementation
        To reflect fully gNMI Set,
        we should pass all delete, replace and update lists
        :param prefix: gNMI path prefix
        :param paths: list of gNMI paths to delete
        :return: gNMI UpdateResult operation
        """
        pass

    class SubscriptionHandler(ABC):

        class SubscriptionEvent(Enum):
            SAMPLE = 0
            SEND_CHANGES = 1
            FINISH = 10

        def __init__(self, adapter, subscription_list):
            self.adapter = adapter
            self.subscription_list = subscription_list
            self.read_queue = None
            if not self.is_once():
                self.read_queue = Queue()

        @abstractmethod
        def get_sample(self, path, prefix) -> List:
            """
            Create gNMI subscription updates for given path and prefix
            :param path: gNMI path for updates
            :param prefix: gNMI prefix
            #TODO do we need to return array or would just one Update be enough?
            :return: gNMI update array
            """
            pass

        @abstractmethod
        def add_path_for_monitoring(self, path, prefix):
            """
            Add this path for monitoring for changes
            Monitoring must be stopped.
            :param path:
            :param prefix:
            :return:
            """
            pass

        @abstractmethod
        def get_monitored_changes(self) -> List:
            """
            Get gNMI subscription updates for changed values
            :return: gNMI update array
            #TODO should we also return delete array
            """
            pass

        @abstractmethod
        def start_monitoring(self):
            """
            Start monitoring for changes.
            This method should be non blocking.
            :return:
            """
            pass

        @abstractmethod
        def stop_monitoring(self):
            """
            Stop monitoring changes
            (it must be started with start_monitoring)
            :return:
            """
            pass

        def is_once(self):
            """
            Return True if subscription is of such type that that only one sample
            is needed (no read thread)
            :return:
            """
            return self.subscription_list.mode == gnmi_pb2.SubscriptionList.ONCE

        def is_poll(self):
            """
            Return True if subscription is of such type (POLL) that more requests
            can be expected.
            :return:
            """
            return self.subscription_list.mode == gnmi_pb2.SubscriptionList.POLL

        def is_monitor_changes(self):
            """
            Return True if subscription is of such type that we should monitor
            changes.
            :return:
            """
            return self.subscription_list.mode == gnmi_pb2.SubscriptionList.STREAM

        def put_event(self, event):
            """
            Put event to queue of `read` function.
            :param event:
            :return:
            """
            log.info("==> event=%s", event)
            assert self.subscription_list is not None
            assert self.read_queue is not None
            self.read_queue.put(event)
            log.info("<== ")

        def stop(self):
            """
            Stop processing of subscriptions.
            Sends SubscriptionEvent.FINISH to read function.
            """
            log.info("==>")
            self.put_event(self.SubscriptionEvent.FINISH)
            log.info("<==")

        def sample(self, start_monitoring=False):
            """
            Get current sample of subscribed paths according to
            `self.subscription_list`.
            :param: start_monitoring: if True, the paths will be monitored
            for future changes
            TODO `delete` is processed and `delete` array is empty
            TODO timestamp is 0
            :return: SubscribeResponse with sample
            """
            log.debug("==> start_monitoring=%s", start_monitoring)
            update = []
            for s in self.subscription_list.subscription:
                update.extend(self.get_sample(path=s.path,
                                              prefix=self.subscription_list.prefix))
                if start_monitoring:
                    self.add_path_for_monitoring(s.path,
                                                 self.subscription_list.prefix)
            notif = gnmi_pb2.Notification(timestamp=0,
                                          prefix=self.subscription_list.prefix,
                                          update=update,
                                          delete=[],
                                          atomic=False)
            response = gnmi_pb2.SubscribeResponse(update=notif)
            if start_monitoring:
                self.start_monitoring()
            log.debug("<== response=%s", response)
            return response

        def sync_response(self):
            """
            create SubscribeResponse with  sync_response set to True
            :return: SubscribeResponse with sync_response set to True
            """
            log.debug("==> sync_response")
            response = gnmi_pb2.SubscribeResponse(sync_response=True)
            log.debug("<== response=%s", response)
            return response


        def changes(self):
            """
            Get subscription responses for changes (subscribed values).
            `update` arrays contain changes
            TODO `delete` is processed and `delete` array is empty
            TODO timestamp is 0
            :return: SubscribeResponse with changes
            """
            log.debug("==>")
            notifications = self.get_subscription_notifications()
            responses = [gnmi_pb2.SubscribeResponse(update=notif)
                         for notif in notifications]
            log.debug("<== responses=%s", responses)
            return responses

        def get_subscription_notifications(self):
            update = self.get_monitored_changes()
            notif = gnmi_pb2.Notification(timestamp=0,
                                          prefix=self.subscription_list.prefix,
                                          update=update,
                                          delete=[],
                                          atomic=False)
            return [notif]

        def read(self):
            """
            Read (get) subscription response(s) (in stream) for added
            subscription requests.
            This is generator function. For streaming subscription it contains
            event loop driven by self.read_queue (Queue object) and
            SubscriptionEvent messages.
            Response contains `notification` or `sync_response`.
            :return: nothing
            #TODO POLL mode with updates_only (send sync_response)
            :see: SubscriptionHandler.SubscriptionEvent
            """
            log.info("==>")
            # TODO exceptions
            assert self.subscription_list is not None
            if not self.is_once():
                assert self.read_queue is not None
            event = None
            first_sample = True
            while True:
                log.debug("Processing event type %s", event)
                # SAMPLE is handled in the same way as "first_sample"
                if first_sample or event == self.SubscriptionEvent.SAMPLE:
                    response = self.sample(
                        start_monitoring=self.is_monitor_changes() and first_sample)
                    yield response
                    if first_sample:
                        yield self.sync_response()
                    first_sample = False
                    if self.is_once():
                        break
                elif event == self.SubscriptionEvent.FINISH:
                    log.debug("finishing subscription read")
                    break
                elif event == self.SubscriptionEvent.SEND_CHANGES:
                    response = self.changes()
                    log.debug("Sending changes")
                    yield from response
                elif event is None:
                    log.warning("**** event is None ! ****")
                    # TODO error
                    break
                else:
                    log.warning("**** event=%s not processed ! ****", event)
                    # TODO error
                    break
                log.debug("Waiting for event")
                event = self.read_queue.get()
                log.debug("Woke up event=%s", event)
            if self.is_monitor_changes():
                self.stop_monitoring()

            log.info("<==")

        def poll(self):
            """
            Poll (invoke SubscriptionEvent.SAMPLE in read) current state
            according to the subscription_list and add it to request stream.
            """
            log.info("==>")
            # TODO exception
            self.put_event(self.SubscriptionEvent.SAMPLE)
            log.info("<==")

    @abstractmethod
    def get_subscription_handler(self,
                                 subscription_list) -> SubscriptionHandler:
        pass

    @classmethod
    @abstractmethod
    def get_adapter(cls):
        """
        Get adapter instance
        We use this, since we want to have some adapter variants as singleton.
        :return: adapter instance
        """
        pass
