import itertools
from datetime import datetime, timezone

from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.status import today_kst
from app.features.savings_simulator.simulator import match_real_housing_policies, match_real_savings_policies

_key_seq = itertools.count(1)


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key=f"P{next(_key_seq)}",
        policy_name="청년내일저축계좌",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category="금융･복지･문화",
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def _match_input(**overrides) -> PolicyMatchInput:
    defaults = dict(age=29, is_married=False, annual_income_krw=40_000_000, region="서울")
    defaults.update(overrides)
    return PolicyMatchInput(**defaults)


def test_match_real_savings_policies_finds_savings_keyword_policy(db_session):
    policy = _seed_policy(db_session, policy_name="청년내일저축계좌 지원")
    result = match_real_savings_policies([policy], _match_input(), today_kst())
    assert [p.policy_key for p in result] == [policy.policy_key]


def test_match_real_savings_policies_excludes_policy_without_savings_keyword(db_session):
    policy = _seed_policy(db_session, policy_name="청년 취업 지원 사업")
    result = match_real_savings_policies([policy], _match_input(), today_kst())
    assert result == []


def test_match_real_savings_policies_applies_age_eligibility(db_session):
    policy = _seed_policy(db_session, policy_name="청년내일저축계좌", min_age=19, max_age=34)
    assert match_real_savings_policies([policy], _match_input(age=29), today_kst()) != []
    assert match_real_savings_policies([policy], _match_input(age=50), today_kst()) == []


def test_match_real_savings_policies_excludes_expired(db_session):
    policy = _seed_policy(
        db_session, policy_name="청년내일저축계좌", apply_start_ymd="20200101", apply_end_ymd="20200201"
    )
    assert match_real_savings_policies([policy], _match_input(), today_kst()) == []


def test_match_real_savings_policies_excludes_disability_only_policy_for_non_disabled(db_session):
    # matching.is_eligible을 재사용하므로 장애인/보훈대상자 전용 정책 필터링도
    # 자동으로 같이 적용돼야 한다.
    policy = _seed_policy(db_session, policy_name="장애인 자산형성 통장")
    assert match_real_savings_policies([policy], _match_input(has_disability=False), today_kst()) == []
    assert match_real_savings_policies([policy], _match_input(has_disability=True), today_kst()) != []


def test_match_real_savings_policies_dedupes_same_policy_name(db_session):
    # 2026-09-02 QA에서 발견: 온통청년 원본에 같은 이름의 정책이 설명만 다르게
    # 중복 등록된 경우가 있어(예: "청년주택드림청약통장") 화면에 두 번 떴었다.
    policy_a = _seed_policy(db_session, policy_name="청년주택드림청약통장", description="설명 A")
    policy_b = _seed_policy(db_session, policy_name="청년주택드림청약통장", description="설명 B")
    result = match_real_savings_policies([policy_a, policy_b], _match_input(), today_kst())
    assert len(result) == 1
    assert result[0].policy_name == "청년주택드림청약통장"


def test_match_real_housing_policies_splits_by_jeonse_and_purchase(db_session):
    jeonse_policy = _seed_policy(db_session, policy_name="신혼부부 전세자금 대출이자 지원", large_category="주거")
    purchase_policy = _seed_policy(db_session, policy_name="청년 주택구입 대출이자 지원", large_category="주거")
    all_policies = [jeonse_policy, purchase_policy]

    jeonse_result = match_real_housing_policies(all_policies, "jeonse", _match_input(), today_kst())
    purchase_result = match_real_housing_policies(all_policies, "purchase", _match_input(), today_kst())

    assert [p.policy_key for p in jeonse_result] == [jeonse_policy.policy_key]
    assert [p.policy_key for p in purchase_result] == [purchase_policy.policy_key]


def _signup_login(client, email="sim-user@example.com", **overrides):
    payload = {
        "email": email,
        "password": "secret123",
        "age": 29,
        "is_married": False,
        "annual_income_krw": 40_000_000,
        "region": "서울",
        "occupation": "employee",
    }
    payload.update(overrides)
    client.post("/auth/signup", json=payload)
    login = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return login.json()["access_token"]


def test_youth_leap_account_requires_auth(client):
    response = client.post(
        "/savings_simulator/youth_leap_account",
        json={"monthly_amount_krw": 400_000, "goal_years": 3, "annual_income_krw": 30_000_000},
    )
    assert response.status_code == 401


def test_youth_leap_account_lowest_income_bracket_gets_highest_matching_rate(client):
    token = _signup_login(client)
    response = client.post(
        "/savings_simulator/youth_leap_account",
        json={"monthly_amount_krw": 400_000, "goal_years": 3, "annual_income_krw": 20_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["matching_rate"] == 0.060
    assert body["benefit_diff_krw"] > 0
    assert body["policy_total_krw"] > body["market_total_krw"]


def test_youth_leap_account_over_income_cap_is_ineligible(client):
    token = _signup_login(client)
    response = client.post(
        "/savings_simulator/youth_leap_account",
        json={"monthly_amount_krw": 400_000, "goal_years": 5, "annual_income_krw": 100_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert body["matching_rate"] == 0.0
    assert body["benefit_diff_krw"] == 0
    assert body["policy_total_krw"] == body["market_total_krw"]


def test_youth_leap_account_matching_capped_at_400000_monthly():
    # HTTP 왕복 없이 계산 함수를 직접 호출해 매칭 상한(월 40만원)이 실제로 걸리는지
    # 검증한다 — 월 100만원을 넣어도 정부 매칭분은 40만원 기준으로만 계산돼야 한다.
    from app.features.savings_simulator.schemas import YouthLeapAccountInput
    from app.features.savings_simulator.simulator import simulate_youth_leap_account

    months = 3 * 12
    matching_rate = 0.060
    expected_government_total = round(400_000 * matching_rate * months)

    result = simulate_youth_leap_account(
        YouthLeapAccountInput(monthly_amount_krw=1_000_000, goal_years=3, annual_income_krw=20_000_000)
    )
    # policy_total = principal(월납입*개월+시드) + government_total + policy_interest
    # market_total = principal + market_interest 이므로, 두 total의 차이에서 이자 차이분을
    # 빼면 government_total만 남는다. 이자는 policy(비과세) - market(세후)이라 항상
    # policy_interest > market_interest이므로, diff는 government_total보다 크거나 같다.
    diff = result.policy_total_krw - result.market_total_krw
    assert diff >= expected_government_total


def test_housing_loan_requires_auth(client):
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,
        },
    )
    assert response.status_code == 401


def test_housing_loan_jeonse_within_income_cap_is_eligible(client):
    token = _signup_login(client)
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["product_name"] == "버팀목 전세자금대출(예시)"
    assert body["loan_amount_krw"] == 200_000_000  # min(250M*0.8=200M, 250M-50M=200M)
    assert body["monthly_saving_krw"] > 0


def test_housing_loan_purchase_over_income_cap_is_ineligible(client):
    token = _signup_login(client)
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "purchase",
            "target_price_krw": 400_000_000,
            "self_capital_krw": 100_000_000,
            "household_annual_income_krw": 150_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert body["monthly_saving_krw"] == 0


def test_youth_leap_account_response_includes_real_matched_policies(client, db_session):
    _seed_policy(db_session, policy_name="청년내일저축계좌 지원", min_age=19, max_age=39)
    _seed_policy(db_session, policy_name="청년 취업 지원 사업")  # 저축 키워드 없어 안 나와야 함
    token = _signup_login(client, age=29, region="서울")
    response = client.post(
        "/savings_simulator/youth_leap_account",
        json={"monthly_amount_krw": 400_000, "goal_years": 3, "annual_income_krw": 20_000_000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    matched = response.json()["matched_policies"]
    assert [p["policy_name"] for p in matched] == ["청년내일저축계좌 지원"]


def test_housing_loan_response_includes_real_matched_policies(client, db_session):
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출이자 지원", large_category="주거")
    token = _signup_login(client, age=29, region="서울")
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 250_000_000,
            "self_capital_krw": 50_000_000,
            "household_annual_income_krw": 65_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    matched = response.json()["matched_policies"]
    assert [p["policy_name"] for p in matched] == ["신혼부부 전세자금 대출이자 지원"]


def test_housing_loan_amount_never_exceeds_price_minus_self_capital(client):
    token = _signup_login(client)
    # LTV 한도(80%)보다 목표가-자기자본 차액이 더 작은 경우, 그 작은 쪽을 따라야 한다.
    response = client.post(
        "/savings_simulator/housing_loan",
        json={
            "housing_type": "jeonse",
            "target_price_krw": 200_000_000,
            "self_capital_krw": 180_000_000,
            "household_annual_income_krw": 65_000_000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    assert body["loan_amount_krw"] == 20_000_000
