from pydantic import BaseModel


class CardSpendingReportInput(BaseModel):
    month: str  # "YYYY-MM"


class CategorySpending(BaseModel):
    category: str
    amount_krw: int


class CardSpendingReportOutput(BaseModel):
    month: str
    categories: list[CategorySpending]
    total_amount_krw: int
