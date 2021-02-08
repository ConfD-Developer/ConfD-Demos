from confd_gnmi_adapter import GnmiServerAdapter


class GnmiNetconfServerAdapter(GnmiServerAdapter):

    @classmethod
    def get_inst(cls):
        pass

    def set(self, prefix, path, val):
        pass

    def get_subscription_handler(self, subscription_list):
        pass

    def capabilities(self):
        return []

    def get(self, prefix, paths, data_type, use_models):
        return []
