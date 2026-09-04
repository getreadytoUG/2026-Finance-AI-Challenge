from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NoticeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    title: str
    content: str
    created_at: datetime


class NoticeListResponse(BaseModel):
    notices: list[NoticeOut]
