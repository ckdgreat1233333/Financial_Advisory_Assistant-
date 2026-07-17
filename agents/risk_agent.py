class RiskAgent:

    def __init__(self):

        self.service = RiskService()

    def evaluate(

        self,

        application,

        extracted_data,

    ):

        return self.service.evaluate(

            application,

            extracted_data,

        )