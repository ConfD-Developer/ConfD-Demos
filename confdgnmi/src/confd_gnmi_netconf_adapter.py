from confd_gnmi_adapter import GnmiServerAdapter


class GnmiNetconfServerAdapter(GnmiServerAdapter):

    def get_subscription_handler(self):
        pass

    def get_instance(cls):
        return GnmiNetconfServerAdapter()

    def capabilities(self):
        return []

    def get(self, prefix, paths, data_type, use_models):
        return []

