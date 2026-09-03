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


# --- 2026-09-03 추가: 온통청년 원본 코드값 점검 화면 ---
# 이 값들은 별도 테이블에 저장하지 않는다 — 매 요청마다 cached_policies를 그대로
# 집계해서 보여주므로 배치가 갱신할 때마다 자동으로 최신 상태다("직접 DB에서
# 보여주면 된다", 사용자 요청). matching.py/categories.py의 정적 매핑표가 실제
# 데이터를 못 따라가는 경우(온통청년이 새 코드를 추가/변경)를 admin이 눈으로
# 확인할 수 있게 하는 게 목적.


class AdminMaritalStatusCode(BaseModel):
    value: str
    count: int
    # 2026-09-03: 온통청년 공식 코드정의서(matching.MARITAL_STATUS_LABELS)로 디코딩한
    # 값 — "기혼"/"미혼"/"제한없음" 중 하나면 채워지고, 모르는 값(빈 문자열 포함)이면
    # None이다. None인데 count가 크면 온통청년이 새 코드를 쓰기 시작했다는 신호.
    label: str | None


class AdminRegionPrefix(BaseModel):
    prefix: str
    count: int
    # matching.REGIONS 중 이 접두사에 매핑된 시/도 이름(matching.region_names_for_prefix).
    # 비어있으면 REGIONS 어디에도 안 걸리는 미확인 접두사라는 뜻 — 광주/전남 통합
    # 코드(12)처럼 온통청년이 새 코드를 쓰기 시작했을 가능성.
    mapped_region_names: list[str]


class AdminCategoryTag(BaseModel):
    value: str
    count: int
    # categories.PolicyCategoryTag Literal에 포함된 값인지 — 새 대분류 태그가
    # 추가되면 여기 없이도 카운트에는 잡히지만 policy_chat의 Literal 스키마에는
    # 없어서 LLM이 그 태그로 검색을 못 만드는 문제(categories.py 주석 참고)를
    # 눈으로 확인할 수 있다.
    is_known: bool


class AdminMidCategoryValue(BaseModel):
    value: str
    count: int


class AdminCodeValuesResponse(BaseModel):
    generated_at: datetime
    # cached_policies.refreshed_at의 최댓값 — 이 집계가 어느 시점 배치 데이터를
    # 보고 있는지 알려준다(집계 자체는 항상 즉석 계산이라 generated_at과 다를 수 있음).
    cache_last_refreshed_at: datetime | None
    total_policies: int
    marital_status_codes: list[AdminMaritalStatusCode]
    # region_code가 빈 문자열인(=전국 대상) 정책 수. 접두사 집계엔 안 잡히므로 별도로.
    nationwide_region_count: int
    region_prefixes: list[AdminRegionPrefix]
    large_category_tags: list[AdminCategoryTag]
    mid_categories: list[AdminMidCategoryValue]
