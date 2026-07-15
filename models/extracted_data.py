from dataclasses import dataclass
@dataclass(kw_only=True)
class ExtractedData:
    monthly_salary: float | None = None
    employer: str | None = None
    employee_name: str | None = None
    employment_duration: str | None = None
    account_number: str | None = None
    average_monthly_balance: float | None = None