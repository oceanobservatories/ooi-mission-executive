__author__ = 'petercable'


class ErrorPolicy(object):
    def __init__(self, policy_dict):
        """
        An empty dict will default to an abort policy
        :param policy_dict:
        :return:
        """
        self.action = policy_dict.get('type', 'abort')
        self.count = 1
        self.backoff = 0

        if self.action == 'retry':
            self.count = policy_dict.get('count', 3)
            self.backoff = policy_dict.get('backoff', 10)
