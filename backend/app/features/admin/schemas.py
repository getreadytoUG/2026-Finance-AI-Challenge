from datetime import datetime

from pydantic import BaseModel

from app.auth.schemas import OccupationType


class AdminOverview(BaseModel):
    total_users: int
    married_users: int
    total_policies: int
    last_cache_refreshed_at: datetime | None
    policies_missing_link: int
    policies_expired: int
    nationwide_template_policies: int
    total_recommendations: int
    unread_recommendations: int


class AdminUserItem(BaseModel):
    id: int
    email: str
    age: int | None
    is_married: bool | None
    annual_income_krw: int | None
    region: str | None
    occupation: OccupationType | None


class AdminUserListResponse(BaseModel):
    users: list[AdminUserItem]
    total: int


class AdminCategoryStat(BaseModel):
    name: str
    count: int


class AdminStatusStat(BaseModel):
    status: str
    count: int


class AdminPolicyStatsResponse(BaseModel):
    total: int
    by_category: list[AdminCategoryStat]
    by_status: list[AdminStatusStat]
    missing_link_count: int
    nationwide_template_count: int
    last_refreshed_at: datetime | None


class AdminRefreshResponse(BaseModel):
    upserted: int
