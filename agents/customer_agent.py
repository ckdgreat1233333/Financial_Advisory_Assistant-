from services.customer_service import CustomerService


class CustomerAgent:

    def __init__(self):
        self.customer = CustomerService()

    def answer(
        self,
        question,
        mode="friendly",
    ):
        return self.customer.answer(
            question,
            mode,
        )