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
    created_at: datetime | None


class AdminUserListResponse(BaseModel):
    users: list[AdminUserItem]
    total: int


class AdminSignupTrendPoint(BaseModel):
    date: str
    count: int


class AdminSignupTrendResponse(BaseModel):
    points: list[AdminSignupTrendPoint]
    unknown_signup_date_count: int


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


class AdminPolicyItem(BaseModel):
    policy_key: str
    policy_name: str
    description: str
    large_category: str
    status: str
    application_period: str
    region_code: str
    apply_url: str
    refreshed_at: datetime


class AdminPolicyListResponse(BaseModel):
    items: list[AdminPolicyItem]
    total: int
    page: int
    page_size: int
