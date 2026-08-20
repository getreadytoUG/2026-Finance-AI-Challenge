from pydantic import BaseModel


class SubscriptionReportInput(BaseModel):
    month: str  # "YYYY-MM"


class SubscriptionItem(BaseModel):
    service_name: str
    monthly_cost_krw: int


class SubscriptionReportOutput(BaseModel):
    month: str
    items: list[SubscriptionItem]
    total_cost_krw: int
