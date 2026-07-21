from dataclasses import dataclass, field
from typing import Optional


@dataclass(kw_only=True)
class ExtractedData:
    # Salary Slip fields
    monthly_salary: Optional[float] = None
    employer: Optional[str] = None
    employee_name: Optional[str] = None
    employment_duration: Optional[str] = None
    designation: Optional[str] = None

    # Bank Statement fields
    account_number: Optional[str] = None
    average_monthly_balance: Optional[float] = None
    bank_name: Optional[str] = None

    # PAN Card fields
    pan_number: Optional[str] = None
    name_on_pan: Optional[str] = None

    # Aadhaar Card fields
    aadhaar_number: Optional[str] = None
    name_on_aadhaar: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None

    # Generic metadata
    metadata: dict = field(default_factory=dict)