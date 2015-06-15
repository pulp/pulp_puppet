from pulp.client.commands.consumer import bind

from pulp_puppet.common import constants


class BindCommand(bind.ConsumerBindCommand):
    def add_distributor_option(self):
        pass

    def get_distributor_id(self, kwargs):
        return constants.DISTRIBUTOR_TYPE_ID


class UnbindCommand(bind.ConsumerUnbindCommand):
    def add_distributor_option(self):
        pass

    def get_distributor_id(self, kwargs):
        return constants.DISTRIBUTOR_TYPE_ID

