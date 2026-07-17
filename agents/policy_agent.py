class PolicyAgent:

    def __init__(self):

        self.policy = PolicyService()

    def search(

        self,

        query,

    ):

        return self.policy.retrieve_context(query)